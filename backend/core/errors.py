"""Domain and infrastructure error types mapped to bridge error codes."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base application error with structured bridge code and Indonesian message."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        field_errors: dict[str, str] | None = None,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.field_errors = field_errors
        self.details = details
        self.retryable = retryable


class ValidationError(AppError):
    def __init__(
        self, message: str, *, field_errors: dict[str, str] | None = None
    ) -> None:
        super().__init__("VALIDATION", message, field_errors=field_errors)


class NotFoundError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__("NOT_FOUND", message)


class ConflictError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__("CONFLICT", message)


class StorageError(AppError):
    def __init__(self, message: str, *, code: str = "PERMISSION_DENIED") -> None:
        super().__init__(code, message)
