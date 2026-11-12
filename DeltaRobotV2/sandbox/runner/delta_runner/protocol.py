"""Mesaj biçimleri ve ayrıştırıcılar (api.md: stdio satır protokolü, Koşucu ↔ API).

Konteyner stdout'u bayt olarak gelir; `StdoutDemux` satırları `\\x1eDELTA ` önekine göre RPC
isteği ya da kullanıcı çıktısı olarak ayırır. Ağ ya da süreç kodu içermez.
"""

from __future__ import annotations

import codecs
import json
from dataclasses import dataclass
from typing import Any

RPC_PREFIX = b"\x1eDELTA "
RPC_METHODS = frozenset(
    {"robot", "state", "move", "magnet", "torque", "stop", "board", "board_reset"}
)
EXIT_REASONS = frozenset({"ok", "timeout", "output_limit", "cancelled", "error"})
MAX_LINE_BYTES = 64 * 1024
MAX_ID_LEN = 64

RpcId = int | str


class ProtocolError(ValueError):
    """API'den gelen mesaj sözleşmeye uymuyor."""


@dataclass(frozen=True)
class Output:
    """Kullanıcı çıktısı (stdout)."""

    data: str


@dataclass(frozen=True)
class RpcRequest:
    id: RpcId
    method: str
    params: dict[str, Any]


@dataclass(frozen=True)
class RpcInvalid:
    """`\\x1eDELTA ` önekli ama geçersiz satır. Kimlik okunabildiyse `id` doludur."""

    id: RpcId | None
    message: str


Event = Output | RpcRequest | RpcInvalid


def _valid_id(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return -(2**53) <= value <= 2**53
    return isinstance(value, str) and 0 < len(value) <= MAX_ID_LEN


def _reject_constant(name: str) -> Any:
    # NaN/Infinity JSON değildir; API tarafındaki katı ayrıştırıcıları bozmasın.
    raise ValueError(name)


def parse_rpc(payload: bytes) -> RpcRequest | RpcInvalid:
    """Önekten sonraki JSON gövdesini çözer."""
    try:
        msg = json.loads(payload, parse_constant=_reject_constant)
    except (ValueError, RecursionError):
        return RpcInvalid(None, "RPC satırı geçerli JSON değil")
    if not isinstance(msg, dict):
        return RpcInvalid(None, "RPC satırı nesne değil")
    req_id = msg.get("id")
    if not _valid_id(req_id):
        return RpcInvalid(None, "RPC kimliği geçersiz")
    method = msg.get("method")
    if method not in RPC_METHODS:
        return RpcInvalid(req_id, f"bilinmeyen yöntem: {str(method)[:40]!r}")
    params = msg.get("params", {})
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return RpcInvalid(req_id, "params nesne olmalı")
    return RpcRequest(req_id, method, params)


class StdoutDemux:
    """Bayt akışını olaylara böler. Tamamlanmamış satır `max_line` baytı aşarsa çıktı sayılır."""

    def __init__(self, max_line: int = MAX_LINE_BYTES) -> None:
        self._buf = bytearray()
        self._max_line = max_line
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")

    def feed(self, chunk: bytes) -> list[Event]:
        self._buf += chunk
        events: list[Event] = []
        start = 0
        while True:
            nl = self._buf.find(b"\n", start)
            if nl < 0:
                break
            self._line(bytes(self._buf[start : nl + 1]), events)
            start = nl + 1
        del self._buf[:start]
        if len(self._buf) > self._max_line:
            self._text(bytes(self._buf), events)
            self._buf.clear()
        return _coalesce(events)

    def close(self) -> list[Event]:
        """Akış bitti: yarım kalan satır (önekli olsa bile) çıktıdır."""
        events: list[Event] = []
        if self._buf:
            self._text(bytes(self._buf), events)
            self._buf.clear()
        tail = self._decoder.decode(b"", final=True)
        if tail:
            events.append(Output(tail))
        return _coalesce(events)

    def _line(self, line: bytes, events: list[Event]) -> None:
        # Önek satır ortasında da olabilir: kullanıcı `print(..., end="")` sonrası istemci çağırdı.
        idx = line.find(RPC_PREFIX)
        if idx < 0:
            self._text(line, events)
            return
        if idx > 0:
            self._text(line[:idx], events)
        events.append(parse_rpc(line[idx + len(RPC_PREFIX) :].rstrip(b"\r\n")))

    def _text(self, data: bytes, events: list[Event]) -> None:
        text = self._decoder.decode(data)
        if text:
            events.append(Output(text))


def _coalesce(events: list[Event]) -> list[Event]:
    out: list[Event] = []
    for ev in events:
        if isinstance(ev, Output) and out and isinstance(out[-1], Output):
            out[-1] = Output(out[-1].data + ev.data)
        else:
            out.append(ev)
    return out


class OutputBudget:
    """stdout+stderr bayt sayacı. `take` izin verilen kadarını döndürür; aşım kalıcıdır."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.used = 0
        self.exceeded = False

    def take(self, n: int) -> int:
        allowed = max(0, min(n, self.limit - self.used))
        self.used += allowed
        if allowed < n:
            self.exceeded = True
        return allowed


# Konteyner stdin'ine giden satırlar


def encode_start(code: str) -> bytes:
    return (json.dumps({"code": code}) + "\n").encode()


def encode_rpc_reply(req_id: RpcId, *, result: Any = None, error: Any = None) -> bytes:
    body: dict[str, Any] = {"id": req_id}
    if error is not None:
        body["error"] = error
    else:
        body["result"] = result
    return (json.dumps(body) + "\n").encode()


def error_body(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


# API -> koşucu


def parse_api_message(text: str | bytes) -> dict[str, Any]:
    """API mesajını doğrular; sözleşme dışı mesajda `ProtocolError`."""
    try:
        msg = json.loads(text, parse_constant=_reject_constant)
    except (ValueError, RecursionError) as exc:
        raise ProtocolError("geçerli JSON değil") from exc
    if not isinstance(msg, dict):
        raise ProtocolError("mesaj nesne değil")
    kind = msg.get("type")
    if kind == "start":
        for key in ("job_id", "code", "secret"):
            if not isinstance(msg.get(key), str):
                raise ProtocolError(f"start: {key} metin olmalı")
        if not msg["job_id"]:
            raise ProtocolError("start: job_id boş")
    elif kind == "rpc_result":
        if not _valid_id(msg.get("id")):
            raise ProtocolError("rpc_result: id geçersiz")
        if ("result" in msg) == ("error" in msg):
            raise ProtocolError("rpc_result: result ya da error'dan tam biri olmalı")
        if "error" in msg and not isinstance(msg["error"], dict):
            raise ProtocolError("rpc_result: error nesne olmalı")
    elif kind != "cancel":
        raise ProtocolError(f"bilinmeyen tür: {str(kind)[:40]!r}")
    return msg


# Koşucu -> API


def rpc_message(req: RpcRequest) -> dict[str, Any]:
    return {"type": "rpc", "id": req.id, "method": req.method, "params": req.params}


def stream_message(kind: str, data: str) -> dict[str, Any]:
    if kind not in ("stdout", "stderr"):
        raise ValueError(kind)
    return {"type": kind, "data": data}


def exit_message(exit_code: int, reason: str) -> dict[str, Any]:
    if reason not in EXIT_REASONS:
        raise ValueError(reason)
    return {"type": "exit", "exit_code": exit_code, "reason": reason}
