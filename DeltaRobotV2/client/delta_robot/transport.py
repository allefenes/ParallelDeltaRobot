"""Taşımalar: HTTPS (httpx) ve stdio satır protokolü (sandbox); ikisi de aynı `call` arayüzünde."""

from __future__ import annotations

import json
import sys
import threading
from typing import IO, Any, Protocol

import httpx

from .errors import DeltaError, error_from_code, error_from_status

API_PREFIX = "/api/v1"
STDIO_PREFIX = "\x1eDELTA "

# Yöntem adı -> (HTTP yöntemi, REST yolu). stdio yöntem adlarıyla birebir aynıdır.
ROUTES: dict[str, tuple[str, str]] = {
    "robot": ("GET", "/robot"),
    "state": ("GET", "/state"),
    "move": ("POST", "/move"),
    "magnet": ("POST", "/magnet"),
    "torque": ("POST", "/torque"),
    "stop": ("POST", "/stop"),
}


class Transport(Protocol):
    """Robot komutlarını taşıyan en küçük arayüz."""

    def call(
        self, method: str, params: dict[str, Any] | None = None, *, timeout: float | None = None
    ) -> dict[str, Any]: ...

    def close(self) -> None: ...


def _route(method: str) -> tuple[str, str]:
    try:
        return ROUTES[method]
    except KeyError:
        raise ValueError(f"bilinmeyen yöntem: {method}") from None


class HttpTransport:
    """REST uç noktalarına HTTPS ile bağlanır."""

    def __init__(
        self,
        url: str,
        token: str | None,
        verify: Any,
        timeout: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.timeout = timeout
        self._client = httpx.Client(
            base_url=url.rstrip("/") + API_PREFIX,
            headers=headers,
            verify=verify,
            timeout=timeout,
            transport=transport,
        )

    def call(
        self, method: str, params: dict[str, Any] | None = None, *, timeout: float | None = None
    ) -> dict[str, Any]:
        verb, path = _route(method)
        kwargs: dict[str, Any] = {}
        if timeout is not None:
            kwargs["timeout"] = timeout
        if verb == "POST":
            kwargs["json"] = params or {}
        try:
            resp = self._client.request(verb, path, **kwargs)
        except httpx.HTTPError as exc:
            raise DeltaError(f"bağlantı hatası: {exc}", code="connection") from exc
        try:
            body = resp.json()
        except ValueError:
            body = None
        if resp.status_code >= 400:
            payload = body if isinstance(body, dict) else {"message": resp.text}
            raise error_from_status(resp.status_code, payload)
        if not isinstance(body, dict):
            raise DeltaError("sunucu geçersiz yanıt döndü", status=resp.status_code)
        return body

    def close(self) -> None:
        self._client.close()


class StdioTransport:
    """Sandbox içinde koşucuyla `\\x1eDELTA {json}` satırlarıyla konuşur."""

    def __init__(self, stdin: IO[str] | None = None, stdout: IO[str] | None = None) -> None:
        # Kullanıcı sys.stdout'u değiştirse de protokol asıl akışlardan gider.
        self._in = stdin if stdin is not None else sys.__stdin__
        self._out = stdout if stdout is not None else sys.__stdout__
        self._next_id = 1
        self._lock = threading.Lock()

    def call(
        self, method: str, params: dict[str, Any] | None = None, *, timeout: float | None = None
    ) -> dict[str, Any]:
        _route(method)
        if self._in is None or self._out is None:
            raise DeltaError("stdio akışları yok", code="connection")
        with self._lock:
            req_id = self._next_id
            self._next_id += 1
            msg = {"id": req_id, "method": method, "params": params or {}}
            self._out.write(STDIO_PREFIX + json.dumps(msg, allow_nan=False) + "\n")
            self._out.flush()
            return self._read_response(req_id)

    def _read_response(self, req_id: int) -> dict[str, Any]:
        while True:
            line = self._in.readline()
            if not line:
                raise DeltaError("koşucu bağlantısı kapandı", code="connection")
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError as exc:
                raise DeltaError(f"geçersiz yanıt satırı: {line[:80]}") from exc
            # Eski ya da başka isteğe ait yanıtlar atlanır.
            if not isinstance(msg, dict) or msg.get("id") != req_id:
                continue
            if "error" in msg:
                err = msg["error"] if isinstance(msg["error"], dict) else {"message": msg["error"]}
                raise error_from_code(err)
            result = msg.get("result")
            if not isinstance(result, dict):
                raise DeltaError("yanıtta result nesnesi yok")
            return result

    def close(self) -> None:
        pass
