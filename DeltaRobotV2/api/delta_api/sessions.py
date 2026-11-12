"""Oturumlar: robot modunda tek paylaşılan arka uç, simülasyon modunda ziyaretçi başına bir oturum.

F6 (üyeliksiz deneyim arayüzü): her ziyaretçi `POST /session` ile anonim bir oturum alır; oturum
kendi simülasyonunu (SimBackend) ve iş kuyruğunu taşır. Kötüye kullanım korumaları: IP başına
oturum açma sınırı, eşzamanlı oturum üst sınırı, oturum başına istek sınırı, boşta kalma süresi.
Robot modunda (F4) davranış aynı: tek robot, kontrol kilidi.
"""

from __future__ import annotations

import asyncio
import contextlib
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from delta_api.auth import Principal, RateLimiter
from delta_api.backend import Backend
from delta_api.commands import ApiError
from delta_api.jobs import Job, JobManager

ROBOT_KEY = "robot"


@dataclass
class Session:
    backend: Backend
    jobs: JobManager
    last_seen: float = field(default_factory=time.monotonic)
    open_streams: int = 0  # açık telemetri bağlantısı varken oturum boşta sayılmaz


@dataclass(frozen=True)
class Limits:
    max_sessions: int = 50
    idle_timeout_s: float = 600.0
    sessions_per_ip_per_min: int = 10
    requests_per_s: int = 20


class Sessions:
    def __init__(
        self,
        runner_url: str,
        runner_secret: str,
        shared: Backend | None = None,
        factory: Callable[[], Backend] | None = None,
        runner_slots: int = 1,
        limits: Limits | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if (shared is None) == (factory is None):
            raise ValueError("ya paylaşılan arka uç ya da oturum üreticisi verilmeli")
        self.runner_url, self.runner_secret = runner_url, runner_secret
        self.shared, self.factory = shared, factory
        self.runner_slots = runner_slots
        self.limits = limits or Limits()
        self.clock = clock
        self._sessions: dict[str, Session] = {}
        self._anon: dict[str, str] = {}  # belirteç -> oturum kimliği
        self._ip_limit = RateLimiter(self.limits.sessions_per_ip_per_min, 60.0, clock)
        self._req_limit = RateLimiter(self.limits.requests_per_s, 1.0, clock)
        self._slots: asyncio.Semaphore | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._reaper: asyncio.Task | None = None

    @property
    def mode(self) -> str:
        return "robot" if self.shared is not None else "sim"

    def __len__(self) -> int:
        return len(self._sessions)

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._slots = asyncio.Semaphore(self.runner_slots)
        if self.shared is not None:
            self._create(ROBOT_KEY, self.shared)
        else:
            self._reaper = loop.create_task(self._reap_loop())

    def _create(self, key: str, backend: Backend) -> Session:
        backend.bind_loop(self._loop)
        jobs = JobManager(backend, self.runner_url, self.runner_secret, self._slots)
        jobs.start()
        s = Session(backend, jobs, last_seen=self.clock())
        self._sessions[key] = s
        return s

    # --- anonim oturumlar (F6) -------------------------------------------------------------
    def create_anonymous(self, ip: str) -> str:
        """Yeni ziyaretçi oturumu; belirteç döner."""
        if self.shared is not None:
            raise ApiError("not_found", "anonim oturum yalnız simülasyon modunda")
        if not self._ip_limit.allow(ip or "?"):
            raise ApiError("rate_limited", "çok fazla oturum isteği; biraz sonra deneyin")
        if len(self._sessions) >= self.limits.max_sessions:
            raise ApiError("capacity", "simülasyon kapasitesi dolu; biraz sonra deneyin")
        sid = secrets.token_hex(8)
        token = secrets.token_urlsafe(24)
        self._anon[token] = sid
        self._create(f"s:{sid}", self.factory())
        return token

    def principal_for(self, token: str) -> Principal | None:
        sid = self._anon.get(token) if token else None
        return Principal(f"ziyaretci-{sid[:6]}", session=sid) if sid else None

    def get(self, principal: Principal, count_request: bool = True) -> Session:
        """İstek sahibinin oturumu; istek sınırı burada uygulanır."""
        if self.shared is not None:
            return self._sessions[ROBOT_KEY]
        s = self._sessions.get(principal.key)
        if s is None:
            if principal.session is not None:  # süresi dolmuş anonim oturum
                raise ApiError("unauthorized", "oturum süresi doldu; yeni oturum açın")
            if len(self._sessions) >= self.limits.max_sessions:
                raise ApiError("capacity", "simülasyon kapasitesi dolu; biraz sonra deneyin")
            s = self._create(principal.key, self.factory())
        if count_request and not self._req_limit.allow(principal.key):
            raise ApiError("rate_limited", "çok fazla istek")
        s.last_seen = self.clock()
        return s

    async def _reap_loop(self) -> None:
        while True:
            await asyncio.sleep(min(30.0, self.limits.idle_timeout_s / 4))
            await self.reap()

    async def reap(self) -> int:
        """Boşta kalan oturumları kapatır (açık telemetri akışı ya da çalışan iş varsa kalır)."""
        now = self.clock()
        dead = [
            k
            for k, s in self._sessions.items()
            if k != ROBOT_KEY
            and s.open_streams == 0
            and s.jobs.active_id is None
            and now - s.last_seen > self.limits.idle_timeout_s
        ]
        for k in dead:
            await self._close(k)
        self._ip_limit.prune()
        self._req_limit.prune()
        return len(dead)

    async def _close(self, key: str) -> None:
        s = self._sessions.pop(key)
        for tok in [t for t, sid in self._anon.items() if f"s:{sid}" == key]:
            del self._anon[tok]
        self._req_limit.forget(key)
        await s.jobs.close()
        with contextlib.suppress(Exception):
            await s.backend.shutdown()
        s.backend.close()

    def find_job(self, jid: str, principal: Principal) -> tuple[Session, Job]:
        """İşi sahibine göre bulur; başkasının işi 'bulunamadı' döner (IDOR yok)."""
        for s in self._sessions.values():
            job = s.jobs.jobs.get(jid)
            if job is not None:
                if principal.role == "admin" or job.owner == principal.key:
                    return s, job
                break
        raise ApiError("not_found", "iş bulunamadı")

    async def close(self) -> None:
        if self._reaper:
            self._reaper.cancel()
        for k in list(self._sessions):
            if k == ROBOT_KEY:
                s = self._sessions.pop(k)
                await s.jobs.close()
            else:
                await self._close(k)
