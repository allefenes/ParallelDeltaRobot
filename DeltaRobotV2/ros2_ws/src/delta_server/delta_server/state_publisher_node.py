"""delta_state_publisher: motor açılarından dijital ikizin TF'ini ve görsellerini yayımlar.

Arayüzler:
  abone  /joint_states       (sensor_msgs/JointState, motor_1..3, RADYAN)
  abone  /supervisor/events  (delta_interfaces/SupervisorEvent)  hedef ve ret görseli
  yayın  /tf                 base_link -> bicep_i, forearm_i_a/b, platform (joint_states hızında)
  yayın  /delta/markers      (visualization_msgs/MarkerArray, metre)  tabla, taşlar, uç izi, hedef

URDF'te hareketli bağlar `floating` eklemlidir; robot_state_publisher onları yayımlamaz.
Çerçeve tanımları delta_server.frames modülündedir (cad/README.md ile aynı).
"""

from __future__ import annotations

from collections import deque

import rclpy
from delta_interfaces.msg import SupervisorEvent
from geometry_msgs.msg import TransformStamped
from rclpy.node import Node
from sensor_msgs.msg import JointState
from tf2_ros import TransformBroadcaster
from visualization_msgs.msg import MarkerArray

from delta_server import common, markers
from delta_server.frames import link_poses, tip_mm
from delta_server.robot import JOINT_NAMES, rad_to_deg

TRAIL_MIN_STEP_MM = 0.5


class DeltaStatePublisher(Node):
    """İleri kinematikle bağ TF'leri + RViz marker'ları."""

    def __init__(self, **kwargs):
        super().__init__("delta_state_publisher", **kwargs)
        self.robot, _ = common.declare_common(self)
        self.declare_parameter("board_center_mm", [0.0, 0.0])
        self.declare_parameter("board_size_mm", 60.0)
        self.declare_parameter("board_cells", 3)
        self.declare_parameter("piece_diameter_mm", 16.0)
        self.declare_parameter("pieces", "")
        self.declare_parameter("trail_length", 1000)
        self.declare_parameter("marker_rate_hz", 2.0)
        center = list(self.get_parameter("board_center_mm").value)
        self.board = markers.Board(
            center_mm=(float(center[0]), float(center[1])),
            size_mm=float(self.get_parameter("board_size_mm").value),
            cells=int(self.get_parameter("board_cells").value),
            top_z_mm=self.robot.board_top_mm,
            thickness_mm=float(self.robot.spec["task"]["board_thickness"]),
            piece_height_mm=float(self.robot.spec["task"]["piece_height"]),
            piece_diameter_mm=float(self.get_parameter("piece_diameter_mm").value),
        )
        self.pieces = str(self.get_parameter("pieces").value)
        self.trail: deque = deque(maxlen=int(self.get_parameter("trail_length").value))
        self.target: list = []
        self.last_platform_mm = None
        self.tf = TransformBroadcaster(self)
        self.marker_pub = self.create_publisher(
            MarkerArray, common.TOPIC_MARKERS, common.QOS_LATCHED
        )
        self.create_subscription(
            JointState, common.TOPIC_JOINT_STATES, self.on_joint_state, common.QOS_STATE
        )
        self.create_subscription(
            SupervisorEvent, common.TOPIC_EVENTS, self.on_event, common.QOS_EVENTS
        )
        rate = float(self.get_parameter("marker_rate_hz").value)
        self.create_timer(1.0 / rate, self.publish_markers)
        self.publish_markers()

    def transforms(self, theta_deg, stamp) -> list[TransformStamped]:
        """Motor açılarından (derece) tüm hareketli bağların TF'i; FK çözümsüzse boş."""
        poses = link_poses(self.robot, theta_deg)
        if poses is None:
            return []
        out = []
        for name, pose in poses.items():
            t = TransformStamped()
            t.header.stamp = stamp
            t.header.frame_id = markers.FRAME
            t.child_frame_id = name
            x, y, z = (float(v) / 1000.0 for v in pose.position_mm)  # mm -> m
            t.transform.translation.x, t.transform.translation.y = x, y
            t.transform.translation.z = z
            q = pose.quaternion_xyzw()
            t.transform.rotation.x, t.transform.rotation.y = q[0], q[1]
            t.transform.rotation.z, t.transform.rotation.w = q[2], q[3]
            out.append(t)
        self.last_platform_mm = tuple(float(v) for v in poses["platform"].position_mm)
        return out

    def on_joint_state(self, msg: JointState) -> None:
        """Her /joint_states mesajında TF yayımlar (aynı zaman damgasıyla)."""
        try:
            rad = [msg.position[list(msg.name).index(n)] for n in JOINT_NAMES]
        except (ValueError, IndexError):
            self.get_logger().warning("joint_states motor_1..3 içermiyor", throttle_duration_sec=5)
            return
        stamp = msg.header.stamp
        if stamp.sec == 0 and stamp.nanosec == 0:
            stamp = self.get_clock().now().to_msg()
        tfs = self.transforms(rad_to_deg(rad), stamp)
        if not tfs:
            self.get_logger().warning("ileri kinematik çözümsüz", throttle_duration_sec=5)
            return
        self.tf.sendTransform(tfs)
        self.extend_trail(tip_mm(self.robot, self.last_platform_mm))

    def extend_trail(self, p_mm) -> None:
        """Uç izine nokta ekler (0.5 mm'den kısa adımlar atlanır)."""
        if self.trail:
            last = self.trail[-1]
            if sum((a - b) ** 2 for a, b in zip(p_mm, last, strict=True)) < TRAIL_MIN_STEP_MM**2:
                return
        self.trail.append(p_mm)

    def on_event(self, ev: SupervisorEvent) -> None:
        """Süpervizör kararı: kabulde iz sıfırlanır ve hedef yeşil; retde kırmızı + neden."""
        # Hedef P (mm) mıknatıs ucuna çevrilir; iz de uç yolunu gösterir.
        target = tip_mm(self.robot, (ev.target_mm.x, ev.target_mm.y, ev.target_mm.z))
        if ev.accepted:
            self.trail.clear()
            if self.last_platform_mm is not None:
                self.trail.append(tip_mm(self.robot, self.last_platform_mm))
        self.target = markers.target_markers(target, ev.accepted, ev.reason)
        self.publish_markers()

    def publish_markers(self) -> None:
        """Tüm marker'ları tek MarkerArray olarak yayımlar."""
        arr = MarkerArray()
        arr.markers = markers.board_markers(self.board, self.pieces)
        arr.markers.append(markers.trail_marker(list(self.trail)))
        arr.markers += self.target
        self.marker_pub.publish(arr)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = DeltaStatePublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
