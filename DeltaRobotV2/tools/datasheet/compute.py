"""Datasheet hesapları: çalışma alanı, çözünürlük, hız, kuvvet, koşul sayısı, görev yüksekliği.

Tüm sayılar config/robot.yaml ve delta_core (C++ çekirdek, Python bağlaması) üzerinden hesaplanır;
motor parametreleri değişirse sonuçlar yeniden üretilir. Birimler: mm, derece, N, g, mm/s.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

G = 9.81


@dataclass
class Grid:
    """Çalışma alanı ızgarası ve her noktadaki sonuç."""

    step: float
    xs: np.ndarray
    ys: np.ndarray
    zs: np.ndarray
    ok: np.ndarray  # [ix, iy, iz] bool: erişilebilir ve limit içinde
    reason: dict = field(default_factory=dict)  # neden -> adet (reddedilenler)


def scan_workspace(
    robot, step: float = 5.0, xy: float = 150.0, z0: float = -265.0, z1: float = -110.0
) -> Grid:
    """Izgaradaki her noktayı ters kinematik + limit kontrolünden geçirir."""
    xs = np.arange(-xy, xy + 1e-9, step)
    ys = np.arange(-xy, xy + 1e-9, step)
    zs = np.arange(z0, z1 + 1e-9, step)
    ok = np.zeros((len(xs), len(ys), len(zs)), dtype=bool)
    reason: dict[str, int] = {}
    for ix, x in enumerate(xs):
        for iy, y in enumerate(ys):
            for iz, z in enumerate(zs):
                good, _, why = robot.check_point((float(x), float(y), float(z)))
                ok[ix, iy, iz] = good
                if not good:
                    reason[why] = reason.get(why, 0) + 1
    return Grid(step, xs, ys, zs, ok, reason)


def volume_cm3(g: Grid) -> float:
    """Çalışma alanı hacmi (cm³), ızgara hücre sayımıyla."""
    return float(g.ok.sum()) * g.step**3 / 1000.0


def slice_radius(g: Grid, iz: int) -> float:
    """z dilimi için merkezde tamamen geçerli en büyük daire yarıçapı (mm)."""
    X, Y = np.meshgrid(g.xs, g.ys, indexing="ij")
    r = np.hypot(X, Y)
    bad = r[~g.ok[:, :, iz]]
    if not g.ok[:, :, iz].any():
        return 0.0
    limit = float(bad.min()) if bad.size else float(r.max())
    return max(0.0, limit - g.step)


def usable_cylinder(g: Grid) -> dict:
    """Hacmi en büyük, Z ekseninde ortalı, tamamen geçerli silindir (çap, yükseklik, z aralığı)."""
    radii = [slice_radius(g, iz) for iz in range(len(g.zs))]
    best = {"diameter": 0.0, "height": 0.0, "z_min": 0.0, "z_max": 0.0, "volume_cm3": 0.0}
    for i in range(len(radii)):
        r_min = math.inf
        for j in range(i, len(radii)):
            r_min = min(r_min, radii[j])
            if r_min <= 0:
                break
            h = g.zs[j] - g.zs[i] + g.step
            vol = math.pi * r_min**2 * h / 1000.0
            if vol > best["volume_cm3"]:
                best = {
                    "diameter": 2 * r_min,
                    "height": float(h),
                    "z_min": float(g.zs[i]),
                    "z_max": float(g.zs[j]),
                    "volume_cm3": vol,
                }
    return {"radii": radii, **best}


def jacobian_m(robot, theta) -> np.ndarray | None:
    """J (m/rad) ya da None."""
    J = robot.jacobian(theta)
    return None if J is None else np.array(J) / 1000.0


def point_metrics(robot, P, motor: dict, step_deg: float) -> dict | None:
    """Bir noktadaki çözünürlük (mm), garanti hız (mm/s), garanti kuvvet (N), koşul sayısı.

    - Çözünürlük: her motor ±1 adım oynadığında uç noktanın en büyük yer değiştirmesi.
    - Hız: her yönde ulaşılabilen en düşük hız ≈ σ_min(J)·ω_max (2-normla yaklaşık).
    - Kuvvet: her yönde uygulanabilen en düşük kuvvet ≈ τ_sürekli / σ_max(J) (τ = Jᵀ·F).
    """
    th = robot.inverse(P)
    if th is None:
        return None
    J = jacobian_m(robot, th)
    if J is None:
        return None
    sv = np.linalg.svd(J, compute_uv=False)
    step = math.radians(step_deg)
    corners = np.array([[a, b, c] for a in (-1, 1) for b in (-1, 1) for c in (-1, 1)])
    res_mm = float(max(np.linalg.norm(J @ s) for s in corners) * step * 1000.0)
    omega = motor["no_load_rpm"] * 2 * math.pi / 60.0
    tau = motor["stall_torque_nm"] * motor["continuous_torque_fraction"]
    return {
        "res_mm": res_mm,
        "speed_mm_s": float(sv.min() * omega * 1000.0),
        "force_n": float(tau / sv.max()),
        "cond": float(sv.max() / sv.min()),
        "theta": th,
    }


def slice_maps(robot, g: Grid, z: float, motor: dict, step_deg: float) -> dict:
    """z yüksekliğindeki XY diliminde metrik haritaları (geçersiz noktalar NaN)."""
    names = ["res_mm", "speed_mm_s", "force_n", "cond"]
    maps = {n: np.full((len(g.xs), len(g.ys)), np.nan) for n in names}
    for ix, x in enumerate(g.xs):
        for iy, y in enumerate(g.ys):
            if not robot.check_point((float(x), float(y), z))[0]:
                continue
            m = point_metrics(robot, (float(x), float(y), z), motor, step_deg)
            if m:
                for n in names:
                    maps[n][ix, iy] = m[n]
    return maps


def summary_stats(maps: dict) -> dict:
    """Her metrik için en iyi / en kötü / ortalama (NaN hariç)."""
    out = {}
    for k, v in maps.items():
        vals = v[~np.isnan(v)]
        if vals.size:
            out[k] = {
                "min": float(vals.min()),
                "max": float(vals.max()),
                "mean": float(vals.mean()),
            }
    return out


def payload_at(robot, P, motor: dict, moving_mass_kg: float) -> float:
    """P'de düşey taşınabilecek ek yük (g): sürekli torkla, hareketli kütle düşülerek."""
    th = robot.inverse(P)
    J = None if th is None else jacobian_m(robot, th)
    if J is None:
        return 0.0
    tau = motor["stall_torque_nm"] * motor["continuous_torque_fraction"]
    # Aşağı F_z için motor torkları τ_i = J[2][i]·F_z; en çok yüklenen motor sınırı belirler.
    fz_max = tau / max(abs(J[2][i]) for i in range(3))
    return max(0.0, (fz_max - moving_mass_kg * G) / G * 1000.0)


def task_heights(params: dict) -> dict:
    """Tabla, taş ve P yükseklikleri (robot çerçevesi, mm)."""
    k, t = params["kinematics"], params["task"]
    floor = -k["base_to_floor"]
    board_top = floor + t["board_thickness"]
    piece_top = board_top + t["piece_height"]
    pick_p = piece_top + k["ee_offset"]  # mıknatıs ucu taşın üstünde
    travel_p = pick_p + t["piece_height"] + t["lift_height"]
    return {
        "floor": floor,
        "board_top": board_top,
        "piece_top": piece_top,
        "pick_P": pick_p,
        "travel_P": travel_p,
    }


def largest_square(g_ok_slice: np.ndarray, xs: np.ndarray) -> float:
    """Merkezli, tamamen geçerli en büyük karenin kenarı (mm): tic-tac-toe tablası için."""
    best = 0.0
    step = xs[1] - xs[0]
    for half in np.arange(step, xs.max() + step, step):
        sel = np.abs(xs) <= half
        if g_ok_slice[np.ix_(sel, sel)].all():
            best = 2 * half
        else:
            break
    return float(best)


def assumptions(node, path: str = "") -> list[str]:
    """robot.yaml'da 'varsayim' geçen satırları/alanları toplar (yorumlar ayrıca okunur)."""
    out: list[str] = []
    if isinstance(node, dict):
        if node.get("kaynak") == "varsayim":
            out.append(path)
        for k, v in node.items():
            out += assumptions(v, f"{path}.{k}" if path else k)
    return out


def comment_assumptions(yaml_text: str) -> list[tuple[str, str]]:
    """Satır sonu yorumunda 'varsayim' olan anahtarlar: (anahtar, açıklama)."""
    out = []
    for line in yaml_text.splitlines():
        if "#" not in line or "varsayim" not in line.split("#", 1)[1]:
            continue
        key = line.split("#", 1)[0].strip().rstrip(":").split(":")[0].strip("- {")
        note = line.split("#", 1)[1].replace("varsayim", "").strip(" :")
        if key:
            out.append((key, note))
    return out
