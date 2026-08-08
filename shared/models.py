"""Gemeinsame Datenmodelle / Shared data models."""
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class Telemetry(BaseModel):
    """DE: Telemetrie eines Standortes. EN: Site telemetry packet."""
    site_id: str
    device_id: str = "raspberry-pi"
    ts: datetime
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    vpd_kpa: Optional[float] = None
    fan_speed_pct: Optional[int] = Field(default=None, ge=0, le=100)
    device_online: bool = True
    extra: Dict[str, Any] = {}


class Command(BaseModel):
    """DE: Cloud-Anforderung. EN: Cloud request."""
    id: str
    site_id: str
    target: str
    action: str
    value: Any = None
    created_at: datetime
    status: str = "pending"


class CommandResult(BaseModel):
    """DE: Lokales Befehlsergebnis. EN: Local command result."""
    command_id: str
    site_id: str
    ok: bool
    message: str = ""
    actual: Any = None
    ts: datetime
