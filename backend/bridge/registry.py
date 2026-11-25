"""Allowlist method registry for the typed bridge."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from backend.core.errors import ValidationError


class RegisteredMethod:
    """Metadata and handler for an allowlisted bridge method."""

    def __init__(
        self,
        name: str,
        schema: type[BaseModel],
        handler: Callable[[BaseModel], dict[str, Any]],
    ) -> None:
        self.name = name
        self.schema = schema
        self.handler = handler


class MethodRegistry:
    """Strict allowlist registry rejecting unknown or invalid method calls."""

    def __init__(self) -> None:
        self._methods: dict[str, RegisteredMethod] = {}

    def register(
        self,
        name: str,
        schema: type[BaseModel],
        handler: Callable[[Any], dict[str, Any]],
    ) -> None:
        self._methods[name] = RegisteredMethod(name, schema, handler)

    def get(self, name: str) -> RegisteredMethod | None:
        return self._methods.get(name)

    def dispatch(self, name: str, raw_payload: dict[str, Any]) -> dict[str, Any]:
        entry = self._methods.get(name)
        if entry is None:
            raise KeyError(name)
        try:
            validated = entry.schema.model_validate(raw_payload)
        except PydanticValidationError as exc:
            field_errors: dict[str, str] = {}
            for err in exc.errors():
                loc = ".".join(str(part) for part in err.get("loc", ()))
                if loc:
                    field_errors[loc] = str(err.get("msg", "Tidak valid"))
            raise ValidationError(
                f"Payload untuk '{name}' tidak valid.",
                field_errors=field_errors or None,
            ) from exc
        return entry.handler(validated)
