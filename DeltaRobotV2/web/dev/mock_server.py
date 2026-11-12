#!/usr/bin/env python3
"""Arayüz için sahte API sunucusu (yalnız geliştirme). Yalnız standart kütüphane.

docs/api.md v1 sözleşmesini taklit eder:
  /                         web/ statik dosyaları
  /assets/meshes/<ad>.stl   cad/out/meshes
  /i18n/<dil>.json          i18n/locales
  /api/v1/...               REST (Bearer) ve WebSocket (?token=) uç noktaları

Sahte robot hedefe yumuşak doğrusal ara değerlemeyle gider; silindir dışı hedefler G3 ile
reddedilir. İşlerde kullanıcı kodu ÇALIŞTIRILMAZ: küçük bir AST yorumlayıcısı yalnız
print, f-string, robot.move_to / magnet / torque / stop / state (öznitelikleriyle), atama,
for ve try/except CommandRejected (hata.requirement, hata.reason)
kalıplarını taklit eder (gerçek sandbox sözleşmedeki koşucudadır).

Çalıştırma (DeltaRobotV2/ kökünden):
  docker run --rm -p 127.0.0.1:8765:8765 -v "$(cygpath -w "$PWD"):/workspace" -w /workspace \
      deltarobotv2-dev:latest python3 web/dev/mock_server.py --host 0.0.0.0 --port 8765
Belirteç: --token ya da DELTA_MOCK_TOKEN (varsayılan dev-token).
"""

from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import json
import math
import os
import queue
import secrets
import socket
import struct
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

ROBOT = {
    "name": "Delta Robotics V2 (sahte)",
    "geometry": {"R": 65, "L1": 64, "L2": 201, "r": 35, "tool_offset_mm": 15},
    "limits": {
        "motor_min_deg": -70,
        "motor_max_deg": 150,
        "rod_tilt_max_deg": 13,
        "max_joint_velocity_deg_s": 300,
        "max_joint_acceleration_deg_s2": 3000,
    },
    "workspace": {"cylinder_diameter_mm": 82, "z_top_mm": -145, "z_bottom_mm": -250},
    "home_mm": [0, 0, -200],
}
ARM_ANGLES = (0.0, 120.0, 240.0)
SPEED_MM_S = 80.0
MIN_DURATION_S = 0.4
JOB_WALL_S = 120.0
CODE_MAX = 64 * 1024
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
JOB_FINAL = ("done", "failed", "timeout", "cancelled")

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


def inverse(p: tuple[float, float, float]) -> list[float] | None:
    """P (mm) -> motor açıları (derece); çözümsüzse None. Dirsek dışarıda kökü."""
    g = ROBOT["geometry"]
    R, L1, L2, r = g["R"], g["L1"], g["L2"], g["r"]
    out = []
    for a_deg in ARM_ANGLES:
        a = math.radians(a_deg)
        u = (math.cos(a), math.sin(a))
        c = (p[0] + u[0] * (r - R), p[1] + u[1] * (r - R), p[2])
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


def check_target(x: float, y: float, z: float) -> tuple[str, str] | None:
    """Hedef kontrolü; ret ise (gereksinim, neden)."""
    ws = ROBOT["workspace"]
    rad = ws["cylinder_diameter_mm"] / 2
    if math.hypot(x, y) > rad or not (ws["z_bottom_mm"] <= z <= ws["z_top_mm"]):
        return (
            "G3",
            f"G3: hedef ({x:g}, {y:g}, {z:g}) çalışma alanı silindiri dışında "
            f"(çap {ws['cylinder_diameter_mm']} mm, z {ws['z_bottom_mm']}…{ws['z_top_mm']} mm)",
        )
    angles = inverse((x, y, z))
    lim = ROBOT["limits"]
    if angles is None:
        return ("G3", f"G3: hedef ({x:g}, {y:g}, {z:g}) erişilemez")
    if any(not (lim["motor_min_deg"] <= t <= lim["motor_max_deg"]) for t in angles):
        return ("G1", "G1: motor açı limiti dışında")
    return None


# --- Sahte robot --------------------------------------------------------------------------------


class Busy(Exception):
    def __init__(self, job_id: str):
        super().__init__(job_id)
        self.job_id = job_id


class FakeRobot:
    """Durum makinesi + zaman tabanlı yörünge ara değerlemesi."""

    def __init__(self):
        self.cv = threading.Condition()
        self.state = "IDLE"
        self.pos = tuple(float(v) for v in ROBOT["home_mm"])
        self.magnet = False
        self.traj = None  # (id, başlangıç, hedef, t0, süre)
        self.traj_id = None
        self.counter = 0
        self.job_id = None  # kontrol kilidi
        self.listeners: list[queue.Queue] = []
        self.t_start = time.monotonic()

    def _position(self, t: float) -> tuple[float, float, float]:
        if self.traj is None:
            return self.pos
        _, a, b, t0, dur = self.traj
        s = min(max((t - t0) / dur, 0.0), 1.0)
        s = s * s * (3 - 2 * s)  # yumuşak başla/bitir
        return tuple(a[i] + (b[i] - a[i]) * s for i in range(3))

    def _advance(self) -> None:
        """Süresi dolan yörüngeyi bitirir (kilit altında çağrılır)."""
        if self.traj is not None:
            _, _, b, t0, dur = self.traj
            if time.monotonic() >= t0 + dur:
                self.pos = b
                self.traj = None
                self.state = "IDLE"
                self.cv.notify_all()

    def _check_lock(self, source: str | None) -> None:
        if self.job_id is not None and source != self.job_id:
            raise Busy(self.job_id)

    def broadcast(self, msg: dict) -> None:
        for q in list(self.listeners):
            q.put(msg)

    def snapshot(self) -> dict:
        with self.cv:
            self._advance()
            t = time.monotonic()
            p = self._position(t)
            angles = inverse(p)
            moving = self.traj is not None
            wobble = 0.4 * math.sin((t - self.t_start) / 7)
            return {
                "state": self.state,
                "angles_deg": [round(a, 2) for a in angles] if angles else None,
                "position_mm": [round(v, 2) for v in p] if angles else None,
                "magnet": self.magnet,
                "temps_c": [round(31 + wobble + i * 0.7, 1) for i in range(3)],
                "loads": [int(140 + 30 * i) if moving else 8 + i for i in range(3)],
                "voltages": [round(12.0 - (0.15 if moving else 0.02), 2)] * 3,
                "trajectory_id": self.traj_id,
                "edge_connected": True,
                "job_id": self.job_id,
            }

    def move(self, x, y, z, duration_s=None, wait=True, source=None) -> dict:
        with self.cv:
            self._check_lock(source)
            self._advance()
            if self.state == "TORQUE_OFF":
                return {"accepted": False, "requirement": None, "reason": "Tork kapalı."}
            bad = check_target(x, y, z)
            if bad:
                req, reason = bad
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
            start = self._position(time.monotonic())
            dist = math.dist(start, (x, y, z))
            dur = float(duration_s) if duration_s else max(MIN_DURATION_S, dist / SPEED_MM_S)
            self.counter += 1
            tid = f"traj-{self.counter:04d}-{secrets.token_hex(3)}"
            self.traj = (tid, start, (float(x), float(y), float(z)), time.monotonic(), dur)
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
                self.cv.wait(timeout=0.05)
                self._advance()
            done = self.traj_id == tid and self.state == "IDLE"
            res = {"accepted": True, "trajectory_id": tid, "done": done}
            res["position_mm"] = [round(v, 2) for v in self._position(time.monotonic())]
            if not done:
                res["reason"] = "Hareket durduruldu."
            return res

    def set_magnet(self, on: bool, source=None) -> dict:
        with self.cv:
            self._check_lock(source)
            self.magnet = bool(on)
            return {"ok": True, "magnet": self.magnet}

    def torque(self, on: bool, source=None) -> dict:
        with self.cv:
            self._check_lock(source)
            self._advance()
            if on and self.state == "TORQUE_OFF":
                self.state = "IDLE"
            elif not on:
                self.pos = self._position(time.monotonic())
                self.traj = None
                self.state = "TORQUE_OFF"
                self.cv.notify_all()
            return {"ok": True}

    def stop(self) -> dict:
        """Her zaman kabul edilir; o anki konumda tutar."""
        with self.cv:
            self.pos = self._position(time.monotonic())
            self.traj = None
            self.traj_id = None
            self.state = "HOLDING"
            self.cv.notify_all()
            return {"ok": True}


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


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "DeltaMock/1"
    robot: FakeRobot
    jobs: Jobs
    token: str

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

    def authorized(self, query: dict) -> bool:
        h = self.headers.get("Authorization", "")
        tok = h[7:] if h.startswith("Bearer ") else (query.get("token") or [""])[0]
        return secrets.compare_digest(tok, self.token)

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
            return self.send_json(200, {"ok": True, "edge_connected": True, "version": "v1"})
        if not self.authorized(q):
            return self.error(401, "unauthorized", "Belirteç geçersiz ya da eksik.")
        if p == "/api/v1/robot":
            return self.send_json(200, ROBOT)
        if p == "/api/v1/state":
            return self.send_json(200, self.robot.snapshot())
        if p.startswith("/api/v1/jobs/"):
            job = self.jobs.jobs.get(p.rsplit("/", 1)[1])
            if not job:
                return self.error(404, "not_found", "İş bulunamadı.")
            return self.send_json(200, job.to_json())
        if p == "/api/v1/ws/telemetry":
            return self.ws_telemetry()
        if p.startswith("/api/v1/ws/jobs/"):
            job = self.jobs.jobs.get(p.rsplit("/", 1)[1])
            if not job:
                return self.error(404, "not_found", "İş bulunamadı.")
            return self.ws_job(job)
        self.error(404, "not_found", "Bulunamadı.")

    def do_POST(self):
        url = urlparse(self.path)
        p = url.path
        if not self.authorized({}):
            return self.error(401, "unauthorized", "Belirteç geçersiz ya da eksik.")
        b = self.body()
        if b is None:
            return self.error(400, "bad_request", "Gövde geçerli JSON nesnesi değil.")
        r = self.robot
        try:
            if p == "/api/v1/move":
                try:
                    x, y, z = (float(b[k]) for k in ("x", "y", "z"))
                except (KeyError, TypeError, ValueError):
                    return self.error(400, "bad_request", "x, y, z sayı olmalı.")
                res = r.move(x, y, z, b.get("duration_s"), bool(b.get("wait", True)))
                return self.send_json(200, res)
            if p == "/api/v1/magnet":
                return self.send_json(200, r.set_magnet(bool(b.get("on"))))
            if p == "/api/v1/torque":
                return self.send_json(200, r.torque(bool(b.get("on"))))
            if p == "/api/v1/stop":
                return self.send_json(200, r.stop())
        except Busy as e:
            msg = "Bir iş çalışıyor; komut yalnız ondan kabul edilir."
            return self.error(409, "busy", msg, job_id=e.job_id)
        if p == "/api/v1/jobs":
            code = b.get("code")
            if not isinstance(code, str) or len(code.encode()) > CODE_MAX:
                return self.error(400, "bad_request", "Kod metin olmalı ve 64 KB'ı aşmamalı.")
            job = self.jobs.submit(code, str(b.get("name") or "adsız"))
            return self.send_json(202, {"job_id": job.id, "status": "queued"})
        if p.startswith("/api/v1/jobs/") and p.endswith("/cancel"):
            job = self.jobs.jobs.get(p.split("/")[-2])
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

    def ws_telemetry(self) -> None:
        ws = self.ws_upgrade()
        if not ws:
            return
        q: queue.Queue = queue.Queue()
        self.robot.listeners.append(q)
        try:
            while not ws.closed.is_set():
                while not q.empty():
                    ev = q.get_nowait()
                    if not ws.send(ev):
                        break
                if not ws.send({"type": "state", **self.robot.snapshot()}):
                    break
                ws.closed.wait(0.05)  # 20 Hz
        finally:
            self.robot.listeners.remove(q)
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
    args = ap.parse_args()
    robot = FakeRobot()
    Handler.robot, Handler.jobs, Handler.token = robot, Jobs(robot), args.token
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    srv.daemon_threads = True
    print(f"Sahte API: http://{args.host}:{args.port}/  (belirteç: {args.token})", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
