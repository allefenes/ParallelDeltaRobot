#!/usr/bin/env bash
# F4 uçtan uca test: sim yığını (server + sanal Pi + api + runner) ayağa kalkar, gerçek Python
# istemcisi API üzerinden senaryoları koşar (tests/e2e/f4_check.py). Rapor: build/e2e_f4_report.md
#   ./tools/e2e_f4.sh            KEEP_UP=1 ./tools/e2e_f4.sh   (yığın açık kalır)
set -euo pipefail
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")/.."

DC="docker compose --profile sim"
src="$PWD"
command -v cygpath >/dev/null 2>&1 && src="$(cygpath -w "$PWD")"
TOKEN="${DELTA_API_TOKENS:-gelistirici:delta-dev-token-0123456789}"
TOKEN="${TOKEN#*:}"
TOKEN="${TOKEN%%,*}"

cleanup() {
  [[ "${KEEP_UP:-0}" == "1" ]] || $DC down >/dev/null 2>&1 || true
  ids="$(docker ps -aq --filter label=deltarobotv2.sandbox=job)"
  # shellcheck disable=SC2086
  [[ -z "$ids" ]] || timeout 60 docker rm -f $ids >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "== İmajlar =="
docker build -q -f docker/sandbox/Dockerfile -t deltarobotv2-sandbox:latest . >/dev/null
$DC build api runner edge >/dev/null
echo "== Yığın =="
$DC up -d >/dev/null
server="$($DC ps -q server)"

echo "== Senaryolar =="
mkdir -p build
set +e
docker run --rm --network "container:${server}" \
  -v "${src}:/w:ro" -v deltarobotv2_certs:/certs:ro \
  -e DELTA_TOKEN="$TOKEN" -e DELTA_CA_FILE=/certs/ca.crt -e PYTHONDONTWRITEBYTECODE=1 \
  --entrypoint python deltarobotv2-sandbox:latest /w/tests/e2e/f4_check.py | tee build/e2e_f4.log
rc=${PIPESTATUS[0]}
set -e
{
  echo "# F4 uçtan uca test sonucu ($(date -u +%Y-%m-%dT%H:%MZ))"
  echo
  grep -E "^== Sonuç" build/e2e_f4.log | sed 's/== //; s/ ==//'
  echo
  grep -E "^\[.*\] (GEÇTİ|KALDI)" build/e2e_f4.log | sed -E 's/^\[(.*)\] GEÇTİ: /- ✔ \1 — /; s/^\[(.*)\] KALDI: /- ✘ \1 — /'
} >build/e2e_f4_report.md
exit "$rc"
