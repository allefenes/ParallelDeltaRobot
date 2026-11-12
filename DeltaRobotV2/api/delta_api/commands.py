"""Robot komutlarının tek uygulama noktası: REST ve sandbox (stdio RPC) aynı yolu kullanır.

Parametreler burada yeniden doğrulanır; sandbox'tan gelen veri güvenilmezdir. Asıl güvenlik
kapıları ROS yığınında (1. kapı) ve Pi'dedir; buradaki denetim yalnız biçim içindir.
"""

from __future__ import annotations

import math

from delta_api.backend import Backend

METHODS = ("robot", "state", "move", "magnet", "torque", "stop", "board", "board_reset")
MAX_DURATION_S = 60.0  # süpervizörün max_duration_s değeriyle aynı


class ApiError(Exception):
    """Sözleşmedeki hata kodu + Türkçe mesaj (HTTP durumu `status`)."""

    STATUS = {"bad_request": 400, "unauthorized": 401, "not_found": 404, "busy": 409,
              "robot_unavailable": 503}  # fmt: skip

    def __init__(self, code: str, message: str, **extra) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.extra = extra

    @property
    def status(self) -> int:
        return self.STATUS.get(self.code, 400)

    def body(self) -> dict:
        return {"error": self.code, "message": self.message, **self.extra}


def _number(params: dict, key: str) -> float:
    v = params.get(key)
    if isinstance(v, bool) or not isinstance(v, int | float) or not math.isfinite(v):
        raise ApiError("bad_request", f"'{key}' sonlu bir sayı olmalı")
    return float(v)


def _flag(params: dict, key: str, default: bool | None = None) -> bool:
    v = params.get(key, default)
    if not isinstance(v, bool):
        raise ApiError("bad_request", f"'{key}' true ya da false olmalı")
    return v


async def execute(backend: Backend, method: str, params: dict | None, job_id: str | None = None):
    """Komutu çalıştırır, sözleşmedeki yanıt gövdesini döndürür; hata -> ApiError."""
    params = params or {}
    if not isinstance(params, dict):
        raise ApiError("bad_request", "params bir nesne olmalı")
    if method == "robot":
        return backend.info()
    if method == "state":
        return backend.state().to_dict(job_id)
    if method == "move":
        x, y, z = (_number(params, k) for k in ("x", "y", "z"))
        dur = params.get("duration_s")
        if dur is not None:
            dur = _number(params, "duration_s")
            if not 0 < dur <= MAX_DURATION_S:
                raise ApiError(
                    "bad_request", f"duration_s 0 ile {MAX_DURATION_S:g} s arasında olmalı"
                )
        wait = _flag(params, "wait", True)
        _require_connected(backend)
        return (await backend.move(x, y, z, dur, wait)).to_dict()
    if method == "magnet":
        on = _flag(params, "on")
        _require_connected(backend)
        if not await backend.magnet(on):
            raise ApiError("robot_unavailable", "mıknatıs komutu iletilemedi")
        return {"ok": True, "magnet": on}
    if method == "torque":
        on = _flag(params, "on")
        _require_connected(backend)
        if not await backend.torque(on):
            raise ApiError("robot_unavailable", "tork komutu iletilemedi")
        return {"ok": True}
    if method == "stop":
        if not await backend.stop():
            raise ApiError("robot_unavailable", "dur komutu iletilemedi (kenar bağlı değil)")
        return {"ok": True}
    if method == "board":
        board = backend.board()
        if board is None:
            raise ApiError("robot_unavailable", "tabla ikizi yok")
        return board
    if method == "board_reset":
        if backend.state().state == "RUNNING":
            raise ApiError("busy", "robot hareket ederken tabla sıfırlanamaz")
        if not await backend.board_reset():
            raise ApiError("robot_unavailable", "tabla sıfırlanamadı")
        return {"ok": True}
    raise ApiError("bad_request", f"bilinmeyen komut: {method}")


def _require_connected(backend: Backend) -> None:
    if backend.state().state == "DISCONNECTED":
        raise ApiError("robot_unavailable", "robot bağlı değil")
