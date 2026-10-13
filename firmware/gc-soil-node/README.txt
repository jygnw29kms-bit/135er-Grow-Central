Grow-Central Soil Node GC-SOIL-01

Hardware:
- Seeed Studio XIAO ESP32-C3
- Capacitive Soil Moisture Sensor HW-390 V2.0.0
- VCC -> 3V3
- GND -> GND
- AOUT -> A0 / D0 / GPIO2

Current measured engineering references:
- AIR_RAW: 3767
- WATER_RAW: 1310

Firmware features:
- 12-bit ADC on A0/GPIO2
- 64-sample acquisition windows
- 12.5% trimmed mean for outlier suppression
- Median, min/max, span and standard deviation diagnostics
- Exponential moving average for stable UI values
- Provisional 0-100% engineering scale between air and water
- Signal quality classification
- Basic sensor fault / unstable signal detection
- Persistent calibration in ESP32 NVS
- Serial machine-readable GC_SOIL telemetry at 115200 baud

Serial commands:
INFO
CAL AIR
CAL WATER
RESET CAL

Important:
The air/water calibration is an engineering verification scale, not a final substrate volumetric-water-content calibration. Final Grow-Central plant profiles should be calibrated against the actual substrate used in the grow.

Build/upload:
python -m platformio run -t upload

Monitor:
python -m platformio device monitor -p COM5 -b 115200
