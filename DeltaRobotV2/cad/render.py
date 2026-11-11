"""cad/out/delta_v2.FCStd montajını malzemeye göre renklendirip görseller üretir.

FreeCAD arayüzü gerekir.

Çalıştırma: ./tools/cad.sh render  (önce ./tools/cad.sh build).
Arayüz açılır, görüntüler kaydedilir, kapanır.
Çıktı: docs/img/cad/*.png
"""

from __future__ import annotations

import os
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui

CAD_DIR = Path(os.environ.get("DELTA_CAD_DIR", Path(globals().get("__file__", ".")).parent))
IMG_DIR = CAD_DIR.parent / "docs" / "img" / "cad"
SIZE = (1600, 1200)

# Malzeme -> RGB (0..1). PLA rengi gerçek parçalar bilinmediği için turuncu seçildi.
COLORS = {
    "al7075": (0.78, 0.80, 0.83),
    "pom": (0.97, 0.97, 0.95),
    "pla_infill20": (0.96, 0.47, 0.12),
    "pla_solid": (0.90, 0.38, 0.08),
    "steel": (0.42, 0.44, 0.47),
    "bearing": (0.68, 0.70, 0.73),
    "motor": (0.13, 0.13, 0.15),
    "electromagnet": (0.72, 0.45, 0.20),
}


def colorize(doc) -> None:
    for obj in doc.Objects:
        if hasattr(obj, "Malzeme"):
            vo = obj.ViewObject
            vo.ShapeColor = COLORS.get(obj.Malzeme, (0.5, 0.5, 0.5))
            vo.DisplayMode = "Flat Lines"
            vo.LineColor = (0.25, 0.25, 0.25)
            vo.LineWidth = 1.0


def save(view, name: str) -> None:
    Gui.updateGui()
    view.saveImage(str(IMG_DIR / name), SIZE[0], SIZE[1], "White")


def focus(doc, view, names: list[str]) -> None:
    """Verilen nesnelere yakınlaştırır (seçim vurgusu kaydedilmeden önce temizlenir)."""
    Gui.Selection.clearSelection()
    for n in names:
        Gui.Selection.addSelection(doc.Name, n)
    Gui.SendMsgToActiveView("ViewSelection")
    Gui.Selection.clearSelection()


def main() -> None:
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    doc = App.openDocument(str(CAD_DIR / "out" / "delta_v2.FCStd"))
    Gui.activateWorkbench("PartWorkbench")
    Gui.setActiveDocument(doc.Name)
    colorize(doc)
    # Başsız kaydedilen belgede görünürlük bilgisi yoktur:
    # parçalar açık, bağ eksen yardımcıları kapalı.
    helpers = ("App::Origin", "App::Line", "App::Plane", "App::Point")
    for o in doc.Objects:
        o.ViewObject.Visibility = o.TypeId not in helpers
    Gui.updateGui()
    view = Gui.getDocument(doc.Name).ActiveView
    view.setAnimationEnabled(False)

    for name, setter in [
        ("iso.png", view.viewIsometric),
        ("on.png", view.viewFront),
        ("yan.png", view.viewRight),
        ("ust.png", view.viewTop),
    ]:
        setter()
        view.fitAll()
        save(view, name)

    # Hareketli mekanizma yakın plan (gövde ve taban gizli)
    hidden = [o for o in doc.Objects if o.Name.startswith("base_") and hasattr(o, "Malzeme")]
    for o in hidden:
        if o.Malzeme in ("al7075", "pom"):
            o.ViewObject.Visibility = False
    view.viewIsometric()
    focus(
        doc,
        view,
        [o.Name for o in doc.Objects if hasattr(o, "Malzeme") and not o.Name.startswith("base_")],
    )
    save(view, "mekanizma.png")

    # Eklem istifi yakın plan: 1. kolun dirseği (pim, burçlar, somunlar, rot başları)
    elbow = [
        o.Name for o in doc.Objects if o.Name.startswith("bicep_1_") and o.Malzeme != "pla_solid"
    ]
    elbow = [n for n in elbow if "bicep_plate" not in n]
    view.viewAxonometric() if hasattr(view, "viewAxonometric") else view.viewIsometric()
    focus(doc, view, elbow)
    view.zoomOut()
    save(view, "eklem.png")

    App.closeDocument(doc.Name)
    Gui.getMainWindow().close()


main()
