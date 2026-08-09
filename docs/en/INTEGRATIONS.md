# Integrations – v0.6

Grow Central uses direct vendor protocols only where a stable local path is appropriate. Shelly Gen2+ gets a native local adapter. Tapo and FRITZ!SmartHome are connected through Home Assistant. Apple Home/Siri is reached through Home Assistant HomeKit Bridge. Matter remains a later native target.

The Home Assistant connector is intentionally not an arbitrary service proxy: the v0.6 baseline allows only registered `switch.*` entities and on/off commands.
