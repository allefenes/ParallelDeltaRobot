#!/usr/bin/env bash
# ROS2 paket testleri (pytest + launch_testing). deltarobotv2-ros:base imajında, DeltaRobotV2/ kökünden:
#   docker run --rm --user root -v "$PWD":/workspace -w /workspace deltarobotv2-ros:base ./tools/ros_test.sh
# Açıklama paketi depodaki göreli yolları beklediği için çalışma alanı geçici ağaçta derlenir.
set -eo pipefail

source /opt/ros/jazzy/setup.bash
T=$(mktemp -d)
mkdir -p "$T/cad" "$T/ros2_ws"
cp -r cad/out "$T/cad/"
cp -r config "$T/"
cp -r ros2_ws/src "$T/ros2_ws/"
cd "$T/ros2_ws"
colcon build --event-handlers console_direct- >/dev/null
source install/setup.bash

echo "== ROS2 birim testleri (pytest) =="
python3 -m pytest -q -p no:cacheprovider src/delta_server/test src/delta_description/test \
  --deselect src/delta_server/test/test_launch_integration.py::test_launch_integration

echo "== ROS2 yığın testi (launch_testing) =="
launch_test src/delta_server/test/test_launch_integration.py
echo "== Tamam =="
