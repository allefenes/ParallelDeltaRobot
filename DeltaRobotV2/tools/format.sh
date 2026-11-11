#!/usr/bin/env bash
# Tüm kaynakları tek standartta biçimlendirir; geliştirme konteynerinde DeltaRobotV2/ kökünden çalışır.
#   ./tools/format.sh          dosyaları yerinde düzeltir
#   ./tools/format.sh --check  yalnız denetler; biçimsiz dosya varsa 1 ile çıkar (CI ve pre-commit)
# Araçlar: Prettier (JSON/YAML/Markdown), clang-format (C++), ruff (Python). Ayarlar kökteki
# .prettierrc.yaml, .clang-format ve pyproject.toml dosyalarındadır.
set -euo pipefail

cd "$(dirname "$0")/.."

mode="fix"
if [[ "${1:-}" == "--check" ]]; then
  mode="check"
fi

# Derleme çıktıları hariç C++ kaynakları. CMake şablonları (*.in) yer tutucular bozulmasın diye dışarıda.
mapfile -t cpp_files < <(find . -path ./build -prune -o -type f \
  \( -name '*.cpp' -o -name '*.hpp' -o -name '*.h' \) -print | sort)

status=0
if [[ "$mode" == "check" ]]; then
  prettier --check --log-level warn . || status=1
  ruff format --check . || status=1
  ruff check . || status=1
  for f in "${cpp_files[@]}"; do
    clang-format --dry-run --Werror "$f" || status=1
  done
  if [[ $status -ne 0 ]]; then
    echo "Biçim hatası var. Düzeltmek için: docker compose run --rm dev ./tools/format.sh"
  fi
else
  prettier --write --log-level warn .
  ruff format .
  ruff check --fix .
  for f in "${cpp_files[@]}"; do
    clang-format -i "$f"
  done
fi

exit $status
