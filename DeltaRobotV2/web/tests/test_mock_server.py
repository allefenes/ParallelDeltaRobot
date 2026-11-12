"""Sahte API sunucusunun sözleşmeye uyumu (docs/api.md, F6): kinematik ve 1. kapı (G1, G2, G3,
G14), eklem/kartezyen hareket, anonim oturum (429/503/401), otomatik oyun, işler, HTTP + WS."""

import base64
import importlib.util
import json
import math
import os
import socket
import sys
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
sys.modules["mock_server"] = ms
_spec.loader.exec_module(ms)

TOKEN = "test-token"


# --- kinematik ve kapı ----------------------------------------------------------------------------


def test_inverse_closes_chain_and_forward_inverts():
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
    assert ms.forward(th) == pytest.approx(list(P), abs=1e-6)


@pytest.mark.parametrize(
    ("xyz", "req"),
    [((0, 0, -228), "G14"), ((60, 0, -200), "G2"), ((0, 0, -100), "G3"), ((60, 0, -140), "G1")],
)
def test_ik_rejections_match_real_gate(xyz, req):
    # Gerçek delta_core ile aynı sonuçlar (koordinatör, 2026-11-12)
    r = ms.ik_check(*xyz)
    assert r["ok"] is False and r["requirement"] == req and r["reason"].startswith(f"{req}:")


def test_ik_ok_and_fk_preview():
    r = ms.ik_check(0, 0, -200)
    assert r["ok"] and len(r["angles_deg"]) == 3
    f = ms.fk_check(r["angles_deg"])
    assert f["ok"] and f["position_mm"] == pytest.approx([0, 0, -200], abs=0.01)
    for bad in ([160, 0, 0], [-75, 0, 0]):
        f = ms.fk_check(bad)
        assert f == {"ok": False, "position_mm": None, "requirement": "G1", "reason": f["reason"]}


def test_board_cells_reachable_at_pick_and_travel_height():
    for i in range(9):
        x, y = ms.GEO.cell_xy(i)
        assert ms.ik_check(x, y, ms.GEO.pick_p)["ok"]
        assert ms.ik_check(x, y, ms.GEO.travel_p)["ok"]


# --- sahte robot ---------------------------------------------------------------------------------


def test_robot_moves_joint_and_cartesian():
    r = ms.FakeRobot(speed=20)
    res = r.move_joints([30, 10, 20])
    assert res["accepted"] and res["done"]
    assert r.snapshot()["angles_deg"] == pytest.approx([30, 10, 20], abs=0.01)
    res = r.move(10, 5, -205)
    assert res["accepted"] and res["done"]
    assert res["position_mm"] == pytest.approx([10, 5, -205], abs=0.01)
    bad = r.move(0, 0, -228)
    assert not bad["accepted"] and bad["requirement"] == "G14"
    assert r.snapshot()["position_mm"] == pytest.approx([10, 5, -205], abs=0.01)


def test_stop_holds_and_torque_returns_idle():
    r = ms.FakeRobot(speed=0.2)
    t = threading.Thread(target=r.move_joints, args=([-40, -40, -40],))
    t.start()
    time.sleep(0.2)
    r.stop()
    t.join(5)
    assert r.snapshot()["state"] == "HOLDING"
    res = r.move(0, 0, -200)
    assert not res["accepted"] and res["requirement"] == "DURUM"
    r.torque(True)
    assert r.snapshot()["state"] == "IDLE"


def test_job_holds_control_lock():
    r = ms.FakeRobot()
    r.job_id = "job-x"
    with pytest.raises(ms.Busy):
        r.move(0, 0, -200)
    assert r.stop() == {"ok": True}  # Dur her zaman kabul


def test_job_runs_starter_example_without_exec():
    r = ms.FakeRobot(speed=20)
    jobs = ms.Jobs(r)
    code = (WEB / "examples" / "baslangic.py").read_text(encoding="utf-8")
    job = jobs.submit(code, "test")
    t_end = time.monotonic() + 30
    while job.status not in ms.JOB_FINAL and time.monotonic() < t_end:
        time.sleep(0.05)
    assert job.status == "done", job.output()
    out = job.output()
    # (0, 0, -300) yolunda önce G14 (uç tabla altına) ihlal edilir
    assert "Reddedildi: G14" in out and "Bitti" in out
    assert r.job_id is None


def test_auto_game_plays_to_finish():
    s = ms.Session("t", speed=50, max_moves=6, rate=100)
    s.auto.start()
    assert s.robot.job_id == ms.AUTO_OWNER
    with pytest.raises(ms.Busy):
        s.robot.move(0, 0, -200)  # manuel komut oyun sürerken reddedilir
    t_end = time.monotonic() + 60
    while s.auto.running and time.monotonic() < t_end:
        time.sleep(0.05)
    b = s.board()
    a = b["auto"]
    assert a["status"] == "finished", a
    assert 1 <= len(a["moves"]) <= 6
    assert a["winner"] == b["winner"]
    for n, m in enumerate(a["moves"], 1):
        assert m["n"] == n and m["kind"] == ("X" if n % 2 else "O")
        assert m["to"] in ms.bg.ADJACENT[m["from"]]
    assert b["metrics"]["picks"] == b["metrics"]["places"] == len(a["moves"])
    assert s.robot.job_id is None


def test_auto_stop_marks_stopped():
    s = ms.Session("t", speed=2, max_moves=20, rate=100)
    s.auto.start()
    time.sleep(0.3)
    s.auto.stop()
    assert s.board()["auto"]["status"] == "stopped"
    assert s.robot.job_id is None


# --- HTTP ----------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def server():
    ms.Handler.sessions = ms.Sessions(
        dev_token=TOKEN, speed=20, max_sessions=2, per_ip_per_min=3, idle_timeout_s=600
    )
    srv = ThreadingHTTPServer(("127.0.0.1", 0), ms.Handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1]
    srv.shutdown()


def call(port, method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status, res.headers.get("Content-Type"), res.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type"), e.read()


def test_http_auth_and_static(server):
    status, _, body = call(server, "GET", "/api/v1/robot")
    assert status == 401 and json.loads(body)["error"] == "unauthorized"
    status, _, body = call(server, "GET", "/api/v1/robot", token=TOKEN)
    assert json.loads(body)["workspace"]["z_bottom_mm"] == -221
    status, _, body = call(server, "GET", "/api/v1/health")
    assert status == 200 and json.loads(body)["mode"] == "sim"
    _, ctype, body = call(server, "GET", "/")
    assert ctype.startswith("text/html") and b"importmap" in body
    assert call(server, "GET", "/js/main.js")[1].startswith("text/javascript")
    assert "web.exp.live_soon" in json.loads(call(server, "GET", "/i18n/tr.json")[2])
    assert call(server, "GET", "/../config/robot.yaml")[0] == 404


def test_http_f6_endpoints(server):
    t = TOKEN
    ok = json.loads(
        call(server, "POST", "/api/v1/kinematics/ik", {"x": 0, "y": 0, "z": -228}, t)[2]
    )
    assert ok["requirement"] == "G14" and ok["angles_deg"] is not None
    fk = json.loads(
        call(server, "POST", "/api/v1/kinematics/fk", {"angles_deg": [20, 20, 20]}, t)[2]
    )
    assert fk["ok"] and len(fk["position_mm"]) == 3
    assert call(server, "POST", "/api/v1/kinematics/fk", {"angles_deg": [1, 2]}, t)[0] == 400
    mv = json.loads(call(server, "POST", "/api/v1/move_joints", {"angles_deg": [20, 20, 20]}, t)[2])
    assert mv["accepted"] and mv["done"]
    b = json.loads(call(server, "GET", "/api/v1/board", token=t)[2])
    assert b["cells"] == "XXX...OOO" and b["auto"]["status"] == "idle"
    assert json.loads(call(server, "POST", "/api/v1/auto/start", {}, t)[2]) == {"ok": True}
    assert call(server, "POST", "/api/v1/board/reset", {}, t)[0] == 409
    assert call(server, "POST", "/api/v1/move", {"x": 0, "y": 0, "z": -200}, t)[0] == 409
    assert json.loads(call(server, "POST", "/api/v1/auto/stop", {}, t)[2]) == {"ok": True}
    b = json.loads(call(server, "GET", "/api/v1/board", token=t)[2])
    assert b["auto"]["status"] == "stopped"
    assert json.loads(call(server, "GET", "/api/v1/state", token=t)[2])["state"] == "IDLE"
    assert call(server, "POST", "/api/v1/board/reset", {}, t)[0] == 200


def test_session_create_limits_and_expiry(server):
    sessions = ms.Handler.sessions
    st, _, body = call(server, "POST", "/api/v1/session", {})
    assert st == 201
    tok = json.loads(body)["token"]
    assert json.loads(body)["idle_timeout_s"] == 600
    assert call(server, "GET", "/api/v1/state", token=tok)[0] == 200
    assert call(server, "POST", "/api/v1/session", {})[0] == 201
    st, _, body = call(server, "POST", "/api/v1/session", {})
    assert st == 503 and json.loads(body)["error"] == "capacity"
    # Boşta kalan oturum silinir; sonraki çağrı 401.
    sessions.by_token[tok].last_seen -= 10_000
    sessions.sweep()
    assert call(server, "GET", "/api/v1/state", token=tok)[0] == 401
    assert call(server, "POST", "/api/v1/session", {})[0] == 201  # yer açıldı (3. istek)
    st, _, body = call(server, "POST", "/api/v1/session", {})
    assert st == 429 and json.loads(body)["error"] == "rate_limited"


def test_per_session_request_rate_limit():
    s = ms.Session("t", speed=1, max_moves=1, rate=5)
    assert all(s.hit() for _ in range(5))
    assert not s.hit()


@pytest.mark.skipif(
    not (WEB.parent / "cad" / "out" / "meshes" / "base.stl").is_file(),
    reason="CAD mesh'leri üretilmemiş",
)
def test_meshes_served(server):
    assert len(call(server, "GET", "/assets/meshes/bicep_1.stl")[2]) > 1000


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
