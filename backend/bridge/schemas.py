"""Pydantic contracts for bridge envelope and core method payloads."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BridgeRequest(BaseModel):
    """Envelope for incoming bridge requests."""

    model_config = ConfigDict(extra="forbid")

    method: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_.]+$")
    request_id: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class EmptyPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class JobIdPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(min_length=1)
