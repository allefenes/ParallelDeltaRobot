"""Planlayıcı testleri: profil uçları, 100 Hz örnekleme, IK sürekliliği, otomatik süre."""

from __future__ import annotations

import math

import numpy as np
import pytest
from delta_server.planning import (
    QUINTIC_PEAK_ACC,
    QUINTIC_PEAK_VEL,
    auto_duration,
    joint_rates,
    line_points,
    plan_line,
    quintic,
    sample_times,
)

TARGET = (20.0, 10.0, -200.0)


def test_quintic_endpoints_rest_to_rest():
    s = quintic(np.array([0.0, 1.0, -0.5, 1.5]))
    assert s.tolist() == [0.0, 1.0, 0.0, 1.0]
    h = 1e-6
    for tau in (0.0, 1.0):
        lo, hi = max(0.0, tau - h), min(1.0, tau + h)
        assert abs((quintic(np.array([hi]))[0] - quintic(np.array([lo]))[0]) / h) < 1e-4
    assert math.isclose(quintic(np.array([0.5]))[0], 0.5)


def test_quintic_peak_coefficients():
    tau = np.linspace(0, 1, 200001)
    s = quintic(tau)
    ds = np.gradient(s, tau)
    dds = np.gradient(ds, tau)
    assert math.isclose(ds.max(), QUINTIC_PEAK_VEL, rel_tol=1e-4)
    assert math.isclose(np.abs(dds).max(), QUINTIC_PEAK_ACC, rel_tol=1e-3)


def test_sampling_is_100hz_including_endpoints(limits):
    t = sample_times(1.0, limits.rate_hz)
    assert len(t) == 101
    assert t[0] == 0.0 and math.isclose(t[-1], 1.0)
    assert np.allclose(np.diff(t), 1.0 / limits.rate_hz)
    # Periyodun katı olmayan süre bir sonraki örneğe yuvarlanır
    t2 = sample_times(0.555, limits.rate_hz)
    assert math.isclose(t2[-1], 0.56)


@pytest.mark.parametrize("bad", [0.0, -1.0, float("nan"), float("inf")])
def test_sampling_rejects_bad_duration(bad, limits):
    with pytest.raises(ValueError):
        sample_times(bad, limits.rate_hz)


def test_line_points_straight_and_endpoints(robot):
    t = sample_times(0.8, 100.0)
    pts = line_points(robot.home_mm, TARGET, t)
    assert np.allclose(pts[0], robot.home_mm) and np.allclose(pts[-1], TARGET)
    d = np.asarray(TARGET) - np.asarray(robot.home_mm)
    rel = pts - np.asarray(robot.home_mm)
    # Tüm noktalar doğru üzerinde (çapraz çarpım sıfır)
    assert np.allclose(np.cross(rel, d), 0.0, atol=1e-9)


def test_plan_ik_continuity(robot, limits):
    plan = plan_line(robot.kin, robot.home_mm, TARGET, 1.0, limits.rate_hz)
    assert plan.ik_ok
    assert np.allclose(plan.thetas_deg[0], robot.kin.inverse(robot.home_mm))
    assert np.allclose(plan.thetas_deg[-1], robot.kin.inverse(TARGET))
    step = np.abs(np.diff(plan.thetas_deg, axis=0))
    # 100 Hz'de 1 s'lik harekette ardışık örnekler arası açı farkı küçük ve sıçramasız
    assert step.max() < 1.0
    for th, p in zip(plan.thetas_deg, plan.points_mm, strict=True):
        assert np.allclose(robot.kin.forward(tuple(th)), p, atol=1e-6)


def test_plan_unreachable_samples_are_nan(robot, limits):
    plan = plan_line(robot.kin, robot.home_mm, (0.0, 0.0, -100.0), 1.0, limits.rate_hz)
    assert not plan.ik_ok
    assert np.isnan(plan.thetas_deg[-1]).all()
    assert np.isfinite(plan.thetas_deg[0]).all()


def test_auto_duration_respects_g5_limits(robot, limits):
    T = auto_duration(
        robot.kin,
        robot.home_mm,
        TARGET,
        limits.rate_hz,
        limits.max_vel_deg_s,
        limits.max_acc_deg_s2,
        1.0,
    )
    plan = plan_line(robot.kin, robot.home_mm, TARGET, T, limits.rate_hz)
    vel, acc = joint_rates(plan.thetas_deg, limits.rate_hz)
    assert np.abs(vel).max() <= limits.max_vel_deg_s
    assert np.abs(acc).max() <= limits.max_acc_deg_s2
    # Pay çarpanı süreyi uzatır; erişilemeyen hedefte de bir süre döner
    T2 = auto_duration(
        robot.kin,
        robot.home_mm,
        TARGET,
        limits.rate_hz,
        limits.max_vel_deg_s,
        limits.max_acc_deg_s2,
        1.5,
    )
    assert math.isclose(T2, 1.5 * T)
    assert auto_duration(robot.kin, robot.home_mm, (0, 0, -100), 100.0, 300.0, 3000.0, 1.0) > 0


def test_joint_rates_pad_rest():
    th = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    vel, acc = joint_rates(th, 100.0)
    assert vel.shape == (3, 3) and acc.shape == (2, 3)
    assert vel[0, 0] == 0.0 and math.isclose(vel[1, 0], 100.0) and vel[2, 0] == 0.0
