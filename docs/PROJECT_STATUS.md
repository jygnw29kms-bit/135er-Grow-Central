# Project Status – 135er-Grow Central

## Entwicklungsfreigabe und Pi-Abgleich · 14. November 2026

**Der zuvor angeordnete Entwicklungsstopp wurde vom Betreiber ausdrücklich aufgehoben.** Weiterentwicklung und Tests sind wieder freigegeben. Der tatsächlich installierte Pi-Stand wird in `archive/pi-live-2026-11-14` unter `pi-snapshots/2026-11-14/` quellenbezogen archiviert und mit `master` abgeglichen. Nicht veröffentlichbare Betriebsdaten, Schlüssel und Zugangsdaten bleiben ausgeschlossen. Der Archivstand ist kein vollständig verifiziertes Systemabbild und kein Release.


- **Stand:** 14. November 2026
- **Projektmodus:** Weiterentwicklung freigegeben; Pi/Git-Abgleich läuft
- **Repository:** `jygnw29kms-bit/135er-Grow-Central`, Branch `master`
- **Version letzter dokumentierter Kandidat:** `alpha-0.7.5`, Build 461, `CANDIDATE`
- **Hardwarevalidierung:** Vollständige reale Abnahme nicht bestätigt
- **Sicherung:** **Pi-Quellcode-Snapshot teilweise im Archivbranch gesichert; vollständiger Abgleich offen**

## Live-Prüfung am 14.11.2026

Der über MeshCentral erreichbare Host `135er-grow-central` (Debian 13) meldete laufende Dienste für API/Uvicorn (Port 8080), Provisioning-Broker, Cloud-Link-Agenten und HomeKit-Bridge. Der MeshCentral-Agent war ebenfalls aktiv. Der Ordner `/opt/135er-grow-central` ist **kein Git-Repository**; `git status` ist dort nicht möglich. Aus dem laufenden Prozessstatus folgt **keine** vollständige Geräte-, Sensor- oder Feature-Abnahme.

Vorhandene systemd-Timer: `grow-central-healthcheck.timer`, `grow-central-remote-watchdog.timer` und `grow-central-history-backup.timer`. Das sind Betriebs-/Wartungsfunktionen, keine nachgewiesenen Entwicklungsjobs. Sie werden durch die Dokumentationssicherung nicht deaktiviert.

## Entwicklungsbetrieb und Abgleich

1. Der Betreiber hat den zuvor angeordneten Entwicklungsstopp am 14.11.2026 ausdrücklich aufgehoben. Entwicklung, Tests und kontrollierte Deployments sind wieder freigegeben; technische Validierung und Schutz des laufenden Systems bleiben erforderlich.
2. Bestehenden Betrieb und den sicheren Fernwartungsweg nicht abschalten.
3. Keine lokalen Geheimnisse, API-Tokens, Zugangsdaten, privaten Zertifikate, Logs oder Datenbankinhalte in das öffentliche Repository übernehmen.
4. GitHub bleibt Dokumentations- und Quellreferenz. Ein selektiver Quellcode-Snapshot des Pi liegt unter `pi-snapshots/2026-11-14/` im Branch `archive/pi-live-2026-11-14`. Ein vollständiger Dateivergleich bleibt offen.
5. Die Test- und Releasepläne vom 12./13. November bleiben historische Planung; nicht als durchgeführt kennzeichnen.

## Letzter belegter Funktions-/Release-Stand

Der historische reale Pi-4-Sensortest vom 14. Oktober bestätigte Teile des USB-/MQTT-TLS-/Bodenfeuchte-Pfads. Build 461 ist laut [RELEASE_STATE.md](../RELEASE_STATE.md) der zuletzt dokumentierte Image-Candidate mit Sensor-Firmware 0.5.3. Ein vollständiger Test dieses Images auf allen Hardwareklassen und reale Schreibvalidierung der Mars-Hydro-Geräte sind offen.

Weitere technische Beschreibung und Roadmap siehe [README](../README.md), [Roadmap](ROADMAP.md), [Release State](../RELEASE_STATE.md) und [Pi-4-Testplan](de/PI4_END_TO_END_ABNAHME_2026-11-12.md).
