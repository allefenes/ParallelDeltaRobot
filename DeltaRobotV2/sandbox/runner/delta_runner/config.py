"""Koşucu ayarları. Sınırlar ortam değişkenlerinden okunur; varsayılanlar api.md değerleridir.

Değerler `docker run` argümanına girdiği için sıkı biçimde doğrulanır (bayrak enjeksiyonu yok).
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field

_SIZE_RE = re.compile(r"^[1-9][0-9]{0,5}[kmg]$")
_CPUS_RE = re.compile(r"^(0\.[0-9]{1,3}|[1-9][0-9]?(\.[0-9]{1,3})?)$")
_IMAGE_RE = re.compile(r"^[a-z0-9][a-z0-9._/-]*(:[A-Za-z0-9._-]{1,128})?$")

ENV_PREFIX = "DELTA_SANDBOX_"


@dataclass(frozen=True)
class Limits:
    """Kullanıcı kodu konteynerinin kaynak sınırları."""

    memory: str = "256m"  # --memory ve --memory-swap (takas yok)
    cpus: str = "0.5"
    pids: int = 64
    tmpfs_size: str = "16m"
    timeout_s: float = 120.0  # duvar saati
    output_bytes: int = 1024 * 1024  # stdout+stderr toplamı (RPC satırları dahil)

    def __post_init__(self) -> None:
        if not _SIZE_RE.match(self.memory):
            raise ValueError(f"geçersiz bellek sınırı: {self.memory!r}")
        if not _SIZE_RE.match(self.tmpfs_size):
            raise ValueError(f"geçersiz tmpfs boyutu: {self.tmpfs_size!r}")
        if not _CPUS_RE.match(self.cpus):
            raise ValueError(f"geçersiz CPU sınırı: {self.cpus!r}")
        if not (isinstance(self.pids, int) and 8 <= self.pids <= 4096):
            raise ValueError(f"geçersiz süreç sınırı: {self.pids!r}")
        if not (0 < self.timeout_s <= 3600):
            raise ValueError(f"geçersiz süre sınırı: {self.timeout_s!r}")
        if not (isinstance(self.output_bytes, int) and 1024 <= self.output_bytes <= 64 * 2**20):
            raise ValueError(f"geçersiz çıktı sınırı: {self.output_bytes!r}")


@dataclass(frozen=True)
class Config:
    """Koşucunun tüm ayarları."""

    image: str = "deltarobotv2-sandbox:latest"
    docker: str = "docker"
    limits: Limits = field(default_factory=Limits)
    max_code_bytes: int = 64 * 1024
    max_pending_rpc: int = 16
    kill_grace_s: float = 10.0  # rm -f sonrası docker run istemcisinin çıkması için bekleme
    max_jobs: int = 1  # eşzamanlı iş (F6 simülasyon kiralama: kullanıcılar paralel)

    def __post_init__(self) -> None:
        if not _IMAGE_RE.match(self.image):
            raise ValueError(f"geçersiz imaj adı: {self.image!r}")
        if not 1 <= self.max_jobs <= 32:
            raise ValueError(f"geçersiz eşzamanlı iş sayısı: {self.max_jobs!r}")


def config_from_env(env: Mapping[str, str] | None = None) -> Config:
    """`DELTA_SANDBOX_*` ortam değişkenlerinden ayar üretir; boş/eksik olan varsayılanda kalır."""
    env = os.environ if env is None else env

    def get(name: str) -> str | None:
        value = env.get(ENV_PREFIX + name, "").strip()
        return value or None

    base = Limits()
    limits = Limits(
        memory=get("MEMORY") or base.memory,
        cpus=get("CPUS") or base.cpus,
        pids=int(get("PIDS") or base.pids),
        tmpfs_size=get("TMPFS_SIZE") or base.tmpfs_size,
        timeout_s=float(get("TIMEOUT_S") or base.timeout_s),
        output_bytes=int(get("OUTPUT_LIMIT") or base.output_bytes),
    )
    max_jobs = int(get("MAX_JOBS") or Config.max_jobs)
    return Config(image=get("IMAGE") or Config.image, limits=limits, max_jobs=max_jobs)
