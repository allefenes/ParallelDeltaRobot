"""İş kuyruğu: web editöründeki kod sandbox koşucusunda çalışır, komutları API'ye RPC ile sorar.

Tek robot olduğu için işler sırayla çalışır; çalışan iş robotun kontrol kilidini tutar
(docs/api.md "Kontrol kilidi"). Koşucuyla bağlantı: ws://runner:8100/run (iç ağ).
"""

from __future__ import annotations

import asyncio
import datetime as dt
import itertools
import json
import uuid
from dataclasses import dataclass, field

import websockets

from delta_api.backend import Backend
from delta_api.commands import METHODS, ApiError, execute

MAX_CODE_BYTES = 64 * 1024
MAX_OUTPUT_CHARS = 64 * 1024
FINAL = ("done", "failed", "timeout", "cancelled")


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="milliseconds")


@dataclass
class Job:
    job_id: str
    code: str
    name: str | None
    owner: str
    status: str = "queued"
    exit_code: int | None = None
    output: str = ""
    reason: str | None = None
    created_at: str = field(default_factory=_now)
    started_at: str | None = None
    finished_at: str | None = None
    listeners: set = field(default_factory=set, repr=False)
    cancel_requested: bool = False

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "name": self.name,
            "status": self.status,
            "exit_code": self.exit_code,
            "output": self.output,
            "reason": self.reason,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }

    def append(self, kind: str, data: str) -> None:
        room = MAX_OUTPUT_CHARS - len(self.output)
        if room > 0:
            self.output += data[:room]
        self.broadcast({"type": kind, "data": data})

    def broadcast(self, msg: dict) -> None:
        for q in list(self.listeners):
            if not q.full():
                q.put_nowait(msg)


class JobManager:
    def __init__(self, backend: Backend, runner_url: str, runner_secret: str) -> None:
        self.backend = backend
        self.runner_url = runner_url
        self.runner_secret = runner_secret
        self.jobs: dict[str, Job] = {}
        self.queue: asyncio.Queue[Job] = asyncio.Queue()
        self.active: Job | None = None
        self._cancel_events: dict[str, asyncio.Event] = {}
        self._seq = itertools.count(1)
        self._worker: asyncio.Task | None = None

    def start(self) -> None:
        self._worker = asyncio.create_task(self._work())

    async def close(self) -> None:
        if self._worker:
            self._worker.cancel()

    @property
    def active_id(self) -> str | None:
        return self.active.job_id if self.active else None

    def submit(self, code: str, name: str | None, owner: str) -> Job:
        if not isinstance(code, str) or not code.strip():
            raise ApiError("bad_request", "kod boş")
        if len(code.encode("utf-8")) > MAX_CODE_BYTES:
            raise ApiError("bad_request", "kod 64 KB'tan büyük")
        if name is not None and (not isinstance(name, str) or len(name) > 100):
            raise ApiError("bad_request", "ad en çok 100 karakter olmalı")
        jid = f"job-{next(self._seq):04d}-{uuid.uuid4().hex[:4]}"
        job = Job(jid, code, name, owner)
        self.jobs[jid] = job
        self._cancel_events[jid] = asyncio.Event()
        self.queue.put_nowait(job)
        return job

    def get(self, jid: str) -> Job:
        job = self.jobs.get(jid)
        if job is None:
            raise ApiError("not_found", "iş bulunamadı")
        return job

    def cancel(self, jid: str) -> None:
        job = self.get(jid)
        if job.status in FINAL:
            return
        job.cancel_requested = True
        self._cancel_events[jid].set()

    async def _work(self) -> None:
        while True:
            job = await self.queue.get()
            if job.cancel_requested:
                self._finish(job, "cancelled", None, "kuyrukta iptal edildi")
                continue
            self.active = job
            try:
                await self._run(job)
            except Exception as e:  # noqa: BLE001 - iş başarısız sayılır, kuyruk sürer
                if job.status not in FINAL:
                    self._finish(job, "failed", None, f"koşucu hatası: {e}")
            finally:
                self.active = None
                # İş bitince robot güvenli duruşta kalır: yarım hareket olmaz.
                if job.status != "done":
                    try:
                        await self.backend.stop()
                    except Exception:  # noqa: BLE001
                        pass

    def _finish(self, job: Job, status: str, code: int | None, reason: str | None) -> None:
        job.status, job.exit_code, job.reason = status, code, reason
        job.finished_at = _now()
        job.broadcast({"type": "status", "status": status, "exit_code": code, "reason": reason})
        job.broadcast({"type": "_end"})

    async def _run(self, job: Job) -> None:
        cancel_ev = self._cancel_events[job.job_id]
        try:
            ws = await websockets.connect(self.runner_url, max_size=2**22, open_timeout=5)
        except (OSError, websockets.WebSocketException, TimeoutError) as e:
            self._finish(job, "failed", None, f"sandbox koşucusuna bağlanılamadı: {e}")
            return
        async with ws:
            await ws.send(json.dumps({"type": "start", "job_id": job.job_id, "code": job.code,
                                      "secret": self.runner_secret}))  # fmt: skip
            job.status, job.started_at = "running", _now()
            job.broadcast({"type": "status", "status": "running"})
            cancel_task = asyncio.create_task(cancel_ev.wait())
            try:
                while True:
                    recv = asyncio.create_task(ws.recv())
                    done, _ = await asyncio.wait({recv, cancel_task}, return_when="FIRST_COMPLETED")
                    if cancel_task in done and recv not in done:
                        recv.cancel()
                        await ws.send(json.dumps({"type": "cancel"}))
                        cancel_task = asyncio.create_task(asyncio.sleep(3600))
                        continue
                    try:
                        msg = json.loads(recv.result())
                    except websockets.ConnectionClosed:
                        self._finish(job, "failed", None, "koşucu bağlantısı koptu")
                        return
                    if await self._handle(job, ws, msg):
                        return
            finally:
                cancel_task.cancel()

    async def _handle(self, job: Job, ws, msg: dict) -> bool:
        kind = msg.get("type")
        if kind in ("stdout", "stderr"):
            job.append(kind, str(msg.get("data", "")))
        elif kind == "rpc":
            rid, method = msg.get("id"), msg.get("method")
            try:
                if method not in METHODS:
                    raise ApiError("bad_request", f"bilinmeyen komut: {method}")
                result = await execute(self.backend, method, msg.get("params"), job.job_id)
                reply = {"type": "rpc_result", "id": rid, "result": result}
            except ApiError as e:
                reply = {"type": "rpc_result", "id": rid,
                         "error": {"code": e.code, "message": e.message}}  # fmt: skip
            await ws.send(json.dumps(reply))
        elif kind == "exit":
            code, reason = msg.get("exit_code"), msg.get("reason", "error")
            if job.cancel_requested or reason == "cancelled":
                status = "cancelled"
            elif reason == "timeout":
                status = "timeout"
            elif reason == "ok" and code == 0:
                status = "done"
            else:
                status = "failed"
            self._finish(job, status, code, None if status == "done" else reason)
            return True
        return False
