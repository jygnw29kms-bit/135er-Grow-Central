"""Normalized smart-home device models."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DeviceConfig(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,63}$")
    name: str = Field(min_length=1, max_length=120)
    adapter: Literal["shelly", "home_assistant"]
    native_id: str = Field(min_length=1, max_length=160)
    capability: Literal["switch"] = "switch"
    approved: bool = False
    writable: bool = False
    host: str | None = None
    channel: int = Field(default=0, ge=0, le=16)
    username_env: str | None = None
    password_env: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SwitchCommand(BaseModel):
    on: bool


class PublicDevice(BaseModel):
    id: str
    name: str
    adapter: str
    capability: str
    approved: bool
    writable: bool
    metadata: dict[str, Any]
