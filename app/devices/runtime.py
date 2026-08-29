from __future__ import annotations

from .gc_esp32 import GrowCentralEsp32Provider
from .legacy_smarthome import LegacySmartHomeProvider
from .provider import DeviceProvider


_COMPATIBILITY_PROVIDERS = ("shelly", "tapo", "fritz", "home_assistant")


class ProviderRuntime:
    """Small runtime registry for active gc-device-v1 providers.

    The catalog describes what Grow Central can support. This registry describes
    which providers currently have executable code on this installation.
    """

    def __init__(self) -> None:
        self._providers: dict[str, DeviceProvider] = {
            provider_id: LegacySmartHomeProvider(provider_id)
            for provider_id in _COMPATIBILITY_PROVIDERS
        }
        self._providers["growcentral_esp32"] = GrowCentralEsp32Provider()

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))

    def get(self, provider_id: str) -> DeviceProvider:
        try:
            return self._providers[provider_id]
        except KeyError as exc:
            raise KeyError(f"provider runtime unavailable: {provider_id}") from exc

    def providers(self) -> list[DeviceProvider]:
        return [self._providers[key] for key in sorted(self._providers)]


runtime = ProviderRuntime()
