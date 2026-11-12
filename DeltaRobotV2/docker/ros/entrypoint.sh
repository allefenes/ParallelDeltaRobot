#!/usr/bin/env bash
# ROS ortamını ve imajdaki Delta çalışma alanını yükleyip komutu çalıştırır.
set -e
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
if [[ -f /opt/delta/ros2_ws/install/setup.bash ]]; then
  # shellcheck disable=SC1091
  source /opt/delta/ros2_ws/install/setup.bash
fi
exec "$@"
