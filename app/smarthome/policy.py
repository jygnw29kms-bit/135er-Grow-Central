"""Deny-by-default smart-home command policy."""
from __future__ import annotations

import os

from .models import DeviceConfig


class PolicyDenied(ValueError):
    pass


def smart_home_enabled() -> bool:
    # Runtime integration is available by default; actual writes still require
    # local API authentication plus approved+writable device flags.
    return os.getenv("GC_SMARTHOME_ENABLED", "true").lower() == "true"


def assert_switch_write_allowed(device: DeviceConfig) -> None:
    if not smart_home_enabled():
        raise PolicyDenied("smart-home writes are globally disabled")
    if not device.approved:
        raise PolicyDenied("device is not approved")
    if not device.writable:
        raise PolicyDenied("device is read-only")
    if device.capability != "switch":
        raise PolicyDenied("device does not expose a switch capability")
