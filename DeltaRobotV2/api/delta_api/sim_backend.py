"""Süreç içi simülasyon arka ucu (F6 simülasyon kiralama): kullanıcı başına bir oturum.

ROS yığınıyla AYNI kodu kullanır: delta_core kinematiği, planlayıcı (`planning.py`), 1. güvenlik
kapısı (`safety.validate`: G1–G5, G14) ve tabla ikizi (`board_game.py`). Böylece kullanıcı gerçek
sistemdeki ret nedenlerini görür; ROS yığını kullanıcı başına çoğaltılmaz. Pi'deki son kapı ve
bekçi burada yoktur (simülasyonda sunucu ile kenar arası ağ yok); yörünge 1. kapıdan geçtiyse
örnekleri gerçek zamanlı (ya da `time_scale` ile hızlı) oynatılır.
"""

from __future__ import annotations

import asyncio
import contextlib
import itertools
import math
import random

import numpy as np
from delta_server.board_game import (
    BoardTwin,
    Geometry,
    apply_move,
    best_move,
    initial_cells,
    winner,
)
from delta_server.planning import (
    QUINTIC_PEAK_ACC,
    QUINTIC_PEAK_VEL,
    auto_duration,
    plan_line,
    quintic,
    sample_times,
)
from delta_server.robot import Robot
from delta_server.safety import CORE_REASON_REQUIREMENT, Limits, min_tool_z_mm, validate

from delta_api.backend import (
    DEFAULT_LIMITS,
    DEFAULT_WORKSPACE,
    Backend,
    MoveOutcome,
    RobotState,
    robot_info,
)

AUTO_MARGIN = 1.25
AUTO_MAX_MOVES = 20  # beraberlik döngüsünü keser
AUTO_DEPTH = 4  # planlayıcının auto_duration_margin değeriyle aynı (server.yaml)
_ids = itertools.count(1)


class _AutoAbort(Exception):
    """Otomatik oyunda hareket reddedildi ya da tamamlanmadı."""


def _new_auto() -> dict:
    return {"status": "idle", "turn": "X", "winner": None, "reason": None, "moves": []}


def limits_for(robot: Robot) -> Limits:
    """server.yaml'daki varsayılan G5 sınırları + robot.yaml'dan G14 (ROS yığınıyla aynı)."""
    return Limits(
        max_vel_deg_s=DEFAULT_LIMITS["max_joint_velocity_deg_s"],
        max_acc_deg_s2=DEFAULT_LIMITS["max_joint_acceleration_deg_s2"],
        rate_hz=100.0,
        min_tool_z_mm=min_tool_z_mm(robot.spec),
        tool_offset_mm=float(robot.spec["kinematics"]["ee_offset"]),
    )


class SimBackend(Backend):
    """Tek kullanıcının simülasyon oturumu: kinematik + 1. kapı + oynatma + tabla ikizi."""

    def __init__(self, robot: Robot, time_scale: float = 1.0) -> None:
        super().__init__()
        self.robot = robot
        self.limits = limits_for(robot)
        self.time_scale = float(time_scale)
        self.twin = BoardTwin(Geometry.from_spec(robot.spec))
        home = robot.home_mm
        th = robot.kin.inverse(home)
        if th is None:
            raise ValueError("başlangıç pozu erişilemez")
        self._s = RobotState(
            state="IDLE", edge_connected=True, voltages=[12.0] * 3, temps_c=[30.0] * 3
        )
        self._set_angles(list(th))
        self._play_task: asyncio.Task | None = None
        self._auto_task: asyncio.Task | None = None
        self._auto = _new_auto()
        self._rng = random.Random()

    # --- yardımcılar -----------------------------------------------------------------------
    def _set_angles(self, th: list[float]) -> None:
        s = self._s
        s.angles_deg = [round(float(a), 3) for a in th]
        p = self.robot.kin.forward(tuple(float(a) for a in th))
        s.position_mm = [round(float(v), 3) for v in p] if p is not None else None

    def _tip(self):
        p = self._s.position_mm
        return None if p is None else (p[0], p[1], p[2] - self.limits.tool_offset_mm)

    def _twin_step(self) -> None:
        self.twin.update(self._tip(), self._s.magnet)

    # --- arayüz ----------------------------------------------------------------------------
    def info(self) -> dict:
        return robot_info(
            self.robot.spec, list(self.robot.home_mm), DEFAULT_WORKSPACE, DEFAULT_LIMITS
        )

    def state(self) -> RobotState:
        return self._s

    async def move(self, x, y, z, duration_s, wait) -> MoveOutcome:
        s = self._s
        if s.state != "IDLE":
            return MoveOutcome(
                False, requirement="DURUM", reason=f"robot hazır değil: durum {s.state}"
            )
        start = tuple(s.position_mm)
        target = (float(x), float(y), float(z))
        lim = self.limits
        if not duration_s:
            duration_s = auto_duration(
                self.robot.kin,
                start,
                target,
                lim.rate_hz,
                lim.max_vel_deg_s,
                lim.max_acc_deg_s2,
                AUTO_MARGIN,
            )
        try:
            plan = plan_line(self.robot.kin, start, target, float(duration_s), lim.rate_hz)
        except ValueError as e:
            return MoveOutcome(False, requirement="G4", reason=f"G4: istek geçersiz: {e}")
        return await self._run_plan(plan.thetas_deg, plan.times, plan.points_mm, wait)

    async def _run_plan(self, thetas, times, cart, wait: bool) -> MoveOutcome:
        """1. kapı (safety.validate) + oynatma; move ve move_joints ortak yolu."""
        s, lim = self._s, self.limits
        tid = f"sim-{next(_ids):05d}"
        v = validate(
            self.robot.kin, thetas, times, lim, cartesian_mm=cart, current_deg=s.angles_deg
        )
        if not v.accepted:
            self.emit(
                {
                    "type": "event",
                    "accepted": False,
                    "requirement": v.requirement,
                    "reason": v.message,
                    "trajectory_id": tid,
                }
            )
            return MoveOutcome(False, requirement=v.requirement, reason=v.message)
        s.state, s.trajectory_id = "RUNNING", tid
        self._play_task = asyncio.create_task(self._play(np.asarray(thetas), lim.rate_hz))
        if not wait:
            return MoveOutcome(True, trajectory_id=tid, done=False)
        await self._play_task
        ok = s.state == "IDLE"
        return MoveOutcome(
            True,
            trajectory_id=tid,
            done=ok,
            position_mm=list(s.position_mm),
            reason=None if ok else f"yörünge tamamlanmadı: {s.state}",
        )

    async def _play(self, thetas: np.ndarray, rate_hz: float) -> None:
        """Örnekleri sırayla uygular; dur komutu (HOLDING) oynatmayı keser."""
        dt = 1.0 / rate_hz / self.time_scale
        loop = asyncio.get_running_loop()
        t0 = loop.time()
        n = len(thetas)
        k = 0
        while k < n:
            if self._s.state != "RUNNING":
                return
            self._set_angles(list(thetas[k]))
            self._twin_step()
            k += 1
            # Gerçek zamana yetiş: geride kalınırsa örnek atlanmaz, bekleme kısalır.
            delay = t0 + k * dt - loop.time()
            if delay > 0:
                await asyncio.sleep(delay)
            elif k % 20 == 0:
                await asyncio.sleep(0)
        self._s.state = "IDLE"

    # --- F6: eklem uzayında hareket, FK/IK önizleme ------------------------------------------
    async def move_joints(self, angles_deg, duration_s, wait) -> MoveOutcome:
        """Eklem uzayında quintic yörünge; kartezyen yol eklemlerden gelir, aynı 1. kapı."""
        s, lim = self._s, self.limits
        if s.state != "IDLE":
            return MoveOutcome(
                False, requirement="DURUM", reason=f"robot hazır değil: durum {s.state}"
            )
        th0 = np.asarray(s.angles_deg, dtype=float)
        th1 = np.asarray(angles_deg, dtype=float)
        d = float(np.max(np.abs(th1 - th0)))
        if not duration_s:
            t_v = QUINTIC_PEAK_VEL * d / lim.max_vel_deg_s
            t_a = math.sqrt(QUINTIC_PEAK_ACC * d / lim.max_acc_deg_s2)
            duration_s = max(t_v, t_a, 2.0 / lim.rate_hz) * AUTO_MARGIN
        times = sample_times(float(duration_s), lim.rate_hz)
        u = quintic(times / times[-1]) if times[-1] > 0 else np.ones_like(times)
        thetas = th0 + np.outer(u, th1 - th0)
        return await self._run_plan(thetas, times, None, wait)

    def _point_verdict(self, angles, p) -> dict | None:
        """Statik nokta denetimi (G1, G2, G3, G14); geçerse None."""
        kin, lim = self.robot.kin, self.limits
        if p is None:
            return {"requirement": "G3", "reason": "G3: erişilemez (ileri kinematik çözümsüz)"}
        ok, arm, why = kin.check_limits(tuple(angles), tuple(p))
        if not ok:
            req = CORE_REASON_REQUIREMENT.get(why, "G3")
            kol = f" (kol {arm + 1})" if arm >= 0 else ""
            return {"requirement": req, "reason": f"{req}: {why}{kol}"}
        tip = float(p[2]) - lim.tool_offset_mm
        if lim.min_tool_z_mm is not None and tip < lim.min_tool_z_mm - 1e-6:
            return {
                "requirement": "G14",
                "reason": f"G14: uç tabla/zemin yüzeyinin altına iner: z_uç {tip:.1f} mm < "
                f"{lim.min_tool_z_mm:g} mm",
            }
        return None

    def fk(self, angles_deg) -> dict:
        th = [float(a) for a in angles_deg]
        lo, hi = self.robot.kin.params.motor_limit_min, self.robot.kin.params.motor_limit_max
        for j, a in enumerate(th):
            if not lo <= a <= hi:
                return {
                    "ok": False,
                    "position_mm": None,
                    "requirement": "G1",
                    "reason": f"G1: motor açı limiti (kol {j + 1}: {a:g}° ∉ [{lo:g}, {hi:g}])",
                }
        p = self.robot.kin.forward(tuple(th))
        bad = self._point_verdict(th, p)
        pos = [round(float(v), 3) for v in p] if p is not None else None
        if bad:
            return {"ok": False, "position_mm": pos, **bad}
        return {"ok": True, "position_mm": pos}

    def ik(self, x: float, y: float, z: float) -> dict:
        p = (float(x), float(y), float(z))
        th = self.robot.kin.inverse(p)
        if th is None:
            ok, arm, why = self.robot.kin.check_point(p)
            req = CORE_REASON_REQUIREMENT.get(why, "G3")
            return {
                "ok": False,
                "angles_deg": None,
                "requirement": req,
                "reason": f"{req}: {why or 'erişilemez'}",
            }
        th = [round(float(a), 3) for a in th]
        bad = self._point_verdict(th, p)
        if bad:
            return {"ok": False, "angles_deg": th, **bad}
        return {"ok": True, "angles_deg": th}

    # --- F6: otomatik mod (robot kendi kendine tic-tac-toe oynar) -----------------------------
    @property
    def auto_running(self) -> bool:
        return self._auto_task is not None and not self._auto_task.done()

    async def auto_start(self) -> None:
        if self.auto_running:
            return
        if self._s.state in ("HOLDING", "TORQUE_OFF"):
            await self.torque(True)
        if self.twin.held is not None:
            self._s.magnet = False
            self._twin_step()
        cells = self.twin.cells()
        if winner(cells) is not None or self._auto["status"] in ("finished", "error"):
            self.twin.reset()
            self._auto = _new_auto()
        if self.twin.cells() == initial_cells() and self._auto["moves"]:
            self._auto = _new_auto()
        self._auto.update(status="playing", reason=None)
        self._auto_task = asyncio.create_task(self._auto_play())

    async def auto_stop(self) -> None:
        task = self._auto_task
        if task is not None and not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            self._auto.update(status="stopped")
        if self._s.state == "RUNNING":
            await self.stop()
        if self._s.state == "HOLDING":
            await self.torque(True)

    async def shutdown(self) -> None:
        await self.auto_stop()

    async def _auto_play(self) -> None:
        a = self._auto
        try:
            cells = self.twin.cells()
            while winner(cells) is None and len(a["moves"]) < AUTO_MAX_MOVES:
                m = best_move(cells, a["turn"], depth=AUTO_DEPTH, rng=self._rng)
                if m is None:
                    break
                await self._pick_place(*m)
                expected = apply_move(cells, m)
                cells = self.twin.cells()
                if cells != expected:
                    a.update(status="error", reason=f"tabla beklenen gibi değil: {cells}")
                    return
                a["moves"].append(
                    {"n": len(a["moves"]) + 1, "kind": a["turn"], "from": m[0], "to": m[1]}
                )
                a["turn"] = "O" if a["turn"] == "X" else "X"
            a.update(status="finished", winner=winner(cells))
        except _AutoAbort as e:
            a.update(status="error", reason=str(e))

    async def _pick_place(self, src: int, dst: int) -> None:
        g = self.twin.geo
        for step, (x, y, z) in g.pick_place_path(src, dst):
            if step == "move":
                r = await self.move(x, y, z, None, True)
                if not (r.accepted and r.done):
                    raise _AutoAbort(r.reason or "hareket tamamlanmadı")
            else:
                await self.magnet(step == "magnet_on")

    def board(self) -> dict | None:
        d = self.twin.to_dict()
        d["auto"] = {k: (list(v) if isinstance(v, list) else v) for k, v in self._auto.items()}
        return d

    async def magnet(self, on: bool) -> bool:
        # Kenarla aynı kural: tork kapalıyken mıknatıs açılamaz.
        if on and self._s.state not in ("IDLE", "RUNNING", "HOLDING"):
            return False
        self._s.magnet = bool(on)
        self._twin_step()
        return True

    async def torque(self, on: bool) -> bool:
        if on:
            if self._s.state in ("TORQUE_OFF", "HOLDING"):
                self._s.state = "IDLE"
        else:
            self._s.state = "TORQUE_OFF"
            self._s.magnet = False
            self._twin_step()
        return True

    async def stop(self) -> bool:
        task = self._auto_task
        if task is not None and not task.done() and asyncio.current_task() is not task:
            task.cancel()  # dur komutu otomatik oyunu da keser
            self._auto.update(status="stopped")
        if self._s.state == "RUNNING":
            self._s.state = "HOLDING"
        return True

    async def board_reset(self) -> bool:
        if self.auto_running:
            return False
        self.twin.reset()
        self._auto = _new_auto()
        return True
