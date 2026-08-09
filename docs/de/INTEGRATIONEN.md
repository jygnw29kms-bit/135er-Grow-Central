# Integrationen – v0.6

GrowControl verwendet direkte Herstellerprotokolle nur dort, wo ein stabiler lokaler Weg sinnvoll ist. Shelly Gen2+ erhält einen nativen lokalen Adapter. Tapo und FRITZ!SmartHome werden über Home Assistant angebunden. Apple Home/Siri wird über Home Assistant HomeKit Bridge erreicht. Matter bleibt ein späteres natives Ziel.

Der Home-Assistant-Connector ist absichtlich kein beliebiger Service-Proxy: nur registrierte `switch.*`-Entities und Ein/Aus-Befehle sind im v0.6-Baselinepfad zugelassen.
