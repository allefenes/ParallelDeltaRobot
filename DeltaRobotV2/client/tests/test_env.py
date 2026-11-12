"""Ortam değişkeni varsayılanları ve TLS doğrulama ayarı."""

from __future__ import annotations

import ssl

import httpx
import pytest

import delta_robot
from delta_robot import Robot
from delta_robot import robot as robot_mod


def ok_transport(seen: list[httpx.Request]) -> httpx.MockTransport:
    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return httpx.Response(200, json={"name": "x"})

    return httpx.MockTransport(handler)


@pytest.fixture
def fake_ssl(monkeypatch):
    calls = []
    real = ssl.create_default_context

    def fake(*args, **kwargs):
        calls.append(kwargs.get("cafile"))
        return real()

    monkeypatch.setattr(robot_mod.ssl, "create_default_context", fake)
    return calls


def test_defaults_without_env():
    r = Robot()
    assert r.url == "https://localhost:8000"
    assert r.token is None
    assert r.verify is True
    assert r.transport_name == "https"
    r.close()


def test_env_defaults(monkeypatch, fake_ssl):
    monkeypatch.setenv("DELTA_URL", "https://env.test:9000/")
    monkeypatch.setenv("DELTA_TOKEN", "env-token")
    monkeypatch.setenv("DELTA_CA_FILE", "/certs/ca.crt")
    seen: list[httpx.Request] = []
    with Robot(_http_transport=ok_transport(seen)) as r:
        r.info()
        assert r.url == "https://env.test:9000"
        assert isinstance(r.verify, ssl.SSLContext)
    assert fake_ssl == ["/certs/ca.crt"]
    assert str(seen[0].url) == "https://env.test:9000/api/v1/robot"
    assert seen[0].headers["Authorization"] == "Bearer env-token"


def test_explicit_args_override_env(monkeypatch, fake_ssl):
    monkeypatch.setenv("DELTA_URL", "https://env.test")
    monkeypatch.setenv("DELTA_TOKEN", "env-token")
    monkeypatch.setenv("DELTA_CA_FILE", "/certs/ca.crt")
    seen: list[httpx.Request] = []
    with Robot(
        "https://arg.test", token="arg", verify="ca.crt", _http_transport=ok_transport(seen)
    ):
        pass
    assert fake_ssl == ["ca.crt"]
    with Robot(
        "https://arg.test", token="arg", verify=False, _http_transport=ok_transport(seen)
    ) as r:
        r.info()
        assert r.verify is False
    assert seen[0].headers["Authorization"] == "Bearer arg"
    assert seen[0].url.host == "arg.test"


def test_empty_ca_env_means_system_store(monkeypatch):
    monkeypatch.setenv("DELTA_CA_FILE", "")
    r = Robot()
    assert r.verify is True
    r.close()


def test_version():
    assert delta_robot.__version__ == "0.1.0"
