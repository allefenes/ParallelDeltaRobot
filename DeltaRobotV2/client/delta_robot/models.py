"""API yanıtlarının veri sınıfları. Bilinmeyen alanlar `raw` içinde korunur."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _vec(value: Any) -> tuple[float, ...] | None:
    if value is None:
        return None
    return tuple(float(v) for v in value)


@dataclass(frozen=True)
class State:
    """Robot durumu (`GET /state` ve telemetri `state` iletisi)."""

    state: str
    angles_deg: tuple[float, ...] | None = None
    position_mm: tuple[float, ...] | None = None  # P noktası; çözümsüzse None
    magnet: bool = False
    temps_c: tuple[float, ...] | None = None
    loads: tuple[float, ...] | None = None
    voltages: tuple[float, ...] | None = None
    trajectory_id: str | None = None
    edge_connected: bool = False
    job_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> State:
        return cls(
            state=str(data.get("state", "DISCONNECTED")),
            angles_deg=_vec(data.get("angles_deg")),
            position_mm=_vec(data.get("position_mm")),
            magnet=bool(data.get("magnet", False)),
            temps_c=_vec(data.get("temps_c")),
            loads=_vec(data.get("loads")),
            voltages=_vec(data.get("voltages")),
            trajectory_id=data.get("trajectory_id"),
            edge_connected=bool(data.get("edge_connected", False)),
            job_id=data.get("job_id"),
            raw=dict(data),
        )


@dataclass(frozen=True)
class MoveResult:
    """Hareket sonucu (`POST /move`). Kapı reddi `accepted=False` ile gelir."""

    accepted: bool
    trajectory_id: str | None = None
    done: bool | None = None
    position_mm: tuple[float, ...] | None = None
    requirement: str | None = None
    reason: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MoveResult:
        done = data.get("done")
        return cls(
            accepted=bool(data.get("accepted", False)),
            trajectory_id=data.get("trajectory_id"),
            done=None if done is None else bool(done),
            position_mm=_vec(data.get("position_mm")),
            requirement=data.get("requirement"),
            reason=data.get("reason"),
            raw=dict(data),
        )


@dataclass(frozen=True)
class Event:
    """Süpervizör olayı (telemetri `event` iletisi)."""

    accepted: bool
    requirement: str | None = None
    reason: str | None = None
    trajectory_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Event:
        return cls(
            accepted=bool(data.get("accepted", False)),
            requirement=data.get("requirement"),
            reason=data.get("reason"),
            trajectory_id=data.get("trajectory_id"),
            raw=dict(data),
        )
