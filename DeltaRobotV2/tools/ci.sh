#!/usr/bin/env bash
# Yerelde ve CI'da aynı denetimler. DeltaRobotV2/ kökünden, geliştirme konteynerinde çalıştırılır:
#   docker compose run --rm dev ./tools/ci.sh
set -euo pipefail

cd "$(dirname "$0")/.."

echo "== Biçim =="
./tools/format.sh --check

echo "== i18n =="
python3 tools/check_i18n.py

echo "== Python testleri =="
python3 -m pytest -q -p no:cacheprovider tests

echo "== delta_core (C++) =="
cmake -S core -B build/core -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build/core
ctest --test-dir build/core --output-on-failure

echo "== Tamam =="
