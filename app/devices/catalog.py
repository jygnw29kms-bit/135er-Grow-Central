from __future__ import annotations

from .models import Capability as C
from .models import DeviceClass as D
from .models import ProviderDescriptor, SupportLevel as S, Transport as T

_COMMON_GROW = (D.LIGHT, D.FAN, D.SWITCH, D.PUMP, D.HUMIDIFIER, D.DEHUMIDIFIER, D.HEATER, D.SENSOR, D.CONTROLLER)
_COMMON_CAPS = (C.POWER, C.BRIGHTNESS, C.FAN_SPEED, C.TEMPERATURE, C.HUMIDITY, C.VPD, C.SCHEDULE, C.MODE)

PROVIDERS: tuple[ProviderDescriptor, ...] = (
    ProviderDescriptor("mars_hydro", "Mars Hydro", "Mars Hydro", (T.BLE, T.CLOUD, T.MQTT), _COMMON_GROW, _COMMON_CAPS + (C.PPFD, C.SOIL_MOISTURE, C.SOIL_TEMPERATURE, C.EC), S.EXPERIMENTAL, True, notes="iConnect/Mars Pro transport selected per model; unsafe raw writes remain gated."),
    ProviderDescriptor("spider_farmer", "Spider Farmer", "Spider Farmer", (T.BLE, T.WIFI_LOCAL, T.MQTT), _COMMON_GROW, _COMMON_CAPS + (C.OSCILLATION,), S.EXPERIMENTAL, True, notes="GGS local BLE is the preferred reference path; model mappings remain explicit."),
    ProviderDescriptor("tuya", "Tuya / Smart Life", "Tuya", (T.WIFI_LOCAL, T.CLOUD, T.ZIGBEE), _COMMON_GROW, _COMMON_CAPS + (C.VOLTAGE, C.CURRENT, C.POWER_METER, C.ENERGY), S.EXPERIMENTAL, True, notes="Tuya DPs are normalized before reaching the entity API."),
    ProviderDescriptor("ac_infinity", "AC Infinity", "AC Infinity", (T.BLE, T.CLOUD, T.BRIDGE), _COMMON_GROW, _COMMON_CAPS, S.DETECTED, True, notes="Provider boundary reserved from day one; model protocols must be validated before writes."),
    ProviderDescriptor("vivosun", "VIVOSUN", "VIVOSUN", (T.BLE, T.CLOUD, T.BRIDGE), _COMMON_GROW, _COMMON_CAPS, S.DETECTED, True, notes="GrowHub/E-series support is model-mapped; no generic unsafe control assumptions."),
    ProviderDescriptor("shelly", "Shelly", "Shelly", (T.HTTP_RPC, T.MQTT, T.WIFI_LOCAL), (D.SWITCH, D.LIGHT, D.SENSOR, D.PUMP, D.HEATER), (C.POWER, C.BRIGHTNESS, C.TEMPERATURE, C.HUMIDITY, C.VOLTAGE, C.CURRENT, C.POWER_METER, C.ENERGY), S.COMPATIBLE, True, notes="Existing adapter migrates behind the universal entity layer; Gen2+ RPC is preferred."),
    ProviderDescriptor("zigbee", "Zigbee", "Generic Zigbee", (T.ZIGBEE, T.MQTT, T.BRIDGE), _COMMON_GROW + (D.GATEWAY,), _COMMON_CAPS + (C.SOIL_MOISTURE, C.EC, C.PH, C.ENERGY), S.EXPERIMENTAL, True, notes="Gateway-neutral abstraction; Zigbee2MQTT-compatible transport is the first target."),
    ProviderDescriptor("growcentral_esp32", "Grow Central ESP32", "135er Grow Central", (T.MQTT, T.WIFI_LOCAL, T.BLE), _COMMON_GROW + (D.GATEWAY,), tuple(C), S.EXPERIMENTAL, True, notes="Native reference provider and protocol for optional Grow Central sensor/actuator modules."),
    ProviderDescriptor("tapo", "TP-Link Tapo", "TP-Link", (T.WIFI_LOCAL, T.CLOUD), (D.SWITCH, D.LIGHT, D.CAMERA, D.SENSOR), (C.POWER, C.BRIGHTNESS, C.POWER_METER, C.ENERGY, C.TEMPERATURE, C.HUMIDITY, C.STREAM, C.SNAPSHOT), S.COMPATIBLE, True, notes="Existing local adapter is preserved and migrated behind this provider."),
    ProviderDescriptor("fritz", "FRITZ! Smart Home", "AVM", (T.WIFI_LOCAL,), (D.SWITCH, D.SENSOR, D.HEATER), (C.POWER, C.TEMPERATURE, C.HUMIDITY, C.POWER_METER, C.ENERGY), S.COMPATIBLE, True, notes="Existing AHA adapter is preserved."),
    ProviderDescriptor("home_assistant", "Home Assistant", "Home Assistant", (T.WIFI_LOCAL, T.BRIDGE), _COMMON_GROW + (D.CAMERA, D.GATEWAY), tuple(C), S.COMPATIBLE, True, notes="Bridge/import provider; entities are normalized and write policy remains explicit."),
    ProviderDescriptor("mqtt", "Generic MQTT", "Generic", (T.MQTT,), _COMMON_GROW + (D.CAMERA, D.GATEWAY), tuple(C), S.EXPERIMENTAL, True, notes="Schema-based integration for community and DIY hardware."),
)


def provider_catalog() -> list[dict]:
    return [provider.public() for provider in PROVIDERS]


def provider_by_id(provider_id: str) -> ProviderDescriptor | None:
    return next((provider for provider in PROVIDERS if provider.id == provider_id), None)
