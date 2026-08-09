"""Adapter factory."""
from __future__ import annotations

from ..models import DeviceConfig
from .base import AdapterError, SwitchAdapter
from .home_assistant import HomeAssistantSwitchAdapter
from .shelly import ShellySwitchAdapter


def build_switch_adapter(device: DeviceConfig) -> SwitchAdapter:
    if device.adapter == "shelly":
        return ShellySwitchAdapter(device)
    if device.adapter == "home_assistant":
        return HomeAssistantSwitchAdapter(device)
    raise AdapterError(f"unsupported adapter: {device.adapter}")
