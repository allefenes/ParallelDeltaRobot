"""Etkileşimli HTML datasheet üretir: docs/datasheet/datasheet.html

Kaynaklar: config/robot.yaml, delta_core (kinematik), cad/out/mass_properties.json (CAD kütleleri),
hardware/bom.csv (malzeme listesi), docs/img/cad (görseller), docs/datasheet/ros_graph.json (F3'te
çalışan sistemden üretilen ROS2 ağı; yoksa planlanan mimari gösterilir).

Çalıştırma (konteynerde, delta_core derlendikten sonra):
    PYTHONPATH=build/core-rel python3 tools/datasheet/build_datasheet.py
Grafikler Plotly ile çizilir; tarayıcı plotly.js ve mermaid'i sabit sürümlü CDN'den yükler.
Değer etiketleri: [H] hesap, [S] simülasyon, [Ö] ölçüm (F5'te doldurulacak).
"""

from __future__ import annotations

import base64
import csv
import html
import json
import math
import sys
from datetime import date
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compute as C  # noqa: E402
import delta_core_py as dc  # noqa: E402

V2 = Path(__file__).resolve().parents[2]
OUT = V2 / "docs" / "datasheet" / "datasheet.html"
PLOTLY_JS = "https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"
MERMAID_JS = "https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.esm.min.mjs"

TAG = {
    "H": '<span class="tag h" title="Hesap">H</span>',
    "S": '<span class="tag s" title="Simülasyon">S</span>',
    "Ö": '<span class="tag o" title="Ölçüm: F5\'te doldurulacak">Ö</span>',
    "K": '<span class="tag k" title="Katalog">K</span>',
    "V": '<span class="tag v" title="Varsayım">V</span>',
}


def esc(x) -> str:
    return html.escape(str(x))


def table(header: list[str], rows: list[list], cls: str = "") -> str:
    th = "".join(f"<th>{esc(h)}</th>" for h in header)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>'


def fig_html(fig: go.Figure, div_id: str) -> str:
    fig.update_layout(
        template="plotly_white",
        margin={"l": 50, "r": 20, "t": 50, "b": 50},
        font={"family": "Inter, system-ui, sans-serif", "size": 12},
    )
    return fig.to_html(
        full_html=False, include_plotlyjs=False, div_id=div_id, config={"responsive": True}
    )


def img_b64(path: Path) -> str:
    if not path.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


# --- Grafikler ---------------------------------------------------------------------------------


def fig_workspace_3d(g: C.Grid) -> go.Figure:
    idx = np.argwhere(g.ok)
    x, y, z = g.xs[idx[:, 0]], g.ys[idx[:, 1]], g.zs[idx[:, 2]]
    fig = go.Figure(
        go.Scatter3d(
            x=x,
            y=y,
            z=z,
            mode="markers",
            marker={
                "size": 2,
                "color": z,
                "colorscale": "Viridis",
                "colorbar": {"title": "z (mm)"},
            },
            hovertemplate="x %{x} mm<br>y %{y} mm<br>z %{z} mm<extra></extra>",
        )
    )
    fig.update_layout(
        title="Çalışma alanı (P noktası; motor ve rot başı limitleri içinde)",
        scene={
            "xaxis_title": "x (mm)",
            "yaxis_title": "y (mm)",
            "zaxis_title": "z (mm)",
            "aspectmode": "data",
        },
        height=560,
    )
    return fig


def fig_slices(g: C.Grid) -> go.Figure:
    """XY dilimleri; z kaydırıcısı ile."""
    fig = go.Figure()
    steps = []
    for iz, z in enumerate(g.zs):
        fig.add_trace(
            go.Heatmap(
                x=g.xs,
                y=g.ys,
                z=g.ok[:, :, iz].T.astype(int),
                visible=(iz == len(g.zs) // 2),
                colorscale=[[0, "#eef1f5"], [1, "#2f7d6d"]],
                showscale=False,
                hovertemplate="x %{x} mm<br>y %{y} mm<extra></extra>",
            )
        )
        steps.append(
            {
                "method": "update",
                "label": f"{z:.0f}",
                "args": [
                    {"visible": [i == iz for i in range(len(g.zs))]},
                    {"title": f"XY dilimi, z = {z:.0f} mm"},
                ],
            }
        )
    fig.update_layout(
        title=f"XY dilimi, z = {g.zs[len(g.zs) // 2]:.0f} mm",
        sliders=[
            {"active": len(g.zs) // 2, "currentvalue": {"prefix": "z (mm): "}, "steps": steps}
        ],
        xaxis_title="x (mm)",
        yaxis_title="y (mm)",
        height=520,
        yaxis={"scaleanchor": "x"},
    )
    return fig


def fig_sections(g: C.Grid) -> go.Figure:
    """V1'deki gibi düşey kesitler: XZ (y=0) ve YZ (x=0)."""
    from plotly.subplots import make_subplots

    iy0 = int(np.argmin(np.abs(g.ys)))
    ix0 = int(np.argmin(np.abs(g.xs)))
    fig = make_subplots(rows=1, cols=2, subplot_titles=("XZ kesiti (y = 0)", "YZ kesiti (x = 0)"))
    cs = [[0, "#eef1f5"], [1, "#2f7d6d"]]
    fig.add_trace(
        go.Heatmap(x=g.xs, y=g.zs, z=g.ok[:, iy0, :].T.astype(int), colorscale=cs, showscale=False),
        1,
        1,
    )
    fig.add_trace(
        go.Heatmap(x=g.ys, y=g.zs, z=g.ok[ix0, :, :].T.astype(int), colorscale=cs, showscale=False),
        1,
        2,
    )
    fig.update_xaxes(title_text="x (mm)", row=1, col=1)
    fig.update_xaxes(title_text="y (mm)", row=1, col=2)
    fig.update_yaxes(title_text="z (mm)", row=1, col=1)
    fig.update_layout(height=430, title="Düşey kesitler")
    return fig


def fig_radius(g: C.Grid, cyl: dict) -> go.Figure:
    fig = go.Figure(go.Scatter(x=cyl["radii"], y=g.zs, mode="lines+markers", name="r(z)"))
    fig.add_shape(
        type="rect",
        x0=0,
        x1=cyl["diameter"] / 2,
        y0=cyl["z_min"],
        y1=cyl["z_max"],
        line={"color": "#c2410c"},
        fillcolor="rgba(194,65,12,0.12)",
    )
    fig.update_layout(
        title="Merkezde tamamen geçerli daire yarıçapı ve kullanılabilir silindir",
        xaxis_title="yarıçap (mm)",
        yaxis_title="z (mm)",
        height=420,
    )
    return fig


def fig_maps(g: C.Grid, maps_by_z: dict) -> go.Figure:
    """Metrik haritaları: açılır menü ile metrik ve yükseklik seçimi."""
    labels = {
        "res_mm": ("Çözünürlük, en kötü (mm)", "Viridis_r"),
        "speed_mm_s": ("Garanti hız, her yönde (mm/s)", "Viridis"),
        "force_n": ("Garanti kuvvet, her yönde (N)", "Viridis"),
        "cond": ("Jacobian koşul sayısı", "Magma_r"),
    }
    fig = go.Figure()
    buttons = []
    keys = [(z, m) for z in maps_by_z for m in labels]
    for i, (z, m) in enumerate(keys):
        title, cs = labels[m]
        fig.add_trace(
            go.Heatmap(
                x=g.xs,
                y=g.ys,
                z=maps_by_z[z][m].T,
                colorscale=cs,
                visible=(i == 0),
                colorbar={"title": title.split(" (")[0]},
                hovertemplate="x %{x} mm<br>y %{y} mm<br>%{z:.3f}<extra></extra>",
            )
        )
        buttons.append(
            {
                "method": "update",
                "label": f"{title} · z = {z:.0f}",
                "args": [
                    {"visible": [j == i for j in range(len(keys))]},
                    {"title": f"{title}, z = {z:.0f} mm"},
                ],
            }
        )
    z0, m0 = keys[0]
    fig.update_layout(
        title=f"{labels[m0][0]}, z = {z0:.0f} mm",
        updatemenus=[{"buttons": buttons, "x": 0, "y": 1.18, "xanchor": "left"}],
        xaxis_title="x (mm)",
        yaxis_title="y (mm)",
        yaxis={"scaleanchor": "x"},
        height=560,
    )
    return fig


def fig_board(g: C.Grid, h: dict, square: float) -> go.Figure:
    iz = int(round((h["pick_P"] - g.zs[0]) / g.step))
    fig = go.Figure(
        go.Heatmap(
            x=g.xs,
            y=g.ys,
            z=g.ok[:, :, iz].T.astype(int),
            colorscale=[[0, "#eef1f5"], [1, "#2f7d6d"]],
            showscale=False,
        )
    )
    s = square / 2
    fig.add_shape(type="rect", x0=-s, x1=s, y0=-s, y1=s, line={"color": "#c2410c", "width": 2})
    for k in (1, 2):
        c = -s + k * square / 3
        fig.add_shape(
            type="line", x0=c, x1=c, y0=-s, y1=s, line={"color": "#c2410c", "dash": "dot"}
        )
        fig.add_shape(
            type="line", x0=-s, x1=s, y0=c, y1=c, line={"color": "#c2410c", "dash": "dot"}
        )
    fig.update_layout(
        title=f"Taş alma yüksekliğinde (P z = {h['pick_P']:.0f} mm) erişim ve en büyük 3×3 tabla",
        xaxis_title="x (mm)",
        yaxis_title="y (mm)",
        yaxis={"scaleanchor": "x"},
        height=520,
    )
    return fig


# --- Sayfa -------------------------------------------------------------------------------------


def cell(v) -> str:
    """Liste ve sözlükleri tablo hücresinde satır satır gösterir."""
    if isinstance(v, dict):
        return "<br>".join(f"{esc(k)}: {esc(x)}" for k, x in v.items())
    if isinstance(v, list | tuple):
        return "<br>".join(esc(x) for x in v)
    return esc(v)


SCENARIO = V2 / "docs" / "datasheet" / "scenario_metrics.json"


def scenario_section() -> str:
    """F4.5 senaryo metrikleri (simülasyon): tools/e2e_f4.sh çıktısı; yoksa bekliyor notu."""
    if not SCENARIO.is_file():
        return '<p class="muted">Senaryo metrikleri: F4.5 uçtan uca koşusu bekliyor (tools/e2e_f4.sh).</p>'
    m = json.loads(SCENARIO.read_text(encoding="utf-8"))
    s, o = TAG["S"], TAG["Ö"]
    rows = [
        ["Oyun", f"{m['moves']} hamle, kazanan {m['winner'] or 'yok'}", s],
        [
            "Hamle (al-taşı-bırak) süresi",
            f"ort. {m['cycle_mean_s']} s, en çok {m['cycle_max_s']} s",
            s,
        ],
        [
            "Yerleştirme hatası (ikiz)",
            f"ort. {m['placement_error_mean_mm']} mm, en çok {m['placement_error_max_mm']} mm",
            s,
        ],
        [
            "Kaçırılan / düşürülen / tabla dışı taş",
            f"{m['missed_picks']} / {m['dropped']} / {m['off_board']}",
            s,
        ],
        ["Gerçek robotta aynı metrikler", "F5 kabul testi H12", o],
    ]
    return (
        "<h3>Senaryo metrikleri (simülasyon)</h3>"
        + table(["Ölçüt", "Değer", ""], rows)
        + '<p class="muted">Kaynak: docs/datasheet/scenario_metrics.json (uçtan uca test, sanal Pi). '
        "Yerleştirme hatası ikizin hesabıdır; gerçek hata kalibrasyon ve boşluğa bağlıdır (H5–H7).</p>"
    )


def ros_section() -> str:
    """ROS2 ağı bölümü. F3'ten sonra docs/datasheet/ros_graph.json çalışan sistemden üretilir."""
    graph = V2 / "docs" / "datasheet" / "ros_graph.json"
    if graph.exists():
        data = json.loads(graph.read_text(encoding="utf-8"))
        mermaid = data["mermaid"]
        rows = [
            [
                f"<b>{esc(n['ad'])}</b>",
                esc(n["amac"]),
                cell(n.get("arayuzler", "")),
                cell(n.get("hz", "")),
                cell(n.get("qos", "")),
                esc(n.get("guvenlik", "")),
            ]
            for n in data["dugumler"]
        ]
        iface_rows = [
            [
                f"<code>{esc(i['ad'])}</code>",
                esc(i["tur"]),
                f"<code>{esc(i['tip'])}</code>",
                cell(i.get("yayinlayan", [])),
                cell(i.get("dinleyen", [])),
                esc(i.get("hz", "") or ""),
                esc(i.get("qos", "")),
                esc(i.get("guvenlik", "")),
            ]
            for i in data.get("arayuzler", [])
        ]
        svg_path = graph.with_suffix(".svg")
        svg = svg_path.read_text(encoding="utf-8") if svg_path.exists() else ""
        svg = svg[svg.find("<svg") :] if "<svg" in svg else ""
        extra = (
            "<h3>rqt_graph tarzı ağ (graphviz)</h3>"
            f'<div style="overflow:auto;background:#fff;border-radius:8px">{svg}</div>'
            "<h3>Arayüzler</h3>"
            + table(
                [
                    "Ad",
                    "Tür",
                    "Tip",
                    "Yayınlayan / sunucu",
                    "Dinleyen / istemci",
                    "Hz",
                    "QoS",
                    "Güvenlik",
                ],
                iface_rows,
            )
        )
        note = f"Kaynak: çalışan sistemin iç gözlemi ({esc(data.get('tarih', ''))}); Compose ile sunucu + sanal Pi ayaktayken üretildi."
    else:
        mermaid = """flowchart LR
  subgraph Sunucu
    API[API / web] --> PLAN[yörünge planlayıcı]
    PLAN --> SUP[1. kapı: süpervizör]
    SUP --> BR[kenar köprüsü]
    BR --> TEL[telemetri arşivi]
  end
  subgraph Pi[Raspberry Pi kenarı]
    EDGE[delta_edge: tampon + son kapı + bekçi] --> DRV[sürücü: AX-12A / mock]
  end
  BR <-- TLS WebSocket (Pi bağlanır) --> EDGE"""
        rows = [
            [
                "API / web",
                "Kullanıcı komutları, oturum",
                "REST/WebSocket",
                "—",
                "—",
                "Kimlik doğrulama",
            ],
            [
                "Yörünge planlayıcı",
                "Komutu zaman damgalı yörüngeye çevirir",
                "action",
                "olay",
                "güvenilir",
                "—",
            ],
            [
                "Süpervizör (1. kapı)",
                "Çalışma alanı, çarpışma, hız/ivme profili",
                "service",
                "olay",
                "güvenilir",
                "G1–G5",
            ],
            [
                "Kenar köprüsü",
                "ROS2 ↔ kenar protokolü",
                "topic",
                "100",
                "best effort (telemetri)",
                "Kalp atışı",
            ],
            [
                "delta_edge (Pi)",
                "Tampon, son kapı, bekçi",
                "WebSocket+TLS",
                "100",
                "—",
                "G1, G4–G10",
            ],
        ]
        note = "Planlanan mimari (F3'te çalışan sistemden otomatik üretilen diyagramla değiştirilecek)."
        extra = ""
    tbl = table(["Düğüm / bileşen", "Amaç", "Arayüz", "Hz", "QoS", "Güvenlik rolü"], rows)
    return f"""<p class="muted">{note}</p>
<pre class="mermaid">{esc(mermaid)}</pre>
<h3>Düğümler</h3>
{tbl}
{extra}
<h3>Kalp atışı ve bekçi</h3>
<p>Sunucu kenara düzenli kalp atışı gönderir. Kenar, kalp atışı T_stop süresince gelmezse hareketin
ortasında bile kontrollü durup konumu tutar; T_off süresince gelmezse torku kapatır ve
elektromıknatısı tanımlı güvenli duruma alır. Süreler ve testleri:
<a href="../guvenlik-gereksinimleri.md">güvenlik gereksinimleri</a> (G6, G7).</p>"""


def main() -> None:
    params = yaml.safe_load((V2 / "config" / "robot.yaml").read_text(encoding="utf-8"))
    yaml_text = (V2 / "config" / "robot.yaml").read_text(encoding="utf-8")
    k, motor = params["kinematics"], params["motor"]
    robot = dc.DeltaKinematics(dc.load_params(str(V2 / "config" / "robot.yaml")))
    mp = json.loads((V2 / "cad" / "out" / "mass_properties.json").read_text(encoding="utf-8"))
    moving_kg = sum(v["mass_kg"] for n, v in mp["links"].items() if n != "base")

    g = C.scan_workspace(robot, step=5.0)
    cyl = C.usable_cylinder(g)
    h = C.task_heights(params)
    iz_pick = int(round((h["pick_P"] - g.zs[0]) / g.step))
    square = C.largest_square(g.ok[:, :, iz_pick], g.xs)
    z_mid = -200.0
    maps = {
        z_mid: C.slice_maps(robot, g, z_mid, motor, k["motor_step"]),
        h["pick_P"]: C.slice_maps(robot, g, h["pick_P"], motor, k["motor_step"]),
    }
    st = C.summary_stats(maps[z_mid])
    home = C.point_metrics(robot, (0.0, 0.0, z_mid), motor, k["motor_step"])
    single_step = float(
        max(np.linalg.norm(np.array(robot.jacobian(home["theta"]))[:, i]) for i in range(3))
        * math.radians(k["motor_step"])
    )
    payload = C.payload_at(robot, (0.0, 0.0, z_mid), motor, moving_kg)
    vol = C.volume_cm3(g)
    reasons = g.reason

    def f(v, d=1):
        return f"{v:.{d}f}"

    summary = table(
        ["Özellik", "Değer", "Kaynak"],
        [
            ["Tip", "3 DOF öteleme deltası (paralelkenar kollar)", TAG["K"]],
            ["Çalışma alanı hacmi", f"{f(vol)} cm³", TAG["H"]],
            [
                "Kullanılabilir silindir",
                f"Ø{f(cyl['diameter'],0)} × {f(cyl['height'],0)} mm (z {f(cyl['z_min'],0)} … {f(cyl['z_max'],0)})",
                TAG["H"],
            ],
            ["Tabla yüksekliğinde en büyük kare", f"{f(square,0)} × {f(square,0)} mm", TAG["H"]],
            [
                "Konum çözünürlüğü (P = 0, 0, −200)",
                f"tek motor adımı {f(single_step,2)} mm; en kötü (3 motor) {f(home['res_mm'],2)} mm",
                TAG["H"],
            ],
            [
                "Çözünürlük aralığı (z = −200 dilimi)",
                f"{f(st['res_mm']['min'],2)} … {f(st['res_mm']['max'],2)} mm",
                TAG["H"],
            ],
            ["Garanti hız, her yönde (merkez)", f"{f(home['speed_mm_s'],0)} mm/s", TAG["H"]],
            [
                "Garanti kuvvet, her yönde (merkez)",
                f"{f(home['force_n'],1)} N (sürekli tork %{int(motor['continuous_torque_fraction']*100)})",
                TAG["H"],
            ],
            [
                "Düşey taşıma kapasitesi (merkez)",
                f"{f(payload,0)} g (hareketli kütle düşülmüş)",
                TAG["H"],
            ],
            [
                "Jacobian koşul sayısı (z = −200)",
                f"{f(st['cond']['min'],2)} … {f(st['cond']['max'],2)}",
                TAG["H"],
            ],
            ["Hareketli kütle", f"{f(moving_kg*1000,0)} g", TAG["S"] + " CAD"],
            ["Tekrarlanabilirlik", "F5'te ölçülecek", TAG["Ö"]],
            ["Mutlak doğruluk", "F5'te ölçülecek", TAG["Ö"]],
            [
                "Çevrim süresi (25/100/25 mm)",
                "F5'te ölçülecek; F3 simülasyonu tahmin verir",
                TAG["Ö"],
            ],
        ],
    )
    geometry = table(
        ["Parametre", "Değer", "Kaynak"],
        [
            ["Taban yarıçapı R", f"{k['base_radius']} mm", "V1 JSON"],
            ["Kısa kol L1", f"{k['bicep_length']} mm", "V1 JSON"],
            ["Uzun kol L2", f"{k['forearm_length']} mm", "V1 JSON"],
            ["Platform yarıçapı r", f"{k['platform_radius']} mm", "V1 JSON"],
            ["P → mıknatıs ucu", f"{k['ee_offset']} mm", "Kullanıcı"],
            ["Motor ekseni → zemin", f"{k['base_to_floor']} mm", "V1 JSON"],
            [
                "Motor açı limitleri",
                f"{k['motor_limit_min']}° … +{k['motor_limit_max']}°",
                "V1 JSON",
            ],
            [
                "Rot başı yanal açı sınırı",
                f"{k['spherical_joint_limit']}°",
                TAG["V"] + " (V1: 14°)",
            ],
            [
                "Kısa kol mekanik yukarı sınırı",
                "≈ −71.2° (uzun kol saplaması üst plakaya değer)",
                TAG["S"] + " CAD",
            ],
        ],
    )
    motor_tbl = table(
        ["Parametre", "Değer", "Kaynak"],
        [
            ["Model", esc(motor["model"]), TAG["K"]],
            [
                "Stall torku",
                f"{motor['stall_torque_nm']} N·m @ {motor['rated_voltage']} V",
                TAG["K"],
            ],
            [
                "Boşta hız",
                f"{motor['no_load_rpm']} rpm ({f(motor['no_load_rpm']*6,0)} °/s)",
                TAG["K"],
            ],
            ["Sürekli tork oranı", f"%{int(motor['continuous_torque_fraction']*100)}", TAG["V"]],
            [
                "Konum çözünürlüğü",
                f"{k['motor_step']}° ({motor['position_range_deg']}° / 1024)",
                TAG["K"],
            ],
            ["Haberleşme", esc(motor["protocol"]), TAG["K"]],
            ["Stall akımı", f"≈ {motor['stall_current_a']} A", TAG["K"]],
            ["Besleme", "12 V, ≥ 5 A anahtarlamalı kaynak (3 servo + mıknatıs)", TAG["V"]],
            ["Robot bilgisayarı", "Raspberry Pi 4B (delta_edge, son güvenlik kapısı)", "V1"],
        ],
    )
    mass_rows = [
        [
            esc(n),
            f(v["mass_kg"] * 1000, 1),
            ", ".join(f(c * 1000, 1) for c in v["com_m"]),
            ", ".join(f"{v['inertia_kg_m2'][i][i]:.2e}" for i in range(3)),
        ]
        for n, v in mp["links"].items()
    ]
    mass_tbl = table(
        ["Bağ", "Kütle (g)", "Kütle merkezi (mm, yerel)", "Ixx, Iyy, Izz (kg·m²)"], mass_rows
    )
    with (V2 / "hardware" / "bom.csv").open(encoding="utf-8") as fh:
        bom = list(csv.DictReader(fh))
    cats: dict[str, list] = {}
    for r in bom:
        c = cats.setdefault(r["Kategori"], [0, 0, 0.0])
        c[0] += 1
        c[1] += int(r["Adet"])
        c[2] += float(r["Toplam kütle (g)"] or 0)
    bom_tbl = table(
        ["Kategori", "Kalem", "Adet", "Kütle (g)"],
        [[esc(c), v[0], v[1], f(v[2])] for c, v in cats.items()],
    )
    assum = comment_rows = C.comment_assumptions(yaml_text)
    assum_tbl = table(["Parametre", "Açıklama"], [[esc(a), esc(b)] for a, b in comment_rows])
    reason_tbl = table(
        ["Ret nedeni", "Izgara noktası"], [[esc(r), n] for r, n in sorted(reasons.items())]
    )

    figs = {
        "ws3d": fig_html(fig_workspace_3d(g), "ws3d"),
        "slices": fig_html(fig_slices(g), "slices"),
        "sections": fig_html(fig_sections(g), "sections"),
        "radius": fig_html(fig_radius(g, cyl), "radius"),
        "maps": fig_html(fig_maps(g, maps), "maps"),
        "board": fig_html(fig_board(g, h, square), "board"),
    }
    imgs = "".join(
        f'<figure><img src="{img_b64(V2 / "docs" / "img" / "cad" / n)}" alt="{a}"><figcaption>{a}</figcaption></figure>'
        for n, a in [
            ("iso.png", "Montaj (izometrik)"),
            ("mekanizma.png", "Mekanizma"),
            ("eklem.png", "Eklem istifi"),
        ]
    )
    page = TEMPLATE.format(
        date=date.today().isoformat(),
        plotly=PLOTLY_JS,
        mermaid=MERMAID_JS,
        imgs=imgs,
        summary=summary,
        geometry=geometry,
        motor=motor_tbl,
        mass=mass_tbl,
        bom=bom_tbl,
        assum=assum_tbl,
        reasons=reason_tbl,
        ros=ros_section(),
        scenario=scenario_section(),
        h_pick=f(h["pick_P"], 0),
        h_travel=f(h["travel_P"], 0),
        board_top=f(h["board_top"], 0),
        square=f(square, 0),
        cell=f(square / 3, 1),
        n_assum=len(assum),
        **figs,
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8", newline="\n")
    print(f"datasheet yazildi: {OUT.name} ({len(page) // 1024} KB)")


TEMPLATE = """<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Delta Robotics V2 Datasheet</title>
<script src="{plotly}"></script>
<style>
:root {{ --bg:#f7f8fa; --card:#ffffff; --ink:#1d2433; --muted:#5b6475; --line:#e3e7ee; --accent:#2f7d6d; --warn:#c2410c; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#11151c; --card:#181e27; --ink:#e7ebf2; --muted:#9aa4b5; --line:#2a3240; --accent:#4fb39e; }} }}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.55 Inter,system-ui,sans-serif }}
header {{ padding:32px 16px 16px; max-width:1100px; margin:auto }}
header h1 {{ margin:0 0 4px; font-size:28px }} .muted {{ color:var(--muted) }}
nav {{ max-width:1100px; margin:auto; padding:0 16px; display:flex; flex-wrap:wrap; gap:8px }}
nav a {{ color:var(--accent); text-decoration:none; font-size:13px; padding:4px 8px; border:1px solid var(--line); border-radius:6px }}
section {{ max-width:1100px; margin:16px auto; padding:20px; background:var(--card); border:1px solid var(--line); border-radius:12px }}
h2 {{ margin-top:0; font-size:20px }} h3 {{ font-size:16px }}
table {{ width:100%; border-collapse:collapse; margin:8px 0 16px; font-size:14px }}
th,td {{ text-align:left; padding:6px 8px; border-bottom:1px solid var(--line); vertical-align:top }}
th {{ color:var(--muted); font-weight:600 }}
.tag {{ display:inline-block; min-width:20px; text-align:center; font-size:11px; font-weight:700; border-radius:4px; padding:1px 5px; color:#fff }}
.tag.h {{ background:#2563eb }} .tag.s {{ background:#7c3aed }} .tag.o {{ background:#c2410c }} .tag.k {{ background:#475569 }} .tag.v {{ background:#a16207 }}
.figs {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:12px }}
figure {{ margin:0 }} figure img {{ width:100%; border:1px solid var(--line); border-radius:8px; background:#fff }}
figcaption {{ font-size:12px; color:var(--muted) }}
.callout {{ border-left:4px solid var(--warn); padding:8px 12px; background:rgba(194,65,12,.07); border-radius:6px }}
pre.mermaid {{ background:#fff; border:1px solid var(--line); border-radius:8px; padding:12px; overflow:auto }}
@media (max-width:640px) {{ section {{ padding:14px }} th,td {{ padding:4px }} }}
</style></head><body>
<header><h1>Delta Robotics V2 — Datasheet</h1>
<p class="muted">Uzaktan erişimli paralel delta robot deney kiti · üretim {date} · tüm değerler config/robot.yaml ve CAD'den hesaplanır, motor parametreleri değişince yeniden üretilir.</p>
<p>Etiketler: {TAG_H} hesap · {TAG_S} simülasyon/CAD · {TAG_K} katalog · {TAG_V} varsayım · {TAG_O} ölçüm (F5)</p></header>
<nav><a href="#ozet">Özet</a><a href="#alan">Çalışma alanı</a><a href="#harita">Performans haritaları</a><a href="#tabla">Görev (tabla)</a><a href="#geo">Geometri ve limitler</a><a href="#motor">Motor ve elektrik</a><a href="#kutle">Kütle ve atalet</a><a href="#bom">Malzeme listesi</a><a href="#ros">Yazılım / ROS2 ağı</a><a href="#varsayim">Varsayımlar</a></nav>
<section id="ozet"><h2>Özet</h2>{summary}<div class="figs">{imgs}</div></section>
<section id="alan"><h2>Çalışma alanı</h2>
<p>Izgara 5 mm; her nokta ters kinematik, motor açı limitleri ve rot başı yanal açı sınırından geçirilir. P noktası platformun eklem düzlemi merkezidir; mıknatıs ucu P'nin 15 mm altındadır.</p>
<p class="callout">Bulgu: çalışma alanını çoğunlukla rot başının yanal açı sınırı (13°) belirler. Rot başı daha büyük açıya izin verseydi alan genişlerdi; gerçek rot başı modeli bilinince yeniden hesaplanır.</p>
{ws3d}{slices}{sections}{radius}{reasons}</section>
<section id="harita"><h2>Performans haritaları</h2>
<p>Çözünürlük: üç motor birden ±1 adım (0.29°) oynadığında uç noktanın en büyük yer değiştirmesi. Garanti hız ≈ σ<sub>min</sub>(J)·ω<sub>max</sub>, garanti kuvvet ≈ τ<sub>sürekli</sub>/σ<sub>max</sub>(J). Koşul sayısı 1'e yakın = izotropik; büyüdükçe tekil konuma yaklaşılır. Menüden metrik ve yükseklik seçilir.</p>
{maps}</section>
<section id="tabla"><h2>Görev: tic-tac-toe tablası</h2>
<p>Tabla üst yüzü z = {board_top} mm, taş alma yüksekliği P z = {h_pick} mm, taşıma yüksekliği P z = {h_travel} mm (varsayımlar: tabla 4 mm, taş 8 mm, kaldırma 20 mm). Bu yükseklikte merkezli en büyük kare {square} mm → hücre {cell} mm. F4.5 tasarımı: 3 × 3 tabla, hücre {cell} mm, taş Ø16 × 8 mm (çelik pullu PLA). Çalışma alanı tablayı doldurduğu için taş deposu yoktur; oyun kaydırmalı tic-tac-toe'dur (Üç Taş ailesi): taşlar baştan tabladadır, komşu boş hücreye taşınır.</p>
{board}{scenario}</section>
<section id="geo"><h2>Geometri ve limitler</h2>{geometry}</section>
<section id="motor"><h2>Motor ve elektrik</h2>{motor}</section>
<section id="kutle"><h2>Kütle ve atalet (CAD)</h2><p class="muted">Bağ yerel çerçevelerinde; kaynak cad/out/mass_properties.json.</p>{mass}</section>
<section id="bom"><h2>Malzeme listesi özeti</h2>{bom}<p class="muted">Tam liste: hardware/bom.md.</p></section>
<section id="ros"><h2>Yazılım mimarisi / ROS2 ağı</h2>{ros}</section>
<section id="varsayim"><h2>Varsayımlar ({n_assum})</h2><p class="muted">config/robot.yaml'da "varsayim" işaretli değerler; ölçümle doğrulanınca güncellenir.</p>{assum}</section>
<script type="module">import mermaid from "{mermaid}"; mermaid.initialize({{ startOnLoad: true, theme: "neutral" }});</script>
</body></html>
"""
TEMPLATE = TEMPLATE.replace("{TAG_H}", TAG["H"].replace("{", "{{").replace("}", "}}"))
for key, t in (("{TAG_S}", "S"), ("{TAG_K}", "K"), ("{TAG_V}", "V"), ("{TAG_O}", "Ö")):
    TEMPLATE = TEMPLATE.replace(key, TAG[t])


if __name__ == "__main__":
    main()
