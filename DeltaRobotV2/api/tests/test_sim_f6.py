"""F6 deneyim arayüzü arka ucu: anonim oturumlar, kötüye kullanım korumaları, manuel mod
(FK/IK önizleme, eklem uzayında hareket), otomatik tic-tac-toe, yalıtım ve IDOR.

SimBackend delta_core_py gerektirir (dev imajında build/core); yoksa simülasyon testleri atlanır.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from delta_api.app import create_app
from delta_api.auth import RateLimiter
from delta_api.sessions import Limits, Sessions

ROOT = Path(__file__).resolve().parents[2]


def test_rate_limiter_window():
    now = [0.0]
    rl = RateLimiter(2, 1.0, clock=lambda: now[0])
    assert rl.allow("a") and rl.allow("a") and not rl.allow("a")
    assert rl.allow("b")
    now[0] = 1.01
    assert rl.allow("a")
    now[0] = 5.0
    rl.prune()
    assert rl._events == {}


dc = pytest.importorskip("delta_core_py")
from delta_server.robot import Robot  # noqa: E402

from delta_api.sim_backend import SimBackend  # noqa: E402


@pytest.fixture(scope="module")
def robot():
    return Robot.load(str(ROOT / "config" / "robot.yaml"))


def make_sim(robot, limits=None, clock=time.monotonic, scale=50.0):
    sessions = Sessions(
        "ws://127.0.0.1:1/run",
        "s",
        factory=lambda: SimBackend(robot, time_scale=scale),
        limits=limits or Limits(),
        clock=clock,
    )
    return TestClient(create_app(None, None, sessions=sessions)), sessions


def session(c) -> dict:
    r = c.post("/api/v1/session")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["idle_timeout_s"] > 0 and len(body["token"]) >= 24
    return {"Authorization": f"Bearer {body['token']}"}


def wait_board(c, h, cond, timeout=60.0):
    end = time.monotonic() + timeout
    b = c.get("/api/v1/board", headers=h).json()
    while time.monotonic() < end and not cond(b):
        time.sleep(0.05)
        b = c.get("/api/v1/board", headers=h).json()
    return b


# --- oturumlar ve kötüye kullanım korumaları ------------------------------------------------


def test_anonymous_session_required_and_isolated(robot):
    c, _ = make_sim(robot)
    with c:
        assert c.get("/api/v1/health").json()["mode"] == "sim"
        assert c.get("/api/v1/state").status_code == 401
        a, b = session(c), session(c)
        c.post("/api/v1/move", headers=a, json={"x": 20, "y": 0, "z": -200})
        c.post("/api/v1/magnet", headers=a, json={"on": True})
        sa = c.get("/api/v1/state", headers=a).json()
        sb = c.get("/api/v1/state", headers=b).json()
    assert sa["position_mm"][0] == pytest.approx(20, abs=0.05) and sa["magnet"]
    assert sb["position_mm"][0] == pytest.approx(0, abs=0.05) and not sb["magnet"]


def test_session_rate_limit_per_ip(robot):
    c, _ = make_sim(robot, Limits(sessions_per_ip_per_min=2))
    with c:
        assert c.post("/api/v1/session").status_code == 201
        assert c.post("/api/v1/session").status_code == 201
        r = c.post("/api/v1/session")
    assert r.status_code == 429 and r.json()["error"] == "rate_limited"


def test_session_capacity(robot):
    c, _ = make_sim(robot, Limits(max_sessions=1))
    with c:
        session(c)
        r = c.post("/api/v1/session")
    assert r.status_code == 503 and r.json()["error"] == "capacity"


def test_request_rate_limit_per_session(robot):
    c, _ = make_sim(robot, Limits(requests_per_s=3))
    with c:
        h = session(c)
        codes = [c.get("/api/v1/state", headers=h).status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200] and 429 in codes[3:]


def test_idle_session_reaped_then_401(robot):
    now = [1000.0]
    c, sessions = make_sim(robot, Limits(idle_timeout_s=10), clock=lambda: now[0])
    with c:
        h = session(c)
        assert c.get("/api/v1/state", headers=h).status_code == 200
        now[0] += 5
        assert asyncio.run_coroutine_threadsafe(sessions.reap(), sessions._loop).result(5) == 0
        now[0] += 11
        assert asyncio.run_coroutine_threadsafe(sessions.reap(), sessions._loop).result(5) == 1
        assert c.get("/api/v1/state", headers=h).status_code == 401
        assert len(sessions) == 0


# --- manuel mod ----------------------------------------------------------------------------------


def test_ik_fk_preview_roundtrip(robot):
    c, _ = make_sim(robot)
    with c:
        h = session(c)
        ik = c.post("/api/v1/kinematics/ik", headers=h, json={"x": 20, "y": 10, "z": -200}).json()
        assert ik["ok"] and len(ik["angles_deg"]) == 3
        fk = c.post("/api/v1/kinematics/fk", headers=h, json={"angles_deg": ik["angles_deg"]})
        assert fk.json()["ok"]
        assert fk.json()["position_mm"] == pytest.approx([20, 10, -200], abs=0.01)
        # önizleme robotu hareket ettirmez
        x = c.get("/api/v1/state", headers=h).json()["position_mm"][0]
        assert x == pytest.approx(0, abs=0.05)


@pytest.mark.parametrize(
    ("kind", "body", "req"),
    [
        ("ik", {"x": 0, "y": 0, "z": -228}, "G14"),
        ("ik", {"x": 60, "y": 0, "z": -200}, "G2"),
        ("ik", {"x": 0, "y": 0, "z": -100}, "G3"),
        ("fk", {"angles_deg": [160, 0, 0]}, "G1"),
        ("fk", {"angles_deg": [-75, 0, 0]}, "G1"),
    ],
)
def test_preview_rejections(robot, kind, body, req):
    c, _ = make_sim(robot)
    with c:
        h = session(c)
        r = c.post(f"/api/v1/kinematics/{kind}", headers=h, json=body).json()
    assert r["ok"] is False and r["requirement"] == req, r
    assert r["reason"].startswith(req)


@pytest.mark.parametrize(
    "raw",
    [
        '{"angles_deg": [1, 2]}',
        '{"angles_deg": [1, 2, "x"]}',
        '{"angles_deg": [1, 2, 1e999]}',
        '{"x": 1, "y": 2}',
    ],
)
def test_preview_bad_request(robot, raw):
    c, _ = make_sim(robot)
    with c:
        h = {**session(c), "content-type": "application/json"}
        kind = "fk" if "angles_deg" in raw else "ik"
        r = c.post(f"/api/v1/kinematics/{kind}", headers=h, content=raw)
    assert r.status_code == 400


def test_move_joints_smooth_and_gated(robot):
    c, _ = make_sim(robot)
    with c:
        h = session(c)
        body = {"x": -15, "y": 15, "z": -205}
        target = c.post("/api/v1/kinematics/ik", headers=h, json=body).json()["angles_deg"]
        r = c.post("/api/v1/move_joints", headers=h, json={"angles_deg": target}).json()
        assert r["accepted"] and r["done"]
        assert r["position_mm"] == pytest.approx([-15, 15, -205], abs=0.05)
        bad = c.post("/api/v1/move_joints", headers=h, json={"angles_deg": [150, 150, 150]})
        assert bad.json()["accepted"] is False
        assert bad.json()["requirement"] in ("G1", "G2", "G3", "G14")


def test_move_joints_is_not_teleport(robot):
    """Eklem uzayı hareketi zaman alır: wait=false sonrası robot RUNNING ve ara pozda."""
    c, _ = make_sim(robot, scale=1.0)
    with c:
        h = session(c)
        body = {"x": 0, "y": 0, "z": -160}
        target = c.post("/api/v1/kinematics/ik", headers=h, json=body).json()["angles_deg"]
        move = {"angles_deg": target, "duration_s": 2.0, "wait": False}
        c.post("/api/v1/move_joints", headers=h, json=move)
        time.sleep(0.5)
        s = c.get("/api/v1/state", headers=h).json()
        assert s["state"] == "RUNNING" and -200 < s["position_mm"][2] < -160
        c.post("/api/v1/stop", headers=h)
        assert c.get("/api/v1/state", headers=h).json()["state"] == "HOLDING"


# --- otomatik mod --------------------------------------------------------------------------------


def test_auto_game_plays_to_end(robot):
    c, _ = make_sim(robot, scale=200.0)
    with c:
        h = session(c)
        assert c.post("/api/v1/auto/start", headers=h).json() == {"ok": True}
        # oyun sürerken elle komut reddedilir
        r = c.post("/api/v1/move", headers=h, json={"x": 0, "y": 0, "z": -200})
        assert r.status_code == 409
        b = wait_board(c, h, lambda b: b["auto"]["status"] != "playing", timeout=120)
    a = b["auto"]
    assert a["status"] == "finished", a
    assert len(a["moves"]) >= 3
    assert b["winner"] is not None or len(a["moves"]) == 20
    m = b["metrics"]
    assert m["picks"] == m["places"] == len(a["moves"])
    assert m["dropped"] == m["missed_picks"] == m["off_board"] == 0


def test_auto_stop_and_restart(robot):
    c, _ = make_sim(robot, scale=5.0)
    with c:
        h = session(c)
        c.post("/api/v1/auto/start", headers=h)
        time.sleep(0.3)
        assert c.post("/api/v1/stop", headers=h).json() == {"ok": True}  # dur oyunu da keser
        b = wait_board(c, h, lambda b: b["auto"]["status"] != "playing", timeout=5)
        assert b["auto"]["status"] == "stopped"
        c.post("/api/v1/auto/stop", headers=h)
        assert c.get("/api/v1/state", headers=h).json()["state"] == "IDLE"
        assert c.post("/api/v1/board/reset", headers=h).json() == {"ok": True}
        b = c.get("/api/v1/board", headers=h).json()
        assert b["cells"] == "XXX...OOO" and b["auto"]["status"] == "idle"


def test_robot_mode_rejects_ui_methods():
    from delta_api.auth import Tokens
    from delta_api.backend import FakeBackend

    tok = "test-belirteci-0123456789"
    c = TestClient(create_app(FakeBackend(), Tokens({"t": tok})))
    with c:
        h = {"Authorization": f"Bearer {tok}"}
        assert c.post("/api/v1/session").status_code == 404
        r = c.post("/api/v1/kinematics/ik", headers=h, json={"x": 0, "y": 0, "z": -200})
        assert r.status_code == 404


def test_job_idor_between_visitors(robot):
    c, _ = make_sim(robot)
    with c:
        a, b = session(c), session(c)
        jid = c.post("/api/v1/jobs", headers=a, json={"code": "print(1)"}).json()["job_id"]
        assert c.get(f"/api/v1/jobs/{jid}", headers=a).status_code == 200
        assert c.get(f"/api/v1/jobs/{jid}", headers=b).status_code == 404
        assert c.post(f"/api/v1/jobs/{jid}/cancel", headers=b).status_code == 404
