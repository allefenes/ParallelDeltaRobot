"""Delta Robotics V2 CAD montajı: parçaları üretir, poza yerleştirir, kontrol eder, dışa aktarır.

Çalıştırma (Windows, DeltaRobotV2/ içinden):  ./tools/cad.sh build
Çıktılar cad/out/ altına yazılır:
    delta_v2.FCStd          renklendirilebilir montaj (her bağ ayrı App::Part)
    meshes/<bag>.stl        her hareketli bağın mesh'i, KENDİ yerel çerçevesinde (URDF/ikiz için)
    mass_properties.json    bağ başına kütle, kütle merkezi, atalet (SI birimleri)
    checks.md               kinematik ölçü, eklem açısı ve çakışma kontrolleri

Bağlar (simülasyon gövdeleri):
    base         sabit: taban, sütun, tavan, motor gövdesi, motorlar, rulmanlar, yataklar
    bicep_i      motor ekseni etrafında döner; yerel çerçeve = kol çerçevesi (bkz. lib/parts.py)
    forearm_i_a/b  uzun kol + rot başları; orijin üst küre merkezi, X alt küreye
    platform     uç platform + kulak eklemleri + elektromıknatıs; orijin P, yönelim sabit
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

CAD_DIR = Path(os.environ.get("DELTA_CAD_DIR", Path(globals().get("__file__", ".")).parent))
sys.path.insert(0, str(CAD_DIR / "lib"))

import FreeCAD as App  # noqa: E402
import kinematics as kin  # noqa: E402
import MeshPart  # noqa: E402
import params  # noqa: E402
import Part  # noqa: E402
import parts as P  # noqa: E402

V = App.Vector
OUT = CAD_DIR / "out"


# --- Malzeme ve kütle --------------------------------------------------------------------------


def density_g_mm3(p: dict, material: str, shape: Part.Shape, mass_override: float | None) -> float:
    """Yoğunluk (g/mm3). Kataloğu bilinen parçalarda (motor, rulman, mıknatıs) kütle esas alınır."""
    if mass_override is not None:
        return mass_override / shape.Volume
    return p["materials"][material]["density"] / 1000.0


class Link:
    """Bir simülasyon gövdesi: yerel çerçevede parça listesi + robot çerçevesine yerleşim."""

    def __init__(self, name: str, placement: App.Placement):
        self.name = name
        self.placement = placement
        self.items: list[dict] = []

    def add(self, label: str, shape: Part.Shape, material: str, mass: float | None = None):
        self.items.append({"label": label, "shape": shape, "material": material, "mass": mass})

    def add_at(self, label, shape, material, pl: App.Placement, mass=None):
        s = shape.copy()
        s.Placement = pl.multiply(s.Placement)
        self.add(label, s, material, mass)


def mass_properties(p: dict, link: Link) -> dict:
    """Bağın kütlesi (kg), kütle merkezi (m) ve kütle merkezindeki atalet tensörü (kg·m²).

    Tümü bağın yerel çerçevesindedir.
    """
    total, cm = 0.0, V(0, 0, 0)
    rows = []
    for it in link.items:
        rho = density_g_mm3(p, it["material"], it["shape"], it["mass"])
        # Boolean işlemleri bileşik (Compound) döndürebilir; özellikler katı başına toplanır.
        for s in it["shape"].Solids:
            m = rho * s.Volume
            rows.append((m, s.CenterOfMass, s.MatrixOfInertia, rho))
            total += m
            cm += s.CenterOfMass * m
    cm = cm * (1.0 / total)
    inertia = [[0.0] * 3 for _ in range(3)]
    for m, c, mi, rho in rows:
        r = c - cm
        rv = (r.x, r.y, r.z)
        own = [[mi.A11, mi.A12, mi.A13], [mi.A21, mi.A22, mi.A23], [mi.A31, mi.A32, mi.A33]]
        for a in range(3):
            for b in range(3):
                steiner = m * ((r.Length**2 if a == b else 0.0) - rv[a] * rv[b])
                inertia[a][b] += own[a][b] * rho + steiner
    return {
        "mass_kg": total / 1000.0,
        "com_m": [cm.x / 1000.0, cm.y / 1000.0, cm.z / 1000.0],
        "inertia_kg_m2": [[v * 1e-9 for v in row] for row in inertia],
    }


# --- Bağların kurulması ------------------------------------------------------------------------


def arm_placement(p: dict, i: int) -> App.Placement:
    """Kol çerçevesi: orijin A_i, X=u_i, Y=t_i, Z yukarı."""
    a = p["kinematics"]["arm_angles"][i]
    R = p["kinematics"]["base_radius"]
    pos = V(R * math.cos(math.radians(a)), R * math.sin(math.radians(a)), 0)
    return App.Placement(pos, App.Rotation(V(0, 0, 1), a))


def stack_into(link: Link, p: dict, core_width: float, n_bush: int, pl: App.Placement) -> list:
    """Eklem istifini bağa ekler; rot başı küre merkezlerini (bağ yerel çerçevesinde) döndürür."""
    centers = []
    mat = {
        "pin": "steel",
        "nut": "steel",
        "rod_end_ball": "steel",
        "bushing": p["joint_stack"]["bushing_material"],
    }
    for name, s in P.joint_stack(p, core_width, n_bush):
        if name == "_ball_center":
            centers.append(pl.multVec(s.Point))
            continue
        link.add_at(name, s, mat[name], pl)
    return centers


def build_base(p: dict) -> Link:
    base = Link("base", App.Placement())
    base.add("pom_base", P.pom_base(p), "pom")
    base.add("column", P.column(p), "al7075")
    base.add("ceiling", P.ceiling(p), "al7075")
    base.add("housing_top", P.housing_top(p), "pla_infill20")
    lay = P.shaft_layout(p)
    for i in range(3):
        pl = arm_placement(p, i)
        base.add_at(f"motor_{i + 1}", P.motor_body(p), "motor", pl, mass=p["motor"]["mass"])
        base.add_at(f"motor_pad_{i + 1}", P.motor_pad(p), "pla_infill20", pl)
        for side in (1, -1):
            lower, cap = P.bearing_block(p, side)
            base.add_at(f"bearing_block_{i + 1}", lower, "pla_infill20", pl)
            base.add_at(f"bearing_cap_{i + 1}", cap, "pla_infill20", pl)
            yc = side * p["output_shaft"]["bearing_offset"]
            base.add_at(f"bearing_{i + 1}", P.bearing(p, yc), "bearing", pl, p["bearing"]["mass"])
    base.layout = lay
    return base


def build_bicep(p: dict, i: int, theta: float) -> tuple[Link, list]:
    pl = arm_placement(p, i).multiply(App.Placement(V(), App.Rotation(V(0, 1, 0), theta)))
    link = Link(f"bicep_{i + 1}", pl)
    link.add("output_shaft", P.output_shaft(p), "pla_solid")
    link.add("bicep_plate", P.bicep_plate(p), "al7075")
    L1 = p["kinematics"]["bicep_length"]
    centers = stack_into(
        link, p, p["bicep"]["thickness"], 2, App.Placement(V(L1, 0, 0), App.Rotation())
    )
    return link, [pl.multVec(c) for c in centers]


def build_platform(p: dict, pos: kin.Vec) -> tuple[Link, list]:
    link = Link("platform", App.Placement(V(*pos), App.Rotation()))
    for name, s in P.platform_parts(p):
        if name == "electromagnet":
            link.add(name, s, "electromagnet", p["electromagnet"]["mass"])
        else:
            link.add(name, s, "pla_infill20")
    r = p["kinematics"]["platform_radius"]
    centers = []
    for a in p["kinematics"]["arm_angles"]:
        u = V(math.cos(math.radians(a)), math.sin(math.radians(a)), 0)
        pl = App.Placement(u * r, App.Rotation(V(0, 0, 1), a))
        c = stack_into(
            link, p, p["platform"]["ear_thickness"], p["platform"]["bushings_per_side"], pl
        )
        centers.append([link.placement.multVec(x) for x in c])
    return link, centers


def forearm_placement(top: App.Vector, bottom: App.Vector, pin_axis: App.Vector) -> App.Placement:
    """Uzun kol çerçevesi: X üstten alta, Y pim eksenine en yakın dik yön (rot başı deliği)."""
    x = (bottom - top).normalize()
    y = pin_axis - x * pin_axis.dot(x)
    y.normalize()
    z = x.cross(y)
    m = App.Matrix(x.x, y.x, z.x, 0, x.y, y.y, z.y, 0, x.z, y.z, z.z, 0, 0, 0, 0, 1)
    return App.Placement(top, App.Rotation(m))


# --- Kontroller --------------------------------------------------------------------------------


def sphere_centers(shape: Part.Shape) -> list[App.Vector]:
    """Şekildeki küresel yüzeylerin merkezleri (rot başı küreleri)."""
    out = []
    for f in shape.Faces:
        if isinstance(f.Surface, Part.Sphere):
            c = f.Surface.Center
            if not any((c - o).Length < 1e-6 for o in out):
                out.append(c)
    return out


def interference(links: list[Link], tol_mm3: float = 0.5) -> list[str]:
    """Tüm parça çiftleri arasında hacimsel çakışma (> tol). Sınır kutusu ile ön eleme yapılır."""
    placed = []
    for ln in links:
        for it in ln.items:
            s = it["shape"].copy()
            s.Placement = ln.placement.multiply(s.Placement)
            placed.append((f"{ln.name}/{it['label']}", s))
    hits = []
    for a in range(len(placed)):
        na, sa = placed[a]
        for b in range(a + 1, len(placed)):
            nb, sb = placed[b]
            if not sa.BoundBox.intersect(sb.BoundBox):
                continue
            v = sa.common(sb).Volume
            if v > tol_mm3:
                hits.append(f"{na} ∩ {nb}: {v:.1f} mm³")
    return hits


# --- Ana akış ----------------------------------------------------------------------------------


def assemble(p: dict, d: kin.Delta, pose: kin.Vec) -> tuple[list[Link], list[str], list[float]]:
    """Verilen platform pozunda tüm bağları kurar; (bağlar, ölçü raporu satırları, θ) döndürür."""
    k = p["kinematics"]
    thetas = d.ik(pose)
    # Rot başı katalog kütlesi küre + gövdedir; küre çelik yoğunluğuyla, kalan gövdeye verilir.
    ball_mass = P.rod_end_ball(p).Volume * p["materials"]["steel"]["density"] / 1000.0
    housing_mass = p["rod_end"]["mass"] - ball_mass
    links = [build_base(p)]
    platform, lower_centers = build_platform(p, pose)
    elbow_centers = []
    for i in range(3):
        bl, centers = build_bicep(p, i, thetas[i])
        links.append(bl)
        elbow_centers.append(centers)

    # Uzun kollar: üst ve alt küre merkezleri eklem istiflerinden gelir (paralelkenar).
    rows = [
        "| Kol | Çubuk | Merkezden merkeze (mm) | Rot başı yanal açısı (°) |",
        "|---|---|---|---|",
    ]
    for i in range(3):
        _, t = kin.arm_axes(k["arm_angles"][i])
        pin_axis = V(*t)
        for j, tag in enumerate(("a", "b")):
            top, bottom = elbow_centers[i][j], lower_centers[i][j]
            link = Link(f"forearm_{i + 1}_{tag}", forearm_placement(top, bottom, pin_axis))
            for name, s in P.forearm_link(p):
                link.add(name, s, "steel", housing_mass if name == "rod_end" else None)
            links.append(link)
            # Kontrol: yerleştirilmiş rot başı küre merkezleri eklem istifiyle çakışmalı
            placed = []
            for it in link.items:
                if it["label"] == "rod_end":
                    s = it["shape"].copy()
                    s.Placement = link.placement.multiply(s.Placement)
                    placed += sphere_centers(s)
            err = min((c - top).Length for c in placed) + min((c - bottom).Length for c in placed)
            tilt = math.degrees(math.asin(abs((bottom - top).normalize().dot(pin_axis))))
            rows.append(
                f"| {i + 1} | {tag} | {(bottom - top).Length:.4f} "
                f"(istif hatası {err:.1e}) | {tilt:.2f} |"
            )
    links.append(platform)

    report = ["### Kinematik ölçüler", ""]
    for i in range(3):
        mid_top = (elbow_centers[i][0] + elbow_centers[i][1]) * 0.5
        mid_bot = (lower_centers[i][0] + lower_centers[i][1]) * 0.5
        A = V(*d.shoulder(i))
        spacing = (elbow_centers[i][0] - elbow_centers[i][1]).Length
        report.append(
            f"- Kol {i + 1}: taban yarıçapı {math.hypot(A.x, A.y):.3f}, "
            f"kısa kol {(mid_top - A).Length:.3f}, "
            f"platform yarıçapı {(mid_bot - V(*pose)).Length:.3f}, saplama aralığı {spacing:.3f} mm"
        )
    report += ["", "### Uzun kollar", ""] + rows
    hits = interference(links)
    report += ["", "### Çakışma (> 0.5 mm³)", ""]
    report += [f"- {h}" for h in hits] if hits else ["- Çakışma yok."]
    return links, report, thetas


def save_fcstd(links: list[Link], path: Path, meshes: Path | None = None) -> None:
    """Bağları App::Part grupları olarak kaydeder; istenirse bağ başına STL yazar."""
    doc = App.newDocument(path.stem)
    for ln in links:
        grp = doc.addObject("App::Part", ln.name)
        grp.Placement = ln.placement
        shapes = []
        for n, it in enumerate(ln.items):
            obj = doc.addObject("Part::Feature", f"{ln.name}_{it['label']}_{n}")
            obj.Shape = it["shape"]
            obj.addProperty("App::PropertyString", "Malzeme", "Delta", "Render rengi ve yoğunluk")
            obj.Malzeme = it["material"]
            grp.addObject(obj)
            shapes.append(it["shape"])
        if meshes is not None:
            mesh = MeshPart.meshFromShape(
                Shape=Part.makeCompound(shapes), LinearDeflection=0.05, AngularDeflection=0.35
            )
            mesh.write(str(meshes / f"{ln.name}.stl"))
    doc.recompute()
    doc.saveAs(str(path))
    App.closeDocument(doc.Name)


def main() -> None:
    p = params.load()
    k = p["kinematics"]
    d = kin.Delta(k)
    ap = p["assembly_pose"]
    pose = (ap["x"], ap["y"], ap["z"])

    links, rows, thetas = assemble(p, d, pose)
    report = [
        "# CAD kontrol raporu",
        "",
        f"## Montaj pozu P = {pose} mm, θ = {[round(t, 2) for t in thetas]}°",
        "",
    ] + rows

    # Uç işlevci: P'den mıknatıs ucuna mesafe kısıttır (ee_offset); geometriden ölçülür.
    plat = next(ln for ln in links if ln.name == "platform")
    magnet = next(it["shape"] for it in plat.items if it["label"] == "electromagnet")
    tool = -magnet.BoundBox.ZMin
    report += [
        "",
        "### Uç işlevci",
        "",
        f"- P'den mıknatıs ucuna {tool:.2f} mm (kısıt: ee_offset = {k['ee_offset']} mm). "
        f"P plakanın orta düzleminde; mıknatıs cebi alt yüzden {P.magnet_pocket_depth(p):.1f} mm "
        "derin (varsayım).",
        f"- Montaj pozunda mıknatıs ucu z = {pose[2] - tool:.1f} mm, "
        f"zemin z = {-k['base_to_floor']:.1f} mm.",
    ]
    if abs(tool - k["ee_offset"]) > 1e-6:
        raise RuntimeError(f"ee_offset kısıtı sağlanmadı: {tool} mm")

    # Ek kontrol pozları (ör. 1. kol yazılım limitinde): çakışma ve ölçüler + görsel için FCStd
    OUT.mkdir(parents=True, exist_ok=True)
    for cp in p.get("check_poses", []):
        cpose = (cp["x"], cp["y"], cp["z"])
        clinks, crows, cth = assemble(p, d, cpose)
        report += [
            "",
            f"## Kontrol pozu `{cp['name']}`: P = {cpose} mm, θ = {[round(t, 2) for t in cth]}°",
            "",
        ] + crows
        save_fcstd(clinks, OUT / f"delta_v2_{cp['name']}.FCStd")

    # Kütle ve atalet
    props = {ln.name: mass_properties(p, ln) for ln in links}
    report += ["", "## Kütleler", "", "| Bağ | Kütle (g) |", "|---|---|"]
    report += [f"| {n} | {v['mass_kg'] * 1000:.1f} |" for n, v in props.items()]
    moving = sum(v["mass_kg"] for n, v in props.items() if n != "base") * 1000
    report += ["", f"Hareketli toplam: {moving:.1f} g"]

    # Dışa aktarım: montaj + bağ mesh'leri
    (OUT / "meshes").mkdir(parents=True, exist_ok=True)
    save_fcstd(links, OUT / "delta_v2.FCStd", OUT / "meshes")
    meta = {
        "units": "SI (kg, m, kg·m²); kütle merkezi ve atalet bağın yerel çerçevesinde",
        "assembly_pose_mm": list(pose),
        "assembly_thetas_deg": thetas,
        "links": props,
    }
    # Windows'ta da LF yazılır; böylece yeniden üretim git farkı oluşturmaz.
    (OUT / "mass_properties.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    (OUT / "checks.md").write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")
    print(f"checks.md yazildi ({len(report)} satir)")


try:
    main()
except Exception:
    import traceback

    traceback.print_exc()
    raise
