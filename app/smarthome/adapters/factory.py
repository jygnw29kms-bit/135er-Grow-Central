"""Adapter factory."""
from __future__ import annotations

from ..models import DeviceConfig
from .base import AdapterError, SwitchAdapter
from .fritz import FritzSwitchAdapter
from .home_assistant import HomeAssistantSwitchAdapter
from .shelly import ShellySwitchAdapter
from .tapo import TapoSwitchAdapter


def build_switch_adapter(device: DeviceConfig) -> SwitchAdapter:
    if device.adapter == "shelly":
        return ShellySwitchAdapter(device)
    if device.adapter == "home_assistant":
        return HomeAssistantSwitchAdapter(device)
    if device.adapter == "fritz":
        return FritzSwitchAdapter(device)
    if device.adapter == "tapo":
        return TapoSwitchAdapter(device)
    raise AdapterError(f"unsupported adapter: {device.adapter}")
