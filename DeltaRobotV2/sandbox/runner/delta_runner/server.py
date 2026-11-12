"""WebSocket sunucusu `ws://0.0.0.0:8100/run` (api.md, Koşucu ↔ API). Aynı anda tek iş."""

from __future__ import annotations

import asyncio
import contextlib
import hmac
import json
import logging
import os
from typing import Any

from websockets.asyncio.server import ServerConnection, serve
from websockets.exceptions import ConnectionClosed
from websockets.http11 import Request, Response

from . import dockerargs
from .config import Config, config_from_env
from .job import Job, remove_stale_jobs, run_docker
from .protocol import ProtocolError, exit_message, parse_api_message, stream_message

log = logging.getLogger(__name__)

RUN_PATH = "/run"
START_TIMEOUT_S = 10.0
MAX_MESSAGE_BYTES = 256 * 1024  # kod ≤ 64 KB; JSON kaçışları için pay
CLOSE_POLICY = 1008
CLOSE_TRY_AGAIN = 1013


class Runner:
    """Bağlantı başına bir iş; meşgulken gelen iş `exit/error` ile reddedilir."""

    def __init__(self, config: Config, secret: str) -> None:
        if not secret:
            raise ValueError("DELTA_RUNNER_SECRET boş olamaz")
        self.config = config
        self._secret = secret.encode()
        self._busy = False

    def process_request(self, connection: ServerConnection, request: Request) -> Response | None:
        if request.path.split("?", 1)[0] != RUN_PATH:
            return connection.respond(404, "not found\n")
        return None

    def _authorized(self, secret: str) -> bool:
        return hmac.compare_digest(secret.encode(), self._secret)

    async def handle(self, ws: ServerConnection) -> None:
        try:
            raw = await asyncio.wait_for(ws.recv(), START_TIMEOUT_S)
            start = parse_api_message(raw)
        except (TimeoutError, ProtocolError, ConnectionClosed):
            await ws.close(CLOSE_POLICY, "start bekleniyordu")
            return
        if start["type"] != "start" or not self._authorized(start["secret"]):
            log.warning("yetkisiz ya da geçersiz başlangıç: %s", ws.remote_address)
            await ws.close(CLOSE_POLICY, "unauthorized")
            return
        if self._busy:
            await _send(ws, stream_message("stderr", "sandbox: koşucu meşgul\n"))
            await _send(ws, exit_message(-1, "error"))
            await ws.close(CLOSE_TRY_AGAIN, "busy")
            return
        self._busy = True
        try:
            await self._run_job(ws, start)
        finally:
            self._busy = False

    async def _run_job(self, ws: ServerConnection, start: dict[str, Any]) -> None:
        await remove_stale_jobs(self.config)
        job = Job(start["job_id"], start["code"], self.config, lambda m: _send(ws, m))
        run = asyncio.create_task(job.run())
        recv = asyncio.create_task(_receive(ws, job))
        try:
            await asyncio.wait({run, recv}, return_when=asyncio.FIRST_COMPLETED)
            if not run.done():
                job.cancel()  # API bağlantısı koptu
            await run
        finally:
            recv.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await recv
            if not run.done():
                job.cancel()
                await run
        await ws.close()


async def _receive(ws: ServerConnection, job: Job) -> None:
    try:
        async for raw in ws:
            try:
                msg = parse_api_message(raw)
            except ProtocolError as exc:
                log.warning("%s: geçersiz API mesajı: %s", job.name, exc)
                continue
            if msg["type"] == "rpc_result":
                await job.rpc_result(msg)
            elif msg["type"] == "cancel":
                job.cancel()
    except ConnectionClosed:
        pass


async def _send(ws: ServerConnection, msg: dict[str, Any]) -> None:
    await ws.send(json.dumps(msg, ensure_ascii=False, allow_nan=False))


async def check_image(config: Config) -> bool:
    code, _ = await run_docker(dockerargs.build_image_inspect_argv(config))
    return code == 0


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = config_from_env()
    runner = Runner(config, os.environ.get("DELTA_RUNNER_SECRET", ""))
    if not await check_image(config):
        raise SystemExit(f"sandbox imajı yok: {config.image} (önce docker build)")
    removed = await remove_stale_jobs(config)
    if removed:
        log.info("%d artık iş konteyneri silindi", removed)
    host = os.environ.get("DELTA_RUNNER_HOST", "0.0.0.0")
    port = int(os.environ.get("DELTA_RUNNER_PORT", "8100"))
    async with serve(
        runner.handle,
        host,
        port,
        process_request=runner.process_request,
        max_size=MAX_MESSAGE_BYTES,
    ) as server:
        log.info("koşucu dinliyor ws://%s:%d%s, sınırlar %s", host, port, RUN_PATH, config.limits)
        await server.serve_forever()
