#!/usr/bin/env bash
# Sandbox testleri: imajları derler, birim + G11 testlerini Docker soketi bağlı test konteynerinde koşturur.
#   ./sandbox/run_tests.sh               hepsi
#   ./sandbox/run_tests.sh -k G11_dns    pytest argümanları aynen geçer
#   ./sandbox/run_tests.sh tests/unit    yalnız birim testleri (Docker'a dokunmaz)
# Windows + Docker Desktop (Git Bash) ve Linux'ta çalışır. İş konteynerleri test konteynerinin
# kardeşi olarak ana Docker'da başlar; her test sonunda geride kalmadığı denetlenir.
set -euo pipefail
export MSYS_NO_PATHCONV=1

cd "$(dirname "$0")/.."   # DeltaRobotV2/

if [[ ! -f client/pyproject.toml ]]; then
  echo "client/pyproject.toml yok: sandbox imajı istemci olmadan derlenemez." >&2
  exit 1
fi

src="$PWD"
if command -v cygpath >/dev/null 2>&1; then
  src="$(cygpath -w "$PWD")"
fi

docker build -q -f docker/sandbox/Dockerfile -t deltarobotv2-sandbox:latest . >/dev/null
docker build -q -f docker/runner/Dockerfile -t deltarobotv2-runner:latest . >/dev/null
docker build -q -f docker/runner/Dockerfile --target test -t deltarobotv2-runner:test . >/dev/null

name="deltarobotv2-sandbox-tests-$$"
cleanup() {
  docker rm -f "$name" >/dev/null 2>&1 || true
  # Kesilen bir test çalışmasından iş konteyneri kalmışsa silinir (yalnız bu etiket).
  ids="$(docker ps -aq --filter label=deltarobotv2.sandbox=job)"
  if [[ -n "$ids" ]]; then
    # shellcheck disable=SC2086
    timeout 60 docker rm -f $ids >/dev/null 2>&1 || true  # takılı konteyner betiği kilitlemesin
  fi
}
trap cleanup EXIT

if [[ $# -eq 0 ]]; then
  set -- tests
fi

docker run --rm --name "$name" \
  -v //var/run/docker.sock:/var/run/docker.sock \
  -v "${src}:/workspace:ro" \
  -w /workspace/sandbox \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e DELTA_REQUIRE_DOCKER=1 \
  deltarobotv2-runner:test \
  python -m pytest -p no:cacheprovider -q "$@"
