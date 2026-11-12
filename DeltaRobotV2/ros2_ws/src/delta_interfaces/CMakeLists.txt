cmake_minimum_required(VERSION 3.22)
project(delta_interfaces)

# Delta Robotics V2 arayüzleri. Konum birimi mm, açı birimi radyan (ROS kuralı).

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(trajectory_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/SupervisorEvent.msg"
  "msg/EdgeStatus.msg"
  "srv/MoveTo.srv"
  "srv/ValidateTrajectory.srv"
  DEPENDENCIES builtin_interfaces geometry_msgs trajectory_msgs)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
