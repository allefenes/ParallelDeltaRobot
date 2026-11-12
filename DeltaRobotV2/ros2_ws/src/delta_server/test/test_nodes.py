"""Düğüm testleri (süreç içi): süpervizör, planlayıcı, durum yayıncısı ve sanal yürütücü.

Düğümler gerçek rclpy düğümüdür; yayıncılar yakalanır, geri çağırmalar doğrudan çağrılır.
Uçtan uca (ayrı süreçler, DDS) davranış test_launch_integration.py'dedir.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from delta_interfaces.msg import EdgeStatus, SupervisorEvent
from delta_interfaces.srv import MoveTo, ValidateTrajectory
from delta_server.common import duration_msg, duration_s
from delta_server.planning import plan_line
from delta_server.robot import JOINT_NAMES, Robot, deg_to_rad, mm_to_m, robot_yaml_path
from delta_server.sim_executor_node import SimExecutor
from delta_server.state_publisher_node import DeltaStatePublisher
from delta_server.supervisor_node import Supervisor
from delta_server.trajectory_planner_node import TrajectoryPlanner, build_request
from geometry_msgs.msg import Point
from rclpy.parameter import Parameter
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

TARGET = (20.0, 10.0, -200.0)


class Capture:
    """Yayıncı yerine geçen kaydedici."""

    def __init__(self):
        self.msgs = []

    def publish(self, msg):
        self.msgs.append(msg)

    def sendTransform(self, msgs):  # noqa: N802 - tf2_ros arayüzü
        self.msgs.append(msgs)


def overrides(robot_yaml, **extra):
    return [Parameter("robot_yaml", value=robot_yaml)] + [
        Parameter(k, value=v) for k, v in extra.items()
    ]


def joint_state(theta_deg) -> JointState:
    js = JointState()
    js.name = list(JOINT_NAMES)
    js.position = deg_to_rad(theta_deg)
    return js


@pytest.fixture
def supervisor(ros_context, robot_yaml):
    n = Supervisor(parameter_overrides=overrides(robot_yaml))
    n.events, n.out = Capture(), Capture()
    yield n
    n.destroy_node()


@pytest.fixture
def planner(ros_context, robot_yaml, supervisor):
    def validator(req):
        r = supervisor.on_validate(req, ValidateTrajectory.Response())
        return r.accepted, r.reason

    n = TrajectoryPlanner(
        validator=validator, parameter_overrides=overrides(robot_yaml, validate_timeout_s=0.2)
    )
    yield n
    n.destroy_node()


def move(planner, target, duration=1.0):
    req = MoveTo.Request()
    req.target = Point(x=float(target[0]), y=float(target[1]), z=float(target[2]))
    req.duration_s = float(duration)
    return planner.on_move_to(req, MoveTo.Response())


def home_state(robot, *nodes):
    for n in nodes:
        n.on_joint_state(joint_state(robot.kin.inverse(robot.home_mm)))


# --- Süpervizör + planlayıcı ----------------------------------------------------------------


def test_move_to_valid_target_accepted_and_sent_to_edge(planner, supervisor, robot):
    home_state(robot, planner, supervisor)
    resp = move(planner, TARGET)
    assert resp.accepted, resp.reason
    assert resp.trajectory_id.startswith("traj-")
    ev = supervisor.events.msgs[-1]
    assert isinstance(ev, SupervisorEvent) and ev.accepted and ev.sample_index == -1
    assert math.isclose(ev.target_mm.z, TARGET[2])
    out = supervisor.out.msgs[-1]
    assert out.header.frame_id == resp.trajectory_id and list(out.joint_names) == list(JOINT_NAMES)
    last = np.degrees(out.points[-1].positions)
    assert np.allclose(last, robot.kin.inverse(TARGET), atol=1e-9)
    assert math.isclose(duration_s(out.points[1].time_from_start), 0.01)


def test_move_to_out_of_limit_rejected_with_event(planner, supervisor, robot):
    home_state(robot, planner, supervisor)
    resp = move(planner, (60.0, 0.0, -140.0))
    assert not resp.accepted and resp.reason[:2] in ("G1", "G2")
    ev = supervisor.events.msgs[-1]
    assert not ev.accepted and ev.requirement in ("G1", "G2") and ev.sample_index >= 0
    assert supervisor.out.msgs == []


def test_move_to_auto_duration(planner, supervisor, robot):
    home_state(robot, planner, supervisor)
    assert move(planner, TARGET, duration=0.0).accepted


def test_move_to_too_fast_rejected_G5(planner, supervisor, robot):
    home_state(robot, planner, supervisor)
    resp = move(planner, TARGET, duration=0.05)
    assert not resp.accepted and resp.reason.startswith("G5")


def test_move_to_nan_target_rejected_G4(planner, supervisor, robot):
    home_state(robot, planner, supervisor)
    resp = move(planner, (float("nan"), 0.0, -200.0))
    assert not resp.accepted and resp.reason.startswith("G4")
    assert supervisor.events.msgs[-1].target_mm.x == 0.0  # NaN olay mesajına yazılmaz


def test_move_to_invalid_requests(planner, robot):
    resp = move(planner, TARGET)
    assert not resp.accepted and "durumu bilinmiyor" in resp.reason
    home_state(robot, planner)
    assert "sayı değil" in move(planner, TARGET, duration=float("nan")).reason


def test_supervisor_busy_and_bad_joint_names(supervisor, robot):
    plan = plan_line(robot.kin, robot.home_mm, TARGET, 0.5, 100.0)
    req = build_request("t-1", plan, TARGET)
    supervisor.on_edge_status(EdgeStatus(state="RUNNING"))
    resp = supervisor.on_validate(req, ValidateTrajectory.Response())
    assert not resp.accepted and resp.requirement == "DURUM"
    supervisor.on_edge_status(EdgeStatus(state="IDLE"))
    req.trajectory.joint_names = ["a", "b", "c"]
    assert supervisor.on_validate(req, ValidateTrajectory.Response()).requirement == "G4"
    req.trajectory.joint_names = list(JOINT_NAMES)
    req.trajectory.points[3].positions = [0.0, 0.0]
    assert supervisor.on_validate(req, ValidateTrajectory.Response()).requirement == "G4"


def test_supervisor_ignores_foreign_joint_state(supervisor):
    js = JointState(name=["x"], position=[0.0])
    supervisor.on_joint_state(js)
    assert supervisor.current_deg is None


def test_planner_without_supervisor_times_out(ros_context, robot_yaml, robot):
    n = TrajectoryPlanner(parameter_overrides=overrides(robot_yaml, validate_timeout_s=0.1))
    try:
        home_state(robot, n)
        resp = move(n, TARGET)
        assert not resp.accepted and "süpervizör" in resp.reason
        n.on_joint_state(JointState(name=["x"], position=[0.0]))
        assert n.current_deg is not None
    finally:
        n.destroy_node()


# --- Durum yayıncısı ------------------------------------------------------------------------


@pytest.fixture
def state_pub(ros_context, robot_yaml):
    n = DeltaStatePublisher(parameter_overrides=overrides(robot_yaml, pieces="X.O......"))
    n.tf, n.marker_pub = Capture(), Capture()
    yield n
    n.destroy_node()


def test_state_publisher_tf_and_trail(state_pub, robot):
    state_pub.on_joint_state(joint_state(robot.kin.inverse(robot.home_mm)))
    tfs = state_pub.tf.msgs[-1]
    assert {t.child_frame_id for t in tfs} == {
        *(f"bicep_{i}" for i in (1, 2, 3)),
        *(f"forearm_{i}_{s}" for i in (1, 2, 3) for s in "ab"),
        "platform",
    }
    assert tfs[0].header.stamp.sec > 0  # sıfır damga şimdiki zamanla değişir
    state_pub.on_joint_state(joint_state(robot.kin.inverse(robot.home_mm)))
    assert len(state_pub.trail) == 1  # aynı nokta ize iki kez girmez
    state_pub.on_joint_state(joint_state(robot.kin.inverse(TARGET)))
    assert len(state_pub.trail) == 2
    n = len(state_pub.tf.msgs)
    state_pub.on_joint_state(JointState(name=["x"], position=[0.0]))
    assert len(state_pub.tf.msgs) == n  # motor_1..3 olmayan mesaj TF üretmez


def test_state_publisher_markers_and_events(state_pub, robot):
    state_pub.publish_markers()
    arr = state_pub.marker_pub.msgs[-1]
    ns = [m.ns for m in arr.markers]
    assert ns.count("pieces") == 2 and "board" in ns and "trail" in ns
    board = arr.markers[0]
    top = (board.pose.position.z + board.scale.z / 2) * 1000.0
    assert math.isclose(top, robot.board_top_mm, abs_tol=1e-6)
    ev = SupervisorEvent(accepted=False, requirement="G1", reason="G1: motor açı limiti")
    ev.target_mm = Point(x=60.0, y=0.0, z=-140.0)
    state_pub.on_event(ev)
    arr = state_pub.marker_pub.msgs[-1]
    text = [m for m in arr.markers if m.ns == "target" and m.type == m.TEXT_VIEW_FACING][0]
    assert "G1" in text.text and text.action == text.ADD
    state_pub.on_joint_state(joint_state(robot.kin.inverse(robot.home_mm)))
    state_pub.on_event(SupervisorEvent(accepted=True, target_mm=Point(x=0.0, y=0.0, z=-200.0)))
    arr = state_pub.marker_pub.msgs[-1]
    text = [m for m in arr.markers if m.ns == "target" and m.type == m.TEXT_VIEW_FACING][0]
    assert text.action == text.DELETE and len(state_pub.trail) == 1


def test_board_cell_centers(state_pub):
    b = state_pub.board
    assert b.cell_mm * b.cells == b.size_mm
    assert b.cell_center_mm(1, 1) == b.center_mm
    x0, y0 = b.cell_center_mm(0, 0)
    assert x0 < b.center_mm[0] and y0 > b.center_mm[1]


# --- Sanal yürütücü -------------------------------------------------------------------------


class FakeClock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


@pytest.fixture
def sim(ros_context, robot_yaml):
    clock = FakeClock()
    n = SimExecutor(clock=clock, parameter_overrides=overrides(robot_yaml))
    n.js_pub, n.status_pub = Capture(), Capture()
    n.fake_clock = clock
    yield n
    n.destroy_node()


def trajectory_msg(thetas_deg, tid="t-sim"):
    msg = JointTrajectory()
    msg.header.frame_id = tid
    msg.joint_names = list(JOINT_NAMES)
    for k, th in enumerate(thetas_deg):
        msg.points.append(
            JointTrajectoryPoint(positions=deg_to_rad(th), time_from_start=duration_msg(k / 100))
        )
    return msg


def test_sim_executor_plays_at_sample_rate(sim, robot):
    sim.tick()
    home = np.degrees(sim.js_pub.msgs[-1].position)
    assert np.allclose(home, robot.kin.inverse(robot.home_mm))
    plan = plan_line(robot.kin, robot.home_mm, TARGET, 0.5, 100.0)
    sim.on_trajectory(trajectory_msg(plan.thetas_deg))
    assert sim.state == "RUNNING" and sim.status_pub.msgs[-1].state == "RUNNING"
    sim.fake_clock.t += 0.255
    sim.tick()
    assert sim.index == 25
    assert np.allclose(np.degrees(sim.js_pub.msgs[-1].position), plan.thetas_deg[25])
    sim.publish_status()
    st = sim.status_pub.msgs[-1]
    assert st.index == 25 and st.trajectory_id == "t-sim" and st.voltages[0] > 0
    sim.fake_clock.t += 10.0
    sim.tick()
    assert sim.state == "IDLE"
    assert np.allclose(np.degrees(sim.js_pub.msgs[-1].position), robot.kin.inverse(TARGET))
    sim.publish_status()
    assert sim.status_pub.msgs[-1].index == -1


def test_sim_executor_refuses_corrupt_trajectory(sim, robot):
    home = robot.kin.inverse(robot.home_mm)
    sim.on_trajectory(trajectory_msg([home, [float("nan"), 0.0, 0.0]]))
    assert sim.state == "FAULT"
    msg = trajectory_msg([home, home])
    msg.joint_names = ["a", "b", "c"]
    sim.state = "IDLE"
    sim.on_trajectory(msg)
    assert sim.state == "FAULT"


# --- Yardımcılar ---------------------------------------------------------------------------


def test_helpers(robot_yaml, tmp_path, monkeypatch):
    assert duration_s(duration_msg(1.234567891)) == pytest.approx(1.234567891, abs=1e-9)
    assert mm_to_m([1000.0, -236.0]) == [1.0, -0.236]
    monkeypatch.setenv("DELTA_ROBOT_YAML", robot_yaml)
    assert robot_yaml_path("") == robot_yaml
    with pytest.raises(FileNotFoundError):
        robot_yaml_path(str(tmp_path / "yok.yaml"))
    r = Robot.load(robot_yaml)
    assert r.board_top_mm == -r.params.base_to_floor + r.spec["task"]["board_thickness"]
