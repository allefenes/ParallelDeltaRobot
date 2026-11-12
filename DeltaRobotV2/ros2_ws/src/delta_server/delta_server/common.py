"""Düğümlerin ortak parametreleri, QoS profilleri ve mesaj yardımcıları."""

from __future__ import annotations

from builtin_interfaces.msg import Duration
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

from delta_server.robot import Robot
from delta_server.safety import Limits

# Konu adları
TOPIC_JOINT_STATES = "/joint_states"
TOPIC_TRAJECTORY_OUT = "/edge/trajectory_out"
TOPIC_EDGE_STATUS = "/edge/status"
TOPIC_EVENTS = "/supervisor/events"
TOPIC_MARKERS = "/delta/markers"
SRV_MOVE_TO = "/move_to"
SRV_VALIDATE = "/supervisor/validate"

# QoS: komut ve olaylar kaybolmamalı (reliable); durum akışı en yeni değerle yetinir.
QOS_COMMAND = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST, depth=10
)
QOS_EVENTS = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST, depth=50
)
QOS_STATE = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST, depth=10
)
QOS_LATCHED = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
)


def declare_common(node: Node) -> tuple[Robot, Limits]:
    """Ortak parametreleri (robot.yaml yolu, G5 sınırları, örnekleme) bildirir ve okur."""
    node.declare_parameter("robot_yaml", "")
    node.declare_parameter("max_joint_velocity_deg_s", 300.0)
    node.declare_parameter("max_joint_acceleration_deg_s2", 3000.0)
    node.declare_parameter("sample_rate_hz", 100.0)
    robot = Robot.load(node.get_parameter("robot_yaml").value)
    limits = Limits(
        max_vel_deg_s=float(node.get_parameter("max_joint_velocity_deg_s").value),
        max_acc_deg_s2=float(node.get_parameter("max_joint_acceleration_deg_s2").value),
        rate_hz=float(node.get_parameter("sample_rate_hz").value),
        min_tool_z_mm=min_tool_z_mm(robot.spec),
        tool_offset_mm=float(robot.spec["kinematics"]["ee_offset"]),
    )
    return robot, limits


def min_tool_z_mm(spec: dict) -> float:
    """G14: mıknatıs ucunun en alçak z'si = tabla üst yüzü (zemin + tabla), robot.yaml'dan.

    Tabla yalnız ortada olsa da sınır her yerde uygulanır (ihtiyatlı taraf).
    """
    k, task = spec["kinematics"], spec.get("task", {})
    return -float(k["base_to_floor"]) + float(task.get("board_thickness", 0.0))


def duration_msg(t_s: float) -> Duration:
    """Saniye -> builtin_interfaces/Duration (nanosaniye yuvarlamalı)."""
    ns = int(round(t_s * 1e9))
    return Duration(sec=ns // 1_000_000_000, nanosec=ns % 1_000_000_000)


def duration_s(d: Duration) -> float:
    """builtin_interfaces/Duration -> saniye."""
    return d.sec + d.nanosec * 1e-9
