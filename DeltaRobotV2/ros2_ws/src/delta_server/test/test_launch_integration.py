"""Uçtan uca launch_testing: yığın (sim_executor ile) ayrı süreçlerde, DDS üzerinden.

1. Geçerli hedefe /move_to -> kabul; /joint_states hedefin ters kinematiğine ulaşır.
2. Limit dışı hedefe /move_to -> G1/G2 nedeniyle ret; SupervisorEvent (accepted=false) yayımlanır.
"""

from __future__ import annotations

import math
import os
import time
import unittest
from pathlib import Path

import delta_core_py as dc
import launch_testing
import pytest
import rclpy
from ament_index_python.packages import get_package_share_directory
from delta_interfaces.msg import EdgeStatus, SupervisorEvent
from delta_interfaces.srv import MoveTo
from delta_server.robot import JOINT_NAMES, robot_yaml_path
from geometry_msgs.msg import Point
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from sensor_msgs.msg import JointState

VALID_TARGET = (20.0, 10.0, -200.0)  # mm, erişilebilir ve limit içinde
OUT_OF_LIMIT = (60.0, 0.0, -140.0)  # mm, motor/rot başı limiti dışında
TOL_RAD = math.radians(0.05)


def _robot_yaml() -> str:
    repo = Path(__file__).resolve().parents[4] / "config" / "robot.yaml"
    return str(repo) if repo.is_file() else robot_yaml_path("")


@pytest.mark.launch_test
def generate_test_description():
    launch = Path(get_package_share_directory("delta_server")) / "launch" / "delta.launch.py"
    stack = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(launch)),
        launch_arguments={"rviz": "false", "sim": "true", "robot_yaml": _robot_yaml()}.items(),
    )
    return LaunchDescription([stack, launch_testing.actions.ReadyToTest()])


class TestStack(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node("delta_integration_test")
        cls.kin = dc.DeltaKinematics(dc.load_params(_robot_yaml()))
        cls.joints = None
        cls.events: list[SupervisorEvent] = []
        cls.node.create_subscription(JointState, "/joint_states", cls._on_js, 10)
        cls.node.create_subscription(SupervisorEvent, "/supervisor/events", cls.events.append, 50)
        cls.edge_state = ""
        cls.node.create_subscription(EdgeStatus, "/edge/status", cls._on_status, 10)
        cls.client = cls.node.create_client(MoveTo, "/move_to")

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()

    @classmethod
    def _on_status(cls, msg: EdgeStatus):
        cls.edge_state = msg.state

    @classmethod
    def _on_js(cls, msg: JointState):
        cls.joints = [msg.position[list(msg.name).index(n)] for n in JOINT_NAMES]

    def spin_until(self, cond, timeout):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            rclpy.spin_once(self.node, timeout_sec=0.05)
            if cond():
                return True
        return False

    def move_to(self, target, duration):
        self.assertTrue(self.client.wait_for_service(timeout_sec=30.0), "/move_to yok")
        req = MoveTo.Request()
        req.target = Point(x=target[0], y=target[1], z=target[2])
        req.duration_s = duration
        fut = self.client.call_async(req)
        self.assertTrue(self.spin_until(fut.done, 20.0), "/move_to yanıtı yok")
        return fut.result()

    def test_1_valid_move_reaches_ik_solution(self):
        self.assertTrue(self.spin_until(lambda: self.joints is not None, 30.0), "joint_states yok")
        resp = self.move_to(VALID_TARGET, 1.0)
        self.assertTrue(resp.accepted, resp.reason)
        goal = [math.radians(a) for a in self.kin.inverse(VALID_TARGET)]

        def reached():
            return self.joints is not None and all(
                abs(a - b) < TOL_RAD for a, b in zip(self.joints, goal, strict=True)
            )

        self.assertTrue(self.spin_until(reached, 15.0), f"hedefe ulaşılamadı: {self.joints}")
        self.assertTrue(self.spin_until(lambda: any(e.accepted for e in self.events), 5.0))
        # Kenar yörüngeyi bitirip boşa geçer (yeni komut ancak o zaman kabul edilir)
        self.assertTrue(self.spin_until(lambda: self.edge_state == "IDLE", 5.0), self.edge_state)

    def test_2_out_of_limit_rejected_with_event(self):
        before = list(self.joints) if self.joints else None
        resp = self.move_to(OUT_OF_LIMIT, 1.0)
        self.assertFalse(resp.accepted)
        self.assertIn(resp.reason[:2], ("G1", "G2"), resp.reason)

        def rejected():
            return any(
                (not e.accepted) and e.trajectory_id == resp.trajectory_id for e in self.events
            )

        self.assertTrue(self.spin_until(rejected, 5.0), "SupervisorEvent (ret) gelmedi")
        ev = [e for e in self.events if e.trajectory_id == resp.trajectory_id][-1]
        self.assertIn(ev.requirement, ("G1", "G2"))
        self.assertAlmostEqual(ev.target_mm.x, OUT_OF_LIMIT[0])
        # Robot yerinde kalır
        self.spin_until(lambda: False, 0.5)
        if before is not None:
            for a, b in zip(self.joints, before, strict=True):
                self.assertLess(abs(a - b), 1e-4)  # rad; ret sonrası hareket yok


@launch_testing.post_shutdown_test()
class TestShutdown(unittest.TestCase):
    def test_exit_codes(self, proc_info):
        # SIGINT ile kapanan düğümler 0 ya da -2 döner
        launch_testing.asserts.assertExitCodes(proc_info, allowable_exit_codes=[0, -2, -15])


if __name__ == "__main__":  # pragma: no cover
    os.sys.exit(0)
