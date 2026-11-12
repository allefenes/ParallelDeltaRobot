"""trajectory_planner: /move_to isteğini zaman damgalı eklem yörüngesine çevirir.

Arayüzler:
  servis  /move_to              (delta_interfaces/MoveTo)              hedef P (mm), süre (s)
  istemci /supervisor/validate  (delta_interfaces/ValidateTrajectory)  1. kapıya gönderim
  abone   /joint_states         (sensor_msgs/JointState)               başlangıç açıları (rad)

Yol: anlık P'den (ileri kinematik) hedefe düz çizgi, quintic zaman profili, 100 Hz örnek,
her örnekte delta_core ters kinematiği. Planlayıcı güvenlik kararı vermez; her yörünge
(erişilemeyen örnekler NaN olarak) süpervizöre gider ve kararı o verir.
"""

from __future__ import annotations

import math
import threading
import uuid

import rclpy
from delta_interfaces.srv import MoveTo, ValidateTrajectory
from geometry_msgs.msg import Point
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

from delta_server import common
from delta_server.planning import Plan, auto_duration, plan_line
from delta_server.robot import JOINT_NAMES, deg_to_rad, rad_to_deg


def build_request(trajectory_id: str, plan: Plan, target_mm) -> ValidateTrajectory.Request:
    """Plan -> ValidateTrajectory isteği (açılar radyan, kartezyen mm)."""
    req = ValidateTrajectory.Request()
    req.trajectory_id = trajectory_id
    traj = JointTrajectory()
    traj.joint_names = list(JOINT_NAMES)
    for t, th in zip(plan.times, plan.thetas_deg, strict=True):
        pt = JointTrajectoryPoint()
        pt.positions = deg_to_rad(float(v) for v in th)  # NaN korunur: süpervizör reddeder
        pt.time_from_start = common.duration_msg(float(t))
        traj.points.append(pt)
    req.trajectory = traj
    req.cartesian_mm = [Point(x=float(p[0]), y=float(p[1]), z=float(p[2])) for p in plan.points_mm]
    req.target_mm = Point(x=float(target_mm[0]), y=float(target_mm[1]), z=float(target_mm[2]))
    return req


class TrajectoryPlanner(Node):
    """MoveTo servisini sunar; planı süpervizöre doğrulatır."""

    def __init__(self, validator=None, **kwargs):
        super().__init__("trajectory_planner", **kwargs)
        self.robot, self.limits = common.declare_common(self)
        self.declare_parameter("auto_duration_margin", 1.25)
        self.declare_parameter("validate_timeout_s", 5.0)
        self.margin = float(self.get_parameter("auto_duration_margin").value)
        self.timeout_s = float(self.get_parameter("validate_timeout_s").value)
        self.current_deg: list[float] | None = None
        self.counter = 0
        self._lock = threading.Lock()
        state_group = MutuallyExclusiveCallbackGroup()
        self.client_group = ReentrantCallbackGroup()
        self.create_subscription(
            JointState,
            common.TOPIC_JOINT_STATES,
            self.on_joint_state,
            common.QOS_STATE,
            callback_group=state_group,
        )
        self.client = self.create_client(
            ValidateTrajectory, common.SRV_VALIDATE, callback_group=self.client_group
        )
        # validator: test için enjekte edilebilir; varsayılan süpervizör servisini çağırır.
        self.validator = validator or self.call_supervisor
        self.create_service(
            MoveTo, common.SRV_MOVE_TO, self.on_move_to, callback_group=ReentrantCallbackGroup()
        )

    def on_joint_state(self, msg: JointState) -> None:
        """Anlık motor açıları (rad -> derece)."""
        try:
            rad = [msg.position[list(msg.name).index(n)] for n in JOINT_NAMES]
        except (ValueError, IndexError):
            return
        self.current_deg = rad_to_deg(rad)

    def start_point_mm(self) -> tuple[float, float, float] | None:
        """Başlangıç P (mm): anlık açılardan ileri kinematik; durum yoksa None."""
        if self.current_deg is None:
            return None
        return self.robot.kin.forward(tuple(self.current_deg))

    def next_id(self) -> str:
        """Yörünge kimliği: sıra + rastgele ek (kayıtlarda eşleştirme için)."""
        with self._lock:
            self.counter += 1
            return f"traj-{self.counter:04d}-{uuid.uuid4().hex[:6]}"

    def call_supervisor(self, req: ValidateTrajectory.Request) -> tuple[bool, str]:
        """Süpervizör servisini çağırır ve yanıtı bekler (çok iş parçacıklı yürütücü gerekir)."""
        if not self.client.wait_for_service(timeout_sec=self.timeout_s):
            return False, "süpervizör erişilemez (servis yok)"
        done = threading.Event()
        future = self.client.call_async(req)
        future.add_done_callback(lambda _f: done.set())
        if not done.wait(self.timeout_s):
            future.cancel()
            return False, "süpervizör yanıt vermedi (zaman aşımı)"
        res = future.result()
        return bool(res.accepted), str(res.reason)

    def plan(self, target_mm, duration_s: float) -> tuple[Plan | None, str]:
        """Plan üretir; istek biçimce geçersizse (None, neden)."""
        start = self.start_point_mm()
        if start is None:
            return None, "robot durumu bilinmiyor (/joint_states yok ya da FK çözümsüz)"
        if not math.isfinite(duration_s):
            return None, "süre sayı değil"
        if duration_s <= 0:
            duration_s = auto_duration(
                self.robot.kin,
                start,
                target_mm,
                self.limits.rate_hz,
                self.limits.max_vel_deg_s,
                self.limits.max_acc_deg_s2,
                self.margin,
            )
        try:
            return plan_line(self.robot.kin, start, target_mm, duration_s, self.limits.rate_hz), ""
        except ValueError as e:
            return None, str(e)

    def on_move_to(self, req: MoveTo.Request, resp: MoveTo.Response) -> MoveTo.Response:
        """MoveTo: planla, 1. kapıya gönder, kararı döndür."""
        target = (req.target.x, req.target.y, req.target.z)
        resp.trajectory_id = self.next_id()
        plan, why = self.plan(target, req.duration_s)
        if plan is None:
            resp.accepted, resp.reason = False, f"istek geçersiz: {why}"
            self.get_logger().warning(f"{resp.trajectory_id}: {resp.reason}")
            return resp
        resp.accepted, resp.reason = self.validator(build_request(resp.trajectory_id, plan, target))
        self.get_logger().info(
            f"{resp.trajectory_id}: hedef {tuple(round(v, 1) for v in target)} mm, "
            f"{plan.duration_s:.2f} s, {len(plan.times)} örnek -> "
            f"{'kabul' if resp.accepted else 'RET ' + resp.reason}"
        )
        return resp


def main(args=None) -> None:
    rclpy.init(args=args)
    node = TrajectoryPlanner()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
