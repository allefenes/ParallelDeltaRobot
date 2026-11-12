"""F4.5 tic-tac-toe: tabla geometrisi, taş ikizi (mıknatısla al/bırak) ve oyun kuralları.

Saf Python (ROS'suz, yalnız standart kütüphane): ROS düğümü `board_twin`, API'nin sahte arka ucu ve
senaryo testleri aynı kodu kullanır.

Oyun: kaydırmalı tic-tac-toe (Üç Taş / Three Men's Morris ailesi). Çalışma alanı tablayı
doldurduğu için (F2: tabla yüksekliğinde en büyük kare 60 mm) taş deposu yoktur; taşlar baştan
tabladadır ve hücreden hücreye taşınır. X üst satırda (satır 0), O alt satırda (satır 2) başlar.
Sırası gelen oyuncu bir taşını çizgi boyunca komşu boş hücreye taşır. Kendi başlangıç satırı
dışındaki herhangi bir satır, sütun ya da köşegende üç taşı dizilen kazanır.

Birimler mm; robot çerçevesi (+Z yukarı). Taş konumu = taşın alt yüz merkezi.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# Hücre sırası: idx = satır * 3 + sütun; satır 0 = +Y tarafı, sütun 0 = -X tarafı.
LINES = (
    (0, 1, 2), (3, 4, 5), (6, 7, 8),  # satırlar
    (0, 3, 6), (1, 4, 7), (2, 5, 8),  # sütunlar
    (0, 4, 8), (2, 4, 6),  # köşegenler
)  # fmt: skip
# Çizgiler boyunca komşuluk (köşegenler merkezden geçer): kenar ortaları birbirine bağlı değil.
ADJACENT = {
    0: (1, 3, 4), 1: (0, 2, 4), 2: (1, 4, 5),
    3: (0, 4, 6), 4: (0, 1, 2, 3, 5, 6, 7, 8), 5: (2, 4, 8),
    6: (3, 4, 7), 7: (4, 6, 8), 8: (4, 5, 7),
}  # fmt: skip
START = {"X": (0, 1, 2), "O": (6, 7, 8)}
CAPTURE_XY_MM = 4.0  # mıknatıs ucu taş merkezine bu kadar yakınsa taş tutulur
CAPTURE_Z_MM = 1.5  # uç taş üst yüzünden en çok bu kadar yukarıda olabilir
CELL_SNAP_MM = 5.0  # bırakılan taş hücre merkezine bu kadar yakınsa o hücrede sayılır
DROP_TOLERANCE_MM = 2.0  # taş yüzeyden bundan yüksekte bırakılırsa "düşürüldü"


@dataclass(frozen=True)
class Geometry:
    """Tabla ve taş ölçüleri; robot.yaml `task` ve `kinematics` bölümlerinden."""

    center: tuple[float, float] = (0.0, 0.0)
    cell: float = 20.0
    board_top: float = -236.0
    piece_height: float = 8.0
    piece_diameter: float = 16.0
    tool_offset: float = 15.0
    lift: float = 20.0

    @classmethod
    def from_spec(cls, spec: dict) -> Geometry:
        k, t = spec["kinematics"], spec.get("task", {})
        b = t.get("board", {})
        return cls(
            center=tuple(b.get("center_mm", (0.0, 0.0))),
            cell=float(b.get("cell_mm", 20.0)),
            board_top=-float(k["base_to_floor"]) + float(t.get("board_thickness", 4.0)),
            piece_height=float(t.get("piece_height", 8.0)),
            piece_diameter=float(b.get("piece_diameter_mm", 16.0)),
            tool_offset=float(k["ee_offset"]),
            lift=float(t.get("lift_height", 20.0)),
        )

    def cell_xy(self, idx: int) -> tuple[float, float]:
        row, col = divmod(idx, 3)
        return (self.center[0] + (col - 1) * self.cell, self.center[1] + (1 - row) * self.cell)

    @property
    def pick_p(self) -> float:
        """Mıknatıs ucu tabladaki taşın üst yüzündeyken P'nin z'si."""
        return self.board_top + self.piece_height + self.tool_offset

    @property
    def travel_p(self) -> float:
        """Taşıma yüksekliği: tutulan taşın altı diğer taşların üstünden `lift` kadar yukarıda."""
        return self.pick_p + self.piece_height + self.lift

    def nearest_cell(self, x: float, y: float) -> tuple[int | None, float]:
        """En yakın hücre ve merkeze uzaklık; tabla dışındaysa (None, uzaklık)."""
        best, dist = None, math.inf
        for i in range(9):
            cx, cy = self.cell_xy(i)
            d = math.hypot(x - cx, y - cy)
            if d < dist:
                best, dist = i, d
        half = 1.5 * self.cell
        inside = abs(x - self.center[0]) <= half and abs(y - self.center[1]) <= half
        return (best if inside else None), dist

    def pick_place_path(self, src: int, dst: int) -> list[tuple[str, tuple[float, float, float]]]:
        """Bir taşı src hücresinden dst'ye taşıyan adımlar: ("move", P) ya da ("magnet", on)."""
        sx, sy = self.cell_xy(src)
        dx, dy = self.cell_xy(dst)
        up, down = self.travel_p, self.pick_p
        return [
            ("move", (sx, sy, up)),
            ("move", (sx, sy, down)),
            ("magnet_on", (sx, sy, down)),
            ("move", (sx, sy, up)),
            ("move", (dx, dy, up)),
            ("move", (dx, dy, down)),
            ("magnet_off", (dx, dy, down)),
            ("move", (dx, dy, up)),
        ]


@dataclass
class Piece:
    pid: str  # "X1"
    kind: str  # "X" | "O"
    pos: list[float]  # alt yüz merkezi (mm)
    held: bool = False


@dataclass
class Metrics:
    """Senaryo metrikleri (datasheet: Senaryo metrikleri)."""

    picks: int = 0
    places: int = 0
    dropped: int = 0  # yüksekten bırakıldı
    off_board: int = 0  # tabla dışına bırakıldı
    missed_picks: int = 0  # mıknatıs açıldı ama taş tutulmadı
    placement_errors_mm: list[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        e = self.placement_errors_mm
        return {
            "picks": self.picks,
            "places": self.places,
            "dropped": self.dropped,
            "off_board": self.off_board,
            "missed_picks": self.missed_picks,
            "placement_error_mean_mm": round(sum(e) / len(e), 3) if e else None,
            "placement_error_max_mm": round(max(e), 3) if e else None,
        }


class BoardTwin:
    """Taşların dijital ikizi: mıknatıs ucunun konumu ve mıknatıs durumundan fizik benzetimi."""

    def __init__(self, geo: Geometry) -> None:
        self.geo = geo
        self.reset()

    def reset(self) -> None:
        g = self.geo
        self.pieces: list[Piece] = []
        for kind, cells in START.items():
            for n, idx in enumerate(cells, 1):
                x, y = g.cell_xy(idx)
                self.pieces.append(Piece(f"{kind}{n}", kind, [x, y, g.board_top]))
        self.metrics = Metrics()
        self._magnet = False

    @property
    def held(self) -> Piece | None:
        return next((p for p in self.pieces if p.held), None)

    def update(self, tip: tuple[float, float, float] | None, magnet: bool) -> None:
        """Telemetri adımı: tip = mıknatıs ucu (P − tool_offset); None ise konum bilinmiyor."""
        g = self.geo
        rising = magnet and not self._magnet
        falling = self._magnet and not magnet
        self._magnet = magnet
        held = self.held
        if tip is None:
            # Konum bilinmiyor: taş son bilinen yerinde bırakılır (mıknatıs kapanınca düşer).
            if falling and held is not None:
                self._release(held)
            return
        if rising and held is None:
            target = self._piece_under(tip)
            if target is None:
                self.metrics.missed_picks += 1
            else:
                target.held = True
                self.metrics.picks += 1
                held = target
        if held is not None:
            held.pos = [tip[0], tip[1], tip[2] - g.piece_height]
            if falling:
                self._release(held)

    def _piece_under(self, tip) -> Piece | None:
        g = self.geo
        for p in self.pieces:
            top = p.pos[2] + g.piece_height
            if (
                math.hypot(tip[0] - p.pos[0], tip[1] - p.pos[1]) <= CAPTURE_XY_MM
                and top - 0.5 <= tip[2] <= top + CAPTURE_Z_MM
            ):
                return p
        return None

    def _release(self, p: Piece) -> None:
        g = self.geo
        p.held = False
        self.metrics.places += 1
        if p.pos[2] - g.board_top > DROP_TOLERANCE_MM:
            self.metrics.dropped += 1
        p.pos[2] = g.board_top
        cell, dist = g.nearest_cell(p.pos[0], p.pos[1])
        if cell is None:
            self.metrics.off_board += 1
        else:
            self.metrics.placement_errors_mm.append(dist)

    def cells(self) -> str:
        """9 karakter: hücredeki taş türü ya da '.'; hücre merkezine yakın olmayan taş sayılmaz."""
        out = ["."] * 9
        for p in self.pieces:
            if p.held:
                continue
            cell, dist = self.geo.nearest_cell(p.pos[0], p.pos[1])
            if cell is not None and dist <= CELL_SNAP_MM:
                out[cell] = p.kind
        return "".join(out)

    def to_dict(self) -> dict:
        cells = self.cells()
        return {
            "cells": cells,
            "winner": winner(cells),
            "pieces": [
                {
                    "id": p.pid,
                    "kind": p.kind,
                    "pos_mm": [round(v, 2) for v in p.pos],
                    "held": p.held,
                }
                for p in self.pieces
            ],  # fmt: skip
            "metrics": self.metrics.to_dict(),
            "geometry": {
                "center_mm": list(self.geo.center),
                "cell_mm": self.geo.cell,
                "board_top_mm": self.geo.board_top,
                "piece_height_mm": self.geo.piece_height,
                "piece_diameter_mm": self.geo.piece_diameter,
                "pick_P_mm": self.geo.pick_p,
                "travel_P_mm": self.geo.travel_p,
            },
        }


# --- kurallar ----------------------------------------------------------------------------------


def initial_cells() -> str:
    return "XXX...OOO"


def winner(cells: str) -> str | None:
    for kind in ("X", "O"):
        for line in LINES:
            if line != START[kind] and all(cells[i] == kind for i in line):
                return kind
    return None


def legal_moves(cells: str, kind: str) -> list[tuple[int, int]]:
    return [
        (src, dst)
        for src in range(9)
        if cells[src] == kind
        for dst in ADJACENT[src]
        if cells[dst] == "."
    ]


def apply_move(cells: str, move: tuple[int, int]) -> str:
    src, dst = move
    s = list(cells)
    s[dst], s[src] = s[src], "."
    return "".join(s)


def best_move(cells: str, kind: str, depth: int = 6) -> tuple[int, int] | None:
    """Sınırlı derinlikte minimaks (rakip yapay zekâ ve senaryo testleri için); deterministik."""
    other = "O" if kind == "X" else "X"

    def score(c: str, turn: str, d: int) -> int:
        w = winner(c)
        if w is not None:
            return (100 + d) if w == kind else -(100 + d)
        moves = legal_moves(c, turn)
        if d == 0 or not moves:
            return 0
        nxt = other if turn == kind else kind
        vals = [score(apply_move(c, m), nxt, d - 1) for m in moves]
        return max(vals) if turn == kind else min(vals)

    moves = legal_moves(cells, kind)
    if not moves:
        return None
    return max(moves, key=lambda m: score(apply_move(cells, m), other, depth - 1))
