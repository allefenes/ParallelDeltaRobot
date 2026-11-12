#!/usr/bin/env bash
# Başsız RViz ekran görüntüleri (Xvfb + rviz2 + ImageMagick), yazılım OpenGL ile.
# Konteynerde, ROS ortamı ve Delta çalışma alanı yüklüyken çalışır (imajın giriş noktası yükler):
#   docker run --rm -v "$PWD":/workspace deltarobotv2-ros:latest ./ros2_ws/tools/capture_screens.sh
# Çıktı: ros2_ws/screenshots/*.png (8 bit RGB, 1600x1000)
#   01_home.png        başlangıç (montaj) pozu
#   02_rejected.png    limit dışı hedef: kırmızı hedef + ret nedeni
#   03_trajectory.png  hareketin ortası, uç izi (camgöbeği çizgi)
#   04_board.png       tic-tac-toe tablası ve taşlar, platform bir hücrenin üstünde
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$HERE/../screenshots}"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
W=1600
H=1000

export LIBGL_ALWAYS_SOFTWARE=1
export QT_QPA_PLATFORM=xcb
export DISPLAY=:97
export ROS_LOG_DIR="${ROS_LOG_DIR:-/tmp/delta_capture_log}"
# Diğer ROS süreçleriyle karışmasın diye ayrı bir alan kimliği
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-42}"

pids=()
cleanup() {
  for p in "${pids[@]}"; do kill -INT "$p" 2>/dev/null || true; done
  sleep 2
  for p in "${pids[@]}"; do kill -KILL "$p" 2>/dev/null || true; done
}
trap cleanup EXIT

Xvfb "$DISPLAY" -screen 0 "${W}x${H}x24" -nolisten tcp >/dev/null 2>&1 &
pids+=($!)
sleep 2

ros2 launch delta_server delta.launch.py rviz:=true ${ROBOT_YAML:+robot_yaml:=$ROBOT_YAML} \
  >"$OUT/../screenshots_launch.log" 2>&1 &
pids+=($!)

# /move_to hazır olana kadar bekle
for _ in $(seq 60); do
  if ros2 service list 2>/dev/null | grep -qx /move_to; then break; fi
  sleep 1
done
sleep 12 # RViz mesh'leri yüklesin ve ilk kareyi çizsin

move_to() { # x y z süre (mm, s)
  ros2 service call /move_to delta_interfaces/srv/MoveTo \
    "{target: {x: $1, y: $2, z: $3}, duration_s: $4}" | tail -n 2
}

shot() { # dosya adı
  import -window root "$OUT/raw.png"
  convert "$OUT/raw.png" -alpha off -depth 8 -type TrueColor "PNG24:$OUT/$1"
  rm -f "$OUT/raw.png"
  echo "kaydedildi: $OUT/$1"
}

shot 01_home.png

move_to 60.0 0.0 -140.0 1.0 # limit dışı: G1/G2 ile ret beklenir
sleep 3
shot 02_rejected.png

move_to -25.0 20.0 -170.0 1.5
sleep 2.5
move_to 25.0 -25.0 -222.0 4.0
sleep 2.0 # yaklaşık yarı yol
shot 03_trajectory.png
sleep 3

move_to 20.0 0.0 -205.0 2.0 # boş hücre (satır 1, sütun 2) üstü
sleep 4
shot 04_board.png

rm -f "$OUT/../screenshots_launch.log"
