"""Motor açılarından tüm hareketli bağların çerçeveleri (dijital ikiz TF'i).

Çerçeveler cad/README.md tablosuyla birebir aynıdır (robot çerçevesinde, mm):
  bicep_i        orijin A_i = R·u_i; dönme Rz(a_i)·Ry(θ_i) (pozitif θ kolu indirir)
  forearm_i_a/b  orijin üst küre merkezi B_i ± s·t_i; X alt küre merkezine (C_i ± s·t_i);
                 Y = t_i'nin X'e dik bileşeni (pim eksenine en yakın dik yön); Z = X × Y
  platform       orijin P, eksenler robot çerçevesine paralel
s = rod_spacing / 2; a = +s, b = -s (CAD'deki eklem istifi sırası).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from delta_server.robot import Robot


@dataclass(frozen=True)
class LinkPose:
    """Bağ pozu: konum (mm) ve dönme matrisi (sütunlar = bağ eksenleri, robot çerçevesinde)."""

    position_mm: np.ndarray
    rotation: np.ndarray

    def quaternion_xyzw(self) -> tuple[float, float, float, float]:
        """Dönme matrisini (x, y, z, w) dördeyine çevirir."""
        return rotation_to_quaternion(self.rotation)


def rotation_to_quaternion(m: np.ndarray) -> tuple[float, float, float, float]:
    """Ortonormal 3x3 matris -> birim dördey (x, y, z, w); Shepperd yöntemi."""
    tr = m[0, 0] + m[1, 1] + m[2, 2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        w, x = 0.25 * s, (m[2, 1] - m[1, 2]) / s
        y, z = (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        w, x = (m[2, 1] - m[1, 2]) / s, 0.25 * s
        y, z = (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        w, x = (m[0, 2] - m[2, 0]) / s, (m[0, 1] + m[1, 0]) / s
        y, z = 0.25 * s, (m[1, 2] + m[2, 1]) / s
    else:
        s = math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        w, x = (m[1, 0] - m[0, 1]) / s, (m[0, 2] + m[2, 0]) / s
        y, z = (m[1, 2] + m[2, 1]) / s, 0.25 * s
    n = math.sqrt(x * x + y * y + z * z + w * w)
    return (x / n, y / n, z / n, w / n)


def quaternion_to_rotation(q: tuple[float, float, float, float]) -> np.ndarray:
    """(x, y, z, w) dördey -> 3x3 dönme matrisi."""
    x, y, z, w = q
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ]
    )


def rot_z(a_rad: float) -> np.ndarray:
    """Z etrafında dönme."""
    c, s = math.cos(a_rad), math.sin(a_rad)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def rot_y(a_rad: float) -> np.ndarray:
    """Y etrafında dönme (pozitif açı X'i -Z'ye, yani aşağı çevirir)."""
    c, s = math.cos(a_rad), math.sin(a_rad)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def arm_axes(a_deg: float) -> tuple[np.ndarray, np.ndarray]:
    """Kol i'nin radyal (u_i) ve teğet/motor ekseni (t_i) birim vektörleri."""
    a = math.radians(a_deg)
    return np.array([math.cos(a), math.sin(a), 0.0]), np.array([-math.sin(a), math.cos(a), 0.0])


def forearm_rotation(top: np.ndarray, bottom: np.ndarray, pin_axis: np.ndarray) -> np.ndarray:
    """Uzun kol çerçevesi: X üstten alta, Y pim eksenine en yakın dik yön, Z = X × Y."""
    x = bottom - top
    x = x / np.linalg.norm(x)
    y = pin_axis - x * float(pin_axis @ x)
    y = y / np.linalg.norm(y)
    return np.column_stack([x, y, np.cross(x, y)])


def link_poses(robot: Robot, theta_deg, platform_mm=None) -> dict[str, LinkPose] | None:
    """Motor açılarından (derece) tüm hareketli bağların pozları; FK çözümsüzse None.

    platform_mm verilirse ileri kinematik yerine o P kullanılır (test ve hız için).
    """
    k = robot.kin
    prm = robot.params
    if platform_mm is None:
        platform_mm = k.forward(tuple(theta_deg))
        if platform_mm is None:
            return None
    P = np.asarray(platform_mm, dtype=float)
    s = robot.rod_half_spacing_mm
    poses: dict[str, LinkPose] = {}
    for i, a_deg in enumerate(prm.arm_angles):
        u, t = arm_axes(a_deg)
        th = math.radians(theta_deg[i])
        poses[f"bicep_{i + 1}"] = LinkPose(
            position_mm=u * prm.base_radius, rotation=rot_z(math.radians(a_deg)) @ rot_y(th)
        )
        B = np.asarray(k.elbow(i, float(theta_deg[i])))
        C = P + u * prm.platform_radius
        for tag, sign in (("a", 1.0), ("b", -1.0)):
            top, bottom = B + sign * s * t, C + sign * s * t
            poses[f"forearm_{i + 1}_{tag}"] = LinkPose(
                position_mm=top, rotation=forearm_rotation(top, bottom, t)
            )
    poses["platform"] = LinkPose(position_mm=P, rotation=np.eye(3))
    return poses


def tip_mm(robot: Robot, platform_mm) -> tuple[float, float, float]:
    """Mıknatıs ucu: P'nin ee_offset (mm) altı."""
    x, y, z = platform_mm
    return (x, y, z - robot.params.ee_offset)
