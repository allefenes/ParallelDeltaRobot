"""İstemci istisnaları. HTTP durum kodları ve stdio hata kodları aynı sınıflara eşlenir."""

from __future__ import annotations

from typing import Any


class DeltaError(Exception):
    """Tüm istemci hatalarının tabanı."""

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status
        self.payload = payload or {}


class AuthError(DeltaError):
    """Belirteç geçersiz ya da eksik (401, `unauthorized`)."""


class RobotBusy(DeltaError):
    """Robot başka bir işin denetiminde (409, `busy`)."""

    @property
    def job_id(self) -> str | None:
        return self.payload.get("job_id")


class RobotUnavailable(DeltaError):
    """Robot ya da kenar bağlantısı yok (503, `robot_unavailable`)."""


class CommandRejected(DeltaError):
    """Güvenlik kapısı hareketi reddetti (`accepted: false`)."""

    def __init__(self, requirement: str | None, reason: str | None, result: Any = None) -> None:
        super().__init__(reason or "komut reddedildi", code="rejected")
        self.requirement = requirement
        self.reason = reason
        self.result = result


class MoveNotCompleted(DeltaError):
    """Hareket kabul edildi ama beklerken tamamlanmadı (`done: false`)."""

    def __init__(self, reason: str | None, result: Any = None) -> None:
        super().__init__(reason or "hareket tamamlanmadı", code="not_completed")
        self.reason = reason
        self.result = result


_BY_STATUS: dict[int, type[DeltaError]] = {
    401: AuthError,
    409: RobotBusy,
    503: RobotUnavailable,
}

_BY_CODE: dict[str, type[DeltaError]] = {
    "unauthorized": AuthError,
    "busy": RobotBusy,
    "robot_unavailable": RobotUnavailable,
}


def error_from_status(status: int, payload: dict[str, Any]) -> DeltaError:
    """HTTP hata yanıtından uygun istisnayı üretir."""
    cls = _BY_STATUS.get(status, DeltaError)
    message = str(payload.get("message") or payload.get("error") or f"HTTP {status}")
    return cls(message, code=payload.get("error"), status=status, payload=payload)


def error_from_code(error: dict[str, Any]) -> DeltaError:
    """stdio `error` nesnesinden uygun istisnayı üretir."""
    code = error.get("code")
    cls = _BY_CODE.get(code, DeltaError) if isinstance(code, str) else DeltaError
    message = str(error.get("message") or code or "bilinmeyen hata")
    return cls(message, code=code, payload=error)
