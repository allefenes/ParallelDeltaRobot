"""Tek bir işin yaşam döngüsü: konteyneri başlat, akışları ayır, sınırları uygula."""

from __future__ import annotations

import asyncio
import codecs
import contextlib
import logging
import secrets
from collections.abc import Awaitable, Callable
from typing import Any

from . import dockerargs
from .config import Config
from .protocol import (
    Output,
    OutputBudget,
    RpcInvalid,
    RpcRequest,
    StdoutDemux,
    encode_rpc_reply,
    encode_start,
    error_body,
    exit_message,
    rpc_message,
    stream_message,
)

log = logging.getLogger(__name__)

Send = Callable[[dict[str, Any]], Awaitable[None]]
READ_CHUNK = 64 * 1024
# Konteynere giden (stdin) yazılmamış veri sınırı. Okuyucu hiçbir zaman stdin'e yazmayı BEKLEMEZ:
# kullanıcı kodu stdin'i okumazsa yanıtlar burada birikir; sınır aşılınca iş durdurulur. Aksi hâlde
# stdout okuyucusu durur, docker istemcisi ve Docker daemon'ının akış kopyası tıkanır ve konteyner
# kill/rm ile bile silinemez hâle gelir (G11 bulgusu, RPC seli testi).
STDIN_BUFFER_LIMIT = 256 * 1024
DOCKER_CMD_TIMEOUT_S = 30.0


async def run_docker(argv: list[str], timeout: float = DOCKER_CMD_TIMEOUT_S) -> tuple[int, bytes]:
    """Kısa bir docker komutu çalıştırır; (çıkış kodu, stdout) döner. Zaman aşımında öldürülür."""
    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout)
    except TimeoutError:
        proc.kill()
        await proc.wait()
        return -1, b""
    return proc.returncode if proc.returncode is not None else -1, out


async def remove_stale_jobs(config: Config) -> int:
    """Etiketli tüm iş konteynerlerini siler (tek iş kuralı: çalışan iş yokken hepsi artıktır)."""
    code, out = await run_docker(dockerargs.build_list_jobs_argv(config))
    ids = out.decode().split() if code == 0 else []
    for cid in ids:
        await run_docker(dockerargs.build_rm_argv(config, cid))
    return len(ids)


class Job:
    """Bir kod çalıştırması. `run()` bitene kadar `rpc_result` ve `cancel` çağrılabilir."""

    def __init__(
        self, job_id: str, code: str, config: Config, send: Send, timeout_s: float | None = None
    ) -> None:
        self.job_id = job_id
        self.code = code
        self.config = config
        # İşe özel süre (plan kotası) koşucu sınırını aşamaz.
        limit = config.limits.timeout_s
        self.timeout_s = limit if timeout_s is None else max(0.1, min(float(timeout_s), limit))
        self.name = dockerargs.container_name(job_id, secrets.token_hex(4))
        self._send_raw = send
        self._budget = OutputBudget(config.limits.output_bytes)
        self._pending: set[tuple[type, Any]] = set()
        self._reason: str | None = None
        self._stop = asyncio.Event()
        self._proc: asyncio.subprocess.Process | None = None

    # Dış olaylar

    def cancel(self, reason: str = "cancelled") -> None:
        self._request_stop(reason)

    async def rpc_result(self, msg: dict[str, Any]) -> None:
        """API yanıtını konteynere iletir; bekleyen bir isteğe ait değilse yok sayar."""
        key = (type(msg["id"]), msg["id"])
        if key not in self._pending:
            log.warning("%s: beklenmeyen rpc_result id=%r yok sayıldı", self.name, msg["id"])
            return
        self._pending.discard(key)
        if "error" in msg:
            line = encode_rpc_reply(msg["id"], error=msg["error"])
        else:
            line = encode_rpc_reply(msg["id"], result=msg["result"])
        await self._write_stdin(line)

    # Çalıştırma

    async def run(self) -> dict[str, Any]:
        """Konteyneri çalıştırır, `exit` mesajını gönderir ve döndürür."""
        if len(self.code.encode()) > self.config.max_code_bytes:
            await self._send(stream_message("stderr", "sandbox: kod boyut sınırını aşıyor\n"))
            return await self._finish(-1, "error")
        argv = dockerargs.build_run_argv(self.config, self.job_id, self.name)
        log.info("%s: başlatılıyor", self.name)
        try:
            self._proc = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            log.error("%s: docker çalıştırılamadı: %s", self.name, exc)
            return await self._finish(-1, "error")
        proc = self._proc
        try:
            await self._write_stdin(encode_start(self.code))
            pump = asyncio.create_task(self._pump(proc))
            stop = asyncio.create_task(self._stop.wait())
            try:
                done, _ = await asyncio.wait(
                    {pump, stop}, timeout=self.timeout_s, return_when=asyncio.FIRST_COMPLETED
                )
                if pump not in done:
                    if stop not in done:
                        self._request_stop("timeout")
                    await self._remove_container()
                    try:
                        await asyncio.wait_for(asyncio.shield(pump), self.config.kill_grace_s)
                    except TimeoutError:
                        log.error("%s: docker run istemcisi çıkmadı, öldürülüyor", self.name)
                        with contextlib.suppress(ProcessLookupError):
                            proc.kill()
                        await pump
            finally:
                stop.cancel()
                if not pump.done():
                    pump.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await pump
        finally:
            if proc.returncode is None:
                with contextlib.suppress(ProcessLookupError):
                    proc.kill()
                await proc.wait()
            # Kural: iş nasıl biterse bitsin konteyner kalmaz (--rm'e ek güvence).
            await self._remove_container()
        exit_code = proc.returncode if proc.returncode is not None else -1
        reason = self._reason or ("ok" if exit_code == 0 else "error")
        log.info("%s: bitti exit_code=%s reason=%s", self.name, exit_code, reason)
        return await self._finish(exit_code, reason)

    async def _finish(self, exit_code: int, reason: str) -> dict[str, Any]:
        msg = exit_message(exit_code, reason)
        await self._send(msg)
        return msg

    async def _pump(self, proc: asyncio.subprocess.Process) -> None:
        assert proc.stdout is not None and proc.stderr is not None
        await asyncio.gather(self._read_stdout(proc.stdout), self._read_stderr(proc.stderr))
        await proc.wait()

    def _within_budget(self, chunk: bytes) -> bytes:
        allowed = self._budget.take(len(chunk))
        if self._budget.exceeded:
            self._request_stop("output_limit")
        return chunk[:allowed]

    async def _read_stdout(self, stream: asyncio.StreamReader) -> None:
        demux = StdoutDemux()
        while chunk := await stream.read(READ_CHUNK):
            if self._stopping:
                continue  # durduruldu: yalnız boşalt, iletme
            for ev in demux.feed(self._within_budget(chunk)):
                await self._handle(ev)
        if not self._stopping:
            for ev in demux.close():
                await self._handle(ev)

    async def _read_stderr(self, stream: asyncio.StreamReader) -> None:
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        while chunk := await stream.read(READ_CHUNK):
            if self._stopping:
                continue
            text = decoder.decode(self._within_budget(chunk))
            if text:
                await self._send(stream_message("stderr", text))
        tail = decoder.decode(b"", final=True)
        if tail and not self._stopping:
            await self._send(stream_message("stderr", tail))

    async def _handle(self, ev: Output | RpcRequest | RpcInvalid) -> None:
        if isinstance(ev, Output):
            await self._send(stream_message("stdout", ev.data))
        elif isinstance(ev, RpcRequest):
            key = (type(ev.id), ev.id)
            if key in self._pending:
                await self._reply_error(ev.id, "bad_request", "bu kimlikle bekleyen istek var")
            elif len(self._pending) >= self.config.max_pending_rpc:
                # Yanıt beklemeden istek seli: kötüye kullanım, iş durdurulur (yanıt yazılmaz).
                self._request_stop("output_limit")
            else:
                self._pending.add(key)
                await self._send(rpc_message(ev))
        elif ev.id is not None:
            await self._reply_error(ev.id, "bad_request", ev.message)
        else:
            await self._send(stream_message("stderr", f"sandbox: {ev.message}\n"))

    async def _reply_error(self, req_id: Any, code: str, message: str) -> None:
        await self._write_stdin(encode_rpc_reply(req_id, error=error_body(code, message)))

    async def _write_stdin(self, data: bytes) -> None:
        """Bloklamadan yazar; tampon STDIN_BUFFER_LIMIT'i aşarsa iş durdurulur (drain beklenmez)."""
        proc = self._proc
        if proc is None or proc.stdin is None or proc.stdin.is_closing():
            return
        try:
            proc.stdin.write(data)
        except (BrokenPipeError, ConnectionResetError, RuntimeError):
            return  # konteyner çıktı; okuyucular sonucu görecek
        if proc.stdin.transport.get_write_buffer_size() > STDIN_BUFFER_LIMIT:
            log.warning("%s: kullanıcı kodu stdin okumuyor, durduruluyor", self.name)
            self._request_stop("output_limit")

    async def _send(self, msg: dict[str, Any]) -> None:
        try:
            await self._send_raw(msg)
        except Exception as exc:  # API bağlantısı koptu: iş durdurulur
            log.warning("%s: API'ye gönderilemedi (%s), iptal", self.name, exc)
            self._request_stop("cancelled")

    @property
    def _stopping(self) -> bool:
        return self._stop.is_set()

    def _request_stop(self, reason: str) -> None:
        if self._reason is None:
            self._reason = reason
        self._stop.set()

    async def _remove_container(self) -> None:
        """Önce stdin kapanır (daemon'ın akış kopyası tıkanmasın), sonra SIGKILL ve rm -f."""
        proc = self._proc
        if proc is not None and proc.stdin is not None and not proc.stdin.is_closing():
            with contextlib.suppress(Exception):
                proc.stdin.close()
        await run_docker(dockerargs.build_kill_argv(self.config, self.name))
        await run_docker(dockerargs.build_rm_argv(self.config, self.name))
