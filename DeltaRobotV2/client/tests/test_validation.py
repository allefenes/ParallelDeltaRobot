"""İstemci tarafı girdi denetimi: hiçbir geçersiz değer sunucuya gitmez."""

from __future__ import annotations

import math

import pytest


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf, True, False, "1", None, [1]])
@pytest.mark.parametrize("axis", [0, 1, 2])
def test_bad_coordinates_rejected(robot, server, bad, axis):
    coords = [0.0, 0.0, -200.0]
    coords[axis] = bad
    with pytest.raises(ValueError):
        robot.move_to(*coords)
    assert server.requests == []


@pytest.mark.parametrize("bad", [math.nan, math.inf, 0, -1.0, True])
def test_bad_duration_rejected(robot, server, bad):
    with pytest.raises(ValueError):
        robot.move_to(0, 0, -200, duration=bad)
    assert server.requests == []


def test_wait_must_be_bool(robot, server):
    with pytest.raises(TypeError):
        robot.move_to(0, 0, -200, wait=1)
    assert server.requests == []


@pytest.mark.parametrize("method", ["magnet", "torque"])
def test_flags_must_be_bool(robot, server, method):
    with pytest.raises(TypeError):
        getattr(robot, method)(1)
    assert server.requests == []


def test_int_coordinates_become_float(robot, server):
    server.on("POST", "/move", body={"accepted": True, "done": True})
    robot.move_to(1, -2, -200, duration=1)
    body = server.last_json()
    assert body["x"] == 1.0 and isinstance(body["x"], float)
    assert body["duration_s"] == 1.0
