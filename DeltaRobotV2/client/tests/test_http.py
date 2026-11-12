"""HTTPS taşıması: uç noktalar, gövdeler, hata eşlemesi."""

from __future__ import annotations

import httpx
import pytest

from delta_robot import (
    AuthError,
    CommandRejected,
    DeltaError,
    MoveNotCompleted,
    MoveResult,
    Robot,
    RobotBusy,
    RobotUnavailable,
    State,
)

STATE = {
    "state": "IDLE",
    "angles_deg": [1.0, 2.0, 3.0],
    "position_mm": [0.0, 0.0, -200.0],
    "magnet": False,
    "temps_c": [30, 31, 32],
    "loads": [0, 0, 0],
    "voltages": [12.0, 12.0, 12.0],
    "trajectory_id": "traj-0001-ab12cd",
    "edge_connected": True,
    "job_id": None,
}


def test_info_uses_prefix_and_bearer(robot, server):
    server.on("GET", "/robot", body={"name": "Delta Robotics V2", "home_mm": [0, 0, -200]})
    info = robot.info()
    assert info["home_mm"] == [0, 0, -200]
    assert str(server.last.url) == "https://robot.test:8000/api/v1/robot"
    assert server.last.headers["Authorization"] == "Bearer tok"


def test_state_dataclass(robot, server):
    server.on("GET", "/state", body=STATE)
    s = robot.state()
    assert isinstance(s, State)
    assert s.state == "IDLE"
    assert s.angles_deg == (1.0, 2.0, 3.0)
    assert s.position_mm == (0.0, 0.0, -200.0)
    assert s.temps_c == (30.0, 31.0, 32.0)
    assert s.edge_connected is True
    assert s.job_id is None
    assert s.raw == STATE


def test_state_null_position(robot, server):
    server.on("GET", "/state", body={**STATE, "position_mm": None, "state": "FAULT"})
    s = robot.state()
    assert s.position_mm is None
    assert s.state == "FAULT"


def test_move_body_and_result(robot, server):
    body = {"accepted": True, "trajectory_id": "t2", "done": True, "position_mm": [20, 10, -200]}
    server.on("POST", "/move", body=body)
    r = robot.move_to(20, 10, -200)
    assert isinstance(r, MoveResult)
    assert r.accepted and r.done
    assert r.position_mm == (20.0, 10.0, -200.0)
    assert r.trajectory_id == "t2"
    expected = {"x": 20.0, "y": 10.0, "z": -200.0, "duration_s": None, "wait": True}
    assert server.last_json() == expected


def test_move_wait_extends_timeout(robot, server):
    server.on("POST", "/move", body={"accepted": True, "done": True})
    robot.move_to(0, 0, -200, duration=2.0)
    assert server.last_json()["duration_s"] == 2.0
    assert server.last.extensions["timeout"]["read"] == pytest.approx(10.0 + 2.0 + 5.0)
    robot.move_to(0, 0, -200)
    assert server.last.extensions["timeout"]["read"] == pytest.approx(10.0 + 30.0 + 5.0)


def test_move_no_wait_uses_default_timeout(robot, server):
    server.on("POST", "/move", body={"accepted": True, "trajectory_id": "t3"})
    r = robot.move_to(0, 0, -200, wait=False)
    assert r.done is None
    assert server.last_json()["wait"] is False
    assert server.last.extensions["timeout"]["read"] == pytest.approx(10.0)


def test_move_rejected_raises(robot, server):
    reason = "G2: rot başı açı limiti (hedef yol, kol 2, örnek 66)"
    server.on("POST", "/move", body={"accepted": False, "requirement": "G2", "reason": reason})
    with pytest.raises(CommandRejected) as info:
        robot.move_to(0, 0, -300)
    exc = info.value
    assert exc.requirement == "G2"
    assert exc.reason == reason
    assert str(exc) == reason
    assert isinstance(exc, DeltaError)
    assert exc.result.accepted is False


def test_move_rejected_check_false(robot, server):
    server.on("POST", "/move", body={"accepted": False, "requirement": "G1", "reason": "dışarıda"})
    r = robot.move_to(0, 0, -300, check=False)
    assert r.accepted is False
    assert r.requirement == "G1"
    assert r.reason == "dışarıda"


def test_move_not_completed(robot, server):
    server.on("POST", "/move", body={"accepted": True, "done": False, "reason": "bekçi"})
    with pytest.raises(MoveNotCompleted) as info:
        robot.move_to(0, 0, -200)
    assert info.value.reason == "bekçi"
    assert robot.move_to(0, 0, -200, check=False).done is False


def test_magnet_torque_stop(robot, server):
    server.on("POST", "/magnet", body={"ok": True, "magnet": True})
    server.on("POST", "/torque", body={"ok": True})
    server.on("POST", "/stop", body={"ok": True})
    assert robot.magnet(True) is True
    assert server.last_json() == {"on": True}
    assert robot.torque(False) is None
    assert server.last_json() == {"on": False}
    assert robot.stop() is None
    assert server.last.url.path == "/api/v1/stop"
    assert server.last_json() == {}


@pytest.mark.parametrize(
    ("status", "code", "cls"),
    [
        (401, "unauthorized", AuthError),
        (409, "busy", RobotBusy),
        (503, "robot_unavailable", RobotUnavailable),
        (400, "bad_request", DeltaError),
        (404, "not_found", DeltaError),
        (500, "internal", DeltaError),
    ],
)
def test_error_mapping(robot, server, status, code, cls):
    server.on("GET", "/state", status=status, body={"error": code, "message": "mesaj"})
    with pytest.raises(cls) as info:
        robot.state()
    assert type(info.value) is cls
    assert info.value.status == status
    assert info.value.code == code
    assert info.value.message == "mesaj"


def test_busy_exposes_job_id(robot, server):
    body = {"error": "busy", "message": "iş çalışıyor", "job_id": "job-0001-ab12"}
    server.on("POST", "/stop", status=409, body=body)
    with pytest.raises(RobotBusy) as info:
        robot.stop()
    assert info.value.job_id == "job-0001-ab12"


def test_error_non_json_body():
    def handler(_req):
        return httpx.Response(502, text="Bad Gateway")

    with Robot("https://x", _http_transport=httpx.MockTransport(handler)) as r:
        with pytest.raises(DeltaError) as info:
            r.info()
    assert info.value.status == 502
    assert info.value.message == "Bad Gateway"


def test_error_empty_body_falls_back_to_status():
    transport = httpx.MockTransport(lambda _r: httpx.Response(500))
    with Robot("https://x", _http_transport=transport) as r:
        with pytest.raises(DeltaError, match="HTTP 500"):
            r.info()


def test_invalid_success_body():
    def handler(_req):
        return httpx.Response(200, json=[1, 2])

    with Robot("https://x", _http_transport=httpx.MockTransport(handler)) as r:
        with pytest.raises(DeltaError, match="geçersiz"):
            r.state()


def test_connection_error():
    def handler(req):
        raise httpx.ConnectError("reddedildi", request=req)

    with Robot("https://x", _http_transport=httpx.MockTransport(handler)) as r:
        with pytest.raises(DeltaError) as info:
            r.state()
    assert info.value.code == "connection"


def test_no_token_no_header():
    seen = []

    def handler(req):
        seen.append(req)
        return httpx.Response(200, json={"name": "x"})

    with Robot("https://x/", _http_transport=httpx.MockTransport(handler)) as r:
        r.info()
    assert "Authorization" not in seen[0].headers
    assert str(seen[0].url) == "https://x/api/v1/robot"


def test_unknown_method(robot):
    with pytest.raises(ValueError):
        robot._transport.call("dance")


def test_repr(robot):
    assert "https" in repr(robot)
