"""ROS2 arka ucu: API'nin komutlarını ROS2 yığınına iletir, durumu ve olayları dinler.

`api` konteyneri `server` konteynerinin ağ ad alanını paylaşır; ROS2 trafiği localhost'ta kalır.
Hareket /move_to (planlayıcı + 1. kapı) üzerinden gider; mıknatıs, tork ve duruş edge_bridge
servisleridir. Bekleme: kenar telemetrisi aynı yörünge kimliğiyle IDLE'a dönünce hareket biter.
"""

from __future__ import annotations

import asyncio
import math
import threading
import time

import rclpy
from delta_interfaces.msg import EdgeStatus, SupervisorEvent
from delta_interfaces.srv import MoveTo
from geometry_msgs.msg import Point
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool
from std_srvs.srv import SetBool, Trigger

from delta_api.backend import (
    DEFAULT_LIMITS,
    DEFAULT_WORKSPACE,
    HOME_MM,
    Backend,
    MoveOutcome,
    RobotState,
    requirement_of,
    robot_info,
)

QOS_STATE = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST, depth=10
)
QOS_EVENTS = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST, depth=50
)
QOS_LATCHED = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
)
SERVICE_TIMEOUT_S = 5.0
STATUS_STALE_S = 1.0  # bu süre telemetri gelmezse durum DISCONNECTED sayılır
AUTO_DURATION_GUESS_S = 30.0  # süre planlayıcıya bırakılınca bekleme üst sınırı için


class RosBackend(Backend):
    """rclpy düğümü ayrı iş parçacığında döner; API asyncio döngüsünden çağrılır."""

    def __init__(self, spec: dict, kin=None) -> None:
        super().__init__()
        self.spec = spec
        self.kin = kin  # delta_core_py.DeltaKinematics: konum için ileri kinematik
        self._s = RobotState()
        self._last_status = 0.0
        self._lock = threading.Lock()
        rclpy.init()
        self.node = Node("api_gateway")
        group = ReentrantCallbackGroup()
        n = self.node
        n.create_subscription(EdgeStatus, "/edge/status", self._on_status, QOS_STATE)
        n.create_subscription(SupervisorEvent, "/supervisor/events", self._on_event, QOS_EVENTS)
        n.create_subscription(Bool, "/edge/connected", self._on_connected, QOS_LATCHED)
        self.cli_move = n.create_client(MoveTo, "/move_to", callback_group=group)
        self.cli_magnet = n.create_client(SetBool, "/edge_bridge/magnet", callback_group=group)
        self.cli_torque = n.create_client(SetBool, "/edge_bridge/torque", callback_group=group)
        self.cli_stop = n.create_client(Trigger, "/edge_bridge/stop", callback_group=group)
        self.executor = MultiThreadedExecutor(num_threads=4)
        self.executor.add_node(n)
        self.thread = threading.Thread(target=self.executor.spin, daemon=True)
        self.thread.start()

    # --- ROS geri çağrıları (yürütücü iş parçacığı) --------------------------------------------
    def _on_status(self, msg: EdgeStatus) -> None:
        angles = [float(math.degrees(a)) for a in msg.angles]
        pos = None
        if self.kin is not None:
            try:
                p = self.kin.forward(tuple(angles))
                if p is not None:
                    pos = [round(float(v), 2) for v in p]
            except Exception:  # noqa: BLE001 - kinematik çözümsüzse konum bilinmez
                pos = None
        with self._lock:
            s = self._s
            s.state = msg.state or "IDLE"
            s.angles_deg = [round(a, 3) for a in angles]
            s.position_mm = pos
            s.magnet = bool(msg.magnet)
            s.temps_c = [float(v) for v in msg.temps]
            s.loads = [float(v) for v in msg.loads]
            s.voltages = [float(v) for v in msg.voltages]
            s.trajectory_id = msg.trajectory_id or None
            self._last_status = time.monotonic()

    def _on_event(self, msg: SupervisorEvent) -> None:
        self.emit(
            {
                "type": "event",
                "accepted": bool(msg.accepted),
                "requirement": msg.requirement,
                "reason": msg.reason,
                "trajectory_id": msg.trajectory_id,
            }
        )

    def _on_connected(self, msg: Bool) -> None:
        with self._lock:
            self._s.edge_connected = bool(msg.data)

    # --- arayüz --------------------------------------------------------------------------------
    def info(self) -> dict:
        return robot_info(self.spec, HOME_MM, DEFAULT_WORKSPACE, DEFAULT_LIMITS)

    def state(self) -> RobotState:
        with self._lock:
            s = RobotState(**{**self._s.__dict__})
        if not s.edge_connected or time.monotonic() - self._last_status > STATUS_STALE_S:
            s.state = "DISCONNECTED"
        return s

    async def _call(self, client, request):
        """Servis çağrısı; servis yoksa ya da yanıt gelmezse None."""

        def run():
            if not client.wait_for_service(timeout_sec=SERVICE_TIMEOUT_S):
                return None
            done = threading.Event()
            fut = client.call_async(request)
            fut.add_done_callback(lambda _f: done.set())
            if not done.wait(SERVICE_TIMEOUT_S + 5.0):
                fut.cancel()
                return None
            return fut.result()

        return await asyncio.to_thread(run)

    async def move(self, x, y, z, duration_s, wait) -> MoveOutcome:
        req = MoveTo.Request()
        req.target = Point(x=float(x), y=float(y), z=float(z))
        req.duration_s = float(duration_s) if duration_s else 0.0
        q = self.add_listener()  # bekleme sırasında kenar reddini yakalamak için
        try:
            res = await self._call(self.cli_move, req)
            if res is None:
                return MoveOutcome(False, requirement="DURUM", reason="planlayıcı yanıt vermedi")
            if not res.accepted:
                return MoveOutcome(False, requirement=requirement_of(res.reason), reason=res.reason)
            tid = res.trajectory_id
            if not wait:
                return MoveOutcome(True, trajectory_id=tid, done=False)
            limit = (duration_s or AUTO_DURATION_GUESS_S) + 5.0
            return await self._wait_done(tid, limit, q)
        finally:
            self.remove_listener(q)

    async def _wait_done(self, tid: str, limit_s: float, q: asyncio.Queue) -> MoveOutcome:
        t_end = time.monotonic() + limit_s
        seen = False
        while time.monotonic() < t_end:
            while not q.empty():
                ev = q.get_nowait()
                if not ev.get("accepted", True) and ev.get("trajectory_id") in ("", tid):
                    return MoveOutcome(
                        True, trajectory_id=tid, done=False, reason=f"{ev['requirement']}: "
                        f"{ev['reason']}", position_mm=self.state().position_mm
                    )  # fmt: skip
            s = self.state()
            if s.trajectory_id == tid:
                seen = True
                if s.state == "IDLE":
                    return MoveOutcome(
                        True, trajectory_id=tid, done=True, position_mm=s.position_mm
                    )
            if seen and s.state in ("HOLDING", "TORQUE_OFF", "FAULT", "ESTOP", "DISCONNECTED"):
                return MoveOutcome(
                    True,
                    trajectory_id=tid,
                    done=False,
                    position_mm=s.position_mm,
                    reason=f"yörünge tamamlanmadı: {s.state}",
                )
            await asyncio.sleep(0.02)
        return MoveOutcome(True, trajectory_id=tid, done=False, reason="bekleme süresi aşıldı")

    async def _set_bool(self, client, on: bool) -> bool:
        res = await self._call(client, SetBool.Request(data=bool(on)))
        return bool(res and res.success)

    async def magnet(self, on: bool) -> bool:
        return await self._set_bool(self.cli_magnet, on)

    async def torque(self, on: bool) -> bool:
        return await self._set_bool(self.cli_torque, on)

    async def stop(self) -> bool:
        res = await self._call(self.cli_stop, Trigger.Request())
        return bool(res and res.success)

    def close(self) -> None:
        self.executor.shutdown()
        self.node.destroy_node()
        rclpy.try_shutdown()
