#pragma once

#include <Arduino.h>

namespace gc::sensors {

enum class Transport : uint8_t { Analog, I2C, OneWire, RS485Modbus, Pulse, Digital, Ble, Wifi };
enum class Verification : uint8_t { VendorVerified, GcHardwareValidated, Candidate };
enum class Health : uint8_t { Good, Stale, Invalid, BusError, PowerError, Offline, Untrusted, Replaced };

struct DriverDescriptor {
  const char* id;
  const char* product;
  Transport transport;
  Verification verification;
  const char* capabilities;
  const char* identityStrategy;
  const char* notes;
};

// VendorVerified = manufacturer/upstream protocol or driver is documented/tested.
// It is NOT a Grow-Central real-hardware validation. Only GcHardwareValidated may claim that.
static constexpr DriverDescriptor kDriverCatalog[] = {
  {"gc.hw390.analog", "HW-390 V2.0.0", Transport::Analog, Verification::GcHardwareValidated,
   "soil_moisture", "gc_uuid+physical_port+calibration", "Current GC reference sensor"},
  {"sensirion.sht45", "Sensirion SHT45", Transport::I2C, Verification::VendorVerified,
   "air_temperature,relative_humidity", "gc_uuid+i2c_bus+address+driver", "Use official Sensirion SHT4x library"},
  {"sensirion.scd41", "Sensirion SCD41", Transport::I2C, Verification::VendorVerified,
   "co2,air_temperature,relative_humidity", "gc_uuid+i2c_bus+address+driver", "Use official Sensirion SCD4x library; SHT45 remains preferred climate reference"},
  {"maxim.ds18b20", "DS18B20", Transport::OneWire, Verification::VendorVerified,
   "water_temperature,temperature", "rom64", "Use unique 64-bit ROM as hardware identity"},
  {"dfrobot.sen0604", "DFRobot SEN0604", Transport::RS485Modbus, Verification::VendorVerified,
   "soil_moisture,soil_temperature,soil_ec,soil_ph", "gc_uuid+modbus_bus+slave_address+driver", "Never use slave address alone as physical identity"},
  {"dfrobot.sen0641", "DFRobot SEN0641", Transport::RS485Modbus, Verification::VendorVerified,
   "ppfd,par", "gc_uuid+modbus_bus+slave_address+driver", "Documented Modbus RTU device"},
  {"dfrobot.sen0550", "DFRobot SEN0550", Transport::Pulse, Verification::VendorVerified,
   "flow_rate,volume", "gc_uuid+physical_port+driver", "Level adaptation/isolation required before ESP32 GPIO"},
  {"seeed.leaf_wetness_rs485", "SenseCAP Industrial Leaf Wetness & Temperature", Transport::RS485Modbus, Verification::VendorVerified,
   "leaf_wetness,leaf_temperature", "gc_uuid+modbus_bus+slave_address+driver", "Industrial RS485/Modbus sensor"},
  {"seeed.air_th_rs485", "Seeed Industrial Air Temperature & Humidity", Transport::RS485Modbus, Verification::VendorVerified,
   "air_temperature,relative_humidity", "gc_uuid+modbus_bus+slave_address+driver", "Industrial RS485/Modbus sensor"},
  {"seeed.liquid_level_rs485", "Seeed Industrial Liquid Level Sensor", Transport::RS485Modbus, Verification::VendorVerified,
   "liquid_level", "gc_uuid+modbus_bus+slave_address+driver", "Prefer native Modbus where available"},
  {"shelly.blu_ht", "Shelly BLU H&T", Transport::Ble, Verification::VendorVerified,
   "air_temperature,relative_humidity", "ble_identity+gc_uuid", "Gateway/node integration, not wired hub"},
  {"shelly.ht_gen3", "Shelly H&T Gen3", Transport::Wifi, Verification::VendorVerified,
   "air_temperature,relative_humidity", "device_identity+gc_uuid", "Local MQTT/web integration; no XIAO required"}
};

static constexpr size_t kDriverCatalogSize = sizeof(kDriverCatalog) / sizeof(kDriverCatalog[0]);

} // namespace gc::sensors
