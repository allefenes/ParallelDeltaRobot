"""Parça geometrileri (FreeCAD Part). Her fonksiyon parçayı KENDİ yerel çerçevesinde üretir.

Ortak yerel çerçeveler (birim mm):
    Kol çerçevesi  : orijin motor ekseninde (A_i); X radyal dışa (u_i), Y motor ekseni (t_i),
                     Z yukarı. Kısa kol XZ düzleminde, Y=0'da durur. Motor, rulman yatağı
                     ve mil bu çerçevede çizilir.
    Eklem çerçevesi: orijin eklem merkezinde, Y pim ekseni. Pim, burç ve somunlar Y boyunca dizilir.
    Rot başı       : orijin küre merkezinde, delik ekseni Y, gövde (şaft) +X yönünde.
    Uzun kol       : orijin üst küre merkezinde, X boyunca alt küre merkezine (forearm_length).
    Platform       : orijin platform eklem düzleminin merkezinde (P); eksenler robot
                     çerçevesine paralel.
    Gövde parçaları: robot çerçevesinde (orijin motor ekseni düzlemi merkezi, Z yukarı).

Ölçüler config/robot.yaml'dan gelir; "varsayim" etiketli değerler orada işaretlidir.
Radyuslar `fillets` bölümünden gelir; uygulanamayan radyus atlanır ve FILLET_LOG'a yazılır.
"""

from __future__ import annotations

import math

import FreeCAD as App
import Part

V = App.Vector
X, Y, Z = V(1, 0, 0), V(0, 1, 0), V(0, 0, 1)
ORIGIN = V(0, 0, 0)

# Radyus sonuçları: {parça etiketi: açıklama}. build.py kontrol raporuna yazar.
FILLET_LOG: dict[str, str] = {}


# --- Yardımcılar -------------------------------------------------------------------------------


def cyl_y(radius: float, y0: float, y1: float, x: float = 0.0, z: float = 0.0) -> Part.Shape:
    """Y ekseni boyunca y0'dan y1'e silindir."""
    return Part.makeCylinder(radius, y1 - y0, V(x, y0, z), Y)


def cyl_x(radius: float, x0: float, x1: float) -> Part.Shape:
    """X ekseni boyunca x0'dan x1'e silindir."""
    return Part.makeCylinder(radius, x1 - x0, V(x0, 0, 0), X)


def box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> Part.Shape:
    """Eksenlere hizalı kutu, köşe aralıklarıyla."""
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def to_arm(shape: Part.Shape, p: dict, alpha_deg: float) -> Part.Shape:
    """Kol çerçevesindeki şekli robot çerçevesine taşır (yerinde değiştirir ve döndürür)."""
    shape.translate(V(p["kinematics"]["base_radius"], 0, 0))
    shape.rotate(ORIGIN, Z, alpha_deg)
    return shape


def axis_line(edge, axis: App.Vector) -> bool:
    """Kenar, verilen eksene paralel bir doğru parçası mı?"""
    if not isinstance(edge.Curve, Part.Line):
        return False
    d = edge.Vertexes[-1].Point - edge.Vertexes[0].Point
    return d.Length > 1e-9 and abs(abs(d.normalize().dot(axis)) - 1.0) < 1e-6


def fillet(shape: Part.Shape, radius: float, pred, label: str) -> Part.Shape:
    """pred(kenar) doğru olan kenarlara radyus verir. Başarısızsa şekli değiştirmeden döndürür.

    Radyuslar sayısal olarak kırılgan olabildiği için sonuç doğrulanır; durum FILLET_LOG'a yazılır.
    """
    edges = [e for e in shape.Edges if pred(e)]
    if radius <= 0 or not edges:
        FILLET_LOG[label] = "uygun kenar yok"
        return shape
    try:
        out = shape.makeFillet(radius, edges)
        if out.isValid() and out.Volume > 0:
            FILLET_LOG[label] = f"R{radius:g}, {len(edges)} kenar"
            return out
    except Part.OCCError:
        pass
    # Toplu radyus başarısızsa kenarları tek tek dene; uygulanabilenleri koru.
    done = 0
    for e in edges:
        target = [f for f in shape.Edges if f.isSame(e) or _same_line(f, e)]
        if not target:
            continue
        try:
            out = shape.makeFillet(radius, target[:1])
        except Part.OCCError:
            continue
        if out.isValid() and out.Volume > 0:
            shape, done = out, done + 1
    FILLET_LOG[label] = (
        f"R{radius:g}, {done}/{len(edges)} kenar (tek tek)"
        if done
        else f"R{radius:g} uygulanamadı, atlandı"
    )
    return shape


def _same_line(a, b) -> bool:
    """İki kenar aynı uç noktalara sahip mi (radyus sonrası yeniden üretilen kenarları eşler)."""
    pa = sorted((v.Point.x, v.Point.y, v.Point.z) for v in a.Vertexes)
    pb = sorted((v.Point.x, v.Point.y, v.Point.z) for v in b.Vertexes)
    return len(pa) == len(pb) and all(
        abs(x1 - x2) < 1e-6 and abs(y1 - y2) < 1e-6 and abs(z1 - z2) < 1e-6
        for (x1, y1, z1), (x2, y2, z2) in zip(pa, pb, strict=True)
    )


def slot_hull_xz(r1: float, r2: float, length: float, thickness: float) -> Part.Shape:
    """XZ düzleminde iki dairenin (orijinde r1, x=length'te r2) dış teğet zarfı; Y'de kalınlık."""
    s = (r1 - r2) / length  # teğet doğrusunun eğimine ait sinüs
    c = math.sqrt(1.0 - s * s)
    pts = [V(r1 * s, 0, r1 * c), V(length + r2 * s, 0, r2 * c)]
    pts += [V(length + r2 * s, 0, -r2 * c), V(r1 * s, 0, -r1 * c)]
    quad = Part.Face(Part.makePolygon(pts + [pts[0]])).extrude(V(0, thickness, 0))
    shape = quad.fuse([cyl_y(r1, 0, thickness), cyl_y(r2, 0, thickness, x=length)])
    shape = shape.removeSplitter()
    shape.translate(V(0, -thickness / 2.0, 0))
    return shape


def hex_prism_y(af: float, y0: float, y1: float) -> Part.Shape:
    """Anahtar ağzı `af` olan altıgen prizma, Y boyunca."""
    r = af / math.sqrt(3.0)  # köşe yarıçapı
    pts = [
        V(r * math.cos(math.radians(60 * k)), y0, r * math.sin(math.radians(60 * k)))
        for k in range(6)
    ]
    return Part.Face(Part.makePolygon(pts + [pts[0]])).extrude(V(0, y1 - y0, 0))


def cross_y(size: float, width: float, y0: float, y1: float) -> Part.Shape:
    """Y boyunca artı kesitli prizma: uçtan uca `size`, kol genişliği `width`."""
    a = box(-size / 2, size / 2, y0, y1, -width / 2, width / 2)
    b = box(-width / 2, width / 2, y0, y1, -size / 2, size / 2)
    return a.fuse(b).removeSplitter()


# --- Kol çerçevesindeki parçalar ----------------------------------------------------------------


def shaft_layout(p: dict) -> dict:
    """Mil boyunca (Y ekseni) parça konumlarını tek yerde hesaplar."""
    sh, br, mo = p["output_shaft"], p["bearing"], p["motor"]
    b_in = sh["bearing_offset"] - br["width"] / 2.0  # rulmanın kol düzlemine yakın yüzü
    b_out = sh["bearing_offset"] + br["width"] / 2.0
    flange0 = -(b_out + 3.5)  # mil flanşı: rulman yatağı duvarının dışında
    horn1 = flange0  # göbek dış yüzü flanşa oturur
    horn0 = horn1 - mo["horn"]["thickness"]
    return {
        "b_in": b_in,
        "b_out": b_out,
        "block": (b_in - 1.5, b_out + 1.5),  # rulman yatağı Y aralığı (pozitif taraf)
        "flange": (flange0, flange0 + 2.0),
        "horn": (horn0, horn1),
        "motor_face": horn0,  # motor gövdesinin göbek tarafı yüzü
        "shaft_end": b_out + sh["length_beyond_bearing"],
    }


def output_shaft(p: dict) -> Part.Shape:
    """PLA çıkış mili: göbeğe bağlanan Ø16 flanş + tüm boyu artı kesit.

    Artı kesitin uçları Ø8 daire üzerindedir; böylece mil 608ZZ iç bileziğine oturur ve kısa kol
    artı deliğiyle milin üzerinden kaydırılarak takılabilir (kullanıcı). İç köşeler radyuslu.
    """
    sh, lay = p["output_shaft"], shaft_layout(p)
    f0, f1 = lay["flange"]
    y1 = lay["shaft_end"]
    arms = cross_y(sh["cross_size"], sh["cross_arm_width"], f1, y1)
    arms = arms.common(cyl_y(sh["journal_diameter"] / 2, f1, y1))
    w = sh["cross_arm_width"]
    arms = fillet(
        arms,
        p["fillets"]["shaft_inner"],
        lambda e: axis_line(e, Y) and math.hypot(e.Vertexes[0].Point.x, e.Vertexes[0].Point.z) < w,
        "çıkış mili: artı kesit iç köşeleri",
    )
    return cyl_y(8.0, f0, f1).fuse(arms).removeSplitter()


def bicep_plate(p: dict) -> Part.Shape:
    """7075 kısa kol: motor ucunda artı delik ve 4 küçük delik, eklem ucunda Ø5 delik."""
    b, k, sh = p["bicep"], p["kinematics"], p["output_shaft"]
    L = k["bicep_length"]
    plate = slot_hull_xz(b["motor_lobe_radius"], b["tip_boss_diameter"] / 2.0, L, b["thickness"])
    cl = b["cross_hole_clearance"]
    t = b["thickness"] + 2
    holes = [cross_y(sh["cross_size"] + cl, sh["cross_arm_width"] + cl, -t, t)]
    holes.append(cyl_y(b["pin_hole"] / 2.0, -t, t, x=L))
    sm = b["small_holes"]
    for n in range(sm["count"]):
        a = math.radians(45 + 90 * n)
        cx, cz = sm["pcd"] / 2 * math.cos(a), sm["pcd"] / 2 * math.sin(a)
        holes.append(cyl_y(sm["diameter"] / 2, -t, t, x=cx, z=cz))
    plate = plate.cut(holes)
    # Artı deliğin merkeze yakın 4 köşesi (malzeme köşeleri): çentik etkisini azaltır
    lim = sh["cross_arm_width"] + cl
    return fillet(
        plate,
        p["fillets"]["bicep_hole"],
        lambda e: axis_line(e, Y)
        and math.hypot(e.Vertexes[0].Point.x, e.Vertexes[0].Point.z) < lim,
        "kısa kol: artı delik iç köşeleri",
    )


def bearing(p: dict, y_center: float) -> Part.Shape:
    """608ZZ rulman (halka), Y ekseninde."""
    br = p["bearing"]
    y0, y1 = y_center - br["width"] / 2, y_center + br["width"] / 2
    return cyl_y(br["outer"] / 2, y0, y1).cut(cyl_y(br["inner"] / 2, y0 - 1, y1 + 1))


def motor_envelope(p: dict) -> tuple[float, float, float, float, float, float]:
    """AX-12A gövde zarfı kol çerçevesinde: (x0, x1, y0, y1, z0, z1)."""
    mo, lay = p["motor"], shaft_layout(p)
    bd = mo["body"]
    x1, y1 = mo["horn_axis_from_end"], lay["motor_face"]
    return x1 - bd["height"], x1, y1 - bd["width"], y1, -bd["depth"] / 2, bd["depth"] / 2


def motor_body(p: dict) -> Part.Shape:
    """AX-12A sadeleştirilmiş zarf + göbek. Çıkış ekseni Y, gövde radyal içe (-X) uzanır."""
    x0, x1, y0, y1, z0, z1 = motor_envelope(p)
    h0, h1 = shaft_layout(p)["horn"]
    horn = cyl_y(p["motor"]["horn"]["diameter"] / 2, h0, h1)
    return box(x0, x1, y0, y1, z0, z1).fuse(horn).removeSplitter()


def housing_bottom_z(p: dict) -> float:
    """Motor gövdesi üst plakasının alt yüzü (robot Z)."""
    return p["motor"]["body"]["depth"] / 2 + p["housing"]["clearance_above_motor"]


def block_y(p: dict, side: int) -> tuple[float, float]:
    """Rulman yatağının Y aralığı; side=+1/-1 mil üzerindeki taraf."""
    y0, y1 = shaft_layout(p)["block"]
    return (y0, y1) if side > 0 else (-y1, -y0)


def cap_screw_points(p: dict, side: int) -> list[App.Vector]:
    """Kapak vidalarının eksen noktaları (kol çerçevesi, z=0 düzleminde)."""
    y0, y1 = block_y(p, side)
    off = p["housing"]["cap_screw"]["offset"]
    return [V(sx * off, (y0 + y1) / 2, 0) for sx in (-1, 1)]


def bearing_cap(p: dict, side: int) -> Part.Shape:
    """Rulman yatağının alt yarısı (kapak): alttan takılır, rulmanı alttan tutar.

    2 vida alttan girer (başları aşağıda) ve gövdenin sabit üst yarısına vidalanır
    (baskıya diş açılması ya da ısıyla gömülen insert: varsayım).
    """
    h, br = p["housing"], p["bearing"]
    y0, y1 = block_y(p, side)
    w = h["bearing_block_width"] / 2
    cap = box(-w, w, y0, y1, -h["cap_height"], 0).cut(cyl_y(br["outer"] / 2, y0 - 1, y1 + 1))
    d = h["cap_screw"]["diameter"] + 0.4
    holes = [
        Part.makeCylinder(d / 2, h["cap_height"] + 2, q + V(0, 0, -h["cap_height"] - 1), Z)
        for q in cap_screw_points(p, side)
    ]
    return cap.cut(holes)


def insert_nut(p: dict) -> Part.Shape:
    """Isıyla gömülen M3 pirinç insert (dış tırtıl çizilmedi); orijin alt yüz, +Z boyunca."""
    ins = p["housing"]["insert"]
    tube = Part.makeCylinder(ins["od"] / 2, ins["length"], ORIGIN, Z)
    return tube.cut(Part.makeCylinder(ins["bore"] / 2, ins["length"] + 2, V(0, 0, -1), Z))


def cap_screw(p: dict) -> Part.Shape:
    """M3 kapak vidası (diş çizilmedi); orijin başın üst (dayanma) yüzü, başı -Z, gövdesi +Z.

    Kapağın alt yüzüne yerleştirilir: gövde kapaktan geçip üst yarıya depth_into_block kadar girer.
    """
    cs, h = p["housing"]["cap_screw"], p["housing"]
    length = h["cap_height"] + cs["depth_into_block"]
    shank = Part.makeCylinder(cs["diameter"] / 2, length, ORIGIN, Z)
    head = Part.makeCylinder(
        cs["head_diameter"] / 2, cs["head_height"], V(0, 0, -cs["head_height"]), Z
    )
    return shank.fuse(head).removeSplitter()


# --- Motor gövdesi (tek parça PLA baskı, robot çerçevesi) ---------------------------------------


def housing_plate(p: dict) -> Part.Shape:
    """Üst plaka: tavana 3 cıvatayla bağlı; her kolun üstünde dikdörtgen açıklık (kullanıcı)."""
    h, k = p["housing"], p["kinematics"]
    z0, t = housing_bottom_z(p), h["top_thickness"]
    plate = Part.makeCylinder(housing_radius(p), t, V(0, 0, z0), Z)
    sl = h["arm_slot"]
    cuts = mount_holes(p, z0 - 1, z0 + t + 1)
    for a in k["arm_angles"]:
        x0, x1 = k["base_radius"] + sl["x_from"], k["base_radius"] + sl["x_to"]
        slot = box(x0, x1, -sl["width"] / 2, sl["width"] / 2, z0 - 1, z0 + t + 1)
        slot.rotate(ORIGIN, Z, a)
        cuts.append(slot)
    plate = plate.cut(cuts)
    return fillet(
        plate,
        p["fillets"]["housing_slot"],
        lambda e: axis_line(e, Z),
        "üst plaka: açıklık köşeleri",
    )


def housing_radius(p: dict) -> float:
    """Üst plaka yarıçapı. 'auto': rulman yatağı dış köşesi + top_margin (kullanıcı kuralı)."""
    h = p["housing"]
    if h["top_radius"] != "auto":
        return float(h["top_radius"])
    _, y1 = shaft_layout(p)["block"]
    x_out = p["kinematics"]["base_radius"] + h["bearing_block_width"] / 2
    return math.hypot(x_out, y1) + h["top_margin"]


def motor_box(p: dict) -> Part.Shape:
    """Motor kutusu (kol çerçevesi): AX-12A'yı dört yandan ve üstten sarar, altı açık.

    Kutu motor gövdesini dönmeye karşı tutar (tepki torku); göbek tarafındaki duvarda göbeğin
    döndüğü delik vardır. Motor alttan girer. Dış kenarlar radyusludur.
    """
    h = p["housing"]
    x0, x1, y0, y1, z0, _ = motor_envelope(p)
    w = h["motor_box_wall"]
    top = housing_bottom_z(p)
    outer = box(x0 - w, x1 + w, y0 - w, y1 + w, z0, top)
    outer = fillet(
        outer,
        p["fillets"]["motor_box"],
        lambda e: e.BoundBox.ZMin < top - 1e-6,  # üst yüzdeki kenarlar plakaya kaynaşır
        "motor kutusu: dış kenarlar",
    )
    cavity = box(x0, x1, y0, y1, z0 - 1, z0 + p["motor"]["body"]["depth"])
    horn_hole = cyl_y(h["horn_hole_diameter"] / 2, y1 - 1, y1 + w + 1)
    return outer.cut([cavity, horn_hole])


def bearing_block_upper(p: dict, side: int) -> Part.Shape:
    """Rulman yatağının sabit üst yarısı (kol çerçevesi): mil ekseninden üst plakaya kadar dolu.

    Üst plakayla tek baskı parçasıdır (kullanıcı); rulman yuvası ve vida delikleri
    motor_housing'de açılır.
    """
    h = p["housing"]
    y0, y1 = block_y(p, side)
    w = h["bearing_block_width"] / 2
    return box(-w, w, y0, y1, 0, housing_bottom_z(p))


def motor_housing(p: dict) -> Part.Shape:
    """Tek parça PLA motor gövdesi: üst plaka + 3 motor kutusu + 6 rulman yatağı üst yarısı.

    Rulman yuvaları (Ø22), mil boşlukları ve kapak vida delikleri birleştirmeden sonra açılır.
    """
    k, br = p["kinematics"], p["bearing"]
    pieces = []
    cuts = []
    cs = p["housing"]["cap_screw"]
    for a in k["arm_angles"]:
        pieces.append(to_arm(motor_box(p), p, a))
        for side in (1, -1):
            pieces.append(to_arm(bearing_block_upper(p, side), p, a))
            y0, y1 = block_y(p, side)
            cuts.append(to_arm(cyl_y(br["outer"] / 2, y0 - 1, y1 + 1), p, a))
            ins = p["housing"]["insert"]
            for q in cap_screw_points(p, side):
                # Insert cebi (bölme yüzünden yukarı) + vidanın insert ötesine geçtiği delik
                pocket = Part.makeCylinder(ins["od"] / 2, ins["length"] + 1, q + V(0, 0, -1), Z)
                hole = Part.makeCylinder(
                    cs["diameter"] / 2, cs["depth_into_block"] + 1, q + V(0, 0, -1), Z
                )
                cuts += [to_arm(pocket, p, a), to_arm(hole, p, a)]
    body = housing_plate(p).fuse(pieces).removeSplitter()
    return body.cut(cuts)


# --- Eklem parçaları (eklem çerçevesi: Y pim ekseni) --------------------------------------------


def bushing(p: dict, y0: float, y1: float, narrow_at_y1: bool) -> Part.Shape:
    """Burç: boydan boya konik (kesik koni), Ø5 delik. Dar ucu rot başına bakar (kullanıcı)."""
    js = p["joint_stack"]
    rw, rn = js["bushing_outer"] / 2, js["bushing_cone_outer"] / 2
    r_start, r_end = (rw, rn) if narrow_at_y1 else (rn, rw)
    cone = Part.makeCone(r_start, r_end, y1 - y0, V(0, y0, 0), Y)
    return cone.cut(cyl_y(2.5, y0 - 1, y1 + 1))


def nut(p: dict, y0: float) -> Part.Shape:
    """M5 fiber somun (naylon halka ayrıca çizilmedi), y0'dan +Y yönüne."""
    n = p["joint_stack"]["nut"]
    s = hex_prism_y(n["width_af"], y0, y0 + n["height"])
    return s.cut(cyl_y(2.5, y0 - 1, y0 + n["height"] + 1))


def joint_stack(p: dict, core_width: float, inner_len: float) -> list[tuple[str, Part.Shape]]:
    """Pim boyunca istif (kullanıcı):
    somun | dış burç | rot başı | iç burç | çekirdek | iç burç | rot başı | dış burç | somun.

    Çekirdek (kısa kol ya da platform kulağı) Y=0'da ortalanır. Rot başının KÜRESİ pimle birlikte
    durur ve listeye girer; gövdesi uzun kolla küre etrafında eğilir (rod_end). Saplama aralığı
    = çekirdek + 2·iç burç + küre genişliği. Pim boyu istiften türetilir.
    """
    js, re = p["joint_stack"], p["rod_end"]
    bw, outer, nh = re["ball_width"], js["outer_bushing_length"], js["nut"]["height"]
    half = core_width / 2 + inner_len + bw + outer + nh
    out: list[tuple[str, Part.Shape]] = [("pin", cyl_y(2.5, -half, half))]
    for side in (1, -1):
        y = core_width / 2
        parts = [("bushing_inner", bushing(p, y, y + inner_len, narrow_at_y1=True))]
        y += inner_len
        ball = rod_end_ball(p)
        ball.translate(V(0, y + bw / 2, 0))
        parts.append(("rod_end_ball", ball))
        center = y + bw / 2
        y += bw
        parts.append(("bushing_outer", bushing(p, y, y + outer, narrow_at_y1=False)))
        y += outer
        parts.append(("nut", nut(p, y)))
        for name, s in parts:
            out.append((name, s if side > 0 else s.mirror(ORIGIN, Y)))
        out.append(("_ball_center", Part.Vertex(V(0, side * center, 0))))
    return out


def rod_end_ball(p: dict) -> Part.Shape:
    """Rot başının küresi: Ø5 delikli, iki yanı düz; pim ekseni Y. Pimle birlikte durur."""
    re = p["rod_end"]
    rb, hb = re["ball_diameter"] / 2, re["ball_width"] / 2
    ball = Part.makeSphere(rb).common(box(-rb, rb, -hb, hb, -rb, rb))
    return ball.cut(cyl_y(re["bore"] / 2, -hb - 1, hb + 1))


def rod_end(p: dict) -> Part.Shape:
    """Dişi M5 rot başı gövdesi + dişli şaft (küre ayrı: rod_end_ball). Delik Y, şaft +X.

    Gövde küre etrafında serbestçe eğilir; uzun kolun yanal açısı bu eğilmedir (≤ tilt_limit).
    """
    re = p["rod_end"]
    rb = re["ball_diameter"] / 2
    hh = re["housing_width"] / 2
    head = cyl_y(re["head_diameter"] / 2, -hh, hh).cut(Part.makeSphere(rb))
    x_end = re["center_to_end"]
    shank = cyl_x(re["shank_diameter"] / 2, re["head_diameter"] / 2 - 2, x_end)
    shank = shank.cut(cyl_x(re["bore"] / 2 * 0.85, x_end - re["thread_depth"], x_end + 1))
    return head.fuse(shank).removeSplitter()


def forearm_rod(p: dict) -> Part.Shape:
    """M5 saplama: iki rot başına thread_depth kadar girer (uzun kol çerçevesi, X ekseni)."""
    re, L = p["rod_end"], p["kinematics"]["forearm_length"]
    x0 = re["center_to_end"] - re["thread_depth"]
    return cyl_x(p["forearm_rod"]["diameter"] / 2 * 0.85, x0, L - x0)


def forearm_link(p: dict) -> list[tuple[str, Part.Shape]]:
    """Bir uzun kol: saplama + iki rot başı. Orijin üst küre merkezi, X alt küreye doğru."""
    L = p["kinematics"]["forearm_length"]
    top = rod_end(p)
    bottom = rod_end(p)
    bottom.rotate(ORIGIN, Y, 180)
    bottom.translate(V(L, 0, 0))
    return [("rod_end", top), ("rod", forearm_rod(p)), ("rod_end", bottom)]


# --- Platform ----------------------------------------------------------------------------------


def platform_parts(p: dict) -> list[tuple[str, Part.Shape]]:
    """PLA uç platform (dairesel) + 3 kulak + elektromıknatıs. Orijin P (eklem düzlemi merkezi).

    Kısıt: P'den mıknatıs ucuna mesafe = kinematics.ee_offset (kullanıcı: 15 mm).
    Eklem eksenleri plakanın orta düzlemindedir (z=0); mıknatıs alt yüzdeki cebe, üst yüzü z=0'a
    gelecek şekilde oturur. Disk dairesel ve rot başı gövdelerinden küçüktür; kulaklar kenardan
    dışarı taşar ve eksenleri r = radius (35) üzerindedir. Kulaklar arasında 3 süs deliği vardır.
    """
    pl, k, em = p["platform"], p["kinematics"], p["electromagnet"]
    r, rd, t = pl["radius"], pl["disc_radius"], pl["thickness"]
    disc = Part.makeCylinder(rd, t, V(0, 0, -t / 2), Z)
    half_t, lug = pl["ear_thickness"] / 2, pl["ear_lug_radius"]
    ears = []
    for a in k["arm_angles"]:
        ear = box(rd - 4, r, -half_t, half_t, -t / 2, t / 2)
        ear = ear.fuse(cyl_y(lug, -half_t, half_t, x=r)).removeSplitter()
        ear.rotate(ORIGIN, Z, a)
        ears.append(ear)
    body = disc.fuse(ears).removeSplitter()
    body = fillet(
        body,
        p["fillets"]["platform"],
        lambda e: axis_line(e, Z) and abs(e.Length - t) < 1e-6,
        "platform: kulak kökleri",
    )
    # Pim delikleri, mıknatıs cebi ve süs delikleri tek boolean işlemde açılır;
    # ardışık kesimlerde çakışan yüzeyler OCC'de boş sonuç verebiliyor.
    z_tip = -k["ee_offset"]
    cuts = [Part.makeCylinder(em["diameter"] / 2 + 0.2, em["height"], V(0, 0, z_tip), Z)]
    for a in k["arm_angles"]:
        hole = cyl_y(2.5, -half_t - 1, half_t + 1, x=r)
        hole.rotate(ORIGIN, Z, a)
        cuts.append(hole)
    dh = pl["deco_holes"]  # yalnız görsel amaçlı delikler (kullanıcı)
    for n in range(dh["count"]):
        a = math.radians(dh["angle_offset"] + 360.0 / dh["count"] * n)
        cc = V(dh["radius"] * math.cos(a), dh["radius"] * math.sin(a), -t)
        cuts.append(Part.makeCylinder(dh["diameter"] / 2, 2 * t, cc, Z))
    body = body.cut(cuts)
    magnet = Part.makeCylinder(em["diameter"] / 2, em["height"], V(0, 0, z_tip), Z)
    return [("platform", body), ("electromagnet", magnet)]


def magnet_pocket_depth(p: dict) -> float:
    """Mıknatıs cebinin plaka alt yüzünden derinliği (mm); türetilmiş değer."""
    z_top = -p["kinematics"]["ee_offset"] + p["electromagnet"]["height"]
    return z_top + p["platform"]["thickness"] / 2


# --- Gövde (robot çerçevesi) -------------------------------------------------------------------


def ceiling(p: dict) -> Part.Shape:
    """Tavan levhası (anahtar deliği): robot üstünde küçük daire, boyun, sütun üstünde daire."""
    f = p["frame"]
    t = f["plate_thickness"]
    z0 = housing_bottom_z(p) + p["housing"]["top_thickness"]
    dcol, rcol = f["column_distance"], f["column_radius"]
    round_ = Part.makeCylinder(f["ceiling_round_radius"], t, V(0, 0, z0), Z)
    neck = box(-dcol, 0, -f["neck_width"] / 2, f["neck_width"] / 2, z0, z0 + t)
    end = Part.makeCylinder(rcol, t, V(-dcol, 0, z0), Z)
    plate = round_.fuse([neck, end]).removeSplitter()
    plate = fillet(
        plate, p["fillets"]["ceiling"], lambda e: axis_line(e, Z), "tavan: boyun geçişleri"
    )
    plate = plate.cut(mount_holes(p, z0 - 1, z0 + t + 1))
    plate.rotate(ORIGIN, Z, f["column_azimuth"] - 180.0)
    return plate


def mount_holes(p: dict, z0: float, z1: float) -> list[Part.Shape]:
    """Motor gövdesini tavana bağlayan 3 cıvata deliği (merkeze yakın, kollar arasında)."""
    mh = p["housing"]["mount_holes"]
    out = []
    for n in range(mh["count"]):
        a = math.radians(60 + 120 * n)
        c = V(mh["pcd"] / 2 * math.cos(a), mh["pcd"] / 2 * math.sin(a), z0)
        out.append(Part.makeCylinder(mh["diameter"] / 2, z1 - z0, c, Z))
    return out


def column(p: dict) -> Part.Shape:
    """7075 D kesitli sütun: yarım silindir + düz yüzü kapatan levha (robota bakar), kaynaklı."""
    f, k = p["frame"], p["kinematics"]
    t = f["plate_thickness"]
    z0 = -k["base_to_floor"]
    z1 = housing_bottom_z(p) + p["housing"]["top_thickness"]
    ro = f["column_radius"]
    shell = Part.makeCylinder(ro, z1 - z0, V(0, 0, z0), Z).cut(
        Part.makeCylinder(ro - t, z1 - z0 + 2, V(0, 0, z0 - 1), Z)
    )
    half = box(-ro - 1, 0, -ro - 1, ro + 1, z0 - 1, z1 + 1)  # sütun merkezinin arkası (-X)
    shell = shell.common(half)
    # Açık yüz 5 mm levhayla kapalı: kesit D biçiminde (kullanıcı)
    flat = box(-t, 0, -ro, ro, z0, z1)
    shell = shell.fuse(flat).removeSplitter()
    shell.translate(V(-f["column_distance"], 0, 0))
    shell.rotate(ORIGIN, Z, f["column_azimuth"] - 180.0)
    return shell


def pom_base(p: dict) -> Part.Shape:
    """5 mm POM taban: robot altında yuvarlak uç, sütun tarafında köşeleri radyuslu dikdörtgen."""
    f, k = p["frame"], p["kinematics"]
    t = f["plate_thickness"]
    z1 = -k["base_to_floor"]
    rr = f["pom_round_radius"]
    x_back = -(f["column_distance"] + f["column_radius"] + f["pom_extra_behind_column"])
    round_ = Part.makeCylinder(rr, t, V(0, 0, z1 - t), Z)
    rect = box(x_back, 0, -f["pom_width"] / 2, f["pom_width"] / 2, z1 - t, z1)
    s = round_.fuse(rect).removeSplitter()
    s = fillet(
        s,
        p["fillets"]["pom_corner"],
        lambda e: axis_line(e, Z) and e.Vertexes[0].Point.x < x_back + 1,
        "POM taban: dikdörtgen uç köşeleri",
    )
    s.rotate(ORIGIN, Z, f["column_azimuth"] - 180.0)
    return s
