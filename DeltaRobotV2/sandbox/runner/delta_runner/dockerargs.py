"""`docker` komut satırı üreticileri. Saf fonksiyonlar; testler api.md ile karşılaştırır."""

from __future__ import annotations

import re

from .config import Config, Limits

CONTAINER_PREFIX = "deltarobotv2-job-"
LABEL_KEY = "deltarobotv2.sandbox"
LABEL_VALUE = "job"
JOB_LABEL_KEY = "deltarobotv2.job_id"
SANDBOX_USER = "65534:65534"

_UNSAFE_RE = re.compile(r"[^A-Za-z0-9_.-]")
_SUFFIX_RE = re.compile(r"^[0-9a-f]{4,32}$")


def safe_job_id(job_id: str) -> str:
    """İş kimliğini konteyner adına ve etikete güvenle girecek biçime indirger."""
    cleaned = _UNSAFE_RE.sub("-", job_id).strip("-.")[:40]
    return cleaned or "job"


def container_name(job_id: str, suffix: str) -> str:
    """Benzersiz konteyner adı: `deltarobotv2-job-<kimlik>-<rastgele onaltılık>`."""
    if not _SUFFIX_RE.match(suffix):
        raise ValueError(f"geçersiz ad soneki: {suffix!r}")
    return f"{CONTAINER_PREFIX}{safe_job_id(job_id)}-{suffix}"


def security_flags(limits: Limits) -> list[str]:
    """api.md'deki değiştirilemez `docker run` bayrakları, aynı sırayla."""
    return [
        "--network",
        "none",
        "--read-only",
        "--tmpfs",
        f"/tmp:rw,size={limits.tmpfs_size},noexec",
        "--memory",
        limits.memory,
        "--memory-swap",
        limits.memory,
        "--cpus",
        limits.cpus,
        "--pids-limit",
        str(limits.pids),
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--user",
        SANDBOX_USER,
        "-i",
        "--rm",
    ]


def build_run_argv(config: Config, job_id: str, name: str) -> list[str]:
    """Kullanıcı kodu konteynerini başlatan tam komut. Ortam değişkeni ya da bağlama aktarılmaz."""
    return [
        config.docker,
        "run",
        *security_flags(config.limits),
        "--name",
        name,
        "--label",
        f"{LABEL_KEY}={LABEL_VALUE}",
        "--label",
        f"{JOB_LABEL_KEY}={safe_job_id(job_id)}",
        config.image,
    ]


def build_rm_argv(config: Config, name: str) -> list[str]:
    return [config.docker, "rm", "-f", name]


def build_kill_argv(config: Config, name: str) -> list[str]:
    return [config.docker, "kill", "--signal", "KILL", name]


def build_list_jobs_argv(config: Config) -> list[str]:
    """Bu koşucunun etiketiyle duran/çalışan tüm iş konteynerlerinin kimlikleri."""
    return [config.docker, "ps", "-aq", "--filter", f"label={LABEL_KEY}={LABEL_VALUE}"]


def build_image_inspect_argv(config: Config) -> list[str]:
    return [config.docker, "image", "inspect", "--format", "{{.Id}}", config.image]
