# Home Assistant, Apple Home/Siri, Alexa and Google Assistant

Grow Central exports explicitly selected sensor readings and approved switches
through a local Home Assistant custom integration. Home Assistant provides the
maintained HomeKit, Alexa and Google bridges; Android and iOS also support the
Home Assistant Companion app.

## Configure Grow Central

Complete first-boot setup and configure the existing service environment:

```dotenv
GC_HA_EXPORT_ENABLED=true
GC_HA_BRIDGE_TOKEN=<separate-random-secret-at-least-32-characters>
GC_HA_EXPORT_DEVICE_IDS=lamp,growcentral_esp32:gc-soil-aabbcc
GC_HA_EXPORT_SWITCH_IDS=lamp
```

Use actual device IDs and generate a random secret, for example with
`openssl rand -hex 32`. Keep it in protected local configuration, never Git.
Restart Grow Central. Empty lists export nothing. Native sensors require manual
trust acceptance. Switches additionally require approval, write permission and
`GC_SMARTHOME_ENABLED=true`; every command checks current permissions. Imported
Home Assistant devices are excluded to prevent loops. Other configured runtime
providers (e.g. `zigbee:climate`) may be explicitly selected as measurements only.

The dedicated token can access only `/api/v1/home-assistant/*`. It is not the
administrator API token. Prefer trusted HTTPS; HTTP transmits the token without
encryption and should only be used on an isolated trusted LAN. TLS verification
is enabled and redirects are refused. Do not expose the Grow Central API through
router port forwarding.

## Install and connect

Copy `integrations/home_assistant/custom_components/grow_central` into the
Home Assistant configuration directory as `custom_components/grow_central`.
Restart HA, then add **Grow Central** under Settings → Devices & services. Enter
the plain local HTTP(S) origin and dedicated bridge token. Polling runs every
30 seconds; offline or removed devices become unavailable. New selected sensors
are added automatically. Authentication failures offer token reauthentication.
For an origin change, remove and re-add the integration.

## Voice assistants

- **Apple Home/Siri:** add HA's HomeKit Bridge, select only intended entities and
  pair its displayed code using the Apple Home app. Initial pairing requires
  reachable local networking/mDNS; remote Apple access requires a supported home
  hub. Temperature, humidity and switches are supported. Numerical soil moisture
  is not a supported HomeKit sensor class and remains in the HA dashboard.
- **Alexa and Google Assistant:** use Home Assistant Cloud/Nabu Casa, explicitly
  expose desired entities, then link the HA account in Alexa/Google Home. This
  requires an account and may require a paid subscription. Android uses the same
  account-linking path. Official manual setup is also available, requiring your
  own Google project or Amazon Smart Home skill and account-linking backend.
  Google also does not support numerical `moisture` sensors. Voice capabilities
  vary by entity class and assistant.
- **Android/iOS:** install the Home Assistant Companion app and connect it to
  your HA instance for sensor dashboards and manual control.

The software was checked using real Home Assistant 2025.1.4/Python 3.12 and
2026.10.1/Python 3.14 runtimes. Actual account linking, voice commands and device
operation must be verified on your target hardware. This custom integration does
not implement BLE sensor provisioning or create external accounts/certificates.

Official sources and their verification record:
[German setup and source list](../de/HOME_ASSISTANT.md),
[smart-home source register](../SMART_HOME_SOURCES.md).
