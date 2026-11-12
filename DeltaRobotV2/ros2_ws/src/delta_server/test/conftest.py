"""delta_server testleri için ortak düzen: robot.yaml, kinematik, sınırlar ve rclpy bağlamı."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import rclpy
import yaml
from delta_server.common import min_tool_z_mm
from delta_server.robot import Robot
from delta_server.safety import Limits

PKG = Path(__file__).resolve().parents[1]
SERVER_YAML = PKG / "config" / "server.yaml"


def _robot_yaml() -> str:
    """Depodaki robot.yaml (bağlı çalışma alanı) ya da imajdaki kopya."""
    repo = PKG.parents[2] / "config" / "robot.yaml"
    if repo.is_file():
        return str(repo)
    return os.environ.get("DELTA_ROBOT_YAML", "/opt/delta/config/robot.yaml")


@pytest.fixture(scope="session")
def robot_yaml() -> str:
    return _robot_yaml()


@pytest.fixture(scope="session")
def robot(robot_yaml) -> Robot:
    return Robot.load(robot_yaml)


@pytest.fixture(scope="session")
def server_cfg() -> dict:
    """server.yaml: ortak (/**) ve düğüm bölümleri."""
    return yaml.safe_load(SERVER_YAML.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def limits(server_cfg, robot) -> Limits:
    """server.yaml'daki G5 sınırları (testler sayıları koda kopyalamaz)."""
    common = server_cfg["/**"]["ros__parameters"]
    sup = server_cfg["supervisor"]["ros__parameters"]
    return Limits(
        max_vel_deg_s=common["max_joint_velocity_deg_s"],
        max_acc_deg_s2=common["max_joint_acceleration_deg_s2"],
        rate_hz=common["sample_rate_hz"],
        start_tolerance_deg=sup["start_tolerance_deg"],
        cartesian_tolerance_mm=sup["cartesian_tolerance_mm"],
        max_duration_s=sup["max_duration_s"],
        min_tool_z_mm=min_tool_z_mm(robot.spec),
        tool_offset_mm=robot.spec["kinematics"]["ee_offset"],
    )


@pytest.fixture(scope="session")
def ros_context():
    """Oturum boyu tek rclpy bağlamı."""
    rclpy.init()
    yield
    rclpy.try_shutdown()
