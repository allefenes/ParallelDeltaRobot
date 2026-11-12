"""Kenar protokolü v1'in sunucu tarafı (saf fonksiyonlar; ROS ve ağdan bağımsız, test edilebilir).

Protokol tanımı: edge/README.md ve edge/include/delta_edge/protocol.hpp. Mesajlar JSON, `v: 1`.
ROS tarafı radyan, protokol derece kullanır.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass

PROTOCOL_VERSION = 1
MIN_PERIOD_MS = 5
MAX_PERIOD_MS = 50

# Kenar `fault.code` -> güvenlik gereksinimi (docs/guvenlik-gereksinimleri.md)
FAULT_REQUIREMENT = {
    "joint_limit": "G1",
    "parse_error": "G4",
    "non_finite": "G4",
    "velocity_limit": "G5",
    "accel_limit": "G5",
    "heartbeat_hold": "G6",
    "heartbeat_torque_off": "G7",
    "over_temperature": "G9",
    "over_load": "G9",
    "voltage": "G9",
    "estop": "G12",
}


class ProtocolError(ValueError):
    """Kenara gönderilemeyecek ya da kenardan gelen geçersiz mesaj."""


def heartbeat(seq: int) -> str:
    return json.dumps({"v": PROTOCOL_VERSION, "type": "heartbeat", "seq": int(seq)})


def command(kind: str, on: bool | None = None) -> str:
    """stop / hold / reset / torque / magnet komutları."""
    if kind not in {"stop", "hold", "reset", "torque", "magnet"}:
        raise ProtocolError(f"bilinmeyen komut: {kind}")
    msg: dict = {"v": PROTOCOL_VERSION, "type": kind}
    if kind in {"torque", "magnet"}:
        if on is None:
            raise ProtocolError(f"{kind} için 'on' gerekli")
        msg["on"] = bool(on)
    return json.dumps(msg)


def trajectory(
    traj_id: str, times_s: list[float], points_rad: list[list[float]], magnet: bool | None = None
) -> str:
    """Zaman damgalı eklem yörüngesini (radyan) protokol mesajına (derece, sabit periyot) çevirir.

    Örnekler eşit aralıklı olmalıdır (planlayıcı 100 Hz örnekler); periyot ilk iki örnekten alınır.
    """
    if not points_rad or len(points_rad) != len(times_s):
        raise ProtocolError("boş ya da zamanla uyuşmayan yörünge")
    if len(points_rad) == 1:
        period_ms = 10
    else:
        period_ms = round((times_s[1] - times_s[0]) * 1000.0)
        for a, b in zip(times_s, times_s[1:], strict=False):
            if abs((b - a) * 1000.0 - period_ms) > 0.5:
                raise ProtocolError("örnekler eşit aralıklı değil")
    if not MIN_PERIOD_MS <= period_ms <= MAX_PERIOD_MS:
        raise ProtocolError(f"periyot {period_ms} ms aralık dışında")
    pts = []
    for p in points_rad:
        if len(p) != 3 or not all(math.isfinite(v) for v in p):
            raise ProtocolError("nokta 3 sonlu açı içermeli")
        pts.append([math.degrees(v) for v in p])
    msg: dict = {
        "v": PROTOCOL_VERSION,
        "type": "trajectory",
        "id": traj_id,
        "period_ms": period_ms,
        "points": pts,
    }
    if magnet is not None:
        msg["magnet"] = bool(magnet)
    return json.dumps(msg)


@dataclass
class Telemetry:
    state: str
    angles_rad: list[float]
    temps: list[float]
    loads: list[float]
    voltages: list[float]
    traj_id: str
    index: int


def parse_incoming(text: str) -> tuple[str, object]:
    """Kenardan gelen mesaj: ("telemetry", Telemetry) | ("ack", id) | ("fault", (code, detail))."""
    try:
        msg = json.loads(text)
    except json.JSONDecodeError as e:
        raise ProtocolError(f"JSON değil: {e}") from e
    if not isinstance(msg, dict) or msg.get("v") != PROTOCOL_VERSION:
        raise ProtocolError("sürüm ya da biçim hatalı")
    kind = msg.get("type")
    if kind == "telemetry":
        try:
            angles = [math.radians(float(v)) for v in msg["angles"]]
            t = Telemetry(
                state=str(msg["state"]),
                angles_rad=angles,
                temps=[float(v) for v in msg["temps"]],
                loads=[float(v) for v in msg["loads"]],
                voltages=[float(v) for v in msg["voltages"]],
                traj_id=msg.get("traj_id") or "",
                index=int(msg.get("index", -1)),
            )
        except (KeyError, TypeError, ValueError) as e:
            raise ProtocolError(f"telemetri alanları hatalı: {e}") from e
        if len(t.angles_rad) != 3 or not all(math.isfinite(v) for v in t.angles_rad):
            raise ProtocolError("telemetri açıları geçersiz")
        return "telemetry", t
    if kind == "ack":
        return "ack", str(msg.get("id", ""))
    if kind == "fault":
        return "fault", (str(msg.get("code", "")), str(msg.get("detail", "")))
    raise ProtocolError(f"bilinmeyen mesaj tipi: {kind}")


def requirement_for(code: str) -> str:
    """Kenar arıza kodunun ilgili güvenlik gereksinimi; bilinmiyorsa "DURUM"."""
    return FAULT_REQUIREMENT.get(code, "DURUM")
