"""edge_bridge: ROS2 yığını ile Raspberry Pi kenarı (delta_edge) arasındaki köprü.

Pi (ya da sanal Pi) bu düğüme TLS WebSocket ile KENDİSİ bağlanır (robot tarafında gelen port yok).
Köprü kabul edilen yörüngeyi kenar protokolüne çevirip gönderir, kalp atışını yollar ve kenar
telemetrisini ROS konularına yayımlar. Son güvenlik kapısı ve bekçi kenardadır; köprü yalnız taşır.

Arayüzler:
  abone  /edge/trajectory_out (trajectory_msgs/JointTrajectory, radyan)  1. kapıdan geçen yörünge
  yayın  /joint_states        (sensor_msgs/JointState, radyan)  kenar telemetrisi, 20 Hz
  yayın  /edge/status         (delta_interfaces/EdgeStatus)      kenar telemetrisi, 20 Hz
  yayın  /edge/connected      (std_msgs/Bool, kalıcı)            kenar bağlı mı
  yayın  /supervisor/events   (delta_interfaces/SupervisorEvent) kenarın reddettiği / arıza
  servis /edge_bridge/torque         (std_srvs/SetBool)   tork aç/kapa
  servis /edge_bridge/magnet         (std_srvs/SetBool)   elektromıknatıs aç/kapa
  servis /edge_bridge/stop           (std_srvs/Trigger)   yörüngeyi kes, konumu tut (HOLDING)
  servis /edge_bridge/heartbeat_pause (std_srvs/SetBool)  YALNIZ TEST: kalp atışını durdurur
                                                           (bekçi G6/G7 hata enjeksiyonu)
Parametreler: listen_host, listen_port, path, cert_file, key_file, token, heartbeat_hz,
auto_torque (bağlanınca tork aç).
"""

from __future__ import annotations

import asyncio
import ssl
import threading

import rclpy
import websockets
from delta_interfaces.msg import EdgeStatus, SupervisorEvent
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool
from std_srvs.srv import SetBool, Trigger
from trajectory_msgs.msg import JointTrajectory

from delta_server import common
from delta_server import edge_protocol as ep
from delta_server.robot import JOINT_NAMES


class EdgeBridge(Node):
    """Kenar WebSocket sunucusu + ROS köprüsü."""

    def __init__(self, **kwargs):
        super().__init__("edge_bridge", **kwargs)
        p = {
            "listen_host": "0.0.0.0",
            "listen_port": 8443,
            "path": "/edge",
            "cert_file": "/certs/server.crt",
            "key_file": "/certs/server.key",
            "token": "",
            "heartbeat_hz": 20.0,
            "auto_torque": True,
        }
        for k, v in p.items():
            self.declare_parameter(k, v)
        self.cfg = {k: self.get_parameter(k).value for k in p}
        self.js_pub = self.create_publisher(JointState, common.TOPIC_JOINT_STATES, common.QOS_STATE)
        self.status_pub = self.create_publisher(
            EdgeStatus, common.TOPIC_EDGE_STATUS, common.QOS_STATE
        )
        self.event_pub = self.create_publisher(
            SupervisorEvent, common.TOPIC_EVENTS, common.QOS_EVENTS
        )
        self.conn_pub = self.create_publisher(Bool, "/edge/connected", common.QOS_LATCHED)
        self.create_subscription(
            JointTrajectory, common.TOPIC_TRAJECTORY_OUT, self.on_trajectory, common.QOS_COMMAND
        )
        self.create_service(SetBool, "/edge_bridge/torque", self.on_torque)
        self.create_service(SetBool, "/edge_bridge/magnet", self.on_magnet)
        self.create_service(Trigger, "/edge_bridge/stop", self.on_stop)
        self.create_service(SetBool, "/edge_bridge/heartbeat_pause", self.on_pause)
        self.client = None
        self.paused = False
        self.seq = 0
        self.loop = asyncio.new_event_loop()
        self._publish_connected(False)
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    # --- ROS tarafı ---------------------------------------------------------------------------

    def on_trajectory(self, msg: JointTrajectory) -> None:
        """1. kapıdan geçen yörüngeyi kenara gönderir; kenar yoksa olay yayımlar."""
        tid = msg.header.frame_id or "traj"
        if list(msg.joint_names) != list(JOINT_NAMES):
            self._event(tid, "G4", "eklem adları uyuşmuyor")
            return
        times = [pt.time_from_start.sec + pt.time_from_start.nanosec * 1e-9 for pt in msg.points]
        try:
            text = ep.trajectory(tid, times, [list(pt.positions) for pt in msg.points])
        except ep.ProtocolError as e:
            self._event(tid, "G4", f"kenara gönderilemedi: {e}")
            return
        if not self._send(text):
            self._event(tid, "DURUM", "kenar bağlı değil")

    def on_torque(self, req, res):
        res.success = self._send(ep.command("torque", req.data))
        res.message = "gönderildi" if res.success else "kenar bağlı değil"
        return res

    def on_magnet(self, req, res):
        """Mıknatıs komutu; kenar durumu uygun değilse `fault` (not_ready) ile reddeder."""
        res.success = self._send(ep.command("magnet", req.data))
        res.message = "gönderildi" if res.success else "kenar bağlı değil"
        return res

    def on_stop(self, _req, res):
        """Dur: kenar yörüngeyi keser, ölçülen konumu tutar ve HOLDING'e geçer (`hold`).

        API sözleşmesi: duruştan sonra yeniden hareket için `torque on` ile IDLE'a dönülür.
        Kenarın `stop` komutu konumu tutup IDLE'da kalır; arayüzün açık onay adımı için `hold`.
        """
        res.success = self._send(ep.command("hold"))
        res.message = "gönderildi" if res.success else "kenar bağlı değil"
        return res

    def on_pause(self, req, res):
        """YALNIZ TEST: kalp atışını keser (bekçinin G6/G7 davranışını sınamak için)."""
        self.paused = bool(req.data)
        self.get_logger().warning(f"kalp atışı {'DURDURULDU (test)' if self.paused else 'sürüyor'}")
        res.success = True
        res.message = "tamam"
        return res

    def _event(self, tid: str, req: str, reason: str) -> None:
        ev = SupervisorEvent()
        ev.stamp = self.get_clock().now().to_msg()
        ev.trajectory_id = tid
        ev.accepted = False
        ev.requirement = req
        ev.reason = reason
        ev.sample_index = -1
        self.event_pub.publish(ev)
        self.get_logger().warning(f"{tid}: {req}: {reason}")

    def _publish_connected(self, on: bool) -> None:
        self.conn_pub.publish(Bool(data=on))

    def _publish_telemetry(self, t: ep.Telemetry) -> None:
        now = self.get_clock().now().to_msg()
        js = JointState()
        js.header.stamp = now
        js.name = list(JOINT_NAMES)
        js.position = t.angles_rad
        self.js_pub.publish(js)
        st = EdgeStatus()
        st.stamp = now
        st.state = t.state
        st.angles = t.angles_rad
        st.temps = t.temps
        st.loads = [v / 100.0 for v in t.loads]
        st.voltages = t.voltages
        st.trajectory_id = t.traj_id
        st.index = t.index
        st.magnet = t.magnet
        self.status_pub.publish(st)

    # --- Ağ tarafı (ayrı iş parçacığında asyncio) ---------------------------------------------

    def _send(self, text: str) -> bool:
        ws = self.client
        if ws is None:
            return False
        asyncio.run_coroutine_threadsafe(ws.send(text), self.loop)
        return True

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._serve())

    async def _serve(self) -> None:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(self.cfg["cert_file"], self.cfg["key_file"])
        async with websockets.serve(
            self._handler, self.cfg["listen_host"], int(self.cfg["listen_port"]), ssl=ctx
        ):
            self.get_logger().info(
                f"kenar uç noktası: wss://{self.cfg['listen_host']}:{self.cfg['listen_port']}"
                f"{self.cfg['path']}"
            )
            await self._heartbeat_loop()

    async def _heartbeat_loop(self) -> None:
        period = 1.0 / float(self.cfg["heartbeat_hz"])
        while rclpy.ok():
            ws = self.client
            if ws is not None and not self.paused:
                self.seq += 1
                try:
                    await ws.send(ep.heartbeat(self.seq))
                except websockets.ConnectionClosed:
                    pass
            await asyncio.sleep(period)

    async def _handler(self, ws, path: str | None = None) -> None:
        req_path = path if path is not None else getattr(ws, "path", self.cfg["path"])
        if req_path != self.cfg["path"]:
            await ws.close(code=1008, reason="yol")
            return
        token = self.cfg["token"]
        if token and ws.request_headers.get("Authorization", "") != f"Bearer {token}":
            self.get_logger().error("kenar bağlantısı reddedildi: belirteç hatalı")
            await ws.close(code=1008, reason="kimlik")
            return
        if self.client is not None:
            await self.client.close(code=1001, reason="yeni bağlantı")
        self.client = ws
        self._publish_connected(True)
        self.get_logger().info("kenar bağlandı")
        self.seq += 1
        await ws.send(ep.heartbeat(self.seq))
        if self.cfg["auto_torque"]:
            await ws.send(ep.command("torque", True))
        try:
            async for text in ws:
                self._on_incoming(text)
        except websockets.ConnectionClosed:
            pass
        finally:
            if self.client is ws:
                self.client = None
                self._publish_connected(False)
                self.get_logger().warning("kenar bağlantısı koptu")

    def _on_incoming(self, text) -> None:
        try:
            kind, data = ep.parse_incoming(text)
        except ep.ProtocolError as e:
            self.get_logger().error(f"kenardan geçersiz mesaj: {e}")
            return
        if kind == "telemetry":
            self._publish_telemetry(data)
        elif kind == "fault":
            code, detail = data
            self._event("", ep.requirement_for(code), f"kenar: {code}: {detail}")
        else:
            self.get_logger().info(f"kenar yörüngeyi kabul etti: {data}")


def main(args=None) -> None:
    rclpy.init(args=args)
    node = EdgeBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
