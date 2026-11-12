"""WS telemetri akışı: sahte bağlantı işleviyle, gerçek sunucu olmadan."""

from __future__ import annotations

import json
import ssl
from contextlib import contextmanager

import pytest
from websockets.datastructures import Headers
from websockets.exceptions import ConnectionClosedError, InvalidStatus
from websockets.http11 import Response

from delta_robot import AuthError, DeltaError, Event, Robot, State


def fake_connect(messages, calls, error=None):
    @contextmanager
    def connect(uri, **kwargs):
        calls.append((uri, kwargs))

        def frames():
            yield from messages
            if error is not None:
                raise error

        yield frames()

    return connect


def make(url="https://robot.test:8000", token="t k", messages=(), error=None, **kwargs):
    calls = []
    robot = Robot(url, token=token, _ws_connect=fake_connect(messages, calls, error), **kwargs)
    return robot, calls


STATE_MSG = json.dumps({"type": "state", "state": "MOVING", "position_mm": [1, 2, -200]})
EVENT_MSG = json.dumps({"type": "event", "accepted": False, "requirement": "G2", "reason": "r"})


def test_states_only_by_default():
    robot, calls = make(messages=[STATE_MSG, EVENT_MSG, "garbage", "[1]", STATE_MSG])
    items = list(robot.telemetry())
    assert len(items) == 2
    assert all(isinstance(s, State) for s in items)
    assert items[0].state == "MOVING"
    assert "type" not in items[0].raw
    uri, kwargs = calls[0]
    assert uri == "wss://robot.test:8000/api/v1/ws/telemetry?token=t+k"
    assert isinstance(kwargs["ssl"], ssl.SSLContext)
    assert kwargs["open_timeout"] == 10.0


def test_events_included_on_request():
    robot, _ = make(messages=[EVENT_MSG, STATE_MSG])
    items = list(robot.telemetry(events=True))
    assert isinstance(items[0], Event)
    assert (items[0].accepted, items[0].requirement, items[0].reason) == (False, "G2", "r")
    assert isinstance(items[1], State)


def test_plain_ws_without_token():
    robot, calls = make(url="http://localhost:8000", token=None)
    assert list(robot.telemetry()) == []
    uri, kwargs = calls[0]
    assert uri == "ws://localhost:8000/api/v1/ws/telemetry"
    assert kwargs["ssl"] is None


def test_verify_false_disables_check():
    robot, calls = make(verify=False)
    list(robot.telemetry())
    ctx = calls[0][1]["ssl"]
    assert ctx.verify_mode == ssl.CERT_NONE and ctx.check_hostname is False


def test_custom_ssl_context_is_reused():
    ctx = ssl.create_default_context()
    robot, calls = make(verify=ctx)
    list(robot.telemetry())
    assert calls[0][1]["ssl"] is ctx


def test_handshake_401_maps_to_auth_error():
    body = json.dumps({"error": "unauthorized", "message": "geçersiz belirteç"}).encode()
    error = InvalidStatus(Response(401, "Unauthorized", Headers(), body))

    @contextmanager
    def connect(uri, **kwargs):
        raise error
        yield  # pragma: no cover

    robot = Robot("https://x", token="bad", _ws_connect=connect)
    with pytest.raises(AuthError, match="geçersiz belirteç"):
        list(robot.telemetry())


def test_handshake_non_json_body():
    error = InvalidStatus(Response(500, "Err", Headers(), b"oops"))

    @contextmanager
    def connect(uri, **kwargs):
        raise error
        yield  # pragma: no cover

    robot = Robot("https://x", _ws_connect=connect)
    with pytest.raises(DeltaError) as info:
        list(robot.telemetry())
    assert info.value.status == 500


def test_abnormal_close():
    robot, _ = make(messages=[STATE_MSG], error=ConnectionClosedError(None, None))
    it = robot.telemetry()
    assert isinstance(next(it), State)
    with pytest.raises(DeltaError, match="koptu"):
        next(it)


def test_os_error():
    robot, _ = make(error=ConnectionRefusedError("refused"))
    with pytest.raises(DeltaError) as info:
        list(robot.telemetry())
    assert info.value.code == "connection"


def test_default_connect_is_websockets(monkeypatch):
    import websockets.sync.client as ws_client

    calls = []
    monkeypatch.setattr(ws_client, "connect", fake_connect([STATE_MSG], calls))
    robot = Robot("https://x")
    assert len(list(robot.telemetry())) == 1
    assert calls[0][0] == "wss://x/api/v1/ws/telemetry"
