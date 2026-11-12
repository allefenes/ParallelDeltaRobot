"""F4.5 tabla yöntemleri: board, reset_board, cell_xy, pick_place."""

from __future__ import annotations

import json

import pytest

GEO = {
    "center_mm": [0.0, 0.0],
    "cell_mm": 20.0,
    "pick_P_mm": -213.0,
    "travel_P_mm": -185.0,
}
BOARD = {"cells": "XXX...OOO", "winner": None, "pieces": [], "metrics": {}, "geometry": GEO}


def test_board_and_reset(robot, server):
    server.on("GET", "/board", body=BOARD)
    server.on("POST", "/board/reset", body={"ok": True})
    assert robot.board()["cells"] == "XXX...OOO"
    assert server.last.url.path == "/api/v1/board"
    assert robot.reset_board() is None
    assert server.last.url.path == "/api/v1/board/reset"


@pytest.mark.parametrize(
    ("cell", "xy"), [(0, (-20.0, 20.0)), (4, (0.0, 0.0)), (8, (20.0, -20.0)), (5, (20.0, 0.0))]
)
def test_cell_xy(robot, cell, xy):
    assert robot.cell_xy(cell, BOARD) == xy


@pytest.mark.parametrize("cell", [-1, 9, 1.0, True, "4"])
def test_cell_xy_rejects_bad_cell(robot, cell):
    with pytest.raises(ValueError):
        robot.cell_xy(cell, BOARD)


def test_pick_place_sequence(robot, server):
    server.on("GET", "/board", body=BOARD)
    server.on("POST", "/move", body={"accepted": True, "trajectory_id": "t", "done": True,
                                     "position_mm": [0, 0, -200]})  # fmt: skip
    server.on("POST", "/magnet", body={"ok": True, "magnet": True})
    robot.pick_place(1, 4)
    steps = []
    for req in server.requests:
        path = req.url.path.removeprefix("/api/v1")
        if path == "/move":
            body = json.loads(req.content)
            steps.append(("move", body["x"], body["y"], body["z"]))
        elif path == "/magnet":
            steps.append(("magnet", json.loads(req.content)["on"]))
    assert steps == [
        ("move", 0.0, 20.0, -185.0),
        ("move", 0.0, 20.0, -213.0),
        ("magnet", True),
        ("move", 0.0, 20.0, -185.0),
        ("move", 0.0, 0.0, -185.0),
        ("move", 0.0, 0.0, -213.0),
        ("magnet", False),
        ("move", 0.0, 0.0, -185.0),
    ]
