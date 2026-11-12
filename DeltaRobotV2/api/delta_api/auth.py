"""Kimlik: statik belirteçler (F4 yerel kullanım, pip istemcisi) ve anonim oturumlar (F6).

F6 kararı (kullanıcı, 2026-11-12): üyelik yok; tek sayfalık deneyim arayüzü her ziyaretçiye
anonim bir simülasyon oturumu açar (`sessions.Sessions.create_anonymous`). Karşılaştırmalar sabit
sürelidir (zamanlama sızıntısı yok).
"""

from __future__ import annotations

import hmac
import time
from collections import deque
from dataclasses import dataclass

MIN_TOKEN_LEN = 16


class Tokens:
    def __init__(self, mapping: dict[str, str]) -> None:
        for name, tok in mapping.items():
            if len(tok) < MIN_TOKEN_LEN:
                raise ValueError(f"'{name}' belirteci en az {MIN_TOKEN_LEN} karakter olmalı")
        self._items = list(mapping.items())

    @classmethod
    def parse(cls, text: str) -> Tokens:
        mapping: dict[str, str] = {}
        for part in filter(None, (p.strip() for p in (text or "").split(","))):
            name, sep, tok = part.partition(":")
            if not sep or not name or not tok:
                raise ValueError("DELTA_API_TOKENS biçimi: ad:belirteç[,ad:belirteç]")
            mapping[name] = tok
        return cls(mapping)

    def check(self, token: str) -> str | None:
        """Belirtecin sahibi; geçersizse None."""
        if not token:
            return None
        found = None
        for name, tok in self._items:
            if hmac.compare_digest(tok.encode(), token.encode()):
                found = name
        return found


@dataclass(frozen=True)
class Principal:
    """İstek sahibi; `key` simülasyon modunda oturum anahtarıdır."""

    name: str
    role: str = "user"
    session: str | None = None  # anonim oturum kimliği

    @property
    def key(self) -> str:
        return f"s:{self.session}" if self.session else f"n:{self.name}"


class StaticAuth:
    """F4 statik belirteçleri (DELTA_API_TOKENS)."""

    def __init__(self, tokens: Tokens | None) -> None:
        self.tokens = tokens

    async def check(self, token: str) -> Principal | None:
        name = self.tokens.check(token) if self.tokens else None
        return Principal(name) if name else None


class RateLimiter:
    """Kayan pencere: anahtar başına `limit` olay / `window_s` saniye."""

    def __init__(self, limit: int, window_s: float, clock=time.monotonic) -> None:
        self.limit, self.window_s, self.clock = limit, window_s, clock
        self._events: dict[str, deque] = {}

    def allow(self, key: str) -> bool:
        now = self.clock()
        q = self._events.setdefault(key, deque())
        while q and now - q[0] >= self.window_s:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True

    def forget(self, key: str) -> None:
        self._events.pop(key, None)

    def prune(self) -> None:
        """Boşalmış anahtarları bırakır (bellek sınırlı kalsın)."""
        now = self.clock()
        for k in [k for k, q in self._events.items() if not q or now - q[-1] >= self.window_s]:
            del self._events[k]
