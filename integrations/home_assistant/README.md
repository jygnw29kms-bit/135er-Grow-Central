# Grow Central for Home Assistant

Copy `custom_components/grow_central` into your Home Assistant configuration's
`custom_components` directory, restart Home Assistant and add **Grow Central**
under Settings → Devices & services. Configure the explicit export lists and
separate bridge token in Grow Central first.

- [German setup, Apple Home/Siri, Alexa and Google Assistant](../../docs/de/HOME_ASSISTANT.md)
- [English setup](../../docs/en/HOME_ASSISTANT.md)

Tests use real Home Assistant config flows, entities and platform loading.
Run them in an isolated environment to avoid changing Grow Central dependencies:

```sh
python3.14 -m venv /tmp/grow-central-ha-tests
/tmp/grow-central-ha-tests/bin/pip install homeassistant==2026.10.1 pytest pytest-asyncio
/tmp/grow-central-ha-tests/bin/python -m pytest -q integrations/home_assistant/tests/runtime_checks.py
```

The CI matrix also checks Home Assistant 2025.1.4 with Python 3.12. Hardware,
cloud account linking and voice commands require validation on the target setup.
The ZIP artifact contains the `custom_components/grow_central` folder; extract it
into your Home Assistant configuration directory. This is a custom integration,
not an official Home Assistant core integration or certified HomeKit accessory.
