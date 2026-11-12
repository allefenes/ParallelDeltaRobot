"""Sunucu 1. güvenlik kapısının karar mantığı (saf, ROS'suz; supervisor düğümü kullanır).

Her yörünge örneği için (docs/guvenlik-gereksinimleri.md):
  G4  sayı olmayan (NaN/sonsuz) ya da bozuk veri (eklem adı, zaman ızgarası, uzunluk)
  G1  motor açı limiti (robot.yaml motor_limit_min/max)          -> delta_core check_limits
  G2  rot başı yanal açısı (robot.yaml spherical_joint_limit)    -> delta_core check_limits
  G3  erişilemezlik: kartezyen nokta erişilemez, ileri kinematik çözümsüz ya da eklem açıları
      planlanan noktayla / IK koluyla tutarsız
  G5  eklem hız ve ivme sınırları (server.yaml) ve başlangıç sürekliliği
  G14 uç işlevci (mıknatıs ucu = P − ee_offset) tabla/zemin yüzeyinin altına inemez
İlk ihlal kararı belirler; yörünge ya tamamen kabul edilir ya da hiç gönderilmez.

Birimler: açı derece, konum mm, süre s.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from delta_server.planning import joint_rates

# delta_core neden metinleri -> gereksinim numarası
CORE_REASON_REQUIREMENT = {
    "motor açı limiti": "G1",
    "rot başı açı limiti": "G2",
    "erişilemez": "G3",
    "açı sayı değil": "G4",
    "konum sayı değil": "G4",
}


@dataclass(frozen=True)
class Limits:
    """Süpervizör sınırları; açı/konum limitleri delta_core'dadır (robot.yaml)."""

    max_vel_deg_s: float
    max_acc_deg_s2: float
    rate_hz: float
    start_tolerance_deg: float = 1.0
    cartesian_tolerance_mm: float = 0.5
    max_duration_s: float = 60.0
    ik_tolerance_deg: float = 0.05
    # G14: mıknatıs ucunun inebileceği en alçak z (mm) ve P'den uca uzaklık; None = denetim yok
    min_tool_z_mm: float | None = None
    tool_offset_mm: float = 15.0


@dataclass
class Verdict:
    """Karar: kabul ya da ilk ihlalin gereksinimi, nedeni ve örnek sırası."""

    accepted: bool
    requirement: str = ""
    reason: str = ""
    index: int = -1
    details: dict = field(default_factory=dict)

    @property
    def message(self) -> str:
        """İnsan okunur tek satır: "G1: motor açı limiti (kol 1, örnek 37)"."""
        if self.accepted:
            return "kabul"
        return f"{self.requirement}: {self.reason}"


def _reject(req: str, reason: str, index: int = -1, **details) -> Verdict:
    return Verdict(False, req, reason, index, details)


def _core_reject(reason: str, arm: int, index: int, where: str) -> Verdict:
    req = CORE_REASON_REQUIREMENT.get(reason, "G3")
    arm_txt = f"kol {arm + 1}, " if arm >= 0 else ""
    return _reject(req, f"{reason} ({where}{arm_txt}örnek {index})", index)


def check_time_grid(times_s, rate_hz: float, max_duration_s: float) -> Verdict | None:
    """Zaman ızgarası 0'dan başlamalı ve tam 1/rate artmalı; değilse G4."""
    t = np.asarray(times_s, dtype=float)
    if len(t) == 0:
        return _reject("G4", "boş yörünge")
    if not np.all(np.isfinite(t)):
        return _reject("G4", "zaman damgası sayı değil")
    expected = np.arange(len(t)) / rate_hz
    bad = np.nonzero(np.abs(t - expected) > 1e-6)[0]
    if len(bad):
        k = int(bad[0])
        return _reject("G4", f"zaman ızgarası {1.0 / rate_hz:.4f} s değil (örnek {k})", k)
    if t[-1] > max_duration_s:
        return _reject("G4", f"yörünge çok uzun ({t[-1]:.1f} s > {max_duration_s:g} s)")
    return None


def validate(
    kin,
    thetas_deg,
    times_s,
    limits: Limits,
    cartesian_mm=None,
    current_deg=None,
) -> Verdict:
    """Yörüngeyi 1. kapıdan geçirir.

    kin: delta_core_py.DeltaKinematics; thetas_deg: (N, 3); times_s: (N,);
    cartesian_mm: (N, 3) planlanan P ya da None; current_deg: robotun o anki açıları ya da None.
    """
    th = np.asarray(thetas_deg, dtype=float)
    if th.ndim != 2 or th.shape[1] != 3:
        return _reject("G4", "eklem dizisi (N, 3) değil")
    grid = check_time_grid(times_s, limits.rate_hz, limits.max_duration_s)
    if grid is not None:
        return grid
    if len(th) != len(times_s):
        return _reject("G4", "açı ve zaman sayısı farklı")
    cart = None
    if cartesian_mm is not None and len(cartesian_mm):
        cart = np.asarray(cartesian_mm, dtype=float)
        if cart.shape != th.shape:
            return _reject("G4", "kartezyen nokta sayısı eklem örnekleriyle aynı değil")

    lo, hi = kin.params.motor_limit_min, kin.params.motor_limit_max
    for k in range(len(th)):
        if cart is not None:
            if not np.all(np.isfinite(cart[k])):
                return _reject("G4", f"konum sayı değil (hedef yol, örnek {k})", k)
            ok, arm, reason = kin.check_point(tuple(float(v) for v in cart[k]))
            if not ok:
                return _core_reject(reason, arm, k, "hedef yol, ")
        q = th[k]
        if not np.all(np.isfinite(q)):
            return _reject("G4", f"açı sayı değil (örnek {k})", k)
        # G1 ileri kinematikten bağımsız denetlenir (FK çözümsüz olsa da limit nedeni görünür).
        for j in range(3):
            if not lo <= q[j] <= hi:
                return _core_reject("motor açı limiti", j, k, "")
        P = kin.forward(tuple(float(v) for v in q))
        if P is None:
            return _reject("G3", f"ileri kinematik çözümsüz (örnek {k})", k)
        ok, arm, reason = kin.check_limits(tuple(float(v) for v in q), P)
        if not ok:
            return _core_reject(reason, arm, k, "")
        if limits.min_tool_z_mm is not None:
            tip_z = float(P[2]) - limits.tool_offset_mm
            if tip_z < limits.min_tool_z_mm - 1e-6:
                return _reject(
                    "G14",
                    f"uç tabla/zemin yüzeyinin altına iner: z_uç {tip_z:.1f} mm < "
                    f"{limits.min_tool_z_mm:g} mm (örnek {k})",
                    k,
                )
        # Aynı P için delta_core'un seçtiği IK kolu (dirsek dışarıda) bu açılar olmalı.
        ik = kin.inverse(P)
        if ik is None or float(np.max(np.abs(np.asarray(ik) - q))) > limits.ik_tolerance_deg:
            return _reject("G3", f"açılar IK koluyla tutarsız (örnek {k})", k)
        if cart is not None:
            err = float(np.linalg.norm(np.asarray(P) - cart[k]))
            if err > limits.cartesian_tolerance_mm:
                return _reject(
                    "G3", f"eklemler planlanan noktadan {err:.2f} mm sapıyor (örnek {k})", k
                )

    if current_deg is not None:
        jump = float(np.max(np.abs(th[0] - np.asarray(current_deg, dtype=float))))
        if not math.isfinite(jump) or jump > limits.start_tolerance_deg:
            return _reject(
                "G5", f"başlangıç süreksiz: ilk örnek mevcut açıdan {jump:.2f}° uzak", 0, jump=jump
            )

    vel, acc = joint_rates(th, limits.rate_hz)
    v_abs, a_abs = np.abs(vel), np.abs(acc)
    if np.max(v_abs) > limits.max_vel_deg_s:
        k, j = np.unravel_index(int(np.argmax(v_abs)), v_abs.shape)
        return _reject(
            "G5",
            f"eklem hız sınırı: {v_abs[k, j]:.0f}°/s > {limits.max_vel_deg_s:g}°/s "
            f"(kol {j + 1}, örnek {max(0, k - 1)})",
            max(0, int(k) - 1),
        )
    if np.max(a_abs) > limits.max_acc_deg_s2:
        k, j = np.unravel_index(int(np.argmax(a_abs)), a_abs.shape)
        return _reject(
            "G5",
            f"eklem ivme sınırı: {a_abs[k, j]:.0f}°/s² > {limits.max_acc_deg_s2:g}°/s² "
            f"(kol {j + 1}, örnek {int(k)})",
            int(k),
        )
    return Verdict(True)
