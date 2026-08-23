# 135er-Grow Central · Documentation Hub

<p align="center"><img src="assets/brand/135er-grow-central-lockup-v0.9.png" alt="135er-Grow Central · J.L." width="760"></p>

<p align="center"><a href="#deutsch"><strong>Deutsch</strong></a> · <a href="#english"><strong>English</strong></a></p>

> [!IMPORTANT]
> Aktueller kanonischer Release-Stand: **alpha-0.7.5 · master e339602 · Build 118 = nächster Hardwaretest-Kandidat**. Build 117 war erfolgreich getestet, ist aber überholt. Maßgeblich ist [`../RELEASE_STATE.md`](../RELEASE_STATE.md).

## Deutsch

Diese Struktur ist die technische Wissensbasis des Projekts. Historische Build-Dokumente bleiben erhalten, definieren aber nicht den aktuellen Release-Status.

## Zuerst lesen

1. [Kanonischer Release State](../RELEASE_STATE.md)
2. [Aktueller Projektstatus](PROJECT_STATUS.md)
3. [Release Pipeline](RELEASE_PIPELINE.md)
4. [GrowCentral Nexus UI Design System](DESIGN_SYSTEM_NEXUS.md)
5. [Projektgeschichte](../PROJECT_HISTORY.md)
6. [Architektur-Master](ARCHITECTURE_MASTER.md)
7. [Hardware-Testplan](HARDWARE_TEST_PLAN.md)
8. [Security & Trust Model](SECURITY_AND_TRUST_MODEL.md)
9. [Known Limitations](KNOWN_LIMITATIONS.md)
10. [Roadmap](ROADMAP.md)

## Aktueller Testfokus

- Raspberry Pi Build 118 / `pi-universal-alpha-0.7.5-118`
- First Boot / LAN / WLAN / AP / Persistenz
- Logitech C920 / UVC inklusive firmware-/modell-/USB-ID-bewusster LED-Fähigkeitserkennung
- bedingte LED-Steuerung nur auf unterstützter Hardware
- Elecrow 7-Zoll Touch-Kiosk
- FRITZ!/Tapo-Livepfade
- relevante Mars-Hydro-/BLE-Diagnosepfade

## Plattform-Dokumentation

- [API](API.md)
- [Architecture](ARCHITECTURE.md)
- [Architecture Master](ARCHITECTURE_MASTER.md)
- [Cloud](CLOUD.md)
- [Installation](INSTALLATION.md)
- [Protocol Notes](PROTOCOL_NOTES.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Sources](SOURCES.md)
- [Decision Log](DECISION_LOG.md)

## Historische Build-Dokumente

Build-spezifische Dateien wie `BUILD_71_CHECKPOINT.md`, `BUILD_72_MOBILE_V0.1.md` und die Build-85-Testnotizen sind **historische Nachweise**. Sie bleiben zur Nachvollziehbarkeit im Repository, dürfen aber nicht als aktueller Stand interpretiert werden.

## Deutsch

- [Übersicht](de/README.md)
- [Full Platform](de/FULL_PLATFORM.md)
- [Datenbank & Rechte](de/DATENBANK_UND_RECHTE.md)
- [GUI-Vorschau](de/GUI_VORSCHAU.md)
- [Raspberry Pi Test Image](de/RASPBERRY_PI_3B_TEST_IMAGE.md)

## English documentation

- [Overview](en/README.md)
- [Full Platform](en/FULL_PLATFORM.md)
- [Database & RBAC](en/DATABASE_AND_RBAC.md)
- [GUI Preview](en/GUI_PREVIEW.md)
- [Raspberry Pi Test Image](en/RASPBERRY_PI_3B_TEST_IMAGE.md)

## Dokumentationsregeln

- `implemented`: Code/Laufzeit ist nachweisbar vorhanden.
- `experimental`: vorhanden, aber nicht ausreichend am Zielgerät validiert.
- `candidate`: für den nächsten Zieltest vorgesehen, aber noch nicht hardwarevalidiert.
- `validated`: relevanter realer Zieltest erfolgreich abgeschlossen.
- `baseline/design`: Schema, Architektur oder Interface ist definiert, aber nicht zwingend komplett verdrahtet.
- `planned`: noch nicht implementiert.
- Reverse-Engineering-Angaben müssen als Beobachtung/Hypothese gekennzeichnet werden.
- Herstellerangaben, Open-Source-Referenzen, APK-Beobachtungen und Experimente werden getrennt geführt.
- Buildnummern werden aus dem kanonischen Release State übernommen, nicht lokal in einzelnen Dokumenten erfunden.

---

## English

The current canonical state is **alpha-0.7.5 · master e339602 · Build 118 = next hardware-test candidate**. Build 117 was successfully tested but is superseded. See [`../RELEASE_STATE.md`](../RELEASE_STATE.md).

Read first: [Release State](../RELEASE_STATE.md) · [Project Status](PROJECT_STATUS.md) · [Release Pipeline](RELEASE_PIPELINE.md) · [Nexus Design System](DESIGN_SYSTEM_NEXUS.md) · [Hardware Test Plan](HARDWARE_TEST_PLAN.md).

Historical build documents remain available for traceability but do not define the current release state.

Documentation status terms are `implemented`, `experimental`, `candidate`, `validated`, `baseline/design`, and `planned`. A candidate may only become validated after the relevant real target-hardware test has passed.
