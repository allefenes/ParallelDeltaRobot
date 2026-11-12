#!/usr/bin/env bash
# Uçtan uca test: sunucu (ROS2 + kenar köprüsü) + sanal Pi (delta_edge) Compose ile kalkar;
# arızalar dışarıdan enjekte edilir, güvenlik ROS üzerinden doğrulanır (tests/e2e/check.py).
#   ./tools/e2e.sh          (DeltaRobotV2/ içinden; sonunda konteynerler durdurulur)
# Senaryolar ve kanıtladıkları gereksinimler docs/guvenlik-gereksinimleri.md'de.
set -uo pipefail

cd "$(dirname "$0")/.."
export MSYS_NO_PATHCONV=1
DC="docker compose --profile sim"
pass=0
fail=0
results=()

check() { # check <ad> <senaryo> [ek argümanlar]
  local name="$1"
  shift
  local out
  out=$($DC exec -T server bash -lc "source /opt/delta/ros2_ws/install/setup.bash && python3 /e2e/check.py $*" 2>&1 | grep -E "GEÇTİ|BAŞARISIZ|Error|Traceback" | tail -3)
  if grep -q "GEÇTİ" <<<"$out"; then
    pass=$((pass + 1))
    results+=("✔ $name — ${out#GEÇTİ: }")
  else
    fail=$((fail + 1))
    results+=("✘ $name — $out")
  fi
  echo "[$name] $out"
}

netem() { $DC exec -T edge tc qdisc replace dev eth0 root netem "$@"; }
netem_off() { $DC exec -T edge tc qdisc del dev eth0 root 2>/dev/null || true; }

echo "== Sistem kalkıyor =="
$DC up -d --build edge >/dev/null 2>&1 || $DC up -d >/dev/null
$DC up -d >/dev/null
check "Bağlantı (TLS, Pi bağlanır)" connected --timeout 60
check "Yörünge yürütme" move
check "G1/G2: 1. kapı limit reddi" limit
check "G1/G8: son kapı (Pi) reddi, 1. kapı atlanmış" edge_gate
check "G6/G7: hareket ortasında kalp atışı kaybı" hb_loss

echo "== Ağ arızası: 80±40 ms gecikme, %10 kayıp =="
netem delay 80ms 40ms loss 10%
check "Bozuk ağda yörünge yürütme" net_move --timeout 40
netem_off

echo "== Ağ arızası: hareket ortasında bağlantı tamamen kesik (kara delik) =="
check "Uzun hareket başlat" start_long_move
netem loss 100%
sleep 2
netem_off
check "G6/G7: kara delik sonrası güvenli durum ve açık kurtarma" recover --timeout 40

echo "== Arıza: hareket ortasında sunucu konteyneri öldürülüyor =="
check "Uzun hareket başlat" start_long_move
since=$(date -u +%Y-%m-%dT%H:%M:%S)
$DC kill server >/dev/null 2>&1
sleep 3
$DC up -d server >/dev/null 2>&1
check "Sunucu yeniden başlatıldı: kenar yeniden bağlandı" after_server_restart --timeout 60
# Bağlantı koparken kenar kendi başına HOLD ve TORQUE_OFF'a geçmiş olmalı (kenar günlüğü)
log=$($DC logs --no-color --since "$since" edge 2>&1)
if grep -q -- "-> HOLDING" <<<"$log" && grep -q -- "HOLDING -> TORQUE_OFF" <<<"$log"; then
  pass=$((pass + 1))
  results+=("✔ G6/G7: sunucu ölünce kenar kendi başına HOLD → TORQUE_OFF (kenar günlüğü)")
else
  fail=$((fail + 1))
  results+=("✘ G6/G7: sunucu ölünce kenar günlüğünde HOLD/TORQUE_OFF yok")
fi

echo "== Arıza: hareket ortasında Pi çöküyor (SIGKILL, elektrik kesintisi eşdeğeri) =="
# Not: SIGKILL yakalanamaz; gerçek donanımda servolar son hedefte torklu kalır. Bunu yalnız
# fiziksel acil stop (G12) güvenceye alır. Burada doğrulanan: yeniden açılışın güvenli olması.
check "Uzun hareket başlat" start_long_move
$DC kill edge >/dev/null 2>&1
sleep 1
$DC up -d edge >/dev/null 2>&1
since_boot=$(date -u +%Y-%m-%dT%H:%M:%S)
check "Pi çökme sonrası güvenli açılış (TORQUE_OFF) ve bağlantı" final_state --timeout 60

echo "== Pi düzgün kapanıyor (SIGTERM) hareket ortasında =="
check "Uzun hareket başlat" start_long_move
$DC stop -t 5 edge >/dev/null 2>&1
if $DC logs --no-color --since "$since_boot" edge 2>&1 | grep -q "mıknatıs ve tork kapatılıyor"; then
  pass=$((pass + 1))
  results+=("✔ Pi düzgün kapanırken tork ve mıknatıs kapatıldı (kenar günlüğü)")
else
  fail=$((fail + 1))
  results+=("✘ Pi düzgün kapanışında tork/mıknatıs kapatma günlüğü yok")
fi
$DC up -d edge >/dev/null 2>&1
check "Pi yeniden bağlandı" final_state --timeout 60

echo
echo "== Sonuç: $pass geçti, $fail başarısız =="
printf '%s\n' "${results[@]}"
mkdir -p build
{
  echo "# Uçtan uca test sonucu ($(date -u +%Y-%m-%dT%H:%MZ))"
  echo
  echo "$pass geçti, $fail başarısız"
  echo
  printf -- '- %s\n' "${results[@]}"
} >build/e2e_report.md

if [[ "${KEEP_UP:-0}" != "1" ]]; then
  $DC stop >/dev/null 2>&1
fi
[[ $fail -eq 0 ]]
