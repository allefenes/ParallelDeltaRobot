"""Montajı ve parçaları malzemeye göre renklendirip görseller üretir. FreeCAD arayüzü gerekir.

Çalıştırma: ./tools/cad.sh render  (önce ./tools/cad.sh build).
Arayüz açılır, görüntüler kaydedilir, kapanır. Tek FreeCAD süreci kullanılır.
Çıktılar (8 bit RGB PNG, saydamlık yok; telefonda da açılır):
    docs/img/cad/*.png            montaj görünümleri ve kontrol pozu
    docs/img/cad/parcalar/*.png   parça önizlemeleri (ilgili küçük parçalar aynı görselde)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui
from PIL import Image

CAD_DIR = Path(os.environ.get("DELTA_CAD_DIR", Path(globals().get("__file__", ".")).parent))
sys.path.insert(0, str(CAD_DIR / "lib"))

import params  # noqa: E402
import parts as P  # noqa: E402

IMG_DIR = CAD_DIR.parent / "docs" / "img" / "cad"
PART_DIR = IMG_DIR / "parcalar"
SIZE = (1600, 1200)
PART_SIZE = (1000, 750)

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
HELPERS = ("App::Origin", "App::Line", "App::Plane", "App::Point")


def style(obj, material: str) -> None:
    vo = obj.ViewObject
    vo.ShapeColor = COLORS.get(material, (0.5, 0.5, 0.5))
    vo.DisplayMode = "Flat Lines"
    vo.LineColor = (0.25, 0.25, 0.25)
    vo.LineWidth = 1.0


def save(view, path: Path, size: tuple[int, int]) -> None:
    """Görüntüyü kaydeder ve 8 bit RGB'ye çevirir (saydamlık kanalı bazı istemcilerde sorunlu)."""
    Gui.updateGui()
    view.saveImage(str(path), size[0], size[1], "White")
    Image.open(path).convert("RGB").save(path, optimize=True)


def focus(doc, names: list[str]) -> None:
    """Verilen nesnelere yakınlaştırır (seçim vurgusu kaydedilmeden önce temizlenir)."""
    Gui.Selection.clearSelection()
    for n in names:
        Gui.Selection.addSelection(doc.Name, n)
    Gui.SendMsgToActiveView("ViewSelection")
    Gui.Selection.clearSelection()


def open_assembly(name: str):
    """Montaj belgesini açar ve renklendirir; başsız kayıtta olmayan görünürlüğü ayarlar."""
    doc = App.openDocument(str(CAD_DIR / "out" / name))
    Gui.setActiveDocument(doc.Name)
    for o in doc.Objects:
        o.ViewObject.Visibility = o.TypeId not in HELPERS
        if hasattr(o, "Malzeme"):
            style(o, o.Malzeme)
    Gui.updateGui()
    view = Gui.getDocument(doc.Name).ActiveView
    view.setAnimationEnabled(False)
    return doc, view


def render_assembly() -> None:
    doc, view = open_assembly("delta_v2.FCStd")
    for name, setter in [
        ("iso.png", view.viewIsometric),
        ("on.png", view.viewFront),
        ("yan.png", view.viewRight),
        ("ust.png", view.viewTop),
    ]:
        setter()
        view.fitAll()
        save(view, IMG_DIR / name, SIZE)

    # Hareketli mekanizma yakın plan (alüminyum gövde ve POM taban gizli)
    for o in doc.Objects:
        if o.Name.startswith("base_") and getattr(o, "Malzeme", "") in ("al7075", "pom"):
            o.ViewObject.Visibility = False
    view.viewIsometric()
    focus(
        doc,
        [o.Name for o in doc.Objects if hasattr(o, "Malzeme") and not o.Name.startswith("base_")],
    )
    save(view, IMG_DIR / "mekanizma.png", SIZE)

    # Eklem istifi yakın plan: 1. kolun dirseği (pim, burçlar, küreler, somunlar)
    elbow = [
        o.Name
        for o in doc.Objects
        if o.Name.startswith("bicep_1_")
        and getattr(o, "Malzeme", "") in ("steel", "pla_solid")
        and "output_shaft" not in o.Name
    ]
    view.viewIsometric()
    focus(doc, elbow)
    view.zoomOut()
    save(view, IMG_DIR / "eklem.png", SIZE)
    App.closeDocument(doc.Name)


def render_raised() -> None:
    """1. kol yazılım limitinde (~-70°): üst plakadaki dikdörtgen açıklıktan geçişi gösterir."""
    path = CAD_DIR / "out" / "delta_v2_kol1_yukari.FCStd"
    if not path.exists():
        return
    doc, view = open_assembly(path.name)
    view.viewFront()  # 1. kol +X'te: önden profilde, plakadaki açıklıktan geçişi görünür
    view.fitAll()
    save(view, IMG_DIR / "kol1_yukari.png", SIZE)
    view.viewIsometric()
    view.fitAll()
    save(view, IMG_DIR / "kol1_yukari_iso.png", SIZE)
    view.viewFront()
    for o in doc.Objects:
        if o.Name.startswith("base_") and getattr(o, "Malzeme", "") in ("al7075", "pom"):
            o.ViewObject.Visibility = False
    near = [o.Name for o in doc.Objects if o.Name.startswith(("bicep_1_", "base_housing_top"))]
    focus(doc, near)
    save(view, IMG_DIR / "kol1_yukari_yakin.png", SIZE)
    App.closeDocument(doc.Name)


def part_groups(p: dict) -> list[tuple[str, list[tuple[Part.Shape, str]]]]:  # noqa: F821
    """Önizleme grupları: (dosya adı, [(şekil, malzeme)]). Şekiller yerel çerçevelerindedir."""
    lower, cap = P.bearing_block(p, 1)
    lay = P.shaft_layout(p)
    fl = [s for n, s in P.forearm_link(p)]
    stack = {n: s for n, s in P.joint_stack(p, p["bicep"]["thickness"], 2) if n != "_ball_center"}
    plat = dict(P.platform_parts(p))
    return [
        ("01_pom_taban.png", [(P.pom_base(p), "pom")]),
        ("02_sutun_tavan.png", [(P.column(p), "al7075"), (P.ceiling(p), "al7075")]),
        (
            "03_motor_govdesi_ust_plaka.png",
            [(P.housing_top(p), "pla_infill20"), (P.motor_pad(p), "pla_infill20")],
        ),
        ("04_rulman_yatagi_kapak.png", [(lower, "pla_infill20"), (cap, "pla_infill20")]),
        (
            "05_motor_rulman_mil.png",
            [
                (P.motor_body(p), "motor"),
                (P.bearing(p, lay["b_in"] + p["bearing"]["width"] / 2), "bearing"),
                (P.output_shaft(p), "pla_solid"),
            ],
        ),
        ("06_kisa_kol.png", [(P.bicep_plate(p), "al7075")]),
        (
            "07_eklem_pim_burc_somun_kure.png",
            [
                (stack["pin"], "steel"),
                (stack["bushing"], "pla_solid"),
                (stack["nut"], "steel"),
                (stack["rod_end_ball"], "steel"),
            ],
        ),
        ("08_uzun_kol_rot_basi.png", [(fl[0], "steel"), (fl[1], "steel"), (fl[2], "steel")]),
        (
            "09_platform_miknatis.png",
            [(plat["platform"], "pla_infill20"), (plat["electromagnet"], "electromagnet")],
        ),
    ]


def render_parts() -> None:
    """Her grubu ayrı belgede, yan yana dizip izometrik görselini kaydeder."""
    p = params.load()
    for fname, items in part_groups(p):
        doc = App.newDocument("onizleme")
        x = 0.0
        for k, (shape, material) in enumerate(items):
            s = shape.copy()
            bb = s.BoundBox
            s.translate(App.Vector(x - bb.XMin, -bb.Center.y, -bb.Center.z))
            x += bb.XLength + max(10.0, 0.15 * bb.XLength)
            obj = doc.addObject("Part::Feature", f"p{k}")
            obj.Shape = s
            style(obj, material)
        doc.recompute()
        view = Gui.getDocument(doc.Name).ActiveView
        view.setAnimationEnabled(False)
        view.viewIsometric()
        view.fitAll()
        save(view, PART_DIR / fname, PART_SIZE)
        App.closeDocument(doc.Name)


def main() -> None:
    PART_DIR.mkdir(parents=True, exist_ok=True)
    Gui.activateWorkbench("PartWorkbench")
    render_assembly()
    render_raised()
    render_parts()
    Gui.getMainWindow().close()


main()
