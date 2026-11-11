"""Kinematiğin özellik tabanlı testleri (Hypothesis): rastgele girdilerde değişmez özellikler.

Birimler: mm, derece. Çerçeve +Z yukarı. Erişilemeyen noktalar `assume` ile atlanır.
"""

from __future__ import annotations

import math

from hypothesis import assume, given, settings
from hypothesis import strategies as st

# Çalışma alanını kapsayan kutu (mm)
xs = st.floats(-120, 120, allow_nan=False)
zs = st.floats(-260, -120, allow_nan=False)
angles = st.floats(-60, 120, allow_nan=False)


@settings(max_examples=400, deadline=None)
@given(x=xs, y=xs, z=zs)
def test_ik_then_fk_returns_point(robot, x, y, z):
    """FK(IK(P)) = P (erişilebilen her nokta için)."""
    th = robot.inverse((x, y, z))
    assume(th is not None)
    p = robot.forward(th)
    assert p is not None
    assert math.dist(p, (x, y, z)) < 1e-7


@settings(max_examples=400, deadline=None)
@given(t1=st.floats(-60, 85), t2=st.floats(-60, 85), t3=st.floats(-60, 85))
def test_fk_then_ik_returns_angles(robot, t1, t2, t3):
    """IK(FK(θ)) = θ, dirsek dışarıdaki çözüm bölgesinde (θ < 90°) ve tekil olmayan konumda.

    θ ≈ 90°'de kol düşeydir ve Jacobian kötü koşulludur; orada açılar sayısal olarak hassastır
    (Hypothesis bulgusu: θ = (88, 96, 97) için 0.05° fark). Bu bölge datasheet'te gösterilir.
    """
    p = robot.forward((t1, t2, t3))
    assume(p is not None and robot.condition_number((t1, t2, t3)) < 1e3)
    th = robot.inverse(p)
    assert th is not None
    for a, b in zip(th, (t1, t2, t3), strict=True):
        assert abs(a - b) < 1e-6


@settings(max_examples=150, deadline=None)
@given(t1=st.floats(-50, 100), t2=st.floats(-50, 100), t3=st.floats(-50, 100))
def test_jacobian_matches_finite_difference(robot, t1, t2, t3):
    """J = dP/dθ, sayısal türevle uyumlu (merkezi fark)."""
    th = (t1, t2, t3)
    J = robot.jacobian(th)
    assume(J is not None and robot.condition_number(th) < 1e3)
    h = 1e-5
    for c in range(3):
        a, b = list(th), list(th)
        a[c] += h
        b[c] -= h
        pa, pb = robot.forward(a), robot.forward(b)
        assume(pa is not None and pb is not None)
        for r in range(3):
            fd = (pa[r] - pb[r]) / (2 * math.radians(h))
            assert abs(J[r][c] - fd) < 1e-3 * max(1.0, abs(fd))


@settings(max_examples=200, deadline=None)
@given(x=xs, y=xs, z=zs)
def test_120_degree_symmetry(robot, x, y, z):
    """Noktayı Z etrafında 120° döndürmek kol açılarını bir kaydırır."""
    th = robot.inverse((x, y, z))
    assume(th is not None)
    a = 2 * math.pi / 3
    q = (x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a), z)
    tq = robot.inverse(q)
    assert tq is not None
    for i in range(3):
        assert abs(tq[(i + 1) % 3] - th[i]) < 1e-7


@settings(max_examples=300, deadline=None)
@given(x=xs, y=xs, z=zs)
def test_check_point_agrees_with_limits(robot, x, y, z):
    """check_point kabul ederse açı ve rot başı açısı limitlerin içindedir (G1, G2)."""
    ok, arm, reason = robot.check_point((x, y, z))
    th = robot.inverse((x, y, z))
    p = robot.params
    if ok:
        assert th is not None
        for i, t in enumerate(th):
            assert p.motor_limit_min <= t <= p.motor_limit_max
            assert robot.rod_tilt_deg(i, t, (x, y, z)) <= p.spherical_joint_limit + 1e-9
    else:
        assert reason in {"erişilemez", "motor açı limiti", "rot başı açı limiti"}


@settings(max_examples=200, deadline=None)
@given(
    th=st.tuples(angles, angles, angles),
    bad=st.sampled_from([math.nan, math.inf, -math.inf]),
    pos=st.integers(0, 2),
)
def test_non_finite_never_accepted(robot, th, bad, pos):
    """NaN/sonsuz açı ya da konum hiçbir zaman kabul edilmez (G4)."""
    t = list(th)
    t[pos] = bad
    assert robot.forward(t) is None
    assert robot.check_limits(t, (0.0, 0.0, -200.0))[0] is False
    p = [0.0, 0.0, -200.0]
    p[pos] = bad
    assert robot.inverse(p) is None
    assert robot.check_point(p)[0] is False


def test_limit_edges(robot):
    """Limit sınırında: tam sınır kabul, sınırın 1e-9 ötesi ret (G1)."""
    p = robot.params
    P = (0.0, 0.0, -200.0)
    lo = (p.motor_limit_min, 0.0, 0.0)
    assert robot.check_limits(lo, P)[2] != "motor açı limiti"
    over = (p.motor_limit_min - 1e-9, 0.0, 0.0)
    assert robot.check_limits(over, P)[2] == "motor açı limiti"
    over_hi = (0.0, p.motor_limit_max + 1e-9, 0.0)
    assert robot.check_limits(over_hi, P)[2] == "motor açı limiti"


def test_module_metadata(robot):
    import delta_core_py as dc

    assert dc.__version__.count(".") == 2
    assert tuple(robot.elbow(0, 0.0)) == (129.0, 0.0, 0.0)
    params = dc.DeltaParams()
    params.forearm_length = 10.0
    tiny = dc.DeltaKinematics(params)
    assert tiny.forward((0.0, 0.0, 0.0)) is None
    assert tiny.jacobian((0.0, 0.0, 0.0)) is None
