"""supervisor: sunucu tarafı 1. güvenlik kapısı.

Arayüzler:
  servis  /supervisor/validate (delta_interfaces/ValidateTrajectory)  planlayıcıdan yörünge
  yayın   /supervisor/events   (delta_interfaces/SupervisorEvent)     her karar, reliable
  yayın   /edge/trajectory_out (trajectory_msgs/JointTrajectory)      yalnız kabul edilenler
  abone   /joint_states        (sensor_msgs/JointState)               başlangıç sürekliliği
  abone   /edge/status         (delta_interfaces/EdgeStatus)          kenar meşgul mü

Kararın kuralları delta_server.safety modülündedir (G1, G2, G3, G4, G5). Kenara giden yörüngede
açılar RADYAN, zaman 1/sample_rate_hz ızgarasında; header.stamp kabul anı, header.frame_id
yörünge kimliğidir (JointTrajectory'de kimlik alanı yok; eklem uzayında çerçeve kullanılmaz).
Pi'deki delta_edge aynı yörüngeyi kendi (son) kapısından yeniden geçirir.
"""

from __future__ import annotations

import math

import numpy as np
import rclpy
from delta_interfaces.msg import EdgeStatus, SupervisorEvent
from delta_interfaces.srv import ValidateTrajectory
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory

from delta_server import common
from delta_server.robot import JOINT_NAMES, rad_to_deg
from delta_server.safety import Limits, Verdict, validate


class Supervisor(Node):
    """Yörüngeleri denetler; kabul edileni kenara iletir, her kararı olay olarak yayımlar."""

    def __init__(self, **kwargs):
        super().__init__("supervisor", **kwargs)
        robot, base = common.declare_common(self)
        self.declare_parameter("start_tolerance_deg", 1.0)
        self.declare_parameter("cartesian_tolerance_mm", 0.5)
        self.declare_parameter("max_duration_s", 60.0)
        self.robot = robot
        self.limits = Limits(
            max_vel_deg_s=base.max_vel_deg_s,
            max_acc_deg_s2=base.max_acc_deg_s2,
            rate_hz=base.rate_hz,
            start_tolerance_deg=float(self.get_parameter("start_tolerance_deg").value),
            cartesian_tolerance_mm=float(self.get_parameter("cartesian_tolerance_mm").value),
            max_duration_s=float(self.get_parameter("max_duration_s").value),
            min_tool_z_mm=base.min_tool_z_mm,
            tool_offset_mm=base.tool_offset_mm,
        )
        self.current_deg: list[float] | None = None
        self.edge_state = "UNKNOWN"
        self.events = self.create_publisher(SupervisorEvent, common.TOPIC_EVENTS, common.QOS_EVENTS)
        self.out = self.create_publisher(
            JointTrajectory, common.TOPIC_TRAJECTORY_OUT, common.QOS_COMMAND
        )
        self.create_subscription(
            JointState, common.TOPIC_JOINT_STATES, self.on_joint_state, common.QOS_STATE
        )
        self.create_subscription(
            EdgeStatus, common.TOPIC_EDGE_STATUS, self.on_edge_status, common.QOS_STATE
        )
        self.create_service(ValidateTrajectory, common.SRV_VALIDATE, self.on_validate)
        self.get_logger().info(
            f"1. kapı hazır: v<={self.limits.max_vel_deg_s:g}°/s, "
            f"a<={self.limits.max_acc_deg_s2:g}°/s², {self.limits.rate_hz:g} Hz, "
            f"robot.yaml={robot.path}"
        )

    def on_joint_state(self, msg: JointState) -> None:
        """Robotun anlık açıları (radyan -> derece), motor_1..3 adlarıyla."""
        try:
            rad = [msg.position[list(msg.name).index(n)] for n in JOINT_NAMES]
        except (ValueError, IndexError):
            return
        self.current_deg = rad_to_deg(rad)

    def on_edge_status(self, msg: EdgeStatus) -> None:
        """Kenar durumu (RUNNING iken yeni yörünge kabul edilmez)."""
        self.edge_state = msg.state

    def check(self, traj: JointTrajectory, cartesian) -> Verdict:
        """Mesajı ayrıştırır ve safety.validate ile denetler."""
        if list(traj.joint_names) != list(JOINT_NAMES):
            return Verdict(False, "G4", f"eklem adları {list(JOINT_NAMES)} değil")
        if self.edge_state in ("RUNNING", "FAULT"):
            return Verdict(False, "DURUM", f"kenar meşgul ya da arızalı ({self.edge_state})")
        rows, times = [], []
        for k, pt in enumerate(traj.points):
            if len(pt.positions) != 3:
                return Verdict(False, "G4", f"örnek {k}: 3 açı yok", k)
            rows.append(rad_to_deg(pt.positions))
            times.append(common.duration_s(pt.time_from_start))
        th = np.asarray(rows, dtype=float).reshape(-1, 3)
        cart = [(p.x, p.y, p.z) for p in cartesian] if cartesian else None
        return validate(
            self.robot.kin, th, times, self.limits, cartesian_mm=cart, current_deg=self.current_deg
        )

    def on_validate(self, req, resp):
        """ValidateTrajectory servisi: karar ver, olay yayımla, kabulse kenara gönder."""
        verdict = self.check(req.trajectory, list(req.cartesian_mm))
        self.publish_event(req.trajectory_id, verdict, req.target_mm)
        if verdict.accepted:
            out = JointTrajectory()
            out.header.stamp = self.get_clock().now().to_msg()
            out.header.frame_id = req.trajectory_id
            out.joint_names = list(JOINT_NAMES)
            out.points = list(req.trajectory.points)
            self.out.publish(out)
            self.get_logger().info(
                f"{req.trajectory_id}: kabul, {len(out.points)} örnek kenara gönderildi"
            )
        else:
            self.get_logger().warning(f"{req.trajectory_id}: RET {verdict.message}")
        resp.accepted = verdict.accepted
        resp.requirement = verdict.requirement
        resp.reason = verdict.message
        return resp

    def publish_event(self, trajectory_id: str, verdict: Verdict, target_mm) -> None:
        """SupervisorEvent yayımlar."""
        ev = SupervisorEvent()
        ev.stamp = self.get_clock().now().to_msg()
        ev.trajectory_id = trajectory_id
        ev.accepted = verdict.accepted
        ev.requirement = verdict.requirement
        ev.reason = verdict.message
        ev.sample_index = int(verdict.index)
        for ax in ("x", "y", "z"):
            v = float(getattr(target_mm, ax))
            setattr(ev.target_mm, ax, v if math.isfinite(v) else 0.0)
        self.events.publish(ev)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = Supervisor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
