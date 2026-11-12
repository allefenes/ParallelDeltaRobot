"""RViz görselleri (visualization_msgs/Marker): tic-tac-toe tablası, taşlar, uç izi, hedef.

Tüm marker'lar base_link çerçevesinde ve METRE cinsindendir (ROS kuralı); girdiler mm.
Tabla yerleşimi F4.5'te kesinleşir; burada server.yaml parametreleri ve robot.yaml görev
yükseklikleri kullanılır.
"""

from __future__ import annotations

from dataclasses import dataclass

from geometry_msgs.msg import Point
from std_msgs.msg import ColorRGBA
from visualization_msgs.msg import Marker

FRAME = "base_link"
BOARD_COLOR = (0.20, 0.22, 0.26, 1.0)
GRID_COLOR = (0.95, 0.95, 0.95, 1.0)
PIECE_COLORS = {"X": (0.10, 0.45, 0.90, 1.0), "O": (0.95, 0.80, 0.10, 1.0)}
TRAIL_COLOR = (0.10, 0.85, 0.95, 1.0)
REJECT_COLOR = (0.95, 0.10, 0.10, 0.9)
ACCEPT_COLOR = (0.15, 0.85, 0.25, 0.9)
LABEL_COLOR = (1.0, 0.35, 0.30, 1.0)  # koyu arka planda okunur açık kırmızı
LABEL_HEIGHT_M = 0.011  # yazı satır yüksekliği (m)
LABEL_Z_MM = 80.0  # ret yazısının z'si: robot gövdesinin üstü (base_link motor düzlemi)
# RViz (rviz_rendering MovableText) yazı kısıtları, Jazzy:
#  - Yazı tipi yalnız 33-166 kod noktalarını içerir ve metni bayt bayt çizer; UTF-8 Türkçe
#    harfler (ş, ı, ğ, ...) çizimi orada keser. Bu yüzden yazı ASCII'ye çevrilir.
#  - Boşluk genişliği yazı boyutuyla ölçeklenmez (~0.5 m); kelimeler ekran dışına dağılır.
#    Sekme doğru ölçeklenir (biraz geniş), boşluk yerine o kullanılır.
RVIZ_ASCII = str.maketrans(
    {**dict(zip("çğıöşüÇĞİÖŞÜâîûÂÎÛ", "cgiosuCGIOSUaiuAIU", strict=True)), "°": " deg", "²": "^2"}
)


@dataclass(frozen=True)
class Board:
    """Tabla: merkez (mm), kenar (mm), hücre sayısı, üst yüz z (mm), taş ölçüleri (mm)."""

    center_mm: tuple[float, float]
    size_mm: float
    cells: int
    top_z_mm: float
    thickness_mm: float
    piece_height_mm: float
    piece_diameter_mm: float

    @property
    def cell_mm(self) -> float:
        """Hücre kenarı (mm)."""
        return self.size_mm / self.cells

    def cell_center_mm(self, row: int, col: int) -> tuple[float, float]:
        """Hücre merkezi (x, y) mm; satır 0 = +Y tarafı, sütun 0 = -X tarafı."""
        cx, cy = self.center_mm
        half = (self.cells - 1) / 2.0
        return (cx + (col - half) * self.cell_mm, cy + (half - row) * self.cell_mm)


def _color(rgba) -> ColorRGBA:
    return ColorRGBA(r=float(rgba[0]), g=float(rgba[1]), b=float(rgba[2]), a=float(rgba[3]))


def _pt(p_mm) -> Point:
    return Point(x=p_mm[0] / 1000.0, y=p_mm[1] / 1000.0, z=p_mm[2] / 1000.0)


def _marker(ns: str, mid: int, mtype: int, stamp=None) -> Marker:
    m = Marker()
    m.header.frame_id = FRAME
    if stamp is not None:
        m.header.stamp = stamp
    m.ns, m.id, m.type, m.action = ns, mid, mtype, Marker.ADD
    m.pose.orientation.w = 1.0
    return m


def board_markers(board: Board, pieces: str) -> list[Marker]:
    """Tabla gövdesi, ızgara çizgileri ve taşlar."""
    out = []
    body = _marker("board", 0, Marker.CUBE)
    cx, cy = board.center_mm
    body.pose.position = _pt((cx, cy, board.top_z_mm - board.thickness_mm / 2.0))
    body.scale.x = body.scale.y = board.size_mm / 1000.0
    body.scale.z = board.thickness_mm / 1000.0
    body.color = _color(BOARD_COLOR)
    out.append(body)

    grid = _marker("board", 1, Marker.LINE_LIST)
    grid.scale.x = 0.0012
    grid.color = _color(GRID_COLOR)
    half = board.size_mm / 2.0
    z = board.top_z_mm + 0.3
    for n in range(board.cells + 1):
        d = -half + n * board.cell_mm
        grid.points += [_pt((cx + d, cy - half, z)), _pt((cx + d, cy + half, z))]
        grid.points += [_pt((cx - half, cy + d, z)), _pt((cx + half, cy + d, z))]
    out.append(grid)

    for idx, ch in enumerate(pieces[: board.cells * board.cells]):
        if ch.upper() not in PIECE_COLORS:
            continue
        row, col = divmod(idx, board.cells)
        x, y = board.cell_center_mm(row, col)
        m = _marker("pieces", idx, Marker.CYLINDER)
        m.pose.position = _pt((x, y, board.top_z_mm + board.piece_height_mm / 2.0))
        m.scale.x = m.scale.y = board.piece_diameter_mm / 1000.0
        m.scale.z = board.piece_height_mm / 1000.0
        m.color = _color(PIECE_COLORS[ch.upper()])
        out.append(m)
    return out


def trail_marker(points_mm, stamp=None) -> Marker:
    """Mıknatıs ucunun geçtiği yol (LINE_STRIP); nokta yoksa marker silinir."""
    m = _marker("trail", 0, Marker.LINE_STRIP, stamp)
    if len(points_mm) < 2:
        m.action = Marker.DELETE
        return m
    m.scale.x = 0.003
    m.color = _color(TRAIL_COLOR)
    m.points = [_pt(p) for p in points_mm]
    return m


def rviz_text(text: str) -> str:
    """RViz'in çizebildiği metin: Türkçe harfler ASCII, boşluklar sekme."""
    return text.translate(RVIZ_ASCII).replace(" ", "\t")


def reject_label(reason: str) -> str:
    """Ret yazısı, iki satır: "RET G2: rot başı açı limiti" ve ayrıntı "(kol 2, örnek 0)".

    Süpervizör nedeni "G2: rot başı açı limiti (hedef yol, kol 2, örnek 0)" biçimindedir;
    ayrıntı ayrı satıra alınır ki ilk satır kısa ve okunur kalsın.
    """
    head, sep, rest = reason.strip().partition(" (")
    return f"RET {head}" + (f"\n({rest}" if sep else "")


def target_markers(target_mm, accepted: bool, text: str, stamp=None) -> list[Marker]:
    """Hedef küresi (kabul yeşil, ret kırmızı); retde neden yazısı ve yazıdan küreye çizgi.

    Yazı robotun üstünde (LABEL_Z_MM) durur: hedefin yanında olsa kollar ve gövde onu örter.
    """
    sphere = _marker("target", 0, Marker.SPHERE, stamp)
    sphere.pose.position = _pt(target_mm)
    d = 0.008 if accepted else 0.014
    sphere.scale.x = sphere.scale.y = sphere.scale.z = d
    sphere.color = _color(ACCEPT_COLOR if accepted else REJECT_COLOR)
    label = _marker("target", 1, Marker.TEXT_VIEW_FACING, stamp)
    leader = _marker("target", 2, Marker.LINE_LIST, stamp)
    if accepted or not text:
        label.action = Marker.DELETE
        leader.action = Marker.DELETE
    else:
        x, y, z = target_mm
        label.pose.position = _pt((x, y, LABEL_Z_MM))
        label.scale.z = LABEL_HEIGHT_M
        label.color = _color(LABEL_COLOR)
        label.text = rviz_text(reject_label(text))
        leader.scale.x = 0.0008
        leader.color = _color(REJECT_COLOR)
        leader.points = [_pt((x, y, LABEL_Z_MM - 24.0)), _pt((x, y, z))]
    return [sphere, label, leader]
