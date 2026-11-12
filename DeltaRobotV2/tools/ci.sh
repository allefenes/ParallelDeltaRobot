#!/usr/bin/env bash
# Yerelde ve CI'da aynı denetimler. DeltaRobotV2/ kökünden, geliştirme konteynerinde çalıştırılır:
#   docker compose run --rm dev ./tools/ci.sh
# Kapsama raporları build/coverage/ altına yazılır (CI artefaktı). Kapsama bilgi amaçlıdır;
# tek zorunlu taban genel satır kapsaması %80'dir (kullanıcı kararı, risk tabanlı test planı).
set -euo pipefail

cd "$(dirname "$0")/.."
COV=build/coverage
mkdir -p "$COV"

echo "== Biçim =="
./tools/format.sh --check

echo "== Malzeme listesi (CAD ile senkron) =="
python3 tools/bom.py --check

echo "== i18n =="
python3 tools/check_i18n.py

echo "== delta_core (C++) + kapsama =="
cmake -S core -B build/core -G Ninja -DCMAKE_BUILD_TYPE=Debug -DDELTA_CORE_COVERAGE=ON >/dev/null
cmake --build build/core
find build/core -name '*.gcda' -delete
ctest --test-dir build/core --output-on-failure
export DELTA_CORE_BUILD=build/core

echo "== delta_core Python bağlaması: özellik tabanlı testler + V1 çapraz doğrulama =="
python3 -m pytest -q -p no:cacheprovider core/tests/python
gcovr -r core build/core --filter core/src --filter core/include \
  --txt-metric branch --print-summary \
  --xml "$COV/core.xml" --html-details "$COV/core.html" \
  --fail-under-line 80 | tail -4

echo "== delta_edge (C++, Pi kenarı) + kapsama =="
cmake -S edge -B build/edge -G Ninja -DCMAKE_BUILD_TYPE=Debug -DDELTA_EDGE_COVERAGE=ON >/dev/null
cmake --build build/edge
find build/edge -name '*.gcda' -delete
ctest --test-dir build/edge --output-on-failure
gcovr -r edge build/edge --filter edge/src --filter edge/include \
  --txt-metric branch --print-summary \
  --xml "$COV/edge.xml" --html-details "$COV/edge.html" \
  --fail-under-line 80 | tail -4

echo "== Python araç ve datasheet testleri + kapsama =="
python3 -m pytest -q -p no:cacheprovider tests \
  --cov=tools --cov-report=term --cov-report=xml:"$COV/python-tools.xml" \
  --cov-config=pyproject.toml --cov-fail-under=80

echo "== Tamam =="
