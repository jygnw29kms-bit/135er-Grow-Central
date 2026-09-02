<p align="center"><img src="docs/assets/brand/repository-banner-v0.9.png" alt="135er-Grow Central" width="100%"></p>

<p align="center"><strong>Closed Development · Local First · Raspberry Pi · Desktop + Mobile</strong></p>

# 135er-Grow Central

> **Vertrauliches Entwicklungsprojekt.** Dieses Repository ist nicht als Open-Source-Projekt freigegeben. Quellcode, Images, mobile Testpakete, interne Dokumentation und technische Details sind ausschließlich für autorisierte Projektbeteiligte bestimmt.

135er-Grow Central ist eine lokale Steuerungs-, Überwachungs- und Automationsplattform für Grow-Umgebungen. Ein Raspberry Pi bildet die lokale Zentrale; Browser, Smartphone, Tablet und die mobilen Clients dienen als Bedienoberflächen. Eine Cloud-Anbindung ist optional und ersetzt nicht die lokale Geräteautorität.

## Aktueller Referenzstand

| Bereich | Stand |
|---|---|
| Version | `alpha-0.7.5` |
| Aktueller Pi-Candidate | **Build 199** |
| Release-Tag | `pi-universal-alpha-0.7.5-199` |
| Quellstand des Candidates | `34442bc41d2c79328d3d5c61eb63a744f4c433a6` |
| Veröffentlichungsdatum | 31. August 2026 |
| Status | `CANDIDATE` – automatisierte Gates bestanden, reale Hardwarevalidierung offen |
| Entwicklungsmodus | **Closed / nicht öffentlich distribuieren** |

Verbindliche Detailquelle ist [`RELEASE_STATE.md`](RELEASE_STATE.md). Historische Build-Dokumente bleiben nachvollziehbar, definieren aber nicht den aktuellen Projektstand.

## Produktprinzipien

- **Local First:** Steuerung, Messwerte und Automationen bleiben grundsätzlich vor Ort verfügbar.
- **Headless Appliance:** Der Pi benötigt keinen eigenen Desktop oder Monitor.
- **Eine Oberfläche pro Gerätetyp:** Desktop- und Mobile-Ansichten sind für ihren jeweiligen Einsatz optimiert.
- **Herstellerübergreifend:** Geräte werden über eine gemeinsame Plattform eingebunden.
- **Sichere Standardwerte:** Keine bekannten Factory-Passwörter; SSH wird nur ausdrücklich aktiviert.
- **Optionale Cloud:** Fernzugriff und Verwaltung können ergänzt werden, die lokale Instanz bleibt maßgeblich.

## Geplanter und implementierter Funktionsumfang

- geführte Ersteinrichtung mit Netzwerkübernahme;
- Räume, Grow-Bereiche und Gerätezuordnung;
- Sensorwerte, Verlauf und Zustandsübersicht;
- Zeitpläne und zustandsbasierte Automationen;
- Kamera-Unterstützung für geeignete UVC-Geräte;
- einheitliche Diagnose- und Laufzeitübersicht;
- Desktop-Weboberfläche sowie eigene mobile Oberfläche;
- iOS-Sideload- und Android-Testclients;
- optionale Cloud- und Verwaltungsfunktionen.

Der jeweilige Funktionsstatus ist modell-, firmware- und hardwareabhängig. Eine vorhandene Integration bedeutet nicht automatisch, dass sämtliche Lese- und Schreibfunktionen bereits für jedes Gerät freigegeben sind.

## Geräteökosysteme

Aktuell werden Integrationspfade für unter anderem folgende Systeme entwickelt oder validiert:

- AVM FRITZ! Smart Home
- TP-Link Tapo
- Shelly
- Tuya / Smart Life
- Mars Hydro
- Spider Farmer
- Home Assistant
- Zigbee2MQTT und generisches MQTT
- Grow-Central-ESP32-Sensoren und -Aktoren
- Logitech C920 und weitere geeignete UVC-Kameras

Schreibzugriffe bleiben gesperrt, solange Protokoll, Modell oder Firmware nicht ausreichend validiert sind.

## Hardwarestrategie

Grow Central verwendet weiterhin ein Universal-Image mit zentraler Hardwareerkennung.

| Hardware | Klasse | Einordnung |
|---|---|---|
| Raspberry Pi 3B / 3B+ | Legacy/Lite | unterstützt mit konservativen Ressourcenprofilen |
| Raspberry Pi 4B / 400 / CM4 | Full Support | empfohlene Standardplattform |
| Raspberry Pi 5 / CM5 | Full Support Performance | Plattform mit zusätzlicher Leistungsreserve |

Separate Images entstehen nur, wenn unterschiedliche Kernel-, Paket- oder Servicebasen technisch zwingend werden.

## Release-Regeln

1. `master` und die kanonische Dokumentation bilden immer den neuesten bekannten Projektstand ab.
2. Ein erfolgreicher CI-Lauf oder Image-Build erhält zunächst den Status `CANDIDATE`.
3. `VALIDATED` wird erst nach dokumentiertem Test auf realer Zielhardware vergeben.
4. Neue Builds, Images, App-Pakete und Installationsskripte werden bis auf Weiteres nicht öffentlich verteilt.
5. Die öffentliche Seite unter [dezender.de/GC](https://dezender.de/GC/) erklärt nur Produktnutzen und Entwicklungsstatus; interne Downloads, Commit-IDs, Protokolle und Betriebsdetails bleiben dort verborgen.

## Lizenz- und Vertraulichkeitshinweis

Das Repository wurde bisher mit einer MIT-Lizenz veröffentlicht. Eine spätere Umstellung auf private Entwicklung widerruft Rechte an bereits unter dieser Lizenz bezogenen Fassungen nicht. Bis eine mögliche Neulizenzierung für künftige Fassungen rechtlich und mit allen Rechteinhabern geklärt ist, bleibt die Datei [`LICENSE`](LICENSE) maßgeblich. Unabhängig davon gehören Zugangsdaten, Tokens, Schlüssel, lokale Adressen, Diagnosepakete und Kundendaten weder in Commits noch in öffentliche Artefakte.

## English summary

135er-Grow Central is a closed-development, local-first Raspberry Pi platform for grow monitoring, device control and automation. Build 199 is the current `alpha-0.7.5` hardware-test candidate. Automated build gates passed; physical validation is still pending. Source code, images, mobile packages and internal technical documentation are not intended for public distribution.
