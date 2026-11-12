#!/usr/bin/env bash
# F6 deneyim arayüzü uçtan uca testleri (Playwright, konteynerde). DeltaRobotV2/ kökünden ya da
# herhangi bir yerden:
#   ./tests/ui/run.sh                       sahte API'ye karşı (web/dev/mock_server.py)
#   ./tests/ui/run.sh slider_moves_twin     yalnız adı verilen senaryolar
#   UI_BASE_URL=https://host.docker.internal:8000 ./tests/ui/run.sh      gerçek API'ye karşı
#   UI_DOCKER_NETWORK=container:<api-konteyneri> UI_BASE_URL=https://localhost:8000 ./tests/ui/run.sh
# Ekran görüntüleri: web/screenshots/{otomatik,manuel}.png (1280x800).
set -euo pipefail
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")/../.."

IMAGE="deltarobotv2-uitest:latest"
MOCK="deltarobotv2-uimock"
NET="deltarobotv2-uitest"
src="$PWD"
command -v cygpath >/dev/null 2>&1 && src="$(cygpath -w "$PWD")"

started_mock=0
cleanup() {
  if [[ $started_mock == 1 ]]; then
    timeout 60 docker rm -f "$MOCK" >/dev/null 2>&1 || true
    timeout 60 docker network rm "$NET" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "== İmaj =="
timeout 900 docker build -q -t "$IMAGE" tests/ui >/dev/null

net_args=()
if [[ -z "${UI_BASE_URL:-}" ]]; then
  echo "== Sahte API =="
  docker network inspect "$NET" >/dev/null 2>&1 || docker network create "$NET" >/dev/null
  docker rm -f "$MOCK" >/dev/null 2>&1 || true
  started_mock=1
  # Hız çarpanı otomatik oyunu kısaltır; testler her bağlamda yeni oturum açar.
  docker run -d --rm --name "$MOCK" --network "$NET" -v "${src}:/workspace:ro" -w /workspace \
    -e PYTHONDONTWRITEBYTECODE=1 deltarobotv2-dev:latest \
    python3 web/dev/mock_server.py --host 0.0.0.0 --port 8765 --speed 2 \
    --sessions-per-ip 1000 --max-sessions 200 >/dev/null
  base="http://${MOCK}:8765"
  net_args=(--network "$NET")
else
  base="$UI_BASE_URL"
  if [[ -n "${UI_DOCKER_NETWORK:-}" ]]; then
    net_args=(--network "$UI_DOCKER_NETWORK")
  else
    net_args=(--add-host host.docker.internal:host-gateway)
  fi
fi

echo "== Senaryolar ($base) =="
set +e
docker run --rm --name deltarobotv2-uitest-run --ipc=host "${net_args[@]}" \
  -v "${src}:/workspace" -w /workspace \
  -e UI_BASE_URL="$base" -e PYTHONDONTWRITEBYTECODE=1 \
  -e UI_AUTO_TIMEOUT_S="${UI_AUTO_TIMEOUT_S:-240}" \
  "$IMAGE" timeout 1200 python3 tests/ui/ui_check.py "$@"
rc=$?
set -e
exit $rc
