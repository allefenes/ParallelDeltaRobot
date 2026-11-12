"""`Robot` sınıfı: docs/api.md "Python istemcisi" bölümünün uygulaması."""

from __future__ import annotations

import json
import math
import numbers
import os
import ssl
from collections.abc import Callable, Iterator
from typing import Any
from urllib.parse import urlencode, urlsplit, urlunsplit

from .errors import CommandRejected, DeltaError, MoveNotCompleted, error_from_status
from .models import Event, MoveResult, State
from .transport import API_PREFIX, HttpTransport, StdioTransport, Transport

DEFAULT_URL = "https://localhost:8000"
DEFAULT_TIMEOUT = 10.0
# duration_s verilmezse süreyi planlayıcı seçer; bekleme için bu kadar pay bırakılır.
_PLANNER_DURATION_ALLOWANCE = 30.0
_WAIT_MARGIN = 5.0  # sözleşme: bekleme üst sınırı yörünge süresi + 5 s


def _finite(name: str, value: Any) -> float:
    """Sonlu bir sayı ister; bool, NaN ve sonsuz reddedilir."""
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise ValueError(f"{name} sayı olmalı, {type(value).__name__} verildi")
    f = float(value)
    if not math.isfinite(f):
        raise ValueError(f"{name} sonlu olmalı, {f} verildi")
    return f


def _flag(name: str, value: Any) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} bool olmalı, {type(value).__name__} verildi")
    return value


def _ssl_context(verify: Any) -> Any:
    """`verify` değerini httpx/websockets'in kabul ettiği biçime çevirir."""
    if isinstance(verify, str | os.PathLike):
        return ssl.create_default_context(cafile=os.fspath(verify))
    return verify


class Robot:
    """Delta robotun uzak istemcisi.

    Taşıma `DELTA_TRANSPORT=stdio` ise sandbox satır protokolü, değilse HTTPS'dir.
    """

    def __init__(
        self,
        url: str | None = None,
        token: str | None = None,
        verify: bool | str | os.PathLike[str] | ssl.SSLContext | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        *,
        _http_transport: Any = None,
        _stdio: tuple[Any, Any] | None = None,
        _ws_connect: Callable[..., Any] | None = None,
    ) -> None:
        self.url = (url or os.environ.get("DELTA_URL") or DEFAULT_URL).rstrip("/")
        self.token = token if token is not None else os.environ.get("DELTA_TOKEN")
        if verify is None:
            ca_file = os.environ.get("DELTA_CA_FILE")
            verify = ca_file if ca_file else True
        self.verify = _ssl_context(verify)
        self.timeout = float(timeout)
        self._ws_connect = _ws_connect

        mode = os.environ.get("DELTA_TRANSPORT", "").strip().lower()
        self.transport_name = "stdio" if (_stdio is not None or mode == "stdio") else "https"
        self._transport: Transport
        if self.transport_name == "stdio":
            stdin, stdout = _stdio if _stdio is not None else (None, None)
            self._transport = StdioTransport(stdin=stdin, stdout=stdout)
        else:
            self._transport = HttpTransport(
                self.url, self.token, self.verify, self.timeout, transport=_http_transport
            )

    # Bağlam yöneticisi
    def __enter__(self) -> Robot:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._transport.close()

    def __repr__(self) -> str:
        return f"Robot(url={self.url!r}, transport={self.transport_name!r})"

    # Sorgular
    def info(self) -> dict[str, Any]:
        """Robot tanımı (`GET /robot`): geometri, limitler, çalışma uzayı."""
        return self._transport.call("robot")

    def state(self) -> State:
        """Anlık durum (`GET /state`)."""
        return State.from_dict(self._transport.call("state"))

    # Komutlar
    def move_to(
        self,
        x: float,
        y: float,
        z: float,
        duration: float | None = None,
        wait: bool = True,
        check: bool = True,
    ) -> MoveResult:
        """P noktasını (x, y, z) mm'ye taşır.

        `check=True` iken kapı reddi `CommandRejected`, beklenen hareketin tamamlanmaması
        `MoveNotCompleted` fırlatır; `check=False` iken sonuç olduğu gibi döner.
        """
        params: dict[str, Any] = {
            "x": _finite("x", x),
            "y": _finite("y", y),
            "z": _finite("z", z),
            "duration_s": None,
            "wait": _flag("wait", wait),
        }
        if duration is not None:
            d = _finite("duration", duration)
            if d <= 0:
                raise ValueError(f"duration pozitif olmalı, {d} verildi")
            params["duration_s"] = d
        timeout = None
        if wait:
            allowance = params["duration_s"] or _PLANNER_DURATION_ALLOWANCE
            timeout = self.timeout + allowance + _WAIT_MARGIN
        result = MoveResult.from_dict(self._transport.call("move", params, timeout=timeout))
        if check:
            if not result.accepted:
                raise CommandRejected(result.requirement, result.reason, result)
            if wait and result.done is False:
                raise MoveNotCompleted(result.reason, result)
        return result

    def magnet(self, on: bool) -> bool:
        """Elektromıknatısı açar/kapatır; sunucunun bildirdiği durumu döndürür."""
        result = self._transport.call("magnet", {"on": _flag("on", on)})
        return bool(result.get("magnet", on))

    def torque(self, on: bool) -> None:
        """Motor torkunu açar/kapatır."""
        self._transport.call("torque", {"on": _flag("on", on)})

    def stop(self) -> None:
        """Robotu o anki konumda durdurur ve tutar (HOLD). Her zaman kabul edilir."""
        self._transport.call("stop", {})

    # Telemetri
    def _telemetry_uri(self) -> str:
        parts = urlsplit(self.url)
        scheme = {"https": "wss", "http": "ws"}.get(parts.scheme, parts.scheme)
        path = parts.path.rstrip("/") + API_PREFIX + "/ws/telemetry"
        query = urlencode({"token": self.token}) if self.token else ""
        return urlunsplit((scheme, parts.netloc, path, query, ""))

    def _ws_ssl(self, uri: str) -> ssl.SSLContext | None:
        if not uri.startswith("wss:"):
            return None
        if isinstance(self.verify, ssl.SSLContext):
            return self.verify
        ctx = ssl.create_default_context()
        if self.verify is False:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def telemetry(self, events: bool = False) -> Iterator[State | Event]:
        """WS telemetri akışı (20 Hz). `events=True` ise süpervizör olayları da gelir.

        Yalnız ağ taşımasında çalışır; sandbox (stdio) içinde `state()` kullanılır.
        """
        if self.transport_name == "stdio":
            raise DeltaError(
                "telemetry() yalnız ağ taşımasında kullanılabilir; sandbox içinde state() kullanın",
                code="unsupported",
            )
        uri = self._telemetry_uri()
        connect = self._ws_connect
        if connect is None:
            from websockets.sync.client import connect
        from websockets.exceptions import ConnectionClosedError, InvalidStatus

        try:
            with connect(uri, ssl=self._ws_ssl(uri), open_timeout=self.timeout) as ws:
                for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except ValueError:
                        continue
                    if not isinstance(msg, dict):
                        continue
                    kind = msg.pop("type", None)
                    if kind == "state":
                        yield State.from_dict(msg)
                    elif kind == "event" and events:
                        yield Event.from_dict(msg)
        except InvalidStatus as exc:
            status = exc.response.status_code
            body = exc.response.body or b""
            try:
                payload = json.loads(body)
            except ValueError:
                payload = {}
            raise error_from_status(status, payload if isinstance(payload, dict) else {}) from exc
        except ConnectionClosedError as exc:
            raise DeltaError(f"telemetri bağlantısı koptu: {exc}", code="connection") from exc
        except OSError as exc:
            raise DeltaError(f"telemetri bağlantı hatası: {exc}", code="connection") from exc
