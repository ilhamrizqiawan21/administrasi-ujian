"""Structured rotating logging with correlation IDs and PII/path redaction."""

from __future__ import annotations

import contextvars
import json
import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

_correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="-"
)

_SENSITIVE_KEYS = frozenset(
    {
        "nis",
        "nisn",
        "nip",
        "nama",
        "full_name",
        "name",
        "student_name",
        "password",
        "pin",
        "token",
        "secret",
        "private_key",
        "license_key",
    }
)

_PATH_PATTERN = re.compile(
    r"([A-Za-z]:\\[^\s\"']+|/(?:home|Users|tmp|var|etc)/[^\s\"']+)"
)
_DIGIT_ID_PATTERN = re.compile(r"\b\d{8,18}\b")


def set_correlation_id(correlation_id: str) -> contextvars.Token[str]:
    return _correlation_id_var.set(correlation_id)


def reset_correlation_id(token: contextvars.Token[str]) -> None:
    _correlation_id_var.reset(token)


def get_correlation_id() -> str:
    return _correlation_id_var.get()


def redact_text(value: str) -> str:
    """Mask sensitive filesystem paths and long numeric identifiers."""
    redacted = _PATH_PATTERN.sub("[REDACTED_PATH]", value)
    return _DIGIT_ID_PATTERN.sub("[REDACTED_ID]", redacted)


def redact_mapping(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively redact sensitive keys and path strings from log payloads."""
    result: dict[str, Any] = {}
    for key, val in data.items():
        if key.lower() in _SENSITIVE_KEYS:
            result[key] = "[REDACTED]"
        elif isinstance(val, dict):
            result[key] = redact_mapping(val)
        elif isinstance(val, str):
            result[key] = redact_text(val)
        else:
            result[key] = val
    return result


class _JsonRedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "correlation_id": get_correlation_id(),
            "message": redact_text(record.getMessage()),
        }
        extra_data = getattr(record, "extra_data", None)
        if isinstance(extra_data, dict):
            payload["data"] = redact_mapping(extra_data)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(log_dir: Path, *, level: int = logging.INFO) -> logging.Logger:
    """Configure rotating JSON logger for Ujian Cerdas."""
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ujian_cerdas")
    logger.setLevel(level)
    logger.handlers.clear()
    logger.propagate = False

    handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(_JsonRedactingFormatter())
    logger.addHandler(handler)
    return logger
