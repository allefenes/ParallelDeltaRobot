#!/usr/bin/env bash
# ROS grafiğini üretir: yığını başsız başlatır, ros_graph.py ile tarar, yığını durdurur.
# Konteynerde, ROS ortamı ve Delta çalışma alanı yüklüyken çalışır:
#   ./ros2_ws/tools/ros_graph.sh [çıktı_klasörü] [ek launch argümanları...]
#   ör. ./ros2_ws/tools/ros_graph.sh ros2_ws/graph sim:=false
# Varsayılan launch argümanları: rviz:=false sim:=true (sonradan verilenler bunları ezer).
# Çıktı: ros_graph.dot, ros_graph.svg, ros_graph.json (bkz. ros_graph.py).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$HERE/../graph}"
shift || true
mkdir -p "$OUT"

# Diğer ROS süreçleriyle (ekran görüntüsü, testler, başka konteynerler) karışmasın.
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-43}"
export ROS_AUTOMATIC_DISCOVERY_RANGE="${ROS_AUTOMATIC_DISCOVERY_RANGE:-LOCALHOST}"
export ROS_LOG_DIR="${ROS_LOG_DIR:-/tmp/delta_graph_log}"
LOG="$(mktemp /tmp/delta_graph_launch.XXXX.log)"

# Yığın kendi süreç grubunda başlar: etkileşimsiz kabukta arka plan işi SIGINT'i yok sayar,
# bu yüzden durdurma tüm gruba SIGTERM (sonra SIGKILL) ile yapılır; düğümler yetim kalmaz.
setsid ros2 launch delta_server delta.launch.py rviz:=false sim:=true "$@" >"$LOG" 2>&1 &
launch_pid=$!
cleanup() {
  kill -TERM -- "-$launch_pid" 2>/dev/null || true
  for _ in $(seq 20); do
    pgrep -g "$launch_pid" >/dev/null || break
    sleep 0.5
  done
  kill -KILL -- "-$launch_pid" 2>/dev/null || true
}
trap cleanup EXIT

if ! python3 "$HERE/ros_graph.py" --out "$OUT" ${ROS_GRAPH_ARGS:-}; then
  echo "--- launch günlüğü ($LOG) ---"
  tail -n 40 "$LOG"
  exit 1
fi
