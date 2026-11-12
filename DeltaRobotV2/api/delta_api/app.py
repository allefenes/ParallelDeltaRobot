"""FastAPI uygulaması: REST + WebSocket uç noktaları ve web arayüzünün statik dosyaları.

Sözleşme: docs/api.md. Robot komutları `commands.execute` üzerinden, işler `JobManager` ile.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from delta_api.auth import Tokens
from delta_api.backend import Backend
from delta_api.commands import ApiError, execute
from delta_api.jobs import FINAL, JobManager

VERSION = "v1"
TELEMETRY_HZ = 20.0
WS_UNAUTHORIZED = 4401  # WebSocket kapanış kodu: kimlik doğrulama hatası


async def _body(request: Request) -> dict:
    raw = await request.body()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ApiError("bad_request", f"gövde JSON değil: {e.msg}") from e
    if not isinstance(data, dict):
        raise ApiError("bad_request", "gövde bir JSON nesnesi olmalı")
    return data


def create_app(
    backend: Backend,
    tokens: Tokens,
    runner_url: str = "ws://runner:8100/run",
    runner_secret: str = "",
    web_dir: Path | None = None,
    meshes_dir: Path | None = None,
    i18n_dir: Path | None = None,
) -> FastAPI:
    jobs = JobManager(backend, runner_url, runner_secret)

    @contextlib.asynccontextmanager
    async def lifespan(_app: FastAPI):
        backend.bind_loop(asyncio.get_running_loop())
        jobs.start()
        yield
        await jobs.close()

    app = FastAPI(
        title="Delta Robotics V2 API",
        version=VERSION,
        lifespan=lifespan,
        docs_url="/api/v1/docs",
        openapi_url="/api/v1/openapi.json",
        redoc_url=None,
    )
    app.state.backend, app.state.jobs, app.state.tokens = backend, jobs, tokens

    @app.exception_handler(ApiError)
    async def _api_error(_req, e: ApiError):
        return JSONResponse(e.body(), status_code=e.status)

    @app.exception_handler(RequestValidationError)
    async def _validation(_req, e: RequestValidationError):
        return JSONResponse({"error": "bad_request", "message": str(e.errors()[:1])}, 400)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_req, e: StarletteHTTPException):
        code = {404: "not_found", 401: "unauthorized", 405: "bad_request"}.get(e.status_code)
        return JSONResponse({"error": code or "bad_request", "message": str(e.detail)},
                            e.status_code)  # fmt: skip

    def user(request: Request) -> str:
        auth = request.headers.get("authorization", "")
        name = tokens.check(auth[7:] if auth.lower().startswith("bearer ") else "")
        if name is None:
            raise ApiError("unauthorized", "geçersiz ya da eksik belirteç")
        return name

    def require_control() -> None:
        """Kontrol kilidi: iş çalışırken doğrudan robot komutu kabul edilmez."""
        if jobs.active_id is not None:
            raise ApiError("busy", "robotu şu anda bir iş kullanıyor", job_id=jobs.active_id)

    api = "/api/v1"

    @app.get(f"{api}/health")
    async def health():
        s = backend.state()
        return {"ok": True, "edge_connected": s.edge_connected, "version": VERSION}

    @app.get(f"{api}/robot")
    async def robot(request: Request):
        user(request)
        return await execute(backend, "robot", {})

    @app.get(f"{api}/state")
    async def state(request: Request):
        user(request)
        return await execute(backend, "state", {}, jobs.active_id)

    async def command(request: Request, method: str, locked: bool = True):
        user(request)
        params = await _body(request)
        if locked:
            require_control()
        return await execute(backend, method, params)

    @app.post(f"{api}/move")
    async def move(request: Request):
        return await command(request, "move")

    @app.post(f"{api}/magnet")
    async def magnet(request: Request):
        return await command(request, "magnet")

    @app.post(f"{api}/torque")
    async def torque(request: Request):
        return await command(request, "torque")

    @app.post(f"{api}/stop")
    async def stop(request: Request):
        # Güvenlik: dur komutu kilitten bağımsız, her zaman kabul edilir.
        return await command(request, "stop", locked=False)

    @app.post(f"{api}/jobs", status_code=202)
    async def submit(request: Request):
        owner = user(request)
        body = await _body(request)
        job = jobs.submit(body.get("code"), body.get("name"), owner)
        return {"job_id": job.job_id, "status": job.status}

    @app.get(f"{api}/jobs/{{jid}}")
    async def job_get(jid: str, request: Request):
        user(request)
        return jobs.get(jid).to_dict()

    @app.post(f"{api}/jobs/{{jid}}/cancel")
    async def job_cancel(jid: str, request: Request):
        user(request)
        jobs.cancel(jid)
        return {"ok": True}

    async def ws_auth(ws: WebSocket) -> bool:
        if tokens.check(ws.query_params.get("token", "")) is None:
            await ws.close(code=WS_UNAUTHORIZED, reason="unauthorized")
            return False
        await ws.accept()
        return True

    @app.websocket(f"{api}/ws/telemetry")
    async def ws_telemetry(ws: WebSocket):
        if not await ws_auth(ws):
            return
        q = backend.add_listener()
        period = 1.0 / TELEMETRY_HZ
        try:
            while True:
                await ws.send_json({"type": "state", **backend.state().to_dict(jobs.active_id)})
                with contextlib.suppress(TimeoutError):
                    ev = await asyncio.wait_for(q.get(), timeout=period)
                    await ws.send_json(ev)
                    while not q.empty():
                        await ws.send_json(q.get_nowait())
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            backend.remove_listener(q)

    @app.websocket(f"{api}/ws/jobs/{{jid}}")
    async def ws_job(ws: WebSocket, jid: str):
        if not await ws_auth(ws):
            return
        job = jobs.jobs.get(jid)
        if job is None:
            await ws.close(code=4404, reason="not_found")
            return
        q: asyncio.Queue = asyncio.Queue(maxsize=1000)
        job.listeners.add(q)
        try:
            if job.output:
                await ws.send_json({"type": "stdout", "data": job.output})
            if job.status in FINAL:
                await ws.send_json({"type": "status", "status": job.status,
                                    "exit_code": job.exit_code, "reason": job.reason})  # fmt: skip
            else:
                await ws.send_json({"type": "status", "status": job.status})
                while True:
                    msg = await q.get()
                    if msg.get("type") == "_end":
                        break
                    await ws.send_json(msg)
            await ws.close()
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            job.listeners.discard(q)

    if meshes_dir and meshes_dir.is_dir():
        app.mount("/assets/meshes", StaticFiles(directory=meshes_dir), name="meshes")
    if i18n_dir and i18n_dir.is_dir():
        app.mount("/i18n", StaticFiles(directory=i18n_dir), name="i18n")
    if web_dir and web_dir.is_dir():
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
    return app
