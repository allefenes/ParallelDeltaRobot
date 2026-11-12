"""Belirteç doğrulama. Yerel geliştirme: DELTA_API_TOKENS="ad:belirteç,ad2:belirteç2".

Kullanıcı hesapları ve kiralama F6'dadır. Karşılaştırma sabit sürelidir (zamanlama sızıntısı yok).
"""

from __future__ import annotations

import hmac

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
