# Grow-Central Sensor Support Matrix

Status: 2026-10-17

Grow-Central trennt konsequent zwischen Hersteller-/Upstream-Verifikation und eigener Hardwarevalidierung.

- `gc_hardware_validated`: reale Grow-Central-Hardware wurde mit diesem Sensorpfad getestet.
- `vendor_verified`: Herstellerprotokoll, Datenblatt oder etablierter Upstream-Treiber ist verifiziert; Grow-Central-End-to-End-Hardwaretest steht noch aus.
- `candidate`: technisch plausibel, aber noch nicht ausreichend verifiziert.

| Driver-ID | Gerät | Transport | Messwerte | Status | Integrationsweg |
|---|---|---|---|---|---|
| `gc.hw390.analog` | HW-390 V2.0.0 | Analog | Bodenfeuchte | gc_hardware_validated | vorhandene GC-Soil-Firmware |
| `sensirion.sht45` | Sensirion SHT45 | I2C | Temperatur, RH | vendor_verified | offizieller Sensirion SHT4x-Treiber |
| `sensirion.scd41` | Sensirion SCD41 | I2C | CO2, Temperatur, RH | vendor_verified | offizieller Sensirion SCD4x-Treiber |
| `maxim.ds18b20` | DS18B20 | 1-Wire | Temperatur | vendor_verified | 64-Bit-ROM-ID zur Hardwareidentität nutzen |
| `dfrobot.sen0604` | DFRobot SEN0604 | RS485/Modbus RTU | Bodenfeuchte, Temp, EC, pH | vendor_verified | dokumentierte Modbus-Register |
| `dfrobot.sen0641` | DFRobot SEN0641 | RS485/Modbus RTU | PPFD/PAR | vendor_verified | dokumentierte Modbus-Register |
| `dfrobot.sen0550` | DFRobot SEN0550 | Pulse | Durchfluss, Volumen | vendor_verified | Pegelanpassung/Isolation vor ESP32-GPIO erforderlich |
| `seeed.leaf_wetness_rs485` | SenseCAP Leaf Wetness & Temperature | RS485/Modbus | Blattnässe, Blatttemperatur | vendor_verified | Modbus RTU |
| `seeed.air_th_rs485` | Seeed Industrial Air Temp/RH | RS485/Modbus | Temperatur, RH | vendor_verified | Modbus RTU |
| `seeed.liquid_level_rs485` | Seeed Industrial Liquid Level | RS485/Modbus | Wasserstand | vendor_verified | Modbus RTU |
| `shelly.blu_ht` | Shelly BLU H&T | BLE | Temperatur, RH | vendor_verified | direkte Gateway/Node-Integration, nicht kabelgebundener Hub |
| `shelly.ht_gen3` | Shelly H&T Gen3 | WLAN | Temperatur, RH | vendor_verified | lokale MQTT/Web-Integration ohne XIAO |

## Nicht neu erfinden

Für bestätigte Standards sollen bestehende Bibliotheken/Herstellerimplementierungen verwendet werden, sofern Lizenz, Wartungszustand und Zielplattform passen:

- Sensirion SHT4x: offizieller `Sensirion I2C SHT4X` Arduino-Treiber.
- Sensirion SCD4x: offizieller `Sensirion I2C SCD4X` Arduino-Treiber.
- Modbus RTU: etablierter `ModbusMaster`-Treiber als Basis; gerätespezifische Registerdefinitionen bleiben eigene dünne Adapter.
- DS18B20: OneWire/DallasTemperature-Ökosystem statt eigener 1-Wire-Protokollimplementierung.

## Identität

Eine Busadresse ist niemals alleinige Sensoridentität.

- DS18B20: 64-Bit-ROM als Hardware-ID verwenden.
- I2C: GC-UUID + Bus + Adresse + Driver-ID; echte Serien-/Produkt-ID nutzen, falls der konkrete Sensor sie bereitstellt.
- RS485/Modbus: GC-UUID + Bus + Slave-Adresse + Driver-ID; Slave-Adresse allein reicht nicht.
- Analog/Pulse: GC-UUID + physischer Port + Driver-ID + Kalibrierung.

## Gesundheitsmodell

Alle Sensoradapter liefern denselben Zustandsraum:

`GOOD`, `STALE`, `INVALID`, `BUS_ERROR`, `POWER_ERROR`, `OFFLINE`, `UNTRUSTED`, `REPLACED`.

Ungültige, veraltete oder nicht vertrauenswürdige Werte dürfen keine kritische Automation auslösen.

## Nächste reale Hardwarevalidierung

1. SHT45 am XIAO ESP32-C3.
2. SCD41 am selben I2C-Bus, Kollisions- und Langzeittest.
3. isolierter RS485-Adapter + SEN0604.
4. SEN0641 am selben RS485-Bus.
5. INA226 für 5-V-Node- und 12-V-Sensorbus-Diagnose.
6. DS18B20 mit ROM-ID-Erkennung und Austauschfall.

Erst nach bestandenem realem Test wird `vendor_verified` auf `gc_hardware_validated` angehoben.
