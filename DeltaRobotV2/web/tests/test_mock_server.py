"""Sahte API sunucusunun sözleşmeye uyumu (docs/api.md): G3 reddi, kinematik, işler, HTTP + WS."""

import base64
import importlib.util
import json
import math
import os
import socket
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("mock_server", WEB / "dev" / "mock_server.py")
ms = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ms)

TOKEN = "test-token"


def test_G3_outside_cylinder_rejected():
    assert ms.check_target(0, 0, -200) is None
    for p in [(50, 0, -200), (0, 0, -300), (0, 0, -100), (30, 30, -200)]:
        req, reason = ms.check_target(*p)
        assert req == "G3" and reason.startswith("G3:")


def test_inverse_closes_chain():
    g = ms.ROBOT["geometry"]
    P = (15.0, -10.0, -210.0)
    th = ms.inverse(P)
    for a_deg, t in zip(ms.ARM_ANGLES, th, strict=True):
        a, t = math.radians(a_deg), math.radians(t)
        u = (math.cos(a), math.sin(a))
        B = (u[0] * (g["R"] + g["L1"] * math.cos(t)), u[1] * (g["R"] + g["L1"] * math.cos(t)))
        B = (*B, -g["L1"] * math.sin(t))
        C = (P[0] + u[0] * g["r"], P[1] + u[1] * g["r"], P[2])
        assert math.dist(B, C) == pytest.approx(g["L2"], abs=1e-6)


def test_robot_moves_and_rejects():
    r = ms.FakeRobot()
    res = r.move(10, 5, -205, duration_s=0.05)
    assert res["accepted"] and res["done"]
    assert res["position_mm"] == pytest.approx([10, 5, -205])
    bad = r.move(0, 0, -300)
    assert bad == {"accepted": False, "requirement": "G3", "reason": bad["reason"]}
    r.stop()
    assert r.snapshot()["state"] == "HOLDING"


def test_job_runs_starter_example_without_exec():
    r = ms.FakeRobot()
    jobs = ms.Jobs(r)
    code = (WEB / "examples" / "baslangic.py").read_text(encoding="utf-8")
    job = jobs.submit(code, "test")
    t_end = time.monotonic() + 30
    while job.status not in ms.JOB_FINAL and time.monotonic() < t_end:
        time.sleep(0.05)
    assert job.status == "done", job.output()
    out = job.output()
    assert "Reddedildi: G3" in out and "Bitti" in out
    assert r.job_id is None


def test_job_holds_control_lock():
    r = ms.FakeRobot()
    r.job_id = "job-x"
    with pytest.raises(ms.Busy):
        r.move(0, 0, -200)
    assert r.stop() == {"ok": True}  # Dur her zaman kabul


@pytest.fixture(scope="module")
def server():
    robot = ms.FakeRobot()
    ms.Handler.robot, ms.Handler.jobs, ms.Handler.token = robot, ms.Jobs(robot), TOKEN
    srv = ThreadingHTTPServer(("127.0.0.1", 0), ms.Handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1]
    srv.shutdown()


def get(port, path, token=None):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=5) as res:
        return res.status, res.headers.get("Content-Type"), res.read()


def test_http_auth_and_static(server):
    with pytest.raises(urllib.error.HTTPError) as e:
        get(server, "/api/v1/robot")
    assert e.value.code == 401
    assert json.loads(e.value.read())["error"] == "unauthorized"
    status, _, body = get(server, "/api/v1/robot", TOKEN)
    assert json.loads(body)["workspace"]["cylinder_diameter_mm"] == 82
    assert get(server, "/api/v1/health")[0] == 200
    _, ctype, body = get(server, "/")
    assert ctype.startswith("text/html") and b"importmap" in body
    assert get(server, "/js/main.js")[1].startswith("text/javascript")
    assert "web.jog.go" in json.loads(get(server, "/i18n/tr.json")[2])
    with pytest.raises(urllib.error.HTTPError):
        get(server, "/../config/robot.yaml")


@pytest.mark.skipif(
    not (WEB.parent / "cad" / "out" / "meshes" / "base.stl").is_file(),
    reason="CAD mesh'leri üretilmemiş",
)
def test_meshes_served(server):
    assert len(get(server, "/assets/meshes/bicep_1.stl")[2]) > 1000


def test_ws_telemetry_sends_state(server):
    s = socket.create_connection(("127.0.0.1", server), timeout=5)
    key = base64.b64encode(os.urandom(16)).decode()
    s.sendall(
        (
            f"GET /api/v1/ws/telemetry?token={TOKEN} HTTP/1.1\r\nHost: x\r\n"
            f"Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        ).encode()
    )
    buf = b""
    while b"\r\n\r\n" not in buf:
        buf += s.recv(4096)
    head, rest = buf.split(b"\r\n\r\n", 1)
    assert head.startswith(b"HTTP/1.1 101")
    while len(rest) < 2:
        rest += s.recv(4096)
    n = rest[1] & 0x7F
    off = 2
    if n == 126:
        while len(rest) < 4:
            rest += s.recv(4096)
        n, off = int.from_bytes(rest[2:4], "big"), 4
    while len(rest) < off + n:
        rest += s.recv(4096)
    msg = json.loads(rest[off : off + n])
    assert msg["type"] == "state" and msg["state"] in ("IDLE", "HOLDING", "RUNNING")
    assert len(msg["angles_deg"]) == 3 and len(msg["position_mm"]) == 3
    s.close()


def test_ws_accept_matches_rfc6455_sample():
    assert ms.ws_accept("dGhlIHNhbXBsZSBub25jZQ==") == "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="
