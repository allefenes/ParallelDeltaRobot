"""Delta Robotics V2 sunucu yığını.

Başlatılanlar: robot_state_publisher (URDF), delta_state_publisher (TF + marker),
trajectory_planner (/move_to), supervisor (1. kapı), sim_executor (GEÇİCİ sanal Pi; sim:=false
ile kapatılır, gerçek edge_bridge geldiğinde onun yerine geçer) ve isteğe bağlı rviz2.

Kullanım:
  ros2 launch delta_server delta.launch.py                 # başsız
  ros2 launch delta_server delta.launch.py rviz:=true      # RViz ile
Argümanlar: rviz, sim, robot_yaml (boşsa DELTA_ROBOT_YAML), server_config, rviz_config.
"""

from __future__ import annotations

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:
    desc = Path(get_package_share_directory("delta_description"))
    server = Path(get_package_share_directory("delta_server"))
    args = [
        DeclareLaunchArgument("rviz", default_value="false", description="rviz2 başlatılsın mı"),
        DeclareLaunchArgument(
            "sim", default_value="true", description="GEÇİCİ sim_executor (sanal Pi) başlatılsın mı"
        ),
        DeclareLaunchArgument(
            "robot_yaml", default_value="", description="robot.yaml yolu (boş: DELTA_ROBOT_YAML)"
        ),
        DeclareLaunchArgument(
            "server_config", default_value=str(server / "config" / "server.yaml")
        ),
        DeclareLaunchArgument("rviz_config", default_value=str(desc / "rviz" / "delta.rviz")),
    ]
    cfg = LaunchConfiguration("server_config")
    common = [cfg, {"robot_yaml": LaunchConfiguration("robot_yaml")}]
    robot_description = ParameterValue(
        Command(["xacro ", str(desc / "urdf" / "delta.urdf.xacro")]), value_type=str
    )
    nodes = [
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            parameters=[{"robot_description": robot_description}],
            output="screen",
        ),
        Node(
            package="delta_server",
            executable="delta_state_publisher",
            parameters=common,
            output="screen",
        ),
        Node(package="delta_server", executable="supervisor", parameters=common, output="screen"),
        Node(
            package="delta_server",
            executable="trajectory_planner",
            parameters=common,
            output="screen",
        ),
        Node(
            package="delta_server",
            executable="sim_executor",
            parameters=common,
            output="screen",
            condition=IfCondition(LaunchConfiguration("sim")),
        ),
        Node(
            package="rviz2",
            executable="rviz2",
            arguments=["-d", LaunchConfiguration("rviz_config")],
            output="log",
            condition=IfCondition(LaunchConfiguration("rviz")),
        ),
    ]
    return LaunchDescription(args + nodes)
