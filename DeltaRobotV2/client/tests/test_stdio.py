"""stdio taşıması: bellek içi akışlarla satır protokolü."""

from __future__ import annotations

import io
import json
import sys

import pytest

from delta_robot import (
    AuthError,
    CommandRejected,
    DeltaError,
    Robot,
    RobotBusy,
    RobotUnavailable,
)

PREFIX = "\x1eDELTA "


def make(*responses: object) -> tuple[Robot, io.StringIO]:
    lines = [r if isinstance(r, str) else json.dumps(r) for r in responses]
    stdin = io.StringIO("".join(line + "\n" for line in lines))
    stdout = io.StringIO()
    return Robot(_stdio=(stdin, stdout)), stdout


def sent(stdout: io.StringIO) -> list[dict]:
    out = []
    # splitlines() \x1e'yi de satır sonu sayar; protokol yalnız \n ile ayrılır.
    for line in stdout.getvalue().split("\n")[:-1]:
        assert line.startswith(PREFIX)
        out.append(json.loads(line[len(PREFIX) :]))
    return out


def test_request_line_format_and_ids():
    robot, stdout = make(
        {"id": 1, "result": {"name": "Delta Robotics V2"}},
        {"id": 2, "result": {"state": "IDLE", "position_mm": None}},
    )
    assert robot.transport_name == "stdio"
    assert robot.info()["name"] == "Delta Robotics V2"
    assert robot.state().state == "IDLE"
    raw = stdout.getvalue()
    assert raw.startswith(PREFIX) and raw.endswith("\n")
    assert sent(stdout) == [
        {"id": 1, "method": "robot", "params": {}},
        {"id": 2, "method": "state", "params": {}},
    ]


def test_all_methods_and_params():
    robot, stdout = make(
        {"id": 1, "result": {"accepted": True, "done": True, "position_mm": [1, 2, -200]}},
        {"id": 2, "result": {"ok": True, "magnet": True}},
        {"id": 3, "result": {"ok": True}},
        {"id": 4, "result": {"ok": True}},
    )
    r = robot.move_to(1, 2, -200, duration=1.5)
    assert r.position_mm == (1.0, 2.0, -200.0)
    assert robot.magnet(True) is True
    robot.torque(True)
    robot.stop()
    msgs = sent(stdout)
    assert [m["method"] for m in msgs] == ["move", "magnet", "torque", "stop"]
    assert msgs[0]["params"] == {"x": 1.0, "y": 2.0, "z": -200.0, "duration_s": 1.5, "wait": True}
    assert msgs[1]["params"] == {"on": True}
    assert msgs[3]["params"] == {}


def test_skips_blank_stale_and_foreign_lines():
    robot, _ = make("", "[1, 2]", {"id": 99, "result": {}}, {"id": 1, "result": {"name": "ok"}})
    assert robot.info() == {"name": "ok"}


def test_rejected_over_stdio():
    robot, _ = make(
        {"id": 1, "result": {"accepted": False, "requirement": "G3", "reason": "çarpışma"}}
    )
    with pytest.raises(CommandRejected) as info:
        robot.move_to(0, 0, -200)
    assert (info.value.requirement, info.value.reason) == ("G3", "çarpışma")


@pytest.mark.parametrize(
    ("code", "cls"),
    [
        ("unauthorized", AuthError),
        ("busy", RobotBusy),
        ("robot_unavailable", RobotUnavailable),
        ("bad_request", DeltaError),
    ],
)
def test_error_codes(code, cls):
    robot, _ = make({"id": 1, "error": {"code": code, "message": "mesaj"}})
    with pytest.raises(cls) as info:
        robot.state()
    assert type(info.value) is cls
    assert info.value.code == code
    assert info.value.message == "mesaj"


def test_error_as_plain_string():
    robot, _ = make({"id": 1, "error": "bozuk"})
    with pytest.raises(DeltaError, match="bozuk"):
        robot.state()


def test_eof_raises():
    robot, _ = make()
    with pytest.raises(DeltaError) as info:
        robot.state()
    assert info.value.code == "connection"


def test_invalid_json_raises():
    robot, _ = make("not json")
    with pytest.raises(DeltaError, match="geçersiz"):
        robot.state()


def test_missing_result_raises():
    robot, _ = make({"id": 1})
    with pytest.raises(DeltaError, match="result"):
        robot.state()


def test_nan_never_written():
    robot, stdout = make()
    with pytest.raises(ValueError):
        robot.move_to(float("nan"), 0, -200)
    assert stdout.getvalue() == ""


def test_telemetry_not_supported():
    robot, _ = make()
    with pytest.raises(DeltaError, match="ağ taşıması"):
        next(robot.telemetry())


def test_env_selects_stdio_with_process_streams(monkeypatch):
    stdin = io.StringIO(json.dumps({"id": 1, "result": {"ok": True}}) + "\n")
    stdout = io.StringIO()
    monkeypatch.setenv("DELTA_TRANSPORT", "stdio")
    monkeypatch.setattr(sys, "__stdin__", stdin)
    monkeypatch.setattr(sys, "__stdout__", stdout)
    # Kullanıcının sys.stdout'u yönlendirmesi protokolü etkilemez.
    monkeypatch.setattr(sys, "stdout", io.StringIO())
    with Robot() as robot:
        assert robot.transport_name == "stdio"
        robot.stop()
    assert sent(stdout) == [{"id": 1, "method": "stop", "params": {}}]


def test_missing_streams(monkeypatch):
    monkeypatch.setenv("DELTA_TRANSPORT", "stdio")
    monkeypatch.setattr(sys, "__stdin__", None)
    robot = Robot()
    with pytest.raises(DeltaError, match="akış"):
        robot.state()
