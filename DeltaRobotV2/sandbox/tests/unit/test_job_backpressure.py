"""G11 bulgusu regresyonu (Docker'sız): kullanıcı kodu stdin okumazsa koşucu tıkanmamalı.

Bulgu: RPC seli testinde koşucunun stdout okuyucusu stdin'e yanıt yazarken `drain()` bekleyip
durdu; docker istemcisi ve daemon'ın akış kopyası tıkandı, konteyner kill/rm ile silinemedi.
Burada sahte bir `docker` ikilisi aynı davranışı (stdin okumadan sınırsız RPC) üretir.
"""

from __future__ import annotations

import asyncio
import os
import stat
import sys
import textwrap
import time

import pytest
from delta_runner import job as job_mod
from delta_runner.config import Config, Limits
from delta_runner.job import Job

FAKE_DOCKER = textwrap.dedent(
    """\
    #!{python}
    import json, os, signal, sys, time
    pidfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run.pid")
    cmd = sys.argv[1]
    if cmd == "run":
        open(pidfile, "w").write(str(os.getpid()))
        mode = os.environ.get("FAKE_MODE", "flood")
        i = 0
        while True:
            i += 1
            if mode == "flood" or i <= {burst}:
                req = json.dumps({{"id": i, "method": "state"}})
                sys.stdout.write("\\x1eDELTA " + req + "\\n")
                sys.stdout.flush()
            else:
                time.sleep(0.05)
    elif cmd in ("kill", "rm"):
        try:
            os.kill(int(open(pidfile).read()), signal.SIGKILL)
        except (OSError, ValueError):
            pass
    """
)


@pytest.fixture
def fake_docker(tmp_path, monkeypatch):
    def make(mode: str, burst: int = 8) -> Config:
        path = tmp_path / "docker"
        path.write_text(FAKE_DOCKER.format(python=sys.executable, burst=burst))
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        monkeypatch.setenv("FAKE_MODE", mode)
        return Config(docker=str(path), limits=Limits(timeout_s=20.0), kill_grace_s=2.0)

    return make


def run_job(config: Config, api_reply: bool) -> tuple[dict, float, list[dict]]:
    sent: list[dict] = []

    async def main():
        holder: dict = {}

        async def send(msg):
            sent.append(msg)
            if api_reply and msg.get("type") == "rpc":
                # API her isteğe büyük bir yanıt verir; kullanıcı kodu stdin'i hiç okumaz.
                asyncio.get_running_loop().call_soon(
                    asyncio.ensure_future,
                    holder["job"].rpc_result({"id": msg["id"], "result": {"pad": "x" * 60000}}),
                )

        j = Job("bp", "pass", config, send)
        holder["job"] = j
        t0 = time.monotonic()
        res = await asyncio.wait_for(j.run(), 15)
        return res, time.monotonic() - t0

    res, dt = asyncio.run(main())
    return res, dt, sent


@pytest.mark.skipif(os.name != "posix", reason="sahte docker POSIX betiği")
def test_G11_rpc_flood_without_reading_stdin_stops_job(fake_docker):
    res, dt, sent = run_job(fake_docker("flood"), api_reply=False)
    assert res["reason"] == "output_limit"
    assert dt < 10
    assert sum(1 for m in sent if m["type"] == "rpc") <= 16


@pytest.mark.skipif(os.name != "posix", reason="sahte docker POSIX betiği")
def test_G11_unread_replies_do_not_block_reader(fake_docker, monkeypatch):
    # Az istek, büyük yanıtlar: stdin tamponu sınırı aşınca iş durur; okuyucu asla beklemez.
    monkeypatch.setattr(job_mod, "STDIN_BUFFER_LIMIT", 100_000)
    res, dt, _ = run_job(fake_docker("burst", burst=8), api_reply=True)
    assert res["reason"] == "output_limit"
    assert dt < 10
