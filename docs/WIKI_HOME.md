# 135er-Grow Central Wiki · Canonical Home

> Diese Datei ist die kanonische Wiki-Startseite im Repository. Die GitHub-Wiki-Funktion ist aktiviert, wird aber nicht als zweite unabhängige Release-Quelle gepflegt. Inhalte sollen von hier übernommen werden.

## Aktueller Stand

- Version: `alpha-0.7.5`
- Master-Anker: `e339602`
- vorheriger erfolgreicher Teststand: Build 117, inzwischen überholt
- nächster Raspberry-Pi-Hardwaretest: **Build 118**
- Kandidaten-Tag: `pi-universal-alpha-0.7.5-118`
- Status Build 118: **CANDIDATE**, noch nicht hardwarevalidiert
- Design: **GrowCentral Nexus UI**

## Einstieg

1. [Release State](../RELEASE_STATE.md)
2. [Projektstatus](PROJECT_STATUS.md)
3. [Release Pipeline](RELEASE_PIPELINE.md)
4. [Nexus Design System](DESIGN_SYSTEM_NEXUS.md)
5. [Hardware Testplan](HARDWARE_TEST_PLAN.md)
6. [Cloud](CLOUD.md)
7. [Security & Trust Model](SECURITY_AND_TRUST_MODEL.md)
8. [Mobile](../mobile/README.md)
9. [Website](../website/README.md)

## Build 118

Build 118 ist der nächste reale Hardwaretest-Kandidat auf Basis des konsolidierten `e339602`-Stands. Enthalten sind unter anderem aktuelle GUI-/Netzwerk-/FRITZ-/Tapo-/C920-Funktionen, firmware-/modell-/USB-ID-bewusste Kamera-LED-Fähigkeitserkennung, bedingte LED-Steuerung, Elecrow-7-Zoll-Kiosk, Grow-/Raumfunktionen und die gemeinsame Nexus-Designsprache.

## Plattformen

- Raspberry Pi: lokale Geräteautorität
- Android: Nexus WebGUI Client / APK
- iOS: Nexus WebGUI Client / unsigned Sideload IPA
- Cloud: optionaler Serverpfad V6
- APT: signiert unter `https://repo.dezender.de/apt`
- Website: read-only Project Console unter `https://dezender.de`

## Release-Regel

Ein Kandidat wird erst nach realem Zieltest als `VALIDATED` bezeichnet. Historische Build-Seiten und alte Wiki-Inhalte dürfen nicht als aktueller Status verwendet werden, wenn sie `RELEASE_STATE.md` widersprechen.
