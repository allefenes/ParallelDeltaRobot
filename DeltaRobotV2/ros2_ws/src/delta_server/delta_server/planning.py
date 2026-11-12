"""Kartezyen düz çizgi yörünge planlama (saf mantık, ROS'suz).

Yol: P(s) = P0 + s·(P1 - P0), s ∈ [0, 1]. Zaman profili beşinci derece (quintic) polinom:
s(τ) = 10τ³ - 15τ⁴ + 6τ⁵, τ = t/T. Başta ve sonda hız ve ivme sıfırdır; böylece yörünge
durağandan başlar ve durağanda biter. Örnekleme sample_rate_hz (100 Hz) ile, uçlar dahil.
Her örnekte delta_core ters kinematiği çalışır; erişilemeyen örnek NaN açı olarak kalır ve
karar süpervizöre bırakılır (planlayıcı güvenlik kapısı değildir).

Birimler: konum mm, açı derece, süre s.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

# Quintic profilin tepe hız ve ivme katsayıları: max ṡ = 15/8 / T, max s̈ = 10/√3 / T².
QUINTIC_PEAK_VEL = 15.0 / 8.0
QUINTIC_PEAK_ACC = 10.0 / math.sqrt(3.0)


@dataclass
class Plan:
    """Örneklenmiş yörünge: zamanlar (s), kartezyen noktalar (mm), motor açıları (derece)."""

    times: np.ndarray  # (N,)
    points_mm: np.ndarray  # (N, 3)
    thetas_deg: np.ndarray  # (N, 3); erişilemeyen örnekte NaN
    duration_s: float

    @property
    def ik_ok(self) -> bool:
        """Tüm örneklerde ters kinematik çözüldü mü."""
        return bool(np.all(np.isfinite(self.thetas_deg)))


def quintic(tau: np.ndarray) -> np.ndarray:
    """Normalize konum s(τ); τ [0, 1] dışına kırpılır."""
    t = np.clip(tau, 0.0, 1.0)
    return t**3 * (10.0 - 15.0 * t + 6.0 * t * t)


def sample_times(duration_s: float, rate_hz: float) -> np.ndarray:
    """[0, T] aralığını 1/rate periyotla örnekler; son örnek tam T'dir (yuvarlanmış)."""
    if not (math.isfinite(duration_s) and duration_s > 0 and rate_hz > 0):
        raise ValueError("süre ve örnekleme hızı pozitif ve sonlu olmalı")
    n = max(1, int(math.ceil(duration_s * rate_hz - 1e-9)))
    return np.arange(n + 1) / rate_hz


def line_points(start_mm, target_mm, times: np.ndarray) -> np.ndarray:
    """Düz çizgi üzerinde quintic profille noktalar (mm)."""
    p0 = np.asarray(start_mm, dtype=float)
    p1 = np.asarray(target_mm, dtype=float)
    T = times[-1] if times[-1] > 0 else 1.0
    s = quintic(times / T)
    return p0 + np.outer(s, p1 - p0)


def solve_ik(kin, points_mm: np.ndarray) -> np.ndarray:
    """Her nokta için ters kinematik; çözümsüz ya da sayı olmayan noktada NaN."""
    out = np.full((len(points_mm), 3), np.nan)
    for k, p in enumerate(points_mm):
        if not np.all(np.isfinite(p)):
            continue
        th = kin.inverse(tuple(float(v) for v in p))
        if th is not None:
            out[k] = th
    return out


def plan_line(kin, start_mm, target_mm, duration_s: float, rate_hz: float) -> Plan:
    """Başlangıçtan hedefe düz çizgi yörüngesi."""
    times = sample_times(duration_s, rate_hz)
    pts = line_points(start_mm, target_mm, times)
    return Plan(times=times, points_mm=pts, thetas_deg=solve_ik(kin, pts), duration_s=times[-1])


def joint_rates(thetas_deg: np.ndarray, rate_hz: float) -> tuple[np.ndarray, np.ndarray]:
    """Ayrık hız (derece/s) ve ivme (derece/s²); yörünge öncesi ve sonrası durağan kabul edilir.

    İlk ve son örnek birer kez tekrarlanır: robot yörüngeden önce ve sonra durur. Böylece
    basamakla başlayan ya da hızla biten yörünge de sınır kontrolüne takılır.
    """
    th = np.vstack([thetas_deg[:1], thetas_deg, thetas_deg[-1:]])
    vel = np.diff(th, axis=0) * rate_hz
    acc = np.diff(vel, axis=0) * rate_hz
    return vel, acc


def auto_duration(
    kin, start_mm, target_mm, rate_hz: float, vmax: float, amax: float, margin: float
) -> float:
    """G5 sınırlarına uyan en kısa süreyi bulur (s), margin ile çarpılmış.

    Başlangıç tahmini eklem uzayında quintic tepe katsayılarından gelir; kartezyen düz çizgi
    eklem uzayında doğrusal olmadığı için örneklenmiş yörünge denetlenip süre gerekirse artırılır.
    Erişilemeyen yolda tahmin döner (karar süpervizörde).
    """
    p0, p1 = np.asarray(start_mm, float), np.asarray(target_mm, float)
    th0, th1 = kin.inverse(tuple(p0)), kin.inverse(tuple(p1))
    if th0 is None or th1 is None or not np.all(np.isfinite(p1)):
        return max(1.0, 1.0 / rate_hz)
    d = float(np.max(np.abs(np.asarray(th1) - np.asarray(th0))))
    T = max(QUINTIC_PEAK_VEL * d / vmax, math.sqrt(QUINTIC_PEAK_ACC * d / amax), 2.0 / rate_hz)
    for _ in range(40):
        plan = plan_line(kin, p0, p1, T, rate_hz)
        if not plan.ik_ok:
            break
        vel, acc = joint_rates(plan.thetas_deg, rate_hz)
        if np.max(np.abs(vel)) <= vmax and np.max(np.abs(acc)) <= amax:
            break
        T *= 1.1
    return T * margin
