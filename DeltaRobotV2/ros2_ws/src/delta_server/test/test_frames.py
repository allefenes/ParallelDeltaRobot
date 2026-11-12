"""Durum yayıncısı testleri: yayımlanan TF'lerden geometri (ileri kinematik -> bağ çerçeveleri).

Ölçüler robot.yaml'dan okunur (bicep_length, forearm_length, platform_radius, rod_spacing).
Kontroller yalnız yayımlanan TransformStamped'lerle yapılır:
  - her uzun kolun üst küre merkezi (bağ orijini) ile alt küre merkezi forearm_length aralıklı
  - kısa kol: motor ekseni (bicep orijini) -> üst küre çiftinin ortası = bicep_length
  - alt küre merkezleri platform eklemlerinde (P + r·u_i ± s·t_i)
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from builtin_interfaces.msg import Time
from delta_server.frames import (
    arm_axes,
    link_poses,
    quaternion_to_rotation,
    rotation_to_quaternion,
    tip_mm,
)
from delta_server.state_publisher_node import DeltaStatePublisher
from rclpy.parameter import Parameter

POSES_MM = [(0.0, 0.0, -190.0), (20.0, 10.0, -200.0), (-25.0, 15.0, -160.0), (10.0, -30.0, -225.0)]


@pytest.fixture(scope="module")
def node(ros_context, robot_yaml):
    n = DeltaStatePublisher(parameter_overrides=[Parameter("robot_yaml", value=robot_yaml)])
    yield n
    n.destroy_node()


def tf_dict(node, theta):
    out = {}
    for t in node.transforms(theta, Time()):
        assert t.header.frame_id == "base_link"
        tr, q = t.transform.translation, t.transform.rotation
        quat = (q.x, q.y, q.z, q.w)
        assert math.isclose(np.linalg.norm(quat), 1.0, rel_tol=1e-9)
        out[t.child_frame_id] = (
            np.array([tr.x, tr.y, tr.z]) * 1000.0,
            quaternion_to_rotation(quat),
        )
    return out


@pytest.mark.parametrize("P", POSES_MM)
def test_forearm_ball_centers_are_forearm_length_apart(node, robot, P):
    theta = robot.kin.inverse(P)
    tfs = tf_dict(node, theta)
    assert len(tfs) == 10
    prm = robot.params
    s = robot.rod_half_spacing_mm
    plat_pos, plat_rot = tfs["platform"]
    assert np.allclose(plat_pos, P, atol=1e-6) and np.allclose(plat_rot, np.eye(3), atol=1e-9)
    for i, a in enumerate(prm.arm_angles):
        u, t = arm_axes(a)
        for tag, sign in (("a", 1.0), ("b", -1.0)):
            pos, rot = tfs[f"forearm_{i + 1}_{tag}"]
            lower = plat_pos + prm.platform_radius * u + sign * s * t
            assert math.isclose(np.linalg.norm(lower - pos), prm.forearm_length, abs_tol=1e-6)
            # X ekseni alt küreye bakar; Y pim eksenine (t_i) dik değil, ona en yakın yönde
            assert np.allclose(rot[:, 0] * prm.forearm_length, lower - pos, atol=1e-6)
            assert rot[:, 1] @ t > 0.9 and abs(rot[:, 1] @ rot[:, 0]) < 1e-9


@pytest.mark.parametrize("P", POSES_MM)
def test_bicep_length_from_published_frames(node, robot, P):
    theta = robot.kin.inverse(P)
    tfs = tf_dict(node, theta)
    prm = robot.params
    for i, a in enumerate(prm.arm_angles):
        u, t = arm_axes(a)
        origin, rot = tfs[f"bicep_{i + 1}"]
        assert np.allclose(origin, prm.base_radius * u, atol=1e-6)
        elbow = 0.5 * (tfs[f"forearm_{i + 1}_a"][0] + tfs[f"forearm_{i + 1}_b"][0])
        assert math.isclose(np.linalg.norm(elbow - origin), prm.bicep_length, abs_tol=1e-6)
        # Kısa kolun X ekseni dirseğe bakar, Y motor ekseni (t_i)
        assert np.allclose(rot[:, 0] * prm.bicep_length, elbow - origin, atol=1e-6)
        assert np.allclose(rot[:, 1], t, atol=1e-9)
        # Pozitif θ kolu indirir: dirseğin z'si -L1·sin θ
        assert math.isclose(
            elbow[2], -prm.bicep_length * math.sin(math.radians(theta[i])), abs_tol=1e-6
        )


def test_quaternion_roundtrip_all_branches():
    rng = np.random.default_rng(1)
    mats = [np.diag([1.0, -1.0, -1.0]), np.diag([-1.0, 1.0, -1.0]), np.diag([-1.0, -1.0, 1.0])]
    for _ in range(50):
        q = rng.normal(size=4)
        mats.append(quaternion_to_rotation(tuple(q / np.linalg.norm(q))))
    for m in mats:
        assert np.allclose(quaternion_to_rotation(rotation_to_quaternion(m)), m, atol=1e-9)


def test_unsolvable_fk_returns_none(robot):
    class NoFK:
        params = robot.params

        def forward(self, _):
            return None

    class R:
        kin = NoFK()
        params = robot.params
        rod_half_spacing_mm = robot.rod_half_spacing_mm

    assert link_poses(R(), (0.0, 0.0, 0.0)) is None


def test_tip_is_ee_offset_below_platform(robot):
    assert tip_mm(robot, (1.0, 2.0, -190.0)) == (1.0, 2.0, -190.0 - robot.params.ee_offset)
