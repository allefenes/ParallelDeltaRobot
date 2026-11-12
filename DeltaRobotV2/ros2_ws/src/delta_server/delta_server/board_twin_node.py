"""board_twin: tic-tac-toe tablasının dijital ikizi (F4.5).

Kenar telemetrisinden (açılar + mıknatıs) mıknatıs ucunun konumunu bulur, taşları `BoardTwin`
ile al/bırak fiziğine göre taşır; tabla durumunu ve RViz marker'larını yayımlar. Gerçek robotta
(F5+) aynı düğüm beklenen durumu verir; kamera doğrulaması sonraki iş.

Arayüzler:
  abone  /edge/status   (delta_interfaces/EdgeStatus)  açılar (rad) + mıknatıs
  yayın  /board/state   (std_msgs/String, JSON, kalıcı) hücreler, kazanan, taşlar, metrikler
  yayın  /delta/markers (visualization_msgs/MarkerArray, "pieces" ad alanı) taşlar
  servis /board/reset   (std_srvs/Trigger)             taşları başlangıç dizilişine alır
"""

from __future__ import annotations

import json
import math

import rclpy
from delta_interfaces.msg import EdgeStatus
from rclpy.node import Node
from std_msgs.msg import String
from std_srvs.srv import Trigger
from visualization_msgs.msg import Marker, MarkerArray

from delta_server import common, markers
from delta_server.board_game import BoardTwin, Geometry

TOPIC_BOARD_STATE = "/board/state"
SRV_BOARD_RESET = "/board/reset"


class BoardTwinNode(Node):
    def __init__(self, **kwargs):
        super().__init__("board_twin", **kwargs)
        self.robot, _ = common.declare_common(self)
        self.declare_parameter("publish_rate_hz", 10.0)
        self.geo = Geometry.from_spec(self.robot.spec)
        self.twin = BoardTwin(self.geo)
        self.state_pub = self.create_publisher(String, TOPIC_BOARD_STATE, common.QOS_LATCHED)
        self.marker_pub = self.create_publisher(
            MarkerArray, common.TOPIC_MARKERS, common.QOS_LATCHED
        )
        self.create_subscription(
            EdgeStatus, common.TOPIC_EDGE_STATUS, self.on_status, common.QOS_STATE
        )
        self.create_service(Trigger, SRV_BOARD_RESET, self.on_reset)
        rate = float(self.get_parameter("publish_rate_hz").value)
        self.create_timer(1.0 / rate, self.publish)
        self.publish()
        self.get_logger().info(
            f"tabla ikizi hazır: hücre {self.geo.cell:g} mm, alma P z={self.geo.pick_p:g} mm"
        )

    def tip_mm(self, angles_rad) -> tuple[float, float, float] | None:
        """Mıknatıs ucu = P − tool_offset (z); FK çözümsüzse None."""
        P = self.robot.kin.forward(tuple(math.degrees(a) for a in angles_rad))
        if P is None:
            return None
        return (float(P[0]), float(P[1]), float(P[2]) - self.geo.tool_offset)

    def on_status(self, msg: EdgeStatus) -> None:
        self.twin.update(self.tip_mm(list(msg.angles)), bool(msg.magnet))

    def on_reset(self, _req, res):
        self.twin.reset()
        self.publish()
        res.success, res.message = True, "taşlar başlangıç dizilişinde"
        return res

    def publish(self) -> None:
        self.state_pub.publish(String(data=json.dumps(self.twin.to_dict())))
        self.marker_pub.publish(MarkerArray(markers=self.piece_markers()))

    def piece_markers(self) -> list[Marker]:
        out = []
        g = self.geo
        for i, p in enumerate(self.twin.pieces):
            m = Marker()
            m.header.frame_id = markers.FRAME
            m.ns, m.id, m.type, m.action = "pieces", i, Marker.CYLINDER, Marker.ADD
            m.pose.orientation.w = 1.0
            m.pose.position.x = p.pos[0] / 1000.0
            m.pose.position.y = p.pos[1] / 1000.0
            m.pose.position.z = (p.pos[2] + g.piece_height / 2.0) / 1000.0
            m.scale.x = m.scale.y = g.piece_diameter / 1000.0
            m.scale.z = g.piece_height / 1000.0
            r, gg, b, a = markers.PIECE_COLORS[p.kind]
            m.color.r, m.color.g, m.color.b, m.color.a = r, gg, b, a
            out.append(m)
        return out


def main(args=None) -> None:
    rclpy.init(args=args)
    node = BoardTwinNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
