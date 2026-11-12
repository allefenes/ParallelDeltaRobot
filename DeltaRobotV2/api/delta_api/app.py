"""FastAPI uygulaması: REST + WebSocket uç noktaları ve web arayüzünün statik dosyaları.

Sözleşme: docs/api.md. Robot komutları `commands.execute` üzerinden, işler `JobManager` ile.
Robot modunda (F4) tek paylaşılan arka uç ve kontrol kilidi; simülasyon modunda (F6) kullanıcı
başına bir oturum (`sessions.Sessions`; F6 üyeliksiz deneyim arayüzü için anonim oturumlar).
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

from delta_api.auth import Principal, StaticAuth, Tokens
from delta_api.backend import Backend
from delta_api.commands import MANUAL, ApiError, execute
from delta_api.jobs import FINAL
from delta_api.sessions import Session, Sessions

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
    backend: Backend | None,
    tokens: Tokens | None,
    runner_url: str = "ws://runner:8100/run",
    runner_secret: str = "",
    web_dir: Path | None = None,
    meshes_dir: Path | None = None,
    i18n_dir: Path | None = None,
    *,
    sessions: Sessions | None = None,
    auth=None,
) -> FastAPI:
    auth = auth or StaticAuth(tokens)
    if sessions is None:
        sessions = Sessions(runner_url, runner_secret, shared=backend)

    @contextlib.asynccontextmanager
    async def lifespan(_app: FastAPI):
        sessions.start(asyncio.get_running_loop())
        yield
        await sessions.close()

    app = FastAPI(
        title="Delta Robotics V2 API",
        version=VERSION,
        lifespan=lifespan,
        docs_url="/api/v1/docs",
        openapi_url="/api/v1/openapi.json",
        redoc_url=None,
    )
    app.state.sessions, app.state.auth = sessions, auth

    @app.exception_handler(ApiError)
    async def _api_error(_req, e: ApiError):
        return JSONResponse(e.body(), status_code=e.status)

    @app.exception_handler(RequestValidationError)
    async def _validation(_req, e: RequestValidationError):
        return JSONResponse({"error": "bad_request", "message": str(e.errors()[:1])}, 400)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_req, e: StarletteHTTPException):
        code = {404: "not_found", 401: "unauthorized", 405: "bad_request"}.get(e.status_code)
        return JSONResponse(
            {"error": code or "bad_request", "message": str(e.detail)}, e.status_code
        )

    async def principal_of(token: str) -> Principal | None:
        p = sessions.principal_for(token) if sessions.mode == "sim" else None
        return p or await auth.check(token)

    async def user(request: Request) -> Principal:
        h = request.headers.get("authorization", "")
        p = await principal_of(h[7:] if h.lower().startswith("bearer ") else "")
        if p is None:
            raise ApiError("unauthorized", "geçersiz ya da eksik belirteç")
        return p

    def session(p: Principal) -> Session:
        return sessions.get(p)

    def require_control(s: Session) -> None:
        """Kontrol kilidi: oturumda iş çalışırken doğrudan komut kabul edilmez."""
        if s.jobs.active_id is not None:
            raise ApiError("busy", "robotu şu anda bir iş kullanıyor", job_id=s.jobs.active_id)

    api = "/api/v1"

    @app.get(f"{api}/health")
    async def health():
        connected = sessions.mode == "sim" or sessions.shared.state().edge_connected
        return {"ok": True, "edge_connected": connected, "version": VERSION, "mode": sessions.mode}

    async def run(request: Request, method: str, locked: bool = True, body: bool = True):
        p = await user(request)
        s = session(p)
        params = await _body(request) if body else {}
        if locked:
            require_control(s)
        if method in MANUAL and s.backend.auto_running:
            raise ApiError("busy", "otomatik oyun sürüyor; önce durdurun")
        return await execute(s.backend, method, params, s.jobs.active_id)

    @app.post(f"{api}/session", status_code=201)
    async def new_session(request: Request):
        ip = request.client.host if request.client else "?"
        token = sessions.create_anonymous(ip)
        return {"token": token, "idle_timeout_s": int(sessions.limits.idle_timeout_s)}

    @app.post(f"{api}/move_joints")
    async def move_joints(request: Request):
        return await run(request, "move_joints")

    @app.post(f"{api}/kinematics/fk")
    async def fk(request: Request):
        return await run(request, "fk", locked=False)

    @app.post(f"{api}/kinematics/ik")
    async def ik(request: Request):
        return await run(request, "ik", locked=False)

    @app.post(f"{api}/auto/start")
    async def auto_start(request: Request):
        return await run(request, "auto_start")

    @app.post(f"{api}/auto/stop")
    async def auto_stop(request: Request):
        return await run(request, "auto_stop", locked=False)

    @app.get(f"{api}/robot")
    async def robot(request: Request):
        return await run(request, "robot", locked=False, body=False)

    @app.get(f"{api}/state")
    async def state(request: Request):
        return await run(request, "state", locked=False, body=False)

    @app.get(f"{api}/board")
    async def board(request: Request):
        return await run(request, "board", locked=False, body=False)

    @app.post(f"{api}/board/reset")
    async def board_reset(request: Request):
        return await run(request, "board_reset")

    @app.post(f"{api}/move")
    async def move(request: Request):
        return await run(request, "move")

    @app.post(f"{api}/magnet")
    async def magnet(request: Request):
        return await run(request, "magnet")

    @app.post(f"{api}/torque")
    async def torque(request: Request):
        return await run(request, "torque")

    @app.post(f"{api}/stop")
    async def stop(request: Request):
        # Güvenlik: dur komutu kilitten bağımsız, her zaman kabul edilir.
        return await run(request, "stop", locked=False)

    @app.post(f"{api}/jobs", status_code=202)
    async def submit(request: Request):
        p = await user(request)
        s = session(p)
        b = await _body(request)
        job = s.jobs.submit(b.get("code"), b.get("name"), p.key)
        return {"job_id": job.job_id, "status": job.status}

    @app.get(f"{api}/jobs/{{jid}}")
    async def job_get(jid: str, request: Request):
        p = await user(request)
        return sessions.find_job(jid, p)[1].to_dict()

    @app.post(f"{api}/jobs/{{jid}}/cancel")
    async def job_cancel(jid: str, request: Request):
        p = await user(request)
        s, _job = sessions.find_job(jid, p)
        s.jobs.cancel(jid)
        return {"ok": True}

    async def ws_auth(ws: WebSocket) -> Principal | None:
        try:
            p = await principal_of(ws.query_params.get("token", ""))
        except ApiError:
            p = None
        if p is None:
            await ws.close(code=WS_UNAUTHORIZED, reason="unauthorized")
            return None
        await ws.accept()
        return p

    @app.websocket(f"{api}/ws/telemetry")
    async def ws_telemetry(ws: WebSocket):
        p = await ws_auth(ws)
        if p is None:
            return
        try:
            s = sessions.get(p, count_request=False)
        except ApiError:
            await ws.close(code=WS_UNAUTHORIZED, reason="session")
            return
        s.open_streams += 1
        q = s.backend.add_listener()
        period = 1.0 / TELEMETRY_HZ
        try:
            while True:
                await ws.send_json({"type": "state", **s.backend.state().to_dict(s.jobs.active_id)})
                with contextlib.suppress(TimeoutError):
                    ev = await asyncio.wait_for(q.get(), timeout=period)
                    await ws.send_json(ev)
                    while not q.empty():
                        await ws.send_json(q.get_nowait())
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            s.open_streams -= 1
            s.last_seen = sessions.clock()
            s.backend.remove_listener(q)

    @app.websocket(f"{api}/ws/jobs/{{jid}}")
    async def ws_job(ws: WebSocket, jid: str):
        p = await ws_auth(ws)
        if p is None:
            return
        try:
            _s, job = sessions.find_job(jid, p)
        except ApiError:
            await ws.close(code=4404, reason="not_found")
            return
        q: asyncio.Queue = asyncio.Queue(maxsize=1000)
        job.listeners.add(q)
        try:
            if job.output:
                await ws.send_json({"type": "stdout", "data": job.output})
            if job.status in FINAL:
                await ws.send_json(
                    {
                        "type": "status",
                        "status": job.status,
                        "exit_code": job.exit_code,
                        "reason": job.reason,
                    }
                )
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
