from __future__ import annotations

from .models import Capability as C
from .models import DeviceClass as D
from .models import ProviderDescriptor, SupportLevel as S, Transport as T, VerificationLevel as V

_COMMON_GROW = (D.LIGHT, D.FAN, D.SWITCH, D.PUMP, D.HUMIDIFIER, D.DEHUMIDIFIER, D.HEATER, D.SENSOR, D.CONTROLLER)
_COMMON_CAPS = (C.POWER, C.BRIGHTNESS, C.FAN_SPEED, C.TEMPERATURE, C.HUMIDITY, C.VPD, C.SCHEDULE, C.MODE)

PROVIDERS: tuple[ProviderDescriptor, ...] = (
    ProviderDescriptor("mars_hydro", "Mars Hydro", "Mars Hydro", (T.BLE, T.CLOUD, T.MQTT), _COMMON_GROW, _COMMON_CAPS + (C.PPFD, C.SOIL_MOISTURE, C.SOIL_TEMPERATURE, C.EC), S.EXPERIMENTAL, V.COMMUNITY_VERIFIED_READONLY, True, notes="Mars Pro telemetry path is read-only until concrete model/firmware writes are hardware-validated."),
    ProviderDescriptor("spider_farmer", "Spider Farmer", "Spider Farmer", (T.BLE, T.WIFI_LOCAL, T.MQTT), _COMMON_GROW, _COMMON_CAPS + (C.OSCILLATION,), S.EXPERIMENTAL, V.COMMUNITY_VERIFIED_READONLY, True, notes="GGS BLE telemetry is usable read-only; command compatibility remains model/firmware specific."),
    ProviderDescriptor("tuya", "Tuya / Smart Life", "Tuya", (T.WIFI_LOCAL, T.CLOUD, T.ZIGBEE), _COMMON_GROW, _COMMON_CAPS + (C.VOLTAGE, C.CURRENT, C.POWER_METER, C.ENERGY), S.EXPERIMENTAL, V.CANDIDATE, True, notes="Tuya DPs are normalized; exact model mappings must be verified before productive control."),
    ProviderDescriptor("ac_infinity", "AC Infinity", "AC Infinity", (T.BLE, T.CLOUD, T.BRIDGE), _COMMON_GROW, _COMMON_CAPS, S.DETECTED, V.CANDIDATE, True, notes="Provider boundary reserved; model protocols must be validated before writes."),
    ProviderDescriptor("vivosun", "VIVOSUN", "VIVOSUN", (T.BLE, T.CLOUD, T.BRIDGE), _COMMON_GROW, _COMMON_CAPS, S.DETECTED, V.CANDIDATE, True, notes="GrowHub/E-series support is model-mapped; no generic unsafe control assumptions."),
    ProviderDescriptor("shelly", "Shelly", "Shelly", (T.HTTP_RPC, T.MQTT, T.WIFI_LOCAL), (D.SWITCH, D.LIGHT, D.SENSOR, D.PUMP, D.HEATER), (C.POWER, C.BRIGHTNESS, C.TEMPERATURE, C.HUMIDITY, C.VOLTAGE, C.CURRENT, C.POWER_METER, C.ENERGY), S.COMPATIBLE, V.VENDOR_VERIFIED, True, notes="Documented local RPC/MQTT capabilities are preferred; exact device functions remain model-specific."),
    ProviderDescriptor("zigbee", "Zigbee", "Generic Zigbee", (T.ZIGBEE, T.MQTT, T.BRIDGE), _COMMON_GROW + (D.GATEWAY,), _COMMON_CAPS + (C.SOIL_MOISTURE, C.EC, C.PH, C.ENERGY), S.EXPERIMENTAL, V.VENDOR_VERIFIED, True, notes="Gateway-neutral abstraction; Zigbee2MQTT-compatible transport is the first target."),
    ProviderDescriptor("growcentral_esp32", "Grow Central ESP32", "135er Grow Central", (T.MQTT, T.WIFI_LOCAL, T.BLE), _COMMON_GROW + (D.CAMERA, D.GATEWAY,), tuple(C), S.EXPERIMENTAL, V.CANDIDATE, True, notes="Provider covers multiple native device classes; verification is reported per concrete driver/device."),
    ProviderDescriptor("tapo", "TP-Link Tapo", "TP-Link", (T.WIFI_LOCAL, T.CLOUD), (D.SWITCH, D.LIGHT, D.CAMERA, D.SENSOR), (C.POWER, C.BRIGHTNESS, C.POWER_METER, C.ENERGY, C.TEMPERATURE, C.HUMIDITY, C.STREAM, C.SNAPSHOT), S.COMPATIBLE, V.CANDIDATE, True, notes="Existing local adapter is preserved; exact model/local-control paths require model-level verification."),
    ProviderDescriptor("fritz", "FRITZ! Smart Home", "AVM", (T.WIFI_LOCAL,), (D.SWITCH, D.SENSOR, D.HEATER), (C.POWER, C.TEMPERATURE, C.HUMIDITY, C.POWER_METER, C.ENERGY), S.COMPATIBLE, V.VENDOR_VERIFIED, True, notes="Official AHA capabilities are normalized through the existing adapter."),
    ProviderDescriptor("home_assistant", "Home Assistant", "Home Assistant", (T.WIFI_LOCAL, T.BRIDGE), _COMMON_GROW + (D.CAMERA, D.GATEWAY), tuple(C), S.COMPATIBLE, V.VENDOR_VERIFIED, True, notes="Bridge/import provider; explicit allowlists and write policy remain mandatory."),
    ProviderDescriptor("mqtt", "Generic MQTT", "Generic", (T.MQTT,), _COMMON_GROW + (D.CAMERA, D.GATEWAY), tuple(C), S.EXPERIMENTAL, V.VENDOR_VERIFIED, True, notes="Standards-based schema integration for community and DIY hardware."),
)


def provider_catalog() -> list[dict]:
    return [provider.public() for provider in PROVIDERS]


def provider_by_id(provider_id: str) -> ProviderDescriptor | None:
    return next((provider for provider in PROVIDERS if provider.id == provider_id), None)
