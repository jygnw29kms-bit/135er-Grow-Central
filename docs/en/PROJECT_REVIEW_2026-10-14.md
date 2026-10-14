# Project review – 14 October 2026

The authoritative baseline is the current `master` with Final Master on `/ui`.
Build 375 and firmware 0.4.1 remain candidates; these source changes do not
publish a new image or establish additional hardware validation.

## Implemented in this review

- Room mutations now lock the complete read/modify/write operation, including
  USB and network sensor acceptance. Sensor capture reads the latest room state
  after network I/O, preserving concurrent edits, journals and deletions.
- Sensor values must be finite and in the accepted range. Legacy temperature
  and humidity field names are recognized; missing values remain absent.
- `/api/v1/rooms/{room_id}/sensors.csv` exports the most recent samples for one
  room. Default: 5,000; maximum: 50,000. CSV source labels are protected against
  spreadsheet formula execution. Soil values are named `soil_reference_percent`
  and marked `calibration_required` rather than presented as calibrated data.
- `/rooms` offers an authenticated CSV download. Runtime warnings, room freshness,
  camera snapshots and automation definitions use accurate status wording.
- A GitHub Actions workflow runs synthetic Chromium checks for GUI changes
  using pinned Playwright and no production credentials. The workflow itself
  awaits its first GitHub run; the browser suite was exercised locally.
- Roadmap and project metadata reflect Build 375, firmware 0.4.1, the implemented
  diagnostics and the limitations of stored automation definitions.

## Still pending

Actual Pi installation/reboot/endurance tests, substrate calibration, a tested
scheduler, backup/restore, real time-range charts, and optional cloud/assistant
end-to-end tests require further work. The WYSIWYG editor remains a local draft
editor; it does not apply arbitrary layouts to the productive UI.

## Validation

Run `python -m pytest -q` with native Mosquitto tools for MQTT TLS tests and
`node tests/browser/gui-smoke.cjs` for synthetic Chromium checks. The tests cover
concurrent edits/deletion during sensor reads, parallel journal updates,
rollback, corrupt state, invalid measurements, CSV scope and escaping, runtime
failure/recovery, and responsive GUI workflows. Hardware and production
deployments are outside these checks.

See the [current roadmap](../ROADMAP.md), [project status](../PROJECT_STATUS.md)
and [known limitations](../KNOWN_LIMITATIONS.md).
