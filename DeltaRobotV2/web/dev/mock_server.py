#!/usr/bin/env python3
"""Arayüz için sahte API sunucusu (yalnız geliştirme ve arayüz testleri). Yalnız standart kütüphane.

docs/api.md v1 + "F6 deneyim arayüzü" sözleşmesini taklit eder:
  /                         web/ statik dosyaları
  /assets/meshes/<ad>.stl   cad/out/meshes
  /i18n/<dil>.json          i18n/locales
  /api/v1/...               REST (Bearer) ve WebSocket (?token=) uç noktaları

F6: POST /session anonim oturum açar (IP başına dakikada sınır -> 429, kapasite -> 503); her
oturumun kendi sahte robotu, tabla ikizi ve otomatik oyunu vardır. Boşta kalan oturum silinir
(sonraki çağrı 401). Sabit --token (varsayılan dev-token) süresiz bir oturuma bağlıdır.

Kinematik ve 1. kapı (G1, G2, G3, G14) core/src/kinematics.cpp ve delta_server/safety.py'nin
küçük bir Python kopyasıdır; tabla ikizi ve oyun kuralları delta_server/board_game.py'den
(saf Python) yüklenir. Sahte robot hedefe yumuşak (quintic) ara değerlemeyle gider; --speed
süreleri kısaltır (testler için).

İşlerde kullanıcı kodu ÇALIŞTIRILMAZ: küçük bir AST yorumlayıcısı yalnız print, f-string,
robot.move_to / magnet / torque / stop / state, atama, for ve try/except CommandRejected
kalıplarını taklit eder (gerçek sandbox sözleşmedeki koşucudadır).

Çalıştırma (DeltaRobotV2/ kökünden):
  docker run --rm -p 127.0.0.1:8765:8765 -v "$(cygpath -w "$PWD"):/workspace" -w /workspace \
      deltarobotv2-dev:latest python3 web/dev/mock_server.py --host 0.0.0.0 --port 8765
"""

from __future__ import annotations

import argparse
import ast
import base64
import collections
import hashlib
import importlib.util
import json
import math
import os
import queue
import random
import secrets
import socket
import struct
import sys
import threading
import time
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

WEB = Path(__file__).resolve().parent.parent
ROOT = WEB.parent
MESHES = ROOT / "cad" / "out" / "meshes"
LOCALES = ROOT / "i18n" / "locales"
BOARD_GAME = ROOT / "ros2_ws" / "src" / "delta_server" / "delta_server" / "board_game.py"

_spec = importlib.util.spec_from_file_location("board_game", BOARD_GAME)
bg = sys.modules.setdefault("board_game", importlib.util.module_from_spec(_spec))
_spec.loader.exec_module(bg)  # dataclass'lar modülü sys.modules'te arar

ROBOT = {
    "name": "Delta Robotics V2 (sahte)",
    "geometry": {
        "R": 65,
        "L1": 64,
        "L2": 201,
        "r": 35,
        "tool_offset_mm": 15,
        "arm_angles_deg": [0, 120, 240],
        "base_to_floor_mm": 240,
        "rod_spacing_mm": 30,
    },
    "limits": {
        "motor_min_deg": -70,
        "motor_max_deg": 150,
        "rod_tilt_max_deg": 13,
        "min_tool_z_mm": -236,
        "max_joint_velocity_deg_s": 300,
        "max_joint_acceleration_deg_s2": 3000,
    },
    "workspace": {
        "cylinder_diameter_mm": 82,
        "z_top_mm": -145,
        "z_bottom_mm": -221,
        "reference": "P",
    },
    "home_mm": [0, 0, -200],
}
ARM_ANGLES = (0.0, 120.0, 240.0)
SPEED_MM_S = 80.0
JOINT_SPEED_DEG_S = 90.0
MIN_DURATION_S = 0.4
JOB_WALL_S = 120.0
CODE_MAX = 64 * 1024
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
JOB_FINAL = ("done", "failed", "timeout", "cancelled")
AUTO_OWNER = "auto"
AUTO_MAX_MOVES = 20
AUTO_DEPTH = 4
GEO = bg.Geometry(
    board_top=-ROBOT["geometry"]["base_to_floor_mm"] + 4.0,
    tool_offset=ROBOT["geometry"]["tool_offset_mm"],
)

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".py": "text/plain; charset=utf-8",
    ".md": "text/plain; charset=utf-8",
    ".png": "image/png",
    ".stl": "application/octet-stream",
}


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# --- Kinematik (core/src/kinematics.cpp ile aynı çerçeve) ---------------------------------------

_G = ROBOT["geometry"]
_U = [(math.cos(math.radians(a)), math.sin(math.radians(a))) for a in ARM_ANGLES]


def _elbow(i: int, th_deg: float) -> tuple[float, float, float]:
    th = math.radians(th_deg)
    u = _U[i]
    k = _G["R"] + _G["L1"] * math.cos(th)
    return (u[0] * k, u[1] * k, -_G["L1"] * math.sin(th))


def _wrist(i: int, p) -> tuple[float, float, float]:
    u = _U[i]
    return (p[0] + u[0] * _G["r"], p[1] + u[1] * _G["r"], p[2])


def inverse(p) -> list[float] | None:
    """P (mm) -> motor açıları (derece); çözümsüzse None. Dirsek dışarıda kökü."""
    if not all(math.isfinite(v) for v in p):
        return None
    R, L1, L2 = _G["R"], _G["L1"], _G["L2"]
    out = []
    for i in range(3):
        u = _U[i]
        w = _wrist(i, p)
        c = (w[0] - u[0] * R, w[1] - u[1] * R, w[2])
        cx = c[0] * u[0] + c[1] * u[1]
        cz = c[2]
        k = (L1 * L1 + c[0] ** 2 + c[1] ** 2 + c[2] ** 2 - L2 * L2) / (2 * L1)
        rho = math.hypot(cx, cz)
        if rho < 1e-12 or abs(k) > rho:
            return None
        phi = math.atan2(cz, cx)
        acs = math.acos(k / rho)
        r1 = math.remainder(-phi + acs, 2 * math.pi)
        r2 = math.remainder(-phi - acs, 2 * math.pi)
        out.append(math.degrees(r1 if math.cos(r1) >= math.cos(r2) else r2))
    return out


def forward(th) -> list[float] | None:
    """Motor açıları -> P; üç kürenin kesişimi (alttaki kök). Çözümsüzse None."""
    if not all(math.isfinite(t) for t in th):
        return None
    s = []
    for i in range(3):
        b = _elbow(i, th[i])
        s.append((b[0] - _U[i][0] * _G["r"], b[1] - _U[i][1] * _G["r"], b[2]))

    def sub(a, b):
        return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

    def dot(a, b):
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    def scale(a, k):
        return (a[0] * k, a[1] * k, a[2] * k)

    d21 = sub(s[1], s[0])
    d = math.sqrt(dot(d21, d21))
    if d < 1e-9:
        return None
    ex = scale(d21, 1 / d)
    d31 = sub(s[2], s[0])
    i = dot(ex, d31)
    ey = sub(d31, scale(ex, i))
    ey_n = math.sqrt(dot(ey, ey))
    if ey_n < 1e-9:
        return None
    ey = scale(ey, 1 / ey_n)
    ez = (
        ex[1] * ey[2] - ex[2] * ey[1],
        ex[2] * ey[0] - ex[0] * ey[2],
        ex[0] * ey[1] - ex[1] * ey[0],
    )
    j = dot(ey, d31)
    x = d / 2
    y = (i * i + j * j) / (2 * j) - (i / j) * x
    z2 = _G["L2"] ** 2 - x * x - y * y
    if z2 < 0:
        return None
    z = math.sqrt(z2)
    base = tuple(s[0][k] + ex[k] * x + ey[k] * y for k in range(3))
    a = [base[k] + ez[k] * z for k in range(3)]
    b = [base[k] - ez[k] * z for k in range(3)]
    return a if a[2] < b[2] else b


def rod_tilt_deg(i: int, th_deg: float, p) -> float:
    """Rot başı yanal açısı: alt kol doğrultusunun teğet bileşeni."""
    w, e = _wrist(i, p), _elbow(i, th_deg)
    d = (w[0] - e[0], w[1] - e[1], w[2] - e[2])
    n = math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2)
    t = (-_U[i][1], _U[i][0])
    s = min(max(abs(d[0] * t[0] + d[1] * t[1]) / n, 0.0), 1.0)
    return math.degrees(math.asin(s))


def point_verdict(th, p) -> tuple[str, str] | None:
    """Statik nokta denetimi (G1, G2, G3, G14); ret ise (gereksinim, neden)."""
    lim = ROBOT["limits"]
    lo, hi = lim["motor_min_deg"], lim["motor_max_deg"]
    for j, a in enumerate(th):
        if not lo <= a <= hi:
            return "G1", f"G1: motor açı limiti (kol {j + 1}: {a:.1f}° ∉ [{lo:g}, {hi:g}])"
    if p is None:
        return "G3", "G3: erişilemez (ileri kinematik çözümsüz)"
    for j in range(3):
        if rod_tilt_deg(j, th[j], p) > lim["rod_tilt_max_deg"]:
            return "G2", f"G2: rot başı açı limiti (kol {j + 1})"
    tip = p[2] - _G["tool_offset_mm"]
    if tip < lim["min_tool_z_mm"] - 1e-6:
        return (
            "G14",
            f"G14: uç tabla/zemin yüzeyinin altına iner: z_uç {tip:.1f} mm < "
            f"{lim['min_tool_z_mm']:g} mm",
        )
    return None


def fk_check(angles) -> dict:
    th = [float(a) for a in angles]
    p = forward(th)
    pos = [round(v, 3) for v in p] if p is not None else None
    bad = point_verdict(th, p)
    if bad:
        if bad[0] == "G1":
            pos = None
        return {"ok": False, "position_mm": pos, "requirement": bad[0], "reason": bad[1]}
    return {"ok": True, "position_mm": pos}


def ik_check(x: float, y: float, z: float) -> dict:
    th = inverse((x, y, z))
    if th is None:
        return {
            "ok": False,
            "angles_deg": None,
            "requirement": "G3",
            "reason": f"G3: hedef ({x:g}, {y:g}, {z:g}) erişilemez",
        }
    th = [round(a, 3) for a in th]
    bad = point_verdict(th, (x, y, z))
    if bad:
        return {"ok": False, "angles_deg": th, "requirement": bad[0], "reason": bad[1]}
    return {"ok": True, "angles_deg": th}


def check_target(x: float, y: float, z: float) -> tuple[str, str] | None:
    """Tek hedef noktası denetimi (eski arayüz); ret ise (gereksinim, neden)."""
    r = ik_check(x, y, z)
    return None if r["ok"] else (r["requirement"], r["reason"])


def quintic(s: float) -> float:
    s = min(max(s, 0.0), 1.0)
    return s * s * s * (10 - 15 * s + 6 * s * s)


# --- Sahte robot --------------------------------------------------------------------------------


class Busy(Exception):
    def __init__(self, job_id: str):
        super().__init__(job_id)
        self.job_id = job_id


class FakeRobot:
    """Durum makinesi + zaman tabanlı yörünge ara değerlemesi (eklem ya da kartezyen)."""

    def __init__(self, speed: float = 1.0):
        self.cv = threading.Condition()
        self.speed = max(float(speed), 0.05)
        self.state = "IDLE"
        self.q = inverse(ROBOT["home_mm"])
        self.magnet = False
        self.traj = None  # (id, tür, başlangıç, hedef, t0, süre); tür "cart" | "joint"
        self.traj_id = None
        self.counter = 0
        self.job_id = None  # kontrol kilidi: iş kimliği ya da AUTO_OWNER
        self.listeners: list[queue.Queue] = []
        self.on_pose = None  # her poz okumasında çağrılır (tabla ikizi)
        self.t_start = time.monotonic()

    def _pose(self, t: float) -> tuple[list[float], list[float] | None]:
        """(açılar, P) o anda."""
        if self.traj is None:
            return list(self.q), forward(self.q)
        _, kind, a, b, t0, dur = self.traj
        s = quintic((t - t0) / dur)
        v = [a[i] + (b[i] - a[i]) * s for i in range(3)]
        if kind == "joint":
            return v, forward(v)
        return inverse(v) or list(self.q), v

    def _advance(self) -> None:
        """Süresi dolan yörüngeyi bitirir (kilit altında çağrılır)."""
        if self.traj is not None:
            _, kind, _, b, t0, dur = self.traj
            if time.monotonic() >= t0 + dur:
                self.q = list(b) if kind == "joint" else inverse(b)
                self.traj = None
                self.state = "IDLE"
                self.cv.notify_all()

    def _freeze(self) -> None:
        self.q, _ = self._pose(time.monotonic())
        self.traj = None

    def _check_lock(self, source: str | None) -> None:
        if self.job_id is not None and source != self.job_id:
            raise Busy(self.job_id)

    def _tick(self) -> None:
        if self.on_pose is not None:
            _, p = self._pose(time.monotonic())
            self.on_pose(p, self.magnet)

    def broadcast(self, msg: dict) -> None:
        for q in list(self.listeners):
            q.put(msg)

    def snapshot(self) -> dict:
        with self.cv:
            self._advance()
            self._tick()
            t = time.monotonic()
            q, p = self._pose(t)
            moving = self.traj is not None
            wobble = 0.4 * math.sin((t - self.t_start) / 7)
            return {
                "state": self.state,
                "angles_deg": [round(a, 2) for a in q],
                "position_mm": [round(v, 2) for v in p] if p else None,
                "magnet": self.magnet,
                "temps_c": [round(31 + wobble + i * 0.7, 1) for i in range(3)],
                "loads": [int(140 + 30 * i) if moving else 8 + i for i in range(3)],
                "voltages": [round(12.0 - (0.15 if moving else 0.02), 2)] * 3,
                "trajectory_id": self.traj_id,
                "edge_connected": True,
                "job_id": self.job_id if self.job_id != AUTO_OWNER else None,
            }

    def _reject(self, req: str, reason: str) -> dict:
        self.broadcast(
            {
                "type": "event",
                "accepted": False,
                "requirement": req,
                "reason": reason,
                "trajectory_id": None,
            }
        )
        return {"accepted": False, "requirement": req, "reason": reason}

    def _not_ready(self) -> dict | None:
        if self.state != "IDLE":
            return {
                "accepted": False,
                "requirement": "DURUM",
                "reason": f"robot hazır değil: durum {self.state}",
            }
        return None

    def move(self, x, y, z, duration_s=None, wait=True, source=None) -> dict:
        """Kartezyen doğru boyunca; yol örnekleri 1. kapıdan geçer."""
        with self.cv:
            self._check_lock(source)
            self._advance()
            bad = self._not_ready()
            if bad:
                return bad
            start = forward(self.q)
            target = (float(x), float(y), float(z))
            if not all(math.isfinite(v) for v in target):
                return self._reject("G4", "G4: konum sayı değil")
            dist = math.dist(start, target)
            n = max(2, int(dist / 2) + 1)
            for k in range(n + 1):
                pk = [start[i] + (target[i] - start[i]) * k / n for i in range(3)]
                r = ik_check(*pk)
                if not r["ok"]:
                    why = r["reason"]
                    return self._reject(r["requirement"], f"{why} (hedef yol, örnek {k})")
            dur = float(duration_s) if duration_s else max(MIN_DURATION_S, dist / SPEED_MM_S)
            return self._start(("cart", list(start), list(target)), dur / self.speed, wait)

    def move_joints(self, angles, duration_s=None, wait=True, source=None) -> dict:
        """Eklem uzayında quintic yörünge; aynı kapı."""
        with self.cv:
            self._check_lock(source)
            self._advance()
            bad = self._not_ready()
            if bad:
                return bad
            a, b = list(self.q), [float(v) for v in angles]
            if not all(math.isfinite(v) for v in b):
                return self._reject("G4", "G4: açı sayı değil")
            span = max(abs(b[i] - a[i]) for i in range(3))
            n = max(2, int(span) + 1)
            for k in range(n + 1):
                qk = [a[i] + (b[i] - a[i]) * k / n for i in range(3)]
                r = fk_check(qk)
                if not r["ok"]:
                    return self._reject(r["requirement"], f"{r['reason']} (örnek {k})")
            dur = float(duration_s) if duration_s else max(MIN_DURATION_S, span / JOINT_SPEED_DEG_S)
            return self._start(("joint", a, b), dur / self.speed, wait)

    def _start(self, plan, dur: float, wait: bool) -> dict:
        kind, a, b = plan
        self.counter += 1
        tid = f"traj-{self.counter:04d}-{secrets.token_hex(3)}"
        self.traj = (tid, kind, a, b, time.monotonic(), dur)
        self.traj_id = tid
        self.state = "RUNNING"
        self.broadcast(
            {
                "type": "event",
                "accepted": True,
                "requirement": "",
                "reason": "",
                "trajectory_id": tid,
            }
        )
        if not wait:
            return {"accepted": True, "trajectory_id": tid, "done": False, "position_mm": None}
        deadline = time.monotonic() + dur + 5
        while self.traj is not None and self.traj[0] == tid and time.monotonic() < deadline:
            self.cv.wait(timeout=0.02)
            self._advance()
            self._tick()
        self._tick()
        done = self.traj_id == tid and self.state == "IDLE"
        _, p = self._pose(time.monotonic())
        res = {"accepted": True, "trajectory_id": tid, "done": done}
        res["position_mm"] = [round(v, 2) for v in p] if p else None
        if not done:
            res["reason"] = f"yörünge tamamlanmadı: {self.state}"
        return res

    def set_magnet(self, on: bool, source=None) -> dict:
        with self.cv:
            self._check_lock(source)
            self._advance()
            if not (on and self.state == "TORQUE_OFF"):
                self.magnet = bool(on)
            self._tick()
            return {"ok": True, "magnet": self.magnet}

    def torque(self, on: bool, source=None) -> dict:
        with self.cv:
            self._check_lock(source)
            self._advance()
            if on and self.state in ("TORQUE_OFF", "HOLDING"):
                self.state = "IDLE"
            elif not on:
                self._freeze()
                self.state = "TORQUE_OFF"
                self.magnet = False
                self._tick()
                self.cv.notify_all()
            return {"ok": True}

    def stop(self) -> dict:
        """Her zaman kabul edilir; o anki konumda tutar."""
        with self.cv:
            self._advance()
            if self.traj is not None:
                self._freeze()
                self.state = "HOLDING"
            self.traj_id = None
            self.cv.notify_all()
            return {"ok": True}


# --- Otomatik oyun (robot kendi kendine kaydırmalı tic-tac-toe oynar) ---------------------------


class AutoAbort(Exception):
    pass


class AutoGame:
    def __init__(self, robot: FakeRobot, twin, max_moves: int = AUTO_MAX_MOVES):
        self.robot, self.twin, self.max_moves = robot, twin, max_moves
        self.lock = threading.Lock()
        self.thread: threading.Thread | None = None
        self.cancel = threading.Event()
        self.rng = random.Random()
        self.info = self._new()

    @staticmethod
    def _new() -> dict:
        return {"status": "idle", "turn": "X", "winner": None, "reason": None, "moves": []}

    @property
    def running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def to_dict(self) -> dict:
        with self.lock:
            return {k: (list(v) if isinstance(v, list) else v) for k, v in self.info.items()}

    def start(self) -> None:
        if self.running:
            return
        r = self.robot
        with r.cv:
            if r.state in ("HOLDING", "TORQUE_OFF"):
                r.state = "IDLE"
            if self.twin.held is not None:
                r.magnet = False
                r._tick()
            cells = self.twin.cells()
            with self.lock:
                if bg.winner(cells) is not None or self.info["status"] in ("finished", "error"):
                    self.twin.reset()
                    self.info = self._new()
                if self.twin.cells() == bg.initial_cells() and self.info["moves"]:
                    self.info = self._new()
                self.info.update(status="playing", reason=None)
            r.job_id = AUTO_OWNER
        self.cancel.clear()
        self.thread = threading.Thread(target=self._play, daemon=True)
        self.thread.start()

    def stop(self, status: str = "stopped") -> None:
        if not self.running:
            return
        self.cancel.set()
        self.robot.stop()
        self.thread.join(timeout=5)
        with self.lock:
            self.info["status"] = status

    def reset(self) -> None:
        with self.lock:
            self.info = self._new()

    def _play(self) -> None:
        a = self.info
        try:
            cells = self.twin.cells()
            while bg.winner(cells) is None and len(a["moves"]) < self.max_moves:
                m = bg.best_move(cells, a["turn"], depth=AUTO_DEPTH, rng=self.rng)
                if m is None:
                    break
                self._pick_place(*m)
                expected = bg.apply_move(cells, m)
                cells = self.twin.cells()
                if cells != expected:
                    raise AutoAbort(f"tabla beklenen gibi değil: {cells}")
                with self.lock:
                    n = len(a["moves"]) + 1
                    a["moves"].append({"n": n, "kind": a["turn"], "from": m[0], "to": m[1]})
                    a["turn"] = "O" if a["turn"] == "X" else "X"
            self._step("move", (0.0, 0.0, GEO.travel_p))
            with self.lock:
                a.update(status="finished", winner=bg.winner(cells))
        except AutoAbort as e:
            if not self.cancel.is_set():
                with self.lock:
                    a.update(status="error", reason=str(e))
        finally:
            with self.robot.cv:
                if self.robot.job_id == AUTO_OWNER:
                    self.robot.job_id = None

    def _step(self, kind: str, p) -> None:
        if self.cancel.is_set():
            raise AutoAbort("durduruldu")
        if kind == "move":
            r = self.robot.move(*p, source=AUTO_OWNER)
            if not (r["accepted"] and r["done"]):
                raise AutoAbort(r.get("reason") or "hareket tamamlanmadı")
        else:
            self.robot.set_magnet(kind == "magnet_on", source=AUTO_OWNER)

    def _pick_place(self, src: int, dst: int) -> None:
        for kind, p in GEO.pick_place_path(src, dst):
            self._step(kind, p)


# --- Oturumlar ----------------------------------------------------------------------------------


class Session:
    def __init__(self, token: str, speed: float, max_moves: int, rate: int):
        self.token = token
        self.robot = FakeRobot(speed)
        self.twin = bg.BoardTwin(GEO)
        self.robot.on_pose = self._twin_step
        self.auto = AutoGame(self.robot, self.twin, max_moves)
        self.jobs = Jobs(self.robot)
        self.last_seen = time.monotonic()
        self.ws_count = 0
        self.rate = rate
        self.hits: collections.deque[float] = collections.deque()
        self.lock = threading.Lock()

    def _twin_step(self, p, magnet: bool) -> None:
        tip = None if p is None else (p[0], p[1], p[2] - GEO.tool_offset)
        with self.lock:
            self.twin.update(tip, magnet)

    def board(self) -> dict:
        self.robot.snapshot()  # ikizi o anki poza getirir
        with self.lock:
            d = self.twin.to_dict()
        d["auto"] = self.auto.to_dict()
        return d

    def hit(self) -> bool:
        """İstek sayacı; saniyede `rate` isteği aşınca False."""
        now = time.monotonic()
        self.last_seen = now
        with self.lock:
            while self.hits and now - self.hits[0] > 1.0:
                self.hits.popleft()
            if len(self.hits) >= self.rate:
                return False
            self.hits.append(now)
            return True

    def close(self) -> None:
        self.auto.stop()
        for job in self.jobs.jobs.values():
            job.cancel.set()


class Sessions:
    def __init__(
        self,
        dev_token: str | None = None,
        speed: float = 1.0,
        max_sessions: int = 50,
        per_ip_per_min: int = 10,
        idle_timeout_s: float = 600.0,
        max_moves: int = AUTO_MAX_MOVES,
        rate_per_s: int = 20,
    ):
        self.speed, self.max_sessions, self.per_ip = speed, max_sessions, per_ip_per_min
        self.idle_timeout_s, self.max_moves, self.rate = idle_timeout_s, max_moves, rate_per_s
        self.by_token: dict[str, Session] = {}
        self.ip_hits: dict[str, collections.deque] = collections.defaultdict(collections.deque)
        self.lock = threading.Lock()
        self.dev_token = dev_token
        if dev_token:
            self.by_token[dev_token] = self._new(dev_token)

    def _new(self, token: str) -> Session:
        return Session(token, self.speed, self.max_moves, self.rate)

    def create(self, ip: str) -> tuple[int, dict]:
        now = time.monotonic()
        with self.lock:
            hits = self.ip_hits[ip]
            while hits and now - hits[0] > 60:
                hits.popleft()
            if len(hits) >= self.per_ip:
                msg = "Çok fazla oturum isteği; biraz sonra yeniden deneyin."
                return 429, {"error": "rate_limited", "message": msg}
            anon = [s for t, s in self.by_token.items() if t != self.dev_token]
            if len(anon) >= self.max_sessions:
                msg = "Simülasyon kapasitesi dolu; biraz sonra yeniden deneyin."
                return 503, {"error": "capacity", "message": msg}
            hits.append(now)
            token = "anon-" + secrets.token_urlsafe(18)
            self.by_token[token] = self._new(token)
        return 201, {"token": token, "idle_timeout_s": int(self.idle_timeout_s)}

    def get(self, token: str) -> Session | None:
        with self.lock:
            return self.by_token.get(token)

    def sweep(self) -> None:
        """Boşta kalan oturumları siler (açık telemetri bağlantısı oturumu canlı tutar)."""
        now = time.monotonic()
        with self.lock:
            dead = [
                s
                for t, s in self.by_token.items()
                if t != self.dev_token
                and s.ws_count == 0
                and now - s.last_seen > self.idle_timeout_s
            ]
            for s in dead:
                del self.by_token[s.token]
        for s in dead:
            s.close()

    def sweeper(self) -> None:
        while True:
            time.sleep(min(5.0, max(self.idle_timeout_s / 4, 0.2)))
            self.sweep()


# --- Sahte işler (kod çalıştırılmaz; AST taklidi) -----------------------------------------------


class Rejected(Exception):
    """delta_robot.CommandRejected taklidi."""

    def __init__(self, requirement, reason):
        super().__init__(reason)
        self.requirement, self.reason = requirement, reason


class Record:
    """İstemci nesnelerinin (State, MoveResult, CommandRejected) salt okunur taklidi."""

    def __init__(self, fields: dict, text: str | None = None):
        self.fields, self.text = fields, text

    def __str__(self) -> str:
        return self.text if self.text is not None else str(self.fields)


class Cancelled(Exception):
    pass


class Unsupported(Exception):
    pass


_ROBOT = object()


class Job:
    def __init__(self, jid: str, name: str, code: str):
        self.id, self.name, self.code = jid, name, code
        self.status = "queued"
        self.exit_code = None
        self.reason = None
        self.messages: list[dict] = []
        self.cv = threading.Condition()
        self.cancel = threading.Event()
        self.created_at, self.started_at, self.finished_at = now_iso(), None, None

    def emit(self, msg: dict) -> None:
        with self.cv:
            self.messages.append(msg)
            self.cv.notify_all()

    def output(self) -> str:
        return "".join(m["data"] for m in self.messages if m["type"] in ("stdout", "stderr"))

    def to_json(self) -> dict:
        return {
            "job_id": self.id,
            "name": self.name,
            "status": self.status,
            "exit_code": self.exit_code,
            "output": self.output()[-CODE_MAX:],
            "reason": self.reason,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


class Interp:
    """Küçük, güvenli yorumlayıcı: yalnız izin verilen düğümler."""

    def __init__(self, job: Job, robot: FakeRobot):
        self.job, self.robot, self.env = job, robot, {}
        self.t_end = time.monotonic() + JOB_WALL_S

    def run(self, code: str) -> None:
        tree = ast.parse(code)
        self.block(tree.body)

    def block(self, body) -> None:
        for st in body:
            if self.job.cancel.is_set():
                raise Cancelled()
            if time.monotonic() > self.t_end:
                raise TimeoutError()
            self.stmt(st)

    def stmt(self, st) -> None:
        if isinstance(st, ast.Import | ast.ImportFrom):
            return
        if isinstance(st, ast.Expr):
            self.expr(st.value)
        elif isinstance(st, ast.Assign) and len(st.targets) == 1:
            self.bind(st.targets[0], self.expr(st.value))
        elif isinstance(st, ast.For):
            for item in self.expr(st.iter):
                self.bind(st.target, item)
                self.block(st.body)
        elif isinstance(st, ast.Try):
            try:
                self.block(st.body)
            except Rejected as e:
                h = next((h for h in st.handlers if self.catches(h)), None)
                if h is None:
                    raise
                if h.name:
                    fields = {"requirement": e.requirement, "reason": e.reason}
                    self.env[h.name] = Record(fields, e.reason)
                self.block(h.body)
        elif isinstance(st, ast.Pass):
            return
        else:
            raise Unsupported(f"satır {st.lineno}: {type(st).__name__}")

    def catches(self, h) -> bool:
        return h.type is None or (
            isinstance(h.type, ast.Name) and h.type.id in ("CommandRejected", "Exception")
        )

    def bind(self, target, value) -> None:
        if isinstance(target, ast.Name):
            self.env[target.id] = value
        elif isinstance(target, ast.Tuple | ast.List):
            vals = list(value)
            if len(vals) != len(target.elts):
                raise Unsupported(f"satır {target.lineno}: açma boyu uyuşmuyor")
            for t, v in zip(target.elts, vals, strict=True):
                self.bind(t, v)
        else:
            raise Unsupported(f"satır {target.lineno}: atama hedefi")

    def expr(self, e):
        if isinstance(e, ast.Constant):
            return e.value
        if isinstance(e, ast.Name):
            if e.id in self.env:
                return self.env[e.id]
            if e.id in ("True", "False", "None"):
                return {"True": True, "False": False, "None": None}[e.id]
            raise Unsupported(f"satır {e.lineno}: tanımsız ad {e.id}")
        if isinstance(e, ast.Tuple | ast.List):
            return [self.expr(x) for x in e.elts]
        if isinstance(e, ast.UnaryOp) and isinstance(e.op, ast.USub):
            return -self.expr(e.operand)
        if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Add | ast.Sub | ast.Mult | ast.Div):
            a, b = self.expr(e.left), self.expr(e.right)
            ops = {ast.Add: a + b, ast.Sub: a - b, ast.Mult: a * b}
            return ops[type(e.op)] if type(e.op) in ops else a / b
        if isinstance(e, ast.Call):
            return self.call(e)
        if isinstance(e, ast.Attribute):
            obj = self.expr(e.value)
            if isinstance(obj, Record) and e.attr in obj.fields:
                return obj.fields[e.attr]
            raise Unsupported(f"satır {e.lineno}: öznitelik {e.attr}")
        if isinstance(e, ast.JoinedStr):
            parts = []
            for v in e.values:
                if isinstance(v, ast.FormattedValue):
                    spec = self.expr(v.format_spec) if v.format_spec else ""
                    parts.append(format(self.expr(v.value), spec))
                else:
                    parts.append(str(v.value))
            return "".join(parts)
        raise Unsupported(f"satır {e.lineno}: {type(e).__name__}")

    def call(self, e):
        args = [self.expr(a) for a in e.args]
        kw = {k.arg: self.expr(k.value) for k in e.keywords}
        f = e.func
        if isinstance(f, ast.Name) and f.id == "print":
            self.job.emit({"type": "stdout", "data": " ".join(str(a) for a in args) + "\n"})
            return None
        if isinstance(f, ast.Name) and f.id == "Robot":
            return _ROBOT
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            obj = self.env.get(f.value.id)
            if f.value.id == "time" and f.attr == "sleep":
                self.sleep(float(args[0]))
                return None
            if obj is _ROBOT:
                return self.robot_call(f.attr, args, kw)
        raise Unsupported(f"satır {e.lineno}: desteklenmeyen çağrı")

    def sleep(self, s: float) -> None:
        if self.job.cancel.wait(timeout=max(0.0, s)):
            raise Cancelled()

    def robot_call(self, name, args, kw):
        r, src = self.robot, self.job.id
        if name == "move_to":
            res = r.move(*args[:3], duration_s=kw.get("duration"), source=src)
            if not res["accepted"] and kw.get("check", True):
                raise Rejected(res.get("requirement"), res.get("reason") or "")
            return Record(res)
        if name == "magnet":
            return r.set_magnet(args[0], source=src)["magnet"]
        if name == "torque":
            return r.torque(args[0], source=src)
        if name == "stop":
            return r.stop()
        if name == "state":
            return Record(r.snapshot())
        if name == "info":
            return ROBOT
        raise Unsupported(f"robot.{name}")


class Jobs:
    def __init__(self, robot: FakeRobot):
        self.robot = robot
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()
        self.counter = 0

    def submit(self, code: str, name: str) -> Job:
        with self.lock:
            self.counter += 1
            jid = f"job-{self.counter:04d}-{secrets.token_hex(2)}"
            job = Job(jid, name, code)
            self.jobs[jid] = job
        threading.Thread(target=self._run, args=(job,), daemon=True).start()
        return job

    def _finish(self, job: Job, status: str, code: int, reason: str) -> None:
        with self.robot.cv:
            if self.robot.job_id == job.id:
                self.robot.job_id = None
        job.status, job.exit_code, job.reason = status, code, reason
        job.finished_at = now_iso()
        job.emit({"type": "status", "status": status, "exit_code": code, "reason": reason})

    def _run(self, job: Job) -> None:
        # Kontrol kilidi: tek iş; önceki bitene kadar sırada bekler.
        while True:
            if job.cancel.is_set():
                return self._finish(job, "cancelled", -1, "cancelled")
            with self.robot.cv:
                if self.robot.job_id is None:
                    self.robot.job_id = job.id
                    break
            time.sleep(0.1)
        job.status, job.started_at = "running", now_iso()
        job.emit({"type": "status", "status": "running"})
        try:
            Interp(job, self.robot).run(job.code)
        except Cancelled:
            return self._finish(job, "cancelled", -1, "cancelled")
        except TimeoutError:
            return self._finish(job, "timeout", -1, "timeout")
        except Rejected as e:
            job.emit({"type": "stderr", "data": f"delta_robot.CommandRejected: {e}\n"})
            return self._finish(job, "failed", 1, "error")
        except SyntaxError as e:
            job.emit({"type": "stderr", "data": f"SyntaxError: {e}\n"})
            return self._finish(job, "failed", 1, "error")
        except Unsupported as e:
            job.emit({"type": "stderr", "data": f"[sahte sunucu] desteklenmiyor: {e}\n"})
            return self._finish(job, "failed", 1, "error")
        except Exception as e:  # noqa: BLE001 - sahte sunucu düşmesin
            job.emit({"type": "stderr", "data": f"{type(e).__name__}: {e}\n"})
            return self._finish(job, "failed", 1, "error")
        self._finish(job, "done", 0, "ok")


# --- WebSocket (RFC 6455, yalnız metin çerçeveleri) ---------------------------------------------


def ws_accept(key: str) -> str:
    """Sec-WebSocket-Accept değeri (RFC 6455 4.2.2)."""
    return base64.b64encode(hashlib.sha1((key + WS_GUID).encode()).digest()).decode()


class WsConn:
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.send_lock = threading.Lock()
        self.closed = threading.Event()
        threading.Thread(target=self._reader, daemon=True).start()

    def _recv(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError()
            buf += chunk
        return buf

    def _reader(self) -> None:
        try:
            while not self.closed.is_set():
                b0, b1 = self._recv(2)
                op, n = b0 & 0x0F, b1 & 0x7F
                if n == 126:
                    n = struct.unpack(">H", self._recv(2))[0]
                elif n == 127:
                    n = struct.unpack(">Q", self._recv(8))[0]
                mask = self._recv(4) if b1 & 0x80 else b"\0\0\0\0"
                data = bytes(c ^ mask[i % 4] for i, c in enumerate(self._recv(n)))
                if op == 0x8:
                    break
                if op == 0x9:
                    self._frame(0xA, data)
        except (OSError, ConnectionError):
            pass
        self.close()

    def _frame(self, op: int, data: bytes) -> None:
        n = len(data)
        head = bytes([0x80 | op])
        if n < 126:
            head += bytes([n])
        elif n < 65536:
            head += bytes([126]) + struct.pack(">H", n)
        else:
            head += bytes([127]) + struct.pack(">Q", n)
        with self.send_lock:
            self.sock.sendall(head + data)

    def send(self, obj: dict) -> bool:
        if self.closed.is_set():
            return False
        try:
            self._frame(0x1, json.dumps(obj, ensure_ascii=False).encode())
            return True
        except OSError:
            self.close()
            return False

    def close(self) -> None:
        if not self.closed.is_set():
            self.closed.set()
            try:
                self._frame(0x8, struct.pack(">H", 1000))
            except OSError:
                pass


# --- HTTP ---------------------------------------------------------------------------------------


def _numbers(b: dict, keys) -> list[float] | None:
    try:
        vals = [float(b[k]) for k in keys]
    except (KeyError, TypeError, ValueError):
        return None
    return vals if all(math.isfinite(v) for v in vals) else None


def _angles(b: dict) -> list[float] | None:
    a = b.get("angles_deg")
    if not isinstance(a, list) or len(a) != 3:
        return None
    return _numbers(dict(enumerate(a)), range(3))


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "DeltaMock/2"
    sessions: Sessions

    def log_message(self, fmt, *args):  # sessiz; yalnız hatalar
        if args and str(args[1] if len(args) > 1 else "").startswith(("4", "5")):
            super().log_message(fmt, *args)

    # yanıt yardımcıları
    def send_json(self, status: int, obj) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def error(self, status: int, code: str, message: str, **extra) -> None:
        self.send_json(status, {"error": code, "message": message, **extra})

    def send_file(self, path: Path) -> None:
        data = path.read_bytes()
        self.send_response(200)
        ctype = CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def session(self, query: dict) -> Session | None:
        h = self.headers.get("Authorization", "")
        tok = h[7:] if h.startswith("Bearer ") else (query.get("token") or [""])[0]
        return self.sessions.get(tok) if tok else None

    def body(self) -> dict | None:
        n = int(self.headers.get("Content-Length") or 0)
        if n > CODE_MAX * 2:
            return None
        raw = self.rfile.read(n) if n else b"{}"
        try:
            data = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    def unauthorized(self) -> None:
        self.error(401, "unauthorized", "Oturum geçersiz ya da süresi doldu.")

    def rate_limited(self) -> None:
        self.error(429, "rate_limited", "Çok fazla istek; biraz yavaşlayın.")

    # statik
    def static(self, path: str) -> None:
        if path == "/":
            path = "/index.html"
        if path.startswith("/assets/meshes/"):
            base, rel = MESHES, path[len("/assets/meshes/") :]
        elif path.startswith("/i18n/"):
            base, rel = LOCALES, path[len("/i18n/") :]
        else:
            base, rel = WEB, path.lstrip("/")
        target = (base / rel).resolve()
        if not target.is_relative_to(base.resolve()) or not target.is_file():
            return self.error(404, "not_found", "Bulunamadı.")
        self.send_file(target)

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        p = url.path
        if not p.startswith("/api/v1/"):
            return self.static(p)
        if p == "/api/v1/health":
            return self.send_json(
                200, {"ok": True, "edge_connected": True, "version": "v1", "mode": "sim"}
            )
        s = self.session(q)
        if s is None:
            return self.unauthorized()
        if p == "/api/v1/ws/telemetry":
            return self.ws_telemetry(s)
        if p.startswith("/api/v1/ws/jobs/"):
            job = s.jobs.jobs.get(p.rsplit("/", 1)[1])
            if not job:
                return self.error(404, "not_found", "İş bulunamadı.")
            return self.ws_job(job)
        if not s.hit():
            return self.rate_limited()
        if p == "/api/v1/robot":
            return self.send_json(200, ROBOT)
        if p == "/api/v1/state":
            return self.send_json(200, s.robot.snapshot())
        if p == "/api/v1/board":
            return self.send_json(200, s.board())
        if p.startswith("/api/v1/jobs/"):
            job = s.jobs.jobs.get(p.rsplit("/", 1)[1])
            if not job:
                return self.error(404, "not_found", "İş bulunamadı.")
            return self.send_json(200, job.to_json())
        self.error(404, "not_found", "Bulunamadı.")

    def do_POST(self):
        p = urlparse(self.path).path
        b = self.body()
        if b is None:
            return self.error(400, "bad_request", "Gövde geçerli JSON nesnesi değil.")
        if p == "/api/v1/session":
            ip = self.client_address[0]
            return self.send_json(*self.sessions.create(ip))
        s = self.session({})
        if s is None:
            return self.unauthorized()
        if not s.hit():
            return self.rate_limited()
        r = s.robot
        try:
            if p == "/api/v1/move":
                xyz = _numbers(b, ("x", "y", "z"))
                if xyz is None:
                    return self.error(400, "bad_request", "x, y, z sayı olmalı.")
                res = r.move(*xyz, b.get("duration_s"), bool(b.get("wait", True)))
                return self.send_json(200, res)
            if p == "/api/v1/move_joints":
                th = _angles(b)
                if th is None:
                    return self.error(400, "bad_request", "angles_deg üç sayı olmalı.")
                res = r.move_joints(th, b.get("duration_s"), bool(b.get("wait", True)))
                return self.send_json(200, res)
            if p == "/api/v1/magnet":
                return self.send_json(200, r.set_magnet(bool(b.get("on"))))
            if p == "/api/v1/torque":
                return self.send_json(200, r.torque(bool(b.get("on"))))
        except Busy as e:
            if e.job_id == AUTO_OWNER:
                msg = "Otomatik oyun çalışıyor; önce durdurun."
                return self.error(409, "busy", msg, job_id=None)
            msg = "Bir iş çalışıyor; komut yalnız ondan kabul edilir."
            return self.error(409, "busy", msg, job_id=e.job_id)
        if p == "/api/v1/stop":
            s.auto.cancel.set()  # dur komutu otomatik oyunu da keser
            r.stop()
            s.auto.stop()
            return self.send_json(200, {"ok": True})
        if p == "/api/v1/kinematics/fk":
            th = _angles(b)
            if th is None:
                return self.error(400, "bad_request", "angles_deg üç sayı olmalı.")
            return self.send_json(200, fk_check(th))
        if p == "/api/v1/kinematics/ik":
            xyz = _numbers(b, ("x", "y", "z"))
            if xyz is None:
                return self.error(400, "bad_request", "x, y, z sayı olmalı.")
            return self.send_json(200, ik_check(*xyz))
        if p == "/api/v1/auto/start":
            if r.job_id is not None and r.job_id != AUTO_OWNER:
                msg = "Bir iş çalışıyor; komut yalnız ondan kabul edilir."
                return self.error(409, "busy", msg, job_id=r.job_id)
            if r.snapshot()["state"] == "RUNNING" and not s.auto.running:
                return self.error(409, "busy", "Robot hareket ediyor.")
            s.auto.start()
            return self.send_json(200, {"ok": True})
        if p == "/api/v1/auto/stop":
            s.auto.stop()
            r.torque(True, source=r.job_id)
            return self.send_json(200, {"ok": True})
        if p == "/api/v1/board/reset":
            if s.auto.running or r.snapshot()["state"] == "RUNNING":
                return self.error(409, "busy", "Robot hareket ederken tabla sıfırlanamaz.")
            with s.lock:
                s.twin.reset()
            s.auto.reset()
            return self.send_json(200, {"ok": True})
        if p == "/api/v1/jobs":
            code = b.get("code")
            if not isinstance(code, str) or len(code.encode()) > CODE_MAX:
                return self.error(400, "bad_request", "Kod metin olmalı ve 64 KB'ı aşmamalı.")
            job = s.jobs.submit(code, str(b.get("name") or "adsız"))
            return self.send_json(202, {"job_id": job.id, "status": "queued"})
        if p.startswith("/api/v1/jobs/") and p.endswith("/cancel"):
            job = s.jobs.jobs.get(p.split("/")[-2])
            if not job:
                return self.error(404, "not_found", "İş bulunamadı.")
            job.cancel.set()
            return self.send_json(200, {"ok": True})
        self.error(404, "not_found", "Bulunamadı.")

    # WebSocket
    def ws_upgrade(self) -> WsConn | None:
        key = self.headers.get("Sec-WebSocket-Key")
        if self.headers.get("Upgrade", "").lower() != "websocket" or not key:
            self.error(400, "bad_request", "WebSocket bekleniyor.")
            return None
        accept = ws_accept(key)
        self.send_response(101)
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()
        self.wfile.flush()
        self.close_connection = True
        return WsConn(self.connection)

    def ws_telemetry(self, s: Session) -> None:
        ws = self.ws_upgrade()
        if not ws:
            return
        q: queue.Queue = queue.Queue()
        s.robot.listeners.append(q)
        s.ws_count += 1
        try:
            while not ws.closed.is_set():
                if self.sessions.get(s.token) is not s:
                    break  # oturum silindi
                while not q.empty():
                    ev = q.get_nowait()
                    if not ws.send(ev):
                        break
                if not ws.send({"type": "state", **s.robot.snapshot()}):
                    break
                s.last_seen = time.monotonic()
                ws.closed.wait(0.05)  # 20 Hz
        finally:
            s.ws_count -= 1
            s.robot.listeners.remove(q)
            ws.close()

    def ws_job(self, job: Job) -> None:
        ws = self.ws_upgrade()
        if not ws:
            return
        i = 0
        while not ws.closed.is_set():
            with job.cv:
                while i >= len(job.messages) and not ws.closed.is_set():
                    job.cv.wait(timeout=0.25)
                batch = job.messages[i:]
                i = len(job.messages)
            for m in batch:
                ws.send(m)
                if m["type"] == "status" and m["status"] in JOB_FINAL:
                    ws.close()
                    return
        ws.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--token", default=os.environ.get("DELTA_MOCK_TOKEN", "dev-token"))
    ap.add_argument("--speed", type=float, default=1.0, help="hareket hızı çarpanı (testler)")
    ap.add_argument("--max-sessions", type=int, default=50)
    ap.add_argument("--sessions-per-ip", type=int, default=10, help="IP başına dakikada oturum")
    ap.add_argument("--idle-timeout", type=float, default=600.0)
    ap.add_argument("--max-moves", type=int, default=AUTO_MAX_MOVES)
    args = ap.parse_args()
    sessions = Sessions(
        dev_token=args.token,
        speed=args.speed,
        max_sessions=args.max_sessions,
        per_ip_per_min=args.sessions_per_ip,
        idle_timeout_s=args.idle_timeout,
        max_moves=args.max_moves,
    )
    threading.Thread(target=sessions.sweeper, daemon=True).start()
    Handler.sessions = sessions
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    srv.daemon_threads = True
    print(f"Sahte API: http://{args.host}:{args.port}/  (sabit belirteç: {args.token})", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
