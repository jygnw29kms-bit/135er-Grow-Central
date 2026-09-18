<p align="center"><img src="docs/assets/brand/repository-banner-v0.9.png" alt="135er-Grow Central" width="100%"></p>

<p align="center"><strong>Open Source · Local First · Raspberry Pi · Desktop + Mobile</strong></p>

# 135er-Grow Central

> **Vollständig Open Source.** Entwicklung, Quellcode, Dokumentation, Images und veröffentlichbare technische Komponenten werden transparent über dieses Repository bereitgestellt.

135er-Grow Central ist eine lokale Steuerungs-, Überwachungs- und Automationsplattform für Grow-Umgebungen. Ein Raspberry Pi bildet die lokale Zentrale; Browser, Smartphone, Tablet und mobile Clients dienen als Bedienoberflächen. Eine Cloud-Anbindung ist optional und ersetzt nicht die lokale Geräteautorität.

## Open-Source-Grundsatz

Grow Central wird **vollständig als Open-Source-Projekt** entwickelt. Das Repository ist die zentrale öffentliche Referenz für Quellcode, Dokumentation, Build-Informationen und veröffentlichbare Artefakte.

- Beiträge, Issues und Pull Requests sind ausdrücklich willkommen.
- Die kanonische Dokumentation wird öffentlich gepflegt.
- Build- und Release-Informationen werden nachvollziehbar dokumentiert.
- Sicherheitsrelevante Geheimnisse, Zugangsdaten, private Schlüssel und personenbezogene Daten gehören niemals ins Repository.
- Die Open-Source-Lizenz gilt für die jeweils veröffentlichten Projektbestandteile gemäß `LICENSE`.

## Aktueller Referenzstand

| Bereich | Stand |
|---|---|
| Version | `alpha-0.7.5` |
| Aktueller Pi-Candidate | **Build 199** |
| Release-Tag | `pi-universal-alpha-0.7.5-199` |
| Quellstand des Candidates | `34442bc41d2c79328d3d5c61eb63a744f4c433a6` |
| Veröffentlichungsdatum | 31. August 2026 |
| Status | `CANDIDATE` – automatisierte Gates bestanden, reale Hardwarevalidierung offen |
| Entwicklungsmodus | **Open Source / öffentlich** |

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
4. Öffentliche Builds, Images, App-Pakete und Installationsskripte werden – sofern technisch und rechtlich veröffentlichbar – über die Open-Source-Projektkanäle dokumentiert und bereitgestellt.
5. Die öffentliche Projektseite unter [grow-central.de](https://grow-central.de/) dient als Einstiegspunkt und verweist auf Repository, Dokumentation und veröffentlichte Releases.
6. Zugangsdaten, Tokens, private Schlüssel, lokale Adressen, Diagnosepakete mit personenbezogenen Daten und sonstige Geheimnisse werden niemals veröffentlicht.

## Lizenz

Das Projekt steht unter der **MIT License**. Siehe [`LICENSE`](LICENSE).

Die MIT-Lizenz erlaubt Nutzung, Veränderung, Veröffentlichung, Weitergabe und Verkauf der Software unter den dort genannten Bedingungen. Drittanbieter-Komponenten können eigene Lizenzen und Hinweise enthalten; diese bleiben jeweils maßgeblich.

## Mitmachen

Beiträge sind willkommen. Für Änderungen bevorzugen wir nachvollziehbare Pull Requests mit Beschreibung, Tests bzw. Validierung und einer kurzen Dokumentation der Auswirkungen.

## Sicherheit

Bitte veröffentliche keine Zugangsdaten, API-Schlüssel, Tokens, privaten Zertifikate oder personenbezogenen Daten in Issues, Pull Requests oder Commits. Sicherheitslücken sollten verantwortungsvoll gemeldet und nicht unnötig öffentlich ausgenutzt werden.

## English summary

135er-Grow Central is a fully open-source, local-first Raspberry Pi platform for grow monitoring, device control and automation. The public repository is the canonical project reference for source code, documentation and publishable releases. Build 199 is the current `alpha-0.7.5` hardware-test candidate; automated build gates passed and physical validation is still pending.
