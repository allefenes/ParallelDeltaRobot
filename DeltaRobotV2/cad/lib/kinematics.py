"""CAD montaj pozu için hafif kinematik yardımcısı (yalnız standart kütüphane).

Asıl kinematik çekirdek F1'de C++ olarak yazılacak ve bu modülle çapraz kontrol edilecek.

Çerçeve (config/robot.yaml ile aynı): orijin motor eksenleri düzleminin merkezi, +Z yukarı.
Kol i için birim vektörler:
    u_i  radyal, dışa doğru      (cos a, sin a, 0)
    t_i  teğet, motor ekseni     (-sin a, cos a, 0)
Motor açısı θ: 0 iken kısa kol u_i yönünde yatay; pozitif θ kolu aşağı indirir.
P: platform eklem düzleminin merkezi (alt küresel eklem merkezlerinin ortalaması).
"""

from __future__ import annotations

import math

Vec = tuple[float, float, float]


def add(a: Vec, b: Vec) -> Vec:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def scale(a: Vec, s: float) -> Vec:
    return (a[0] * s, a[1] * s, a[2] * s)


def dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def norm(a: Vec) -> float:
    return math.sqrt(dot(a, a))


def unit(a: Vec) -> Vec:
    return scale(a, 1.0 / norm(a))


def arm_axes(alpha_deg: float) -> tuple[Vec, Vec]:
    """Kol i'nin (u, t) birim vektörleri; alpha derece."""
    a = math.radians(alpha_deg)
    return (math.cos(a), math.sin(a), 0.0), (-math.sin(a), math.cos(a), 0.0)


class Delta:
    """Robot geometrisi; k = robot.yaml'daki `kinematics` bölümü (mm, derece)."""

    def __init__(self, k: dict):
        self.R = k["base_radius"]
        self.L1 = k["bicep_length"]
        self.L2 = k["forearm_length"]
        self.r = k["platform_radius"]
        self.alphas = list(k["arm_angles"])

    def shoulder(self, i: int) -> Vec:
        """A_i: motor ekseninin kol düzlemini kestiği nokta."""
        u, _ = arm_axes(self.alphas[i])
        return scale(u, self.R)

    def elbow(self, i: int, theta_deg: float) -> Vec:
        """B_i: kısa kol ucundaki (üst) küresel eklem merkezi."""
        u, _ = arm_axes(self.alphas[i])
        th = math.radians(theta_deg)
        return add(scale(u, self.R + self.L1 * math.cos(th)), (0.0, 0.0, -self.L1 * math.sin(th)))

    def wrist(self, i: int, p: Vec) -> Vec:
        """C_i: platformdaki (alt) küresel eklem merkezi; platform yönelimi sabit."""
        u, _ = arm_axes(self.alphas[i])
        return add(p, scale(u, self.r))

    def ik(self, p: Vec) -> list[float]:
        """Ters kinematik: P -> [θ1, θ2, θ3] derece. Erişilemezse ValueError.

        Kol düzleminde c = C_i - A_i bileşenleri (cx radyal, cz düşey) için
        |B - C| = L2 koşulu  cx·cosθ - cz·sinθ = K  denklemine iner;
        K = (L1² + |c|² - L2²) / (2·L1). İki kökten dirseği dışarıda/yukarıda tutan seçilir.
        """
        thetas = []
        for i in range(3):
            u, _ = arm_axes(self.alphas[i])
            c = sub(self.wrist(i, p), self.shoulder(i))
            cx, cz = dot(c, u), c[2]
            k = (self.L1**2 + dot(c, c) - self.L2**2) / (2.0 * self.L1)
            rho = math.hypot(cx, cz)
            if rho == 0.0 or abs(k) > rho:
                raise ValueError(f"kol {i + 1}: P={p} erişilemez")
            phi = math.atan2(cz, cx)
            # cx·cosθ - cz·sinθ = ρ·cos(θ + φ)
            roots = [-phi + math.acos(k / rho), -phi - math.acos(k / rho)]
            roots = [math.atan2(math.sin(x), math.cos(x)) for x in roots]
            # Dirsek dışarıda: B'nin radyal konumu büyük olan (cos θ büyük) kök
            thetas.append(math.degrees(max(roots, key=math.cos)))
        return thetas

    def rod_tilt_deg(self, i: int, theta_deg: float, p: Vec) -> float:
        """Uzun kolun, motor eksenine dik düzlemden sapması (rot başı yanal açısı), derece."""
        _, t = arm_axes(self.alphas[i])
        d = unit(sub(self.wrist(i, p), self.elbow(i, theta_deg)))
        return math.degrees(math.asin(abs(dot(d, t))))
