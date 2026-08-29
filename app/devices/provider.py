from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Mapping

from .models import Capability, DeviceClass, ProviderDescriptor


@dataclass(slots=True)
class DiscoveredDevice:
    provider_id: str
    native_id: str
    name: str
    device_class: DeviceClass
    capabilities: tuple[Capability, ...]
    transport: str
    model: str | None = None
    manufacturer: str | None = None
    signal: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def global_id(self) -> str:
        return f"{self.provider_id}:{self.native_id}"


@dataclass(slots=True)
class DeviceHealth:
    online: bool
    detail: str = ""
    latency_ms: float | None = None
    transport: str | None = None


class DeviceProvider(ABC):
    """Contract implemented by every vendor or transport integration.

    Vendor-specific payloads end here. Callers receive normalized state and
    capability names only. Writes must be explicit and verifiable.
    """

    descriptor: ProviderDescriptor

    @abstractmethod
    async def discover(self, timeout: float = 5.0) -> list[DiscoveredDevice]:
        raise NotImplementedError

    @abstractmethod
    async def state(self, native_id: str) -> Mapping[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def command(self, native_id: str, capability: Capability, value: Any) -> Mapping[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def health(self, native_id: str) -> DeviceHealth:
        raise NotImplementedError

    async def close(self) -> None:
        return None
