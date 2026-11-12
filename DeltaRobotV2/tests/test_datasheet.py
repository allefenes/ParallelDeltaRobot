"""Datasheet hesaplarının ve üreticisinin testleri (delta_core_py derlenmiş olmalı)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

V2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(os.environ.get("DELTA_CORE_BUILD", V2 / "build" / "core"))))
sys.path.insert(0, str(V2 / "tools" / "datasheet"))

dc = pytest.importorskip("delta_core_py")
import compute as C  # noqa: E402

PARAMS = yaml.safe_load((V2 / "config" / "robot.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def robot():
    return dc.DeltaKinematics(dc.load_params(str(V2 / "config" / "robot.yaml")))


@pytest.fixture(scope="module")
def grid(robot):
    return C.scan_workspace(robot, step=10.0)


def test_workspace_has_points_and_reasons(grid):
    assert grid.ok.sum() > 100
    assert set(grid.reason) <= {"erişilemez", "motor açı limiti", "rot başı açı limiti"}
    # Merkez ekseni çalışma alanında
    ix, iy = int(np.argmin(np.abs(grid.xs))), int(np.argmin(np.abs(grid.ys)))
    iz = int(np.argmin(np.abs(grid.zs + 200)))
    assert grid.ok[ix, iy, iz]


def test_volume_and_cylinder_consistent(grid):
    vol = C.volume_cm3(grid)
    cyl = C.usable_cylinder(grid)
    assert 0 < cyl["volume_cm3"] <= vol
    assert cyl["z_min"] <= cyl["z_max"]
    assert len(cyl["radii"]) == len(grid.zs)


def test_empty_slice_radius_is_zero(grid):
    empty = C.Grid(grid.step, grid.xs, grid.ys, grid.zs, np.zeros_like(grid.ok))
    assert C.slice_radius(empty, 0) == 0.0
    assert C.usable_cylinder(empty)["volume_cm3"] == 0.0
    assert C.largest_square(empty.ok[:, :, 0], empty.xs) == 0.0


def test_point_metrics_plausible(robot):
    m = C.point_metrics(robot, (0.0, 0.0, -200.0), PARAMS["motor"], 0.29)
    assert 0.1 < m["res_mm"] < 5
    assert 50 < m["speed_mm_s"] < 2000
    assert 0.5 < m["force_n"] < 100
    assert 1 <= m["cond"] < 10
    assert C.point_metrics(robot, (0.0, 0.0, -500.0), PARAMS["motor"], 0.29) is None


def test_metrics_scale_with_motor(robot):
    """Datasheet motor parametrelerine göre parametrik: hız ω ile, kuvvet τ ile orantılı."""
    m1 = C.point_metrics(robot, (0, 0, -200), PARAMS["motor"], 0.29)
    fast = dict(PARAMS["motor"], no_load_rpm=PARAMS["motor"]["no_load_rpm"] * 2)
    strong = dict(PARAMS["motor"], stall_torque_nm=PARAMS["motor"]["stall_torque_nm"] * 2)
    assert C.point_metrics(robot, (0, 0, -200), fast, 0.29)["speed_mm_s"] == pytest.approx(
        2 * m1["speed_mm_s"]
    )
    assert C.point_metrics(robot, (0, 0, -200), strong, 0.29)["force_n"] == pytest.approx(
        2 * m1["force_n"]
    )


def test_slice_maps_and_stats(robot, grid):
    maps = C.slice_maps(robot, grid, -200.0, PARAMS["motor"], 0.29)
    st = C.summary_stats(maps)
    assert set(st) == {"res_mm", "speed_mm_s", "force_n", "cond"}
    assert st["cond"]["min"] >= 1.0
    assert C.summary_stats({"x": np.full((2, 2), np.nan)}) == {}


def test_payload(robot):
    assert C.payload_at(robot, (0, 0, -200), PARAMS["motor"], 0.4) > 100
    assert C.payload_at(robot, (0, 0, -500), PARAMS["motor"], 0.4) == 0.0


def test_task_heights():
    h = C.task_heights(PARAMS)
    assert h["floor"] < h["board_top"] < h["piece_top"] < h["pick_P"] < h["travel_P"]
    assert h["pick_P"] - h["piece_top"] == PARAMS["kinematics"]["ee_offset"]


def test_assumption_scanners():
    text = (V2 / "config" / "robot.yaml").read_text(encoding="utf-8")
    rows = C.comment_assumptions(text)
    assert any(k == "spherical_joint_limit" for k, _ in rows)
    assert "housing.insert" in C.assumptions(PARAMS)


def test_build_datasheet(tmp_path, monkeypatch):
    import build_datasheet as B

    monkeypatch.setattr(B, "OUT", tmp_path / "ds.html")
    B.main()
    page = (tmp_path / "ds.html").read_text(encoding="utf-8")
    for anchor in (
        "ozet",
        "alan",
        "harita",
        "tabla",
        "geo",
        "motor",
        "kutle",
        "bom",
        "ros",
        "varsayim",
    ):
        assert f'id="{anchor}"' in page
    assert page.count('class="plotly-graph-div"') == 6
    assert 'pre class="mermaid"' in page


def test_scenario_section_both_states(tmp_path, monkeypatch):
    import json

    import build_datasheet as B

    monkeypatch.setattr(B, "SCENARIO", tmp_path / "yok.json")
    assert "bekliyor" in B.scenario_section()
    f = tmp_path / "m.json"
    f.write_text(
        json.dumps(
            {
                "moves": 7,
                "winner": "X",
                "cycle_mean_s": 4.2,
                "cycle_max_s": 5.0,
                "placement_error_mean_mm": 0.1,
                "placement_error_max_mm": 0.3,
                "missed_picks": 0,
                "dropped": 0,
                "off_board": 0,
            }
        )
    )
    monkeypatch.setattr(B, "SCENARIO", f)
    html = B.scenario_section()
    assert "7 hamle, kazanan X" in html and "0 / 0 / 0" in html
