# Smart-Home source register

Checked for the v0.6 architecture on 2026-08-09.

## Apple

- Apple Developer – HomeKit: https://developer.apple.com/documentation/homekit/
- Apple Developer – Matter: https://developer.apple.com/documentation/matter
- Apple Developer – Developing apps and accessories for the home: https://developer.apple.com/apple-home/
- Apple Developer – Matter support in iOS: https://developer.apple.com/apple-home/matter/

Architecture consequence: v0.6 does not claim to be a certified native HomeKit accessory. Home Assistant HomeKit Bridge is the practical interoperability path; native Matter bridge work is deferred.

## Home Assistant

- HomeKit Bridge: https://www.home-assistant.io/integrations/homekit/
- TP-Link Smart Home / Tapo: https://www.home-assistant.io/integrations/tplink/
- FRITZ!SmartHome: https://www.home-assistant.io/integrations/fritzbox/

Architecture consequence: Tapo and FRITZ! devices are integrated through the maintained Home Assistant device integrations, while selected Home Assistant entities can be exposed to Apple Home through HomeKit Bridge.

## Shelly

- Gen2+ RPC channels: https://shelly-api-docs.shelly.cloud/gen2/General/RPCChannels/
- Gen2+ RPC protocol: https://shelly-api-docs.shelly.cloud/gen2/General/RPCProtocol/

Architecture consequence: Shelly Gen2+ is suitable for a restricted native local JSON-RPC adapter.

## Home Assistant export update — 2026-10-13

The maintained documentation sources for HomeKit, Google Assistant, Alexa and
Home Assistant Cloud were retrieved from the official `home-assistant.io`
GitHub repository (`current/source/_integrations/*.markdown`). Direct website
retrieval returned HTTP 403. These sources support the local HomeKit Bridge and
Cloud/account-linking architecture. Numerical soil moisture (`moisture`) is not
one of HomeKit's numerical sensor classes or Google Assistant's supported sensor
classes; it remains available in Home Assistant. No voice compatibility is
inferred merely from a percentage unit.

- https://github.com/home-assistant/home-assistant.io/blob/current/source/_integrations/homekit.markdown
- https://github.com/home-assistant/home-assistant.io/blob/current/source/_integrations/google_assistant.markdown
- https://github.com/home-assistant/home-assistant.io/blob/current/source/_integrations/alexa.markdown
- https://github.com/home-assistant/home-assistant.io/blob/current/source/_integrations/cloud.markdown

Implementation and setup: [Home Assistant](de/HOME_ASSISTANT.md).
