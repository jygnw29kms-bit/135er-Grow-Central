# Grow-Central Soil Sensor calibration

Grow-Central native capacitive soil sensors use three references, but the three points do **not** all define the same percentage scale.

- `AIR_DRY` defines the electrical dry endpoint (0 % engineering moisture).
- `WATER_SATURATED` defines the electrical wet endpoint (100 % engineering moisture).
- `FRESH_SUBSTRATE_CC` is an agronomic reference measured in representative fresh potting substrate. Despite the historical `CC` label, it is **not** treated as field capacity and is not assigned an invented moisture percentage.

The engineering moisture value remains:

```text
moisture_percent = clamp((air_raw - current_raw) / (air_raw - wet_raw) * 100, 0, 100)
```

The fresh-substrate reference is projected onto the same electrical scale:

```text
substrate_reference_percent = (air_raw - substrate_raw) / (air_raw - wet_raw) * 100
```

Grow-Central additionally reports a dimensionless reference index:

```text
substrate_index_percent = moisture_percent / substrate_reference_percent * 100
```

Interpretation:

- `100 %` index: current electrical reading matches the calibrated fresh-substrate reference.
- `<100 %` index: drier than the fresh-substrate reference.
- `>100 %` index: wetter than the fresh-substrate reference.

`soil_substrate_delta_pp` is the signed percentage-point difference between the current engineering moisture and the fresh-substrate reference on the Air/Water scale. A +/-5 percentage-point band is considered near the reference.

The Pi recomputes these values from the signed `filtered_raw` sensor reading and the server-bound calibration record. Native firmware percentages are retained only as diagnostics/backward compatibility. This prevents the third reference from silently redefining the 0-100 % scale.
