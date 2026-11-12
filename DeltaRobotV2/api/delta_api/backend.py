"""Robot arka ucu arayüzü ve ROS'suz sahte arka uç (testler ve web geliştirme için).

API robotla yalnız bu arayüz üzerinden konuşur. Gerçek sistemde `ros_backend.RosBackend`
(ROS2 yığını + kenar), testlerde `FakeBackend` kullanılır. Güvenlik kararları arka uçta değil
ROS yığınında (1. kapı) ve Pi'de (son kapı) verilir; sahte arka uç yalnız benzetir.
"""

from __future__ import annotations

import asyncio
import math
import re
import time
from dataclasses import asdict, dataclass, field

STATES = ("IDLE", "RUNNING", "HOLDING", "TORQUE_OFF", "FAULT", "ESTOP", "DISCONNECTED")
_REQ_RE = re.compile(r"^\s*(G\d+)\b")


def requirement_of(reason: str) -> str:
    """Ret nedenindeki gereksinim kodu ("G2: ..." -> "G2"); yoksa "DURUM"."""
    m = _REQ_RE.match(reason or "")
    return m.group(1) if m else "DURUM"


@dataclass
class RobotState:
    state: str = "DISCONNECTED"
    angles_deg: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    position_mm: list[float] | None = None
    magnet: bool = False
    temps_c: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    loads: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    voltages: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    trajectory_id: str | None = None
    edge_connected: bool = False

    def to_dict(self, job_id: str | None = None) -> dict:
        d = asdict(self)
        d["job_id"] = job_id
        return d


@dataclass
class MoveOutcome:
    accepted: bool
    trajectory_id: str | None = None
    done: bool = False
    position_mm: list[float] | None = None
    requirement: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict:
        if not self.accepted:
            return {
                "accepted": False,
                "requirement": self.requirement,
                "reason": self.reason,
            }
        d = {
            "accepted": True,
            "trajectory_id": self.trajectory_id,
            "done": self.done,
            "position_mm": self.position_mm,
        }
        if self.reason:
            d["reason"] = self.reason
        return d


class Backend:
    """Arka uç temel sınıfı: durum, komutlar ve olay yayını (asyncio kuyrukları)."""

    def __init__(self) -> None:
        self._listeners: set[asyncio.Queue] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    # --- olaylar -----------------------------------------------------------------------------
    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def add_listener(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._listeners.add(q)
        return q

    def remove_listener(self, q: asyncio.Queue) -> None:
        self._listeners.discard(q)

    def emit(self, event: dict) -> None:
        """Olayı tüm dinleyicilere iletir; başka iş parçacığından da çağrılabilir."""
        loop = self._loop
        if loop is None:
            return

        def push() -> None:
            for q in list(self._listeners):
                if q.full():
                    q.get_nowait()  # yavaş dinleyici: en eskiyi at
                q.put_nowait(event)

        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is loop:
            push()
        else:
            loop.call_soon_threadsafe(push)

    # --- arayüz ------------------------------------------------------------------------------
    def info(self) -> dict:
        raise NotImplementedError

    def state(self) -> RobotState:
        raise NotImplementedError

    async def move(
        self, x: float, y: float, z: float, duration_s: float | None, wait: bool
    ) -> MoveOutcome:
        raise NotImplementedError

    async def magnet(self, on: bool) -> bool:
        raise NotImplementedError

    async def torque(self, on: bool) -> bool:
        raise NotImplementedError

    async def stop(self) -> bool:
        raise NotImplementedError

    def close(self) -> None:
        """Kaynakları bırakır (ROS düğümü vb.)."""


def robot_info(spec: dict, home_mm: list[float], workspace: dict, limits: dict) -> dict:
    """GET /robot yanıtı: robot.yaml içeriğinden (değerler koda gömülmez)."""
    k = spec["kinematics"]
    # G14: mıknatıs ucu tabla üst yüzünün altına inemez -> P için alt sınır yükselir.
    min_tool_z = -float(k["base_to_floor"]) + float(spec.get("task", {}).get("board_thickness", 0))
    ws = dict(workspace)
    ws["z_bottom_mm"] = max(ws["z_bottom_mm"], min_tool_z + float(k["ee_offset"]))
    ws["reference"] = "P"  # z değerleri platform eklem düzlemi merkezi P içindir
    return {
        "name": "Delta Robotics V2",
        "geometry": {
            "R": k["base_radius"],
            "L1": k["bicep_length"],
            "L2": k["forearm_length"],
            "r": k["platform_radius"],
            "tool_offset_mm": k["ee_offset"],
            "arm_angles_deg": k["arm_angles"],
            "base_to_floor_mm": k["base_to_floor"],
            "rod_spacing_mm": spec.get("joint_stack", {}).get("rod_spacing", 30.0),
        },
        "limits": {
            "motor_min_deg": k["motor_limit_min"],
            "motor_max_deg": k["motor_limit_max"],
            "rod_tilt_max_deg": k["spherical_joint_limit"],
            "min_tool_z_mm": min_tool_z,
            **limits,
        },
        "workspace": ws,
        "home_mm": home_mm,
    }


# Datasheet (F2) hesabı: kullanılabilir silindir Ø82 × z -250…-145 mm. Sahte arka uç ve
# robot tanımı bu sayıları kullanır; F4.5'te datasheet çıktısından okunacak.
DEFAULT_WORKSPACE = {"cylinder_diameter_mm": 82.0, "z_top_mm": -145.0, "z_bottom_mm": -250.0}
DEFAULT_LIMITS = {"max_joint_velocity_deg_s": 300.0, "max_joint_acceleration_deg_s2": 3000.0}
HOME_MM = [0.0, 0.0, -200.0]


class FakeBackend(Backend):
    """ROS'suz benzetim: silindir dışındaki hedefi G3 ile reddeder, doğrusal hareket eder.

    Açılar gösterim içindir (gerçek kinematik değil). Yalnız testler ve web geliştirmesi için.
    """

    def __init__(self, spec: dict | None = None, speed_mm_s: float = 200.0) -> None:
        super().__init__()
        self.spec = spec
        self.speed = speed_mm_s
        self._s = RobotState(
            state="IDLE", position_mm=list(HOME_MM), edge_connected=True, voltages=[12.0] * 3
        )
        self._n = 0
        self.commands: list[tuple] = []  # testler için komut kaydı

    def info(self) -> dict:
        if self.spec is None:
            return {"name": "Delta Robotics V2 (sahte)", "workspace": DEFAULT_WORKSPACE}
        return robot_info(self.spec, HOME_MM, DEFAULT_WORKSPACE, DEFAULT_LIMITS)

    def state(self) -> RobotState:
        return self._s

    def _reachable(self, x: float, y: float, z: float) -> bool:
        w = self.info()["workspace"] if self.spec else DEFAULT_WORKSPACE
        return (
            math.hypot(x, y) <= w["cylinder_diameter_mm"] / 2
            and w["z_bottom_mm"] <= z <= w["z_top_mm"]
        )

    async def move(self, x, y, z, duration_s, wait) -> MoveOutcome:
        self.commands.append(("move", x, y, z, duration_s, wait))
        if self._s.state not in ("IDLE",):
            return MoveOutcome(
                False, requirement="DURUM", reason=f"robot hazır değil: {self._s.state}"
            )
        if not self._reachable(x, y, z):
            reason = f"G3: hedef ({x:.1f}, {y:.1f}, {z:.1f}) erişilemez"
            self.emit({"type": "event", "accepted": False, "requirement": "G3", "reason": reason,
                       "trajectory_id": ""})  # fmt: skip
            return MoveOutcome(False, requirement="G3", reason=reason)
        self._n += 1
        tid = f"traj-{self._n:04d}-fake"
        start = list(self._s.position_mm or HOME_MM)
        target = [float(x), float(y), float(z)]
        dist = math.dist(start, target)
        dur = duration_s if duration_s else max(dist / self.speed, 0.05)
        self._s.state, self._s.trajectory_id = "RUNNING", tid
        task = asyncio.create_task(self._play(start, target, dur))
        if not wait:
            return MoveOutcome(True, trajectory_id=tid, done=False)
        await task
        ok = self._s.state == "IDLE"
        return MoveOutcome(
            True,
            trajectory_id=tid,
            done=ok,
            position_mm=list(self._s.position_mm),
            reason=None if ok else f"yörünge tamamlanmadı: {self._s.state}",
        )

    async def _play(self, a: list[float], b: list[float], dur: float) -> None:
        t0 = time.monotonic()
        while True:
            if self._s.state != "RUNNING":
                return  # dur komutu
            u = min((time.monotonic() - t0) / dur, 1.0)
            self._s.position_mm = [a[i] + (b[i] - a[i]) * u for i in range(3)]
            self._s.angles_deg = [round(-self._s.position_mm[2] / 4 - 30, 2)] * 3
            if u >= 1.0:
                self._s.state = "IDLE"
                return
            await asyncio.sleep(0.01)

    async def magnet(self, on: bool) -> bool:
        self.commands.append(("magnet", on))
        if on and self._s.state not in ("IDLE", "RUNNING", "HOLDING"):
            return False
        self._s.magnet = bool(on)
        return True

    async def torque(self, on: bool) -> bool:
        self.commands.append(("torque", on))
        self._s.state = "IDLE" if on else "TORQUE_OFF"
        if not on:
            self._s.magnet = False
        return True

    async def stop(self) -> bool:
        self.commands.append(("stop",))
        if self._s.state == "RUNNING":
            self._s.state = "HOLDING"
        return True
