"""Ortak test araçları: ortam temizliği ve sahte HTTP sunucusu."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from typing import Any

import httpx
import pytest

from delta_robot import Robot

ENV_VARS = ("DELTA_URL", "DELTA_TOKEN", "DELTA_CA_FILE", "DELTA_TRANSPORT")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


class FakeServer:
    """httpx.MockTransport arkasında yol -> yanıt eşlemesi; gelen istekleri kaydeder."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.routes: dict[tuple[str, str], Callable[[httpx.Request], httpx.Response]] = {}

    def on(self, method: str, path: str, status: int = 200, body: Any = None) -> None:
        self.routes[(method, "/api/v1" + path)] = lambda _req: httpx.Response(status, json=body)

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        route = self.routes.get((request.method, request.url.path))
        if route is None:
            return httpx.Response(404, json={"error": "not_found", "message": "yok"})
        return route(request)

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]

    def last_json(self) -> Any:
        return json.loads(self.last.content)


@pytest.fixture
def server() -> FakeServer:
    return FakeServer()


@pytest.fixture
def robot(server: FakeServer) -> Iterator[Robot]:
    r = Robot(
        "https://robot.test:8000",
        token="tok",
        _http_transport=httpx.MockTransport(server.handler),
    )
    yield r
    r.close()
