#!/usr/bin/env bash
# CAD betiklerini yerel FreeCAD 1.1 ile çalıştırır (Windows Git Bash; FreeCAD konteynerde yok).
#   ./tools/cad.sh build    parçalar + montaj + kontroller + mesh/kütle çıktıları (başsız)
#   ./tools/cad.sh render   montaj görsellerini üretir (FreeCAD arayüzü kısa süre açılıp kapanır)
# FreeCAD yolu FREECAD_BIN ile değiştirilebilir.
set -euo pipefail

cd "$(dirname "$0")/.."
FREECAD_BIN="${FREECAD_BIN:-/c/Users/allef/AppData/Local/Programs/FreeCAD 1.1/bin}"
export DELTA_CAD_DIR
DELTA_CAD_DIR="$(cygpath -w "$PWD/cad" 2>/dev/null || echo "$PWD/cad")"

case "${1:-}" in
  build) "$FREECAD_BIN/freecadcmd.exe" "$DELTA_CAD_DIR/build.py" ;;
  render) "$FREECAD_BIN/freecad.exe" "$DELTA_CAD_DIR/render.py" ;;
  *)
    echo "Kullanım: $0 build|render"
    exit 2
    ;;
esac
