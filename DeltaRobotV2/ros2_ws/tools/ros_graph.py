#!/usr/bin/env python3
"""Çalışan ROS2 yığınının grafiğini çıkarır (rclpy graf API'si) ve belgeler.

Yığın aynı ROS_DOMAIN_ID'de çalışırken (bkz. ros_graph.sh):
  python3 ros2_ws/tools/ros_graph.py [--out ros2_ws/graph] [--wait 20] [--rate-window 3]

Çıktılar (--out klasörüne):
  ros_graph.dot / ros_graph.svg  rqt_graph biçimi: düğüm elips, konu kutu, servis kesikli kenar
  ros_graph.json                 tarih, mermaid (flowchart LR), dugumler, arayuzler

ROS iç arayüzleri (/parameter_events, /rosout, düğüm başına parametre servisleri, eylemlerin
gizli konu/servisleri) ve araç düğümleri (bu betik, launch_ros, ros2cli daemon) atlanır.
Hz ölçülür: her konuya --rate-window saniye abone olunur. QoS yayıncıların uç bilgisinden okunur.
Düğümlerin amaç ve güvenlik rolü aşağıdaki BILINEN_DUGUMLER tablosundan gelir; yeni bir düğüm
eklenince oraya bir satır eklenir (yoksa JSON'da "tanımsız" yazar).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import rclpy
from rclpy.action import graph as action_graph
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rosidl_runtime_py.utilities import get_message

PROBE_NAME = "ros_graph_probe"
IC_KONULAR = {"/parameter_events", "/rosout"}
PARAM_SERVIS_EKLERI = (
    "/describe_parameters",
    "/get_parameter_types",
    "/get_parameters",
    "/get_type_description",
    "/list_parameters",
    "/set_parameters",
    "/set_parameters_atomically",
)
ATLANAN_DUGUM = re.compile(r"^(_.*|launch_ros_\d+|ros2cli.*|" + PROBE_NAME + r")$")

# Düğüm adı -> (amaç, güvenlik rolü). Türkçe; yeni düğüm eklendikçe güncellenir.
BILINEN_DUGUMLER: dict[str, tuple[str, str]] = {
    "robot_state_publisher": (
        "URDF'i (delta.urdf.xacro) /robot_description olarak yayımlar; sabit bağların TF'i "
        "/tf_static'e gider. Hareketli bağlar floating eklemli olduğundan onları "
        "delta_state_publisher yayımlar.",
        "yok (görselleştirme)",
    ),
    "delta_state_publisher": (
        "Dijital ikiz: /joint_states'ten ileri kinematikle (delta_core) bicep, forearm ve "
        "platform TF'ini yayımlar; RViz marker'ları: tabla, taşlar, uç izi, hedef ve ret nedeni.",
        "karar vermez; süpervizör kararlarını (/supervisor/events) görünür kılar",
    ),
    "supervisor": (
        "Sunucu 1. güvenlik kapısı: planlayıcının yörüngesini denetler, yalnız kabul edileni "
        "/edge/trajectory_out'a iletir, her kararı /supervisor/events'e yazar.",
        "1. kapı: G1, G2, G3, G4, G5; kenar RUNNING/FAULT iken yeni yörünge reddi (DURUM)",
    ),
    "trajectory_planner": (
        "/move_to isteğini anlık konumdan hedefe düz çizgi, quintic zaman profilli, 100 Hz "
        "örneklenmiş eklem yörüngesine çevirir (delta_core ters kinematiği) ve süpervizöre "
        "doğrulatır.",
        "karar vermez; her plan (erişilemeyen örnekler NaN) 1. kapıya gider",
    ),
    "sim_executor": (
        "GEÇİCİ yer tutucu (sanal Pi): kabul edilen yörüngeyi kendi saatiyle 100 Hz oynatır, "
        "/joint_states ve /edge/status yayımlar. edge_bridge + delta_edge ile değiştirilecek.",
        "yok: son kapı (K), bekçi (G6, G7) ve sağlık sınırları (G9) burada YOK; yalnız sayı "
        "olmayan yörüngeyi oynatmaz",
    ),
    "edge_bridge": (
        "Kenar köprüsü: kabul edilen yörüngeyi kenar protokolüne çevirip TLS WebSocket ile "
        "Pi'deki delta_edge'e gönderir; Pi telemetrisini ROS konularına yayımlar.",
        "taşıyıcı; 2. (son) kapı Pi'de: G1, G4, G5, G8, G9; bekçi G6, G7 (köprü 20 Hz kalp "
        "atışı gönderir; kenar arızalarını /supervisor/events'e gereksinimiyle yayımlar)",
    ),
    "rviz2": ("RViz görselleştirme.", "yok (görselleştirme)"),
}

# Konu/servis adı -> güvenlik notu (README tablosu ve JSON için).
ARAYUZ_GUVENLIK: dict[str, str] = {
    "/move_to": "komut girişi; karar 1. kapıda",
    "/supervisor/validate": "1. kapı girişi (G1–G5)",
    "/supervisor/events": "her kararın kaydı (gereksinim + neden)",
    "/edge/trajectory_out": "yalnız 1. kapıdan geçmiş yörünge (radyan, 100 Hz ızgara)",
    "/edge/status": "kenar durumu; RUNNING/FAULT iken 1. kapı yeni yörüngeyi reddeder",
    "/joint_states": "1. kapı başlangıç sürekliliği (G5) ve planlayıcı başlangıcı",
    "/edge/connected": "kenar (Pi) bağlı mı; kalıcı (transient local)",
    "/edge_bridge/torque": "tork aç/kapa; bekçi sonrası kurtarma yalnız bununla (G7)",
    "/edge_bridge/heartbeat_pause": "YALNIZ TEST: kalp atışını keser (G6/G7 hata enjeksiyonu)",
}


# delta_server.common QoS profilleri (konu -> güvenilirlik, kalıcılık, geçmiş). Yalnız
# delta_server düğümleri için geçerlidir; diğerlerinde derinlik canlı graftan okunamaz.
DELTA_SERVER_DUGUMLERI = {
    "delta_state_publisher",
    "supervisor",
    "trajectory_planner",
    "sim_executor",
}
QOS_PROFIL: dict[str, tuple[str, str, str]] = {
    "/joint_states": ("reliable", "volatile", "keep_last 10 (QOS_STATE)"),
    "/edge/status": ("reliable", "volatile", "keep_last 10 (QOS_STATE)"),
    "/edge/trajectory_out": ("reliable", "volatile", "keep_last 10 (QOS_COMMAND)"),
    "/supervisor/events": ("reliable", "volatile", "keep_last 50 (QOS_EVENTS)"),
    "/delta/markers": ("reliable", "transient_local", "keep_last 1 (QOS_LATCHED)"),
}


# --------------------------------------------------------------------------- graf toplama


def ic_servis(name: str) -> bool:
    """Düğüm başına parametre servisleri ve eylem gizli servisleri."""
    return name.endswith(PARAM_SERVIS_EKLERI) or "/_action/" in name


def ic_konu(name: str) -> bool:
    """ROS iç konuları ve eylem gizli konuları."""
    return name in IC_KONULAR or "/_action/" in name


def full_name(name: str, ns: str) -> str:
    return (ns.rstrip("/") + "/" + name) if ns not in ("", "/") else name


def qos_text(q, node_name: str = "", topic: str = "") -> str:
    """QoS profili -> "reliable, volatile, keep_last 10 (QOS_STATE)".

    Uç bilgisi (endpoint) yalnız güvenilirlik ve kalıcılığı taşır; geçmiş derinliği
    delta_server.common profillerinden (QOS_PROFIL) eklenir, canlı değerle tutarlıysa.
    """
    rel = {ReliabilityPolicy.RELIABLE: "reliable", ReliabilityPolicy.BEST_EFFORT: "best_effort"}
    dur = {
        DurabilityPolicy.VOLATILE: "volatile",
        DurabilityPolicy.TRANSIENT_LOCAL: "transient_local",
    }
    r, d = rel.get(q.reliability, str(q.reliability)), dur.get(q.durability, "?")
    text = f"{r}, {d}"
    prof = QOS_PROFIL.get(topic)
    if node_name in DELTA_SERVER_DUGUMLERI and prof and prof[:2] == (r, d):
        text += f", {prof[2]}"
    return text


def wait_for_graph(node: Node, wait_s: float, expect: list[str]) -> list[tuple[str, str]]:
    """Beklenen düğümler görünene ve düğüm listesi iki ölçümde aynı kalana kadar bekler."""
    deadline = time.monotonic() + wait_s
    last: list = []
    stable = 0
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.5)
        cur = sorted(
            (n, ns) for n, ns in node.get_node_names_and_namespaces() if not ATLANAN_DUGUM.match(n)
        )
        names = {n for n, _ in cur}
        stable = stable + 1 if cur == last and cur else 0
        last = cur
        if all(e in names for e in expect) and stable >= 3:
            break
    time.sleep(1.0)  # uç bilgileri (endpoint) yayılsın
    return last


def collect(node: Node, nodes: list[tuple[str, str]]) -> dict:
    """Düğüm başına yayın/abone/servis/istemci/eylem listeleri."""
    graph = {}
    for name, ns in nodes:
        g = {
            "yayin": [
                (t, ty[0])
                for t, ty in node.get_publisher_names_and_types_by_node(name, ns)
                if not ic_konu(t)
            ],
            "abone": [
                (t, ty[0])
                for t, ty in node.get_subscriber_names_and_types_by_node(name, ns)
                if not ic_konu(t)
            ],
            "servis": [
                (s, ty[0])
                for s, ty in node.get_service_names_and_types_by_node(name, ns)
                if not ic_servis(s)
            ],
            "istemci": [
                (s, ty[0])
                for s, ty in node.get_client_names_and_types_by_node(name, ns)
                if not ic_servis(s)
            ],
            "eylem_sunucu": [
                (a, ty[0])
                for a, ty in action_graph.get_action_server_names_and_types_by_node(node, name, ns)
            ],
            "eylem_istemci": [
                (a, ty[0])
                for a, ty in action_graph.get_action_client_names_and_types_by_node(node, name, ns)
            ],
        }
        graph[full_name(name, ns).lstrip("/")] = {k: sorted(v) for k, v in g.items()}
    return graph


def publisher_qos(node: Node, topics: list[str]) -> dict[str, dict[str, str]]:
    """Konu -> {yayıncı düğüm: QoS metni} (uç bilgisinden)."""
    out: dict[str, dict[str, str]] = {}
    for t in topics:
        out[t] = {
            full_name(i.node_name, i.node_namespace).lstrip("/"): qos_text(
                i.qos_profile, i.node_name, t
            )
            for i in node.get_publishers_info_by_topic(t)
            if not ATLANAN_DUGUM.match(i.node_name)
        }
    return out


def subscriber_qos(node: Node, topics: list[str]) -> dict[str, dict[str, str]]:
    """Konu -> {abone düğüm: QoS metni}."""
    out: dict[str, dict[str, str]] = {}
    for t in topics:
        out[t] = {
            full_name(i.node_name, i.node_namespace).lstrip("/"): qos_text(
                i.qos_profile, i.node_name, t
            )
            for i in node.get_subscriptions_info_by_topic(t)
            if not ATLANAN_DUGUM.match(i.node_name)
        }
    return out


def measure_rates(node: Node, topics: dict[str, str], window_s: float) -> dict[str, float | None]:
    """Her konuya abone olup window_s boyunca mesaj sayar; düzenli yayın yoksa None (olay)."""
    stamps: dict[str, list[float]] = {t: [] for t in topics}
    subs = []
    for t, ty in topics.items():
        infos = node.get_publishers_info_by_topic(t)
        durability = DurabilityPolicy.VOLATILE  # kalıcı (latched) mesajlar hızı bozmasın
        reliability = (
            ReliabilityPolicy.BEST_EFFORT
            if any(i.qos_profile.reliability == ReliabilityPolicy.BEST_EFFORT for i in infos)
            else ReliabilityPolicy.RELIABLE
        )
        qos = QoSProfile(depth=100, reliability=reliability, durability=durability)
        try:
            msg_type = get_message(ty)
        except (AttributeError, ModuleNotFoundError, ValueError):
            continue
        subs.append(
            node.create_subscription(
                msg_type, t, lambda _m, t=t: stamps[t].append(time.monotonic()), qos, raw=True
            )
        )
    end = time.monotonic() + window_s
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.05)
    for s in subs:
        node.destroy_subscription(s)
    rates: dict[str, float | None] = {}
    for t, st in stamps.items():
        if len(st) >= 3 and st[-1] > st[0]:
            hz = (len(st) - 1) / (st[-1] - st[0])
            rates[t] = round(hz, 1) if hz < 20 else float(round(hz))
        else:
            rates[t] = None
    return rates


# --------------------------------------------------------------------------- çıktılar


def build_interfaces(graph: dict, rates: dict, pub_qos: dict) -> list[dict]:
    """arayuzler listesi: konu, servis ve eylemler."""
    items: dict[tuple[str, str], dict] = {}

    def entry(name: str, typ: str, kind: str) -> dict:
        key = (kind, name)
        if key not in items:
            items[key] = {
                "ad": name,
                "tip": typ,
                "tur": kind,
                "yayinlayan": [],
                "dinleyen": [],
            }
        return items[key]

    for n, g in graph.items():
        for t, ty in g["yayin"]:
            entry(t, ty, "topic")["yayinlayan"].append(n)
        for t, ty in g["abone"]:
            entry(t, ty, "topic")["dinleyen"].append(n)
        for s, ty in g["servis"]:
            entry(s, ty, "service")["yayinlayan"].append(n)
        for s, ty in g["istemci"]:
            entry(s, ty, "service")["dinleyen"].append(n)
        for a, ty in g["eylem_sunucu"]:
            entry(a, ty, "action")["yayinlayan"].append(n)
        for a, ty in g["eylem_istemci"]:
            entry(a, ty, "action")["dinleyen"].append(n)

    out = []
    order = {"topic": 0, "service": 1, "action": 2}
    for (kind, name), e in sorted(items.items(), key=lambda kv: (order[kv[0][0]], kv[0][1])):
        e["yayinlayan"].sort()
        e["dinleyen"].sort()
        if kind == "topic":
            e["hz"] = rates.get(name)
            profiles = sorted(set(pub_qos.get(name, {}).values()))
            e["qos"] = " | ".join(profiles) if profiles else "-"
        else:
            e["hz"] = None
            e["qos"] = "servis varsayılanı (reliable)" if kind == "service" else "eylem varsayılanı"
        e["guvenlik"] = ARAYUZ_GUVENLIK.get(name, "-")
        out.append(e)
    return out


def build_nodes(graph: dict, rates: dict, pub_qos: dict, sub_qos: dict) -> list[dict]:
    """dugumler listesi (Türkçe)."""
    out = []
    for n, g in sorted(graph.items()):
        amac, guv = BILINEN_DUGUMLER.get(
            n, ("tanımsız: ros_graph.py BILINEN_DUGUMLER'e ekleyin", "tanımsız")
        )
        ifs = (
            [f"yayın {t} ({ty})" for t, ty in g["yayin"]]
            + [f"abone {t} ({ty})" for t, ty in g["abone"]]
            + [f"servis {s} ({ty})" for s, ty in g["servis"]]
            + [f"istemci {s} ({ty})" for s, ty in g["istemci"]]
            + [f"eylem sunucusu {a} ({ty})" for a, ty in g["eylem_sunucu"]]
            + [f"eylem istemcisi {a} ({ty})" for a, ty in g["eylem_istemci"]]
        )
        # Ölçüm konu başınadır; birden çok yayıncılı konuda toplam hız yazılır.
        hz = {}
        for t, _ in g["yayin"]:
            if rates.get(t) is None:
                continue
            k = len(pub_qos.get(t, {}))
            hz[t] = rates[t] if k <= 1 else f"{rates[t]:g} (konu toplamı, {k} yayıncı)"
        qos = {f"yayın {t}": pub_qos.get(t, {}).get(n, "?") for t, _ in g["yayin"]}
        qos.update({f"abone {t}": sub_qos.get(t, {}).get(n, "?") for t, _ in g["abone"]})
        out.append(
            {
                "ad": n,
                "amac": amac,
                "arayuzler": ifs,
                "hz": hz or None,
                "qos": qos,
                "guvenlik": guv,
            }
        )
    return out


def mid(prefix: str, name: str) -> str:
    """Mermaid/DOT için güvenli kimlik."""
    return prefix + re.sub(r"\W", "_", name.strip("/"))


def build_mermaid(graph: dict, interfaces: list[dict]) -> str:
    """Temiz Mermaid flowchart LR: düğüm (stadyum), konu (kutu), servis (altıgen, kesikli)."""
    lines = ["flowchart LR"]
    for n in sorted(graph):
        lines.append(f'  {mid("n_", n)}(["{n}"])')
    for e in interfaces:
        if e["tur"] == "topic":
            lines.append(f'  {mid("t_", e["ad"])}["{e["ad"]}"]')
        else:
            lines.append(f'  {mid("s_", e["ad"])}{{{{"{e["ad"]}"}}}}')
    lines.append('  delta_edge["delta_edge (Raspberry Pi)"]')
    for e in interfaces:
        if e["tur"] == "topic":
            t = mid("t_", e["ad"])
            lines += [f"  {mid('n_', p)} --> {t}" for p in e["yayinlayan"]]
            lines += [f"  {t} --> {mid('n_', s)}" for s in e["dinleyen"]]
        else:
            s = mid("s_", e["ad"])
            lines += [f"  {mid('n_', c)} -.-> {s}" for c in e["dinleyen"]]
            lines += [f"  {s} -.-> {mid('n_', p)}" for p in e["yayinlayan"]]
    label = '"TLS WebSocket, Pi bağlanır"'
    if "edge_bridge" in graph:
        lines.append(f"  delta_edge <-->|{label}| n_edge_bridge")
    else:
        lines += [
            '  edge_note>"edge_bridge (F3)"]',
            "  t_edge_trajectory_out -.-> edge_note",
            f"  edge_note <-->|{label}| delta_edge",
            "  edge_note -.-> t_joint_states",
            "  classDef note stroke-dasharray: 4 3",
            "  class edge_note note",
        ]
    lines += [
        "  classDef rosnode fill:#dbe9ff,stroke:#3a6ea5",
        "  classDef topic fill:#fff4d6,stroke:#b08900",
        "  classDef srv fill:#e9f7e9,stroke:#3a8a3a,stroke-dasharray: 4 3",
        "  classDef pi fill:#ffe1e1,stroke:#b03030",
    ]
    nodes = [mid("n_", n) for n in sorted(graph)]
    topics = [mid("t_", e["ad"]) for e in interfaces if e["tur"] == "topic"]
    srvs = [mid("s_", e["ad"]) for e in interfaces if e["tur"] != "topic"]
    for cls, ids in (("rosnode", nodes), ("topic", topics), ("srv", srvs)):
        if ids:
            lines.append(f"  class {','.join(ids)} {cls}")
    lines.append("  class delta_edge pi")
    return "\n".join(lines) + "\n"


def dot_q(s: str) -> str:
    return '"' + s.replace('"', '\\"') + '"'


def build_dot(graph: dict, interfaces: list[dict]) -> str:
    """rqt_graph biçiminde Graphviz: düğüm elips, konu kutu, servis kesikli kenar."""
    out = [
        "digraph ros_graph {",
        "  rankdir=LR;",
        '  graph [fontname="DejaVu Sans", fontsize=11, nodesep=0.35, ranksep=0.8,'
        ' label="Delta Robotics V2 ROS2 grafiği (servis: kesikli)", labelloc=t];',
        '  node [fontname="DejaVu Sans", fontsize=11];',
        '  edge [fontname="DejaVu Sans", fontsize=9];',
    ]
    for n in sorted(graph):
        out.append(f"  {mid('n_', n)} [label={dot_q('/' + n)}, shape=ellipse];")
    for e in interfaces:
        if e["tur"] == "topic":
            hz = f"\\n{e['hz']:g} Hz" if e.get("hz") else ""  # ölçülen hız etikete eklenir
            out.append(f"  {mid('t_', e['ad'])} [label={dot_q(e['ad'] + hz)}, shape=box];")
        else:
            style = 'shape=box, style="rounded,dashed"'
            out.append(f"  {mid('s_', e['ad'])} [label={dot_q(e['ad'])}, {style}];")
    for e in interfaces:
        if e["tur"] == "topic":
            t = mid("t_", e["ad"])
            out += [f"  {mid('n_', p)} -> {t};" for p in e["yayinlayan"]]
            out += [f"  {t} -> {mid('n_', s)};" for s in e["dinleyen"]]
        else:
            s = mid("s_", e["ad"])
            out += [f"  {mid('n_', c)} -> {s} [style=dashed];" for c in e["dinleyen"]]
            out += [f"  {s} -> {mid('n_', p)} [style=dashed];" for p in e["yayinlayan"]]
    pi = '  delta_edge [label="delta_edge\\n(Raspberry Pi)", shape=box3d];'
    tls = 'label="TLS WebSocket,\\nPi bağlanır", dir=both, style=bold'
    if "edge_bridge" in graph:
        out += [pi, f"  n_edge_bridge -> delta_edge [{tls}];"]
    else:
        out += [
            pi,
            '  edge_note [label="edge_bridge (F3)", shape=note, style=dashed];',
            "  t_edge_trajectory_out -> edge_note [style=dotted];",
            f"  edge_note -> delta_edge [{tls}];",
            "  edge_note -> t_joint_states [style=dotted];",
        ]
    out.append("}")
    return "\n".join(out) + "\n"


def to_json_prettier(value) -> str:
    """Prettier ile aynı biçimde JSON: nesneler hep açık, satıra sığan ilkel diziler tek satır.

    Böylece betik yeniden çalıştırılınca ./tools/format.sh --check bozulmaz.
    """

    def render(v, indent: int, prefix_len: int) -> str:
        pad, inner = " " * indent, " " * (indent + 2)
        if isinstance(v, dict):
            if not v:
                return "{}"
            parts = []
            for k, x in v.items():
                key = f"{json.dumps(k, ensure_ascii=False)}: "
                parts.append(f"{inner}{key}{render(x, indent + 2, indent + 2 + len(key))},")
            parts[-1] = parts[-1][:-1]
            return "{\n" + "\n".join(parts) + "\n" + pad + "}"
        if isinstance(v, list):
            if not v:
                return "[]"
            if all(not isinstance(x, dict | list) for x in v):
                flat = "[" + ", ".join(json.dumps(x, ensure_ascii=False) for x in v) + "]"
                if prefix_len + len(flat) + 1 <= 100:  # +1: sondaki virgül
                    return flat
            body = ",\n".join(inner + render(x, indent + 2, indent + 2) for x in v)
            return "[\n" + body + "\n" + pad + "]"
        return json.dumps(v, ensure_ascii=False)

    return render(value, 0, 0) + "\n"


# --------------------------------------------------------------------------- ana akış


def main(argv=None) -> int:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(here.parent / "graph"), help="çıktı klasörü")
    ap.add_argument("--wait", type=float, default=30.0, help="graf keşfi için en çok bekleme (s)")
    ap.add_argument("--rate-window", type=float, default=3.0, help="Hz ölçüm penceresi (s)")
    ap.add_argument(
        "--expect",
        default="supervisor,trajectory_planner,delta_state_publisher,robot_state_publisher",
        help="görünmesi beklenen düğümler (virgülle)",
    )
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rclpy.init()
    node = rclpy.create_node(PROBE_NAME)
    try:
        expect = [e for e in args.expect.split(",") if e]
        nodes = wait_for_graph(node, args.wait, expect)
        names = {n for n, _ in nodes}
        missing = [e for e in expect if e not in names]
        if missing:
            print(f"HATA: beklenen düğümler yok: {missing} (görünen: {sorted(names)})")
            return 1
        graph = collect(node, nodes)
        topics = {t: ty for g in graph.values() for t, ty in g["yayin"] + g["abone"]}
        pub_qos = publisher_qos(node, sorted(topics))
        sub_qos = subscriber_qos(node, sorted(topics))
        published = {t: ty for g in graph.values() for t, ty in g["yayin"]}
        rates = measure_rates(node, published, args.rate_window)
    finally:
        node.destroy_node()
        rclpy.try_shutdown()

    interfaces = build_interfaces(graph, rates, pub_qos)
    data = {
        "tarih": datetime.now(UTC).astimezone().isoformat(timespec="seconds"),
        "mermaid": build_mermaid(graph, interfaces),
        "dugumler": build_nodes(graph, rates, pub_qos, sub_qos),
        "arayuzler": interfaces,
    }
    (out / "ros_graph.json").write_text(to_json_prettier(data), encoding="utf-8")
    dot = build_dot(graph, interfaces)
    (out / "ros_graph.dot").write_text(dot, encoding="utf-8")
    try:
        subprocess.run(
            ["dot", "-Tsvg", "-o", str(out / "ros_graph.svg"), str(out / "ros_graph.dot")],
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"UYARI: svg çizilemedi ({e}); graphviz kurulu mu?")
    kinds = {k: sum(1 for e in interfaces if e["tur"] == k) for k in ("topic", "service", "action")}
    print(
        f"{len(graph)} düğüm, {kinds['topic']} konu, {kinds['service']} servis, "
        f"{kinds['action']} eylem -> {out}"
    )
    print("düğümler:", ", ".join(sorted(graph)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
