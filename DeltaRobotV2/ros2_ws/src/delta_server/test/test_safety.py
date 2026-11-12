"""1. kapı (süpervizör) testleri: her ret yolu, test adında gereksinim numarasıyla.

Sınır sayıları koda yazılmaz: açı/rot başı limitleri robot.yaml'dan (delta_core), hız/ivme
sınırları server.yaml'dan gelir.
"""

from __future__ import annotations

import numpy as np
from delta_server.planning import plan_line, sample_times
from delta_server.safety import check_time_grid, validate

TARGET = (20.0, 10.0, -200.0)


def hold(theta_deg, n=10, rate=100.0):
    """Sabit açıda bekleyen n örnekli yörünge."""
    return np.tile(np.asarray(theta_deg, float), (n, 1)), np.arange(n) / rate


def planned(robot, limits, target, duration=1.0):
    plan = plan_line(robot.kin, robot.home_mm, target, duration, limits.rate_hz)
    return plan.thetas_deg, plan.times, plan.points_mm


def test_valid_trajectory_accepted(robot, limits):
    th, t, cart = planned(robot, limits, TARGET)
    home = robot.kin.inverse(robot.home_mm)
    v = validate(robot.kin, th, t, limits, cartesian_mm=cart, current_deg=home)
    assert v.accepted, v.message
    assert v.message == "kabul" and v.requirement == "" and v.index == -1


def test_G1_motor_limit_rejected(robot, limits):
    lo = robot.params.motor_limit_min
    th, t = hold((lo - 5.0, 0.0, 0.0))
    v = validate(robot.kin, th, t, limits)
    assert not v.accepted and v.requirement == "G1"
    assert "motor açı limiti" in v.reason and "kol 1" in v.reason and v.index == 0


def test_G1_motor_limit_rejected_mid_trajectory(robot, limits):
    """Limiti yörüngenin ortasında aşan tek örnek de tüm yörüngeyi reddettirir."""
    home = np.asarray(robot.kin.inverse(robot.home_mm))
    th, t = hold(home, n=50)
    th[25, 2] = robot.params.motor_limit_max + 1.0
    v = validate(robot.kin, th, t, limits)
    assert v.requirement == "G1" and v.index == 25 and "kol 3" in v.reason


def test_G1_or_G2_planned_out_of_limit_point(robot, limits):
    th, t, cart = planned(robot, limits, (60.0, 0.0, -140.0))
    v = validate(robot.kin, th, t, limits, cartesian_mm=cart)
    assert not v.accepted and v.requirement in ("G1", "G2")
    assert "hedef yol" in v.reason


def test_G2_rod_tilt_rejected(robot, limits):
    theta = robot.kin.inverse((60.0, 60.0, -200.0))
    lo, hi = robot.params.motor_limit_min, robot.params.motor_limit_max
    assert all(lo <= a <= hi for a in theta)  # motor limitinde değil, yalnız rot başında
    th, t = hold(theta)
    v = validate(robot.kin, th, t, limits)
    assert not v.accepted and v.requirement == "G2" and "rot başı" in v.reason


def test_G3_unreachable_target_rejected(robot, limits):
    th, t, cart = planned(robot, limits, (0.0, 0.0, -100.0))
    v = validate(robot.kin, th, t, limits, cartesian_mm=cart)
    assert not v.accepted and v.requirement == "G3" and "erişilemez" in v.reason


def test_G3_joints_inconsistent_with_plan_rejected(robot, limits):
    th, t, cart = planned(robot, limits, TARGET)
    cart = cart.copy()
    cart[-1] = cart[-1] + np.array([0.0, 0.0, 3.0])  # erişilebilir ama eklemlerle uyuşmuyor
    v = validate(robot.kin, th, t, limits, cartesian_mm=cart)
    assert not v.accepted and v.requirement == "G3" and "sapıyor" in v.reason


class _NoFK:
    """İleri kinematiği hiç çözmeyen sahte kinematik (tekil konum benzetimi)."""

    def __init__(self, kin):
        self.kin = kin

    def forward(self, _theta):
        return None

    def __getattr__(self, name):
        return getattr(self.kin, name)


class _OtherBranch(_NoFK):
    """IK'nın farklı kol (dirsek) seçtiği durum."""

    def forward(self, theta):
        return self.kin.forward(theta)

    def inverse(self, p):
        th = self.kin.inverse(p)
        return None if th is None else [a + 5.0 for a in th]


def test_G3_forward_kinematics_unsolvable_rejected(robot, limits):
    th, t = hold(robot.kin.inverse(robot.home_mm))
    v = validate(_NoFK(robot.kin), th, t, limits)
    assert v.requirement == "G3" and "ileri kinematik" in v.reason


def test_G3_other_ik_branch_rejected(robot, limits):
    th, t = hold(robot.kin.inverse(robot.home_mm))
    v = validate(_OtherBranch(robot.kin), th, t, limits)
    assert v.requirement == "G3" and "IK kolu" in v.reason


def test_G4_NaN_angle_rejected(robot, limits):
    th, t = hold(robot.kin.inverse(robot.home_mm))
    th[3, 1] = np.nan
    v = validate(robot.kin, th, t, limits)
    assert not v.accepted and v.requirement == "G4" and v.index == 3


def test_G4_inf_angle_rejected(robot, limits):
    th, t = hold(robot.kin.inverse(robot.home_mm))
    th[0, 0] = np.inf
    assert validate(robot.kin, th, t, limits).requirement == "G4"


def test_G4_NaN_target_rejected(robot, limits):
    th, t, cart = planned(robot, limits, TARGET)
    cart = cart.copy()
    cart[5, 2] = np.nan
    v = validate(robot.kin, th, t, limits, cartesian_mm=cart)
    assert v.requirement == "G4" and v.index == 5


def test_G4_malformed_input_rejected(robot, limits):
    th, t = hold(robot.kin.inverse(robot.home_mm))
    assert validate(robot.kin, th[:, :2], t, limits).requirement == "G4"
    assert validate(robot.kin, th, t[:-1], limits).requirement == "G4"
    assert validate(robot.kin, th, t, limits, cartesian_mm=th[:-1]).requirement == "G4"
    assert validate(robot.kin, th[:0], t[:0], limits).requirement == "G4"


def test_G4_bad_time_grid_rejected(limits):
    t = sample_times(0.1, limits.rate_hz)
    bad = t.copy()
    bad[4] += 0.003
    v = check_time_grid(bad, limits.rate_hz, limits.max_duration_s)
    assert v.requirement == "G4" and v.index == 4
    nan = t.copy()
    nan[2] = np.nan
    assert check_time_grid(nan, limits.rate_hz, limits.max_duration_s).requirement == "G4"
    long = sample_times(limits.max_duration_s + 1.0, limits.rate_hz)
    assert "çok uzun" in check_time_grid(long, limits.rate_hz, limits.max_duration_s).reason
    assert check_time_grid(t, limits.rate_hz, limits.max_duration_s) is None


def test_G5_velocity_limit_rejected(robot, limits):
    th, t, cart = planned(robot, limits, TARGET, duration=0.05)
    v = validate(robot.kin, th, t, limits, cartesian_mm=cart)
    assert not v.accepted and v.requirement == "G5" and "hız" in v.reason


def test_G5_acceleration_limit_rejected(robot, limits):
    """Hız sınırın altında, ivme üstünde: kısa mesafe, kısa süre."""
    home = np.asarray(robot.kin.inverse(robot.home_mm))
    t = sample_times(0.08, limits.rate_hz)
    s = (t / t[-1]) ** 3 * (10 - 15 * (t / t[-1]) + 6 * (t / t[-1]) ** 2)
    th = home + np.outer(s, [5.0, 0.0, 0.0])
    v = validate(robot.kin, th, t, limits)
    assert not v.accepted and v.requirement == "G5" and "ivme" in v.reason, v.message


def test_G5_start_discontinuity_rejected(robot, limits):
    th, t, cart = planned(robot, limits, TARGET)
    current = np.asarray(th[0]) + np.array([limits.start_tolerance_deg + 1.0, 0.0, 0.0])
    v = validate(robot.kin, th, t, limits, cartesian_mm=cart, current_deg=current)
    assert v.requirement == "G5" and "başlangıç" in v.reason


def test_G5_step_from_rest_rejected(robot, limits):
    """Durağandan basamakla başlayan yörünge (ilk adımda büyük sıçrama) reddedilir."""
    home = np.asarray(robot.kin.inverse(robot.home_mm))
    th, t = hold(home, n=5)
    th[1:] += np.array([3.0, 0.0, 0.0])
    assert validate(robot.kin, th, t, limits).requirement == "G5"
