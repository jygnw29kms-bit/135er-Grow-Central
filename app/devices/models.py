from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class SupportLevel(_StringEnum):
    DETECTED = "detected"
    EXPERIMENTAL = "experimental"
    COMPATIBLE = "compatible"
    VALIDATED = "validated"
    CERTIFIED = "certified"


class Transport(_StringEnum):
    BLE = "ble"
    WIFI_LOCAL = "wifi_local"
    CLOUD = "cloud"
    MQTT = "mqtt"
    ZIGBEE = "zigbee"
    USB = "usb"
    SERIAL = "serial"
    HTTP_RPC = "http_rpc"
    BRIDGE = "bridge"


class DeviceClass(_StringEnum):
    LIGHT = "light"
    FAN = "fan"
    SWITCH = "switch"
    PUMP = "pump"
    HUMIDIFIER = "humidifier"
    DEHUMIDIFIER = "dehumidifier"
    HEATER = "heater"
    SENSOR = "sensor"
    CAMERA = "camera"
    CONTROLLER = "controller"
    GATEWAY = "gateway"


class Capability(_StringEnum):
    POWER = "power"
    BRIGHTNESS = "brightness"
    FAN_SPEED = "fan_speed"
    OSCILLATION = "oscillation"
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    VPD = "vpd"
    PPFD = "ppfd"
    SOIL_MOISTURE = "soil_moisture"
    SOIL_TEMPERATURE = "soil_temperature"
    EC = "ec"
    PH = "ph"
    VOLTAGE = "voltage"
    CURRENT = "current"
    POWER_METER = "power_meter"
    ENERGY = "energy"
    SCHEDULE = "schedule"
    MODE = "mode"
    SNAPSHOT = "snapshot"
    STREAM = "stream"


@dataclass(frozen=True, slots=True)
class ProviderDescriptor:
    id: str
    name: str
    manufacturer: str
    transports: tuple[Transport, ...]
    device_classes: tuple[DeviceClass, ...]
    capabilities: tuple[Capability, ...]
    support: SupportLevel
    local_first: bool
    enabled_by_default: bool = True
    notes: str = ""

    def public(self) -> dict[str, Any]:
        row = asdict(self)
        row["transports"] = [item.value for item in self.transports]
        row["device_classes"] = [item.value for item in self.device_classes]
        row["capabilities"] = [item.value for item in self.capabilities]
        row["support"] = self.support.value
        return row
