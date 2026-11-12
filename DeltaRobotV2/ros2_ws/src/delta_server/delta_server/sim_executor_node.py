"""sim_executor: GEÇİCİ sanal yürütücü (geliştirme ve ekran görüntüleri için yer tutucu).

!!! Bu düğüm gerçek kenar köprüsü DEĞİLDİR. Ana oturum bunu, Pi'deki `delta_edge` servisiyle
!!! (ya da aynı protokolü konuşan sanal Pi ile) TLS WebSocket üzerinden konuşan `edge_bridge`
!!! düğümüyle değiştirecek. Bekçi (G6/G7), son kapı (K katmanı) ve telemetri sınırları burada
!!! YOKTUR; yalnız sayı olmayan değer içeren yörünge oynatılmaz.

Arayüzler:
  abone  /edge/trajectory_out (trajectory_msgs/JointTrajectory, radyan)  kabul edilen yörünge
  yayın  /joint_states        (sensor_msgs/JointState, motor_1..3, radyan) sample_rate_hz (100 Hz)
  yayın  /edge/status         (delta_interfaces/EdgeStatus)               status_rate_hz (10 Hz)

Oynatma kendi monoton saatiyle yapılır (Pi gibi): örnek sırası = (şimdi - başlangıç) / periyot.
Başlangıç pozu robot.yaml assembly_pose'un ters kinematiğidir.
"""

from __future__ import annotations

import math
import time

import rclpy
from delta_interfaces.msg import EdgeStatus
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory

from delta_server import common
from delta_server.robot import JOINT_NAMES, deg_to_rad

# Sanal telemetri (gerçek değerler delta_edge'den gelir)
SIM_TEMP_C = 30.0
SIM_VOLTAGE_V = 12.0


class SimExecutor(Node):
    """Kabul edilen yörüngeyi 100 Hz oynatır, eklem durumu ve kenar durumu yayımlar."""

    def __init__(self, clock=time.monotonic, **kwargs):
        super().__init__("sim_executor", **kwargs)
        self.robot, self.limits = common.declare_common(self)
        self.declare_parameter("status_rate_hz", 10.0)
        self.now = clock
        home = self.robot.kin.inverse(self.robot.home_mm)
        self.position = deg_to_rad(home) if home is not None else [0.0, 0.0, 0.0]
        self.points: list[list[float]] = []
        self.trajectory_id = ""
        self.index = -1
        self.t0 = 0.0
        self.state = "IDLE"
        self.js_pub = self.create_publisher(JointState, common.TOPIC_JOINT_STATES, common.QOS_STATE)
        self.status_pub = self.create_publisher(
            EdgeStatus, common.TOPIC_EDGE_STATUS, common.QOS_STATE
        )
        self.create_subscription(
            JointTrajectory, common.TOPIC_TRAJECTORY_OUT, self.on_trajectory, common.QOS_COMMAND
        )
        self.create_timer(1.0 / self.limits.rate_hz, self.tick)
        self.create_timer(
            1.0 / float(self.get_parameter("status_rate_hz").value), self.publish_status
        )
        self.get_logger().warning(
            "sim_executor GEÇİCİ yer tutucudur; gerçek kenar köprüsü (edge_bridge) değildir"
        )

    def on_trajectory(self, msg: JointTrajectory) -> None:
        """Yeni yörüngeyi yükler; sayı olmayan değer varsa oynatmaz."""
        pts = [list(p.positions) for p in msg.points]
        if not pts or any(len(p) != 3 or not all(math.isfinite(v) for v in p) for p in pts):
            self.state = "FAULT"
            self.get_logger().error(f"{msg.header.frame_id}: bozuk yörünge, oynatılmadı")
            return
        if list(msg.joint_names) != list(JOINT_NAMES):
            self.state = "FAULT"
            self.get_logger().error(f"{msg.header.frame_id}: eklem adları uyuşmuyor")
            return
        self.points = pts
        self.trajectory_id = msg.header.frame_id
        self.t0 = self.now()
        self.index = 0
        self.state = "RUNNING"
        self.publish_status()  # durum değişimi hemen bildirilir

    def tick(self) -> None:
        """100 Hz: oynatma sırasını ilerletir ve /joint_states yayımlar."""
        if self.state == "RUNNING":
            k = int((self.now() - self.t0) * self.limits.rate_hz + 1e-6)
            if k >= len(self.points) - 1:
                k = len(self.points) - 1
                self.state = "IDLE"
                self.publish_status()
            self.index = k
            self.position = list(self.points[k])
        js = JointState()
        js.header.stamp = self.get_clock().now().to_msg()
        js.name = list(JOINT_NAMES)
        js.position = [float(v) for v in self.position]
        js.velocity = []
        self.js_pub.publish(js)

    def publish_status(self) -> None:
        """Sanal telemetri (EdgeStatus)."""
        st = EdgeStatus()
        st.stamp = self.get_clock().now().to_msg()
        st.state = self.state
        st.angles = [float(v) for v in self.position]
        st.temps = [SIM_TEMP_C] * 3
        st.loads = [0.0] * 3
        st.voltages = [SIM_VOLTAGE_V] * 3
        st.trajectory_id = self.trajectory_id
        st.index = self.index if self.state == "RUNNING" else -1
        self.status_pub.publish(st)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SimExecutor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
