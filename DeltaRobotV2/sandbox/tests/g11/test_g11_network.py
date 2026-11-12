"""G11 ağ: sandbox'ta yalnız geri döngü arayüzü var; DNS, TCP, UDP, kenar erişilemez."""

import pytest
from harness import probe

BLOCKED_TEMPLATE = """
import socket
try:
    {action}
    print("ALLOWED")
except OSError as e:
    print("BLOCKED", type(e).__name__, e.errno)
"""


def blocked(action: str) -> str:
    r = probe(BLOCKED_TEMPLATE.format(action=action))
    assert r.stdout.startswith("BLOCKED"), r.stdout
    return r.stdout.strip()


def test_G11_only_loopback_interface():
    r = probe("import socket; print(sorted(n for _, n in socket.if_nameindex()))")
    assert r.stdout.strip() == "['lo']"


@pytest.mark.parametrize("host", ["example.com", "server", "host.docker.internal"])
def test_G11_dns_resolution_blocked(host):
    out = blocked(f"socket.getaddrinfo({host!r}, 443)")
    assert "gaierror" in out


@pytest.mark.parametrize("addr", [("1.1.1.1", 443), ("8.8.8.8", 53), ("172.17.0.1", 2375)])
def test_G11_outbound_tcp_by_ip_blocked(addr):
    out = blocked(f"socket.create_connection({addr!r}, timeout=3)")
    assert "OSError" in out or "TimeoutError" in out


@pytest.mark.parametrize("addr", [("server", 8443), ("server", 8000), ("runner", 8100)])
def test_G11_edge_and_internal_services_unreachable(addr):
    # Kenar uç noktası wss://server:8443/edge, API ve koşucu iç ağ adlarıyla denenir.
    blocked(f"socket.create_connection({addr!r}, timeout=3)")


def test_G11_outbound_udp_blocked():
    blocked("socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(b'x', ('8.8.8.8', 53))")


def test_G11_ipv6_outbound_blocked():
    blocked("socket.create_connection(('2606:4700:4700::1111', 443), timeout=3)")


def test_G11_raw_socket_blocked():
    # CAP_NET_RAW yok: ICMP/raw paket üretilemez.
    blocked("socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)")
