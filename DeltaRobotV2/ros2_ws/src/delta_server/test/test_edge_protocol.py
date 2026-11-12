"""Kenar protokolünün sunucu tarafı (edge_protocol) birim testleri."""

from __future__ import annotations

import json
import math

import pytest
from delta_server import edge_protocol as ep


def test_heartbeat_and_commands():
    assert json.loads(ep.heartbeat(7)) == {"v": 1, "type": "heartbeat", "seq": 7}
    assert json.loads(ep.command("torque", True))["on"] is True
    assert "on" not in json.loads(ep.command("stop"))
    with pytest.raises(ep.ProtocolError):
        ep.command("magnet")
    with pytest.raises(ep.ProtocolError):
        ep.command("selfdestruct")


def test_trajectory_converts_radians_and_period():
    times = [0.0, 0.01, 0.02]
    pts = [[0.0, 0.0, 0.0], [math.radians(1), 0.0, 0.0], [math.radians(2), 0.0, 0.0]]
    m = json.loads(ep.trajectory("t1", times, pts, magnet=True))
    assert m["period_ms"] == 10
    assert m["points"][2][0] == pytest.approx(2.0)
    assert m["magnet"] is True
    single = json.loads(ep.trajectory("t2", [0.0], [[0.0, 0.0, 0.0]]))
    assert single["period_ms"] == 10


@pytest.mark.parametrize(
    "times,pts",
    [
        ([], []),  # boş
        ([0.0, 0.01], [[0, 0, 0]]),  # uyuşmayan uzunluk
        ([0.0, 0.01, 0.03], [[0, 0, 0]] * 3),  # eşit aralıklı değil
        ([0.0, 0.1], [[0, 0, 0]] * 2),  # periyot 100 ms > 50
        ([0.0, 0.001], [[0, 0, 0]] * 2),  # periyot 1 ms < 5
        ([0.0, 0.01], [[0, 0, 0], [0, math.nan, 0]]),  # G4: sayı değil
        ([0.0, 0.01], [[0, 0, 0], [0, 0]]),  # eksik eksen
    ],
)
def test_trajectory_rejections(times, pts):
    with pytest.raises(ep.ProtocolError):
        ep.trajectory("x", times, pts)


def test_parse_telemetry_ack_fault():
    tel = {
        "v": 1,
        "type": "telemetry",
        "state": "RUNNING",
        "angles": [10, 20, 30],
        "temps": [30, 31, 32],
        "loads": [5, -5, 0],
        "voltages": [12, 12, 12],
        "traj_id": None,
        "index": 4,
    }
    kind, t = ep.parse_incoming(json.dumps(tel))
    assert kind == "telemetry" and t.state == "RUNNING" and t.traj_id == "" and t.index == 4
    assert t.angles_rad[1] == pytest.approx(math.radians(20))
    assert ep.parse_incoming('{"v":1,"type":"ack","id":"a"}') == ("ack", "a")
    assert ep.parse_incoming('{"v":1,"type":"fault","code":"accel_limit","detail":"d"}') == (
        "fault",
        ("accel_limit", "d"),
    )


@pytest.mark.parametrize(
    "text",
    [
        "{bozuk",
        "[]",
        '{"v":2,"type":"ack"}',
        '{"v":1,"type":"bilinmeyen"}',
        '{"v":1,"type":"telemetry","state":"IDLE"}',
        '{"v":1,"type":"telemetry","state":"IDLE","angles":[1,2],"temps":[0,0,0],'
        '"loads":[0,0,0],"voltages":[0,0,0]}',
        '{"v":1,"type":"telemetry","state":"IDLE","angles":[1,2,"x"],"temps":[0,0,0],'
        '"loads":[0,0,0],"voltages":[0,0,0]}',
    ],
)
def test_parse_rejections(text):
    with pytest.raises(ep.ProtocolError):
        ep.parse_incoming(text)


def test_fault_requirement_mapping():
    assert ep.requirement_for("joint_limit") == "G1"
    assert ep.requirement_for("heartbeat_hold") == "G6"
    assert ep.requirement_for("heartbeat_torque_off") == "G7"
    assert ep.requirement_for("over_temperature") == "G9"
    assert ep.requirement_for("not_ready") == "DURUM"
