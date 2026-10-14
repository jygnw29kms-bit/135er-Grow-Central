# GUI smoke checks

From the repository root, run `node tests/browser/gui-smoke.cjs` with Node,
Playwright and Chromium available. The Codex cloud development environment
provides these tools. For another machine, install Playwright outside the
checkout and set `NODE_PATH` to that installation's `node_modules` directory;
set `GC_CHROMIUM` if Chromium is not at `/usr/bin/chromium`.

The test intercepts all requests to `gc.test` and uses synthetic rooms and
sensor data. It does not contact a Pi, change real settings, or validate real
sensor hardware. It covers:

- Final Master on `/ui`, separate room workspace on `/rooms`, and mobile navigation.
- Calibration-required display without provisional soil percentages.
- Room creation, zero-valued targets, optional fields and failed-save recovery.
- CSV download and runtime warning/failure/recovery states.
- Sensor diagnostics, escaped metadata and measurement-capture feedback.
- Switching rooms while an earlier sensor request is still pending.
- Layout overflow and room dialogs at widths 390, 768 and 1440 pixels.
- Room selection and refresh; missing measurements on desktop and mobile.
- Editor text persistence and recovery from invalid imports/stored drafts.

Set `GC_SCREENSHOT_DIR` to a directory outside the checkout to retain console
screenshots. The Python suite remains `python -m pytest -q`; MQTT TLS checks
also need Mosquitto and `mosquitto_passwd` (or the `GC_TEST_MOSQUITTO` and
`GC_TEST_MOSQUITTO_PASSWD` overrides).

GitHub Actions runs this suite through `.github/workflows/gui-browser-tests.yml`
with Playwright 1.62.1 and its matching Chromium. Local runs may use the installed
system Chromium through `GC_CHROMIUM`. All external service requests are stubbed.
