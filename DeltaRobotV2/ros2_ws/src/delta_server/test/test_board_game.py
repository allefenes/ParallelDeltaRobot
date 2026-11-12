"""F4.5 tabla, taş ikizi ve oyun kuralları (saf Python)."""

from __future__ import annotations

import pytest
from delta_server.board_game import (
    ADJACENT,
    LINES,
    BoardTwin,
    Geometry,
    apply_move,
    best_move,
    initial_cells,
    legal_moves,
    winner,
)


@pytest.fixture
def geo(robot):
    return Geometry.from_spec(robot.spec)


def tip_at(geo, idx, z_p):
    x, y = geo.cell_xy(idx)
    return (x, y, z_p - geo.tool_offset)


def run_path(twin, geo, src, dst, offset=(0.0, 0.0)):
    for step, p in geo.pick_place_path(src, dst):
        tip = (p[0] + offset[0], p[1] + offset[1], p[2] - geo.tool_offset)
        if step == "move":
            twin.update(tip, twin._magnet)
        else:
            twin.update(tip, step == "magnet_on")


def test_geometry_from_robot_yaml(geo, robot):
    k, t = robot.spec["kinematics"], robot.spec["task"]
    assert geo.board_top == -k["base_to_floor"] + t["board_thickness"]
    assert geo.pick_p == geo.board_top + t["piece_height"] + k["ee_offset"]
    assert geo.cell_xy(0) == (-geo.cell, geo.cell)  # satır 0 = +Y, sütun 0 = -X
    assert geo.cell_xy(4) == geo.center


def test_all_cells_reachable_and_safe_at_task_heights(geo, robot, limits):
    """Her hücre alma ve taşıma yüksekliğinde erişilir, G1/G2 içinde ve G14'ü ihlal etmez."""
    for i in range(9):
        x, y = geo.cell_xy(i)
        for z in (geo.pick_p, geo.travel_p):
            ok, arm, reason = robot.kin.check_point((x, y, z))
            assert ok, f"hücre {i} z={z}: {reason} (kol {arm})"
        assert geo.pick_p - geo.tool_offset >= limits.min_tool_z_mm  # uç taş üstünde, tablada değil


def test_twin_pick_and_place_moves_piece(geo):
    twin = BoardTwin(geo)
    assert twin.cells() == initial_cells()
    run_path(twin, geo, 1, 4)
    assert twin.cells() == "X.X.X.OOO"
    m = twin.metrics.to_dict()
    assert m["picks"] == 1 and m["places"] == 1 and m["dropped"] == 0 and m["missed_picks"] == 0
    assert m["placement_error_max_mm"] == pytest.approx(0.0, abs=1e-9)


def test_twin_holds_piece_during_travel(geo):
    twin = BoardTwin(geo)
    path = geo.pick_place_path(0, 3)
    for step, p in path[:4]:  # al ve kaldır
        tip = (p[0], p[1], p[2] - geo.tool_offset)
        twin.update(tip, step in ("magnet_on",) or twin._magnet)
    held = twin.held
    assert held is not None and held.kind == "X"
    assert held.pos[2] == pytest.approx(geo.travel_p - geo.tool_offset - geo.piece_height)
    assert twin.cells()[0] == "."


def test_twin_missed_pick_when_offset(geo):
    twin = BoardTwin(geo)
    run_path(twin, geo, 1, 4, offset=(6.0, 0.0))  # 6 mm kaçık: yakalanamaz
    assert twin.cells() == initial_cells()
    assert twin.metrics.missed_picks == 1


def test_twin_placement_error_and_drop(geo):
    twin = BoardTwin(geo)
    x, y = geo.cell_xy(1)
    twin.update((x, y, geo.pick_p - geo.tool_offset), True)  # al
    dx, dy = geo.cell_xy(4)
    twin.update((dx + 3.0, dy, geo.travel_p - geo.tool_offset), True)  # 3 mm kaçık, yüksekte
    twin.update((dx + 3.0, dy, geo.travel_p - geo.tool_offset), False)  # yüksekten bırak
    m = twin.metrics.to_dict()
    assert m["dropped"] == 1
    assert m["placement_error_max_mm"] == pytest.approx(3.0)
    assert twin.cells()[4] == "X"  # 5 mm içinde: hücrede sayılır


def test_twin_release_at_last_known_position_when_tip_unknown(geo):
    twin = BoardTwin(geo)
    x, y = geo.cell_xy(2)
    twin.update((x, y, geo.pick_p - geo.tool_offset), True)
    assert twin.held is not None
    twin.update(None, False)  # konum bilinmiyor ama mıknatıs kapandı: taş son yerinde kalır
    assert twin.held is None and twin.cells()[2] == "X" and twin.metrics.places == 1


def test_twin_off_board(geo):
    twin = BoardTwin(geo)
    x, y = geo.cell_xy(2)
    twin.update((x, y, geo.pick_p - geo.tool_offset), True)
    twin.update((x + 40.0, y, geo.pick_p - geo.tool_offset), True)
    twin.update((x + 40.0, y, geo.pick_p - geo.tool_offset), False)
    assert twin.metrics.off_board == 1 and twin.cells()[2] == "."


def test_twin_reset_and_dict(geo):
    twin = BoardTwin(geo)
    run_path(twin, geo, 1, 4)
    twin.reset()
    d = twin.to_dict()
    assert d["cells"] == initial_cells() and d["winner"] is None
    assert len(d["pieces"]) == 6 and d["metrics"]["picks"] == 0
    assert d["geometry"]["travel_P_mm"] == geo.travel_p


def test_rules_adjacency_is_symmetric_and_along_lines():
    for a, ns in ADJACENT.items():
        for b in ns:
            assert a in ADJACENT[b]
            assert any(a in line and b in line for line in LINES)
    assert 3 not in ADJACENT[1]  # kenar ortaları birbirine bağlı değil


def test_rules_winner_ignores_own_start_row():
    assert winner("XXX...OOO") is None  # başlangıç satırları sayılmaz
    assert winner("...XXXOOO") == "X"
    assert winner("X...X...X") == "X"
    assert winner("OOO......") == "O"  # O için üst satır geçerli bir dizi
    assert winner("X...O...X") is None


def test_rules_moves_and_apply():
    c = initial_cells()
    moves = legal_moves(c, "X")
    assert (1, 4) in moves and all(c[d] == "." for _, d in moves)
    assert apply_move(c, (1, 4)) == "X.X.X.OOO"


def test_best_move_takes_immediate_win():
    pos = "X..X.XOO."  # X: 0, 3, 5; 0 -> 4 orta satırı tamamlar
    assert winner(apply_move(pos, best_move(pos, "X"))) == "X"


def test_best_move_blocks_opponent():
    pos = "XX.XOO..O"  # O tek tehdit: 4 -> 2 sütunu (2, 5, 8) tamamlar; X'in tek savunması 1 -> 2
    assert best_move(pos, "X") == (1, 2)


def test_best_move_none_when_blocked():
    assert legal_moves("XXXOOO...", "X") == []
    assert best_move("XXXOOO...", "X") is None
