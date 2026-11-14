# Project Status – 135er-Grow Central

## Entwicklungsfreigabe und Pi-Abgleich · 14. November 2026

**Der zuvor angeordnete Entwicklungsstopp wurde vom Betreiber ausdrücklich aufgehoben.** Weiterentwicklung und Tests sind wieder freigegeben. Der tatsächlich installierte Pi-Stand wird in `archive/pi-live-2026-11-14` unter `pi-snapshots/2026-11-14/` quellenbezogen archiviert und mit `master` abgeglichen. Nicht veröffentlichbare Betriebsdaten, Schlüssel und Zugangsdaten bleiben ausgeschlossen. Der Archivstand ist kein vollständig verifiziertes Systemabbild und kein Release.


- **Stand:** 14. November 2026
- **Projektmodus:** Weiterentwicklung freigegeben; Pi/Git-Abgleich läuft
- **Repository:** `jygnw29kms-bit/135er-Grow-Central`, Branch `master`
- **Version letzter dokumentierter Kandidat:** `alpha-0.7.5`, Build 461, `CANDIDATE`
- **Hardwarevalidierung:** Vollständige reale Abnahme nicht bestätigt
- **Synchronisierung:** Pi-Snapshot im Archivbranch; die aktuellen Raum-/Growbuch-Oberflächendateien `web/gc-final.html` und `web/gc-final.js` auf `master` übertragen; vollständiger Abgleich offen.

## Live-Prüfung am 14.11.2026

Der über MeshCentral erreichbare Host `135er-grow-central` (Debian 13) meldete laufende Dienste für API/Uvicorn (Port 8080), Provisioning-Broker, Cloud-Link-Agenten und HomeKit-Bridge. Der MeshCentral-Agent war ebenfalls aktiv. Der Ordner `/opt/135er-grow-central` ist **kein Git-Repository**; `git status` ist dort nicht möglich. Aus dem laufenden Prozessstatus folgt **keine** vollständige Geräte-, Sensor- oder Feature-Abnahme.

Vorhandene systemd-Timer: `grow-central-healthcheck.timer`, `grow-central-remote-watchdog.timer` und `grow-central-history-backup.timer`. Das sind Betriebs-/Wartungsfunktionen, keine nachgewiesenen Entwicklungsjobs. Sie werden durch die Dokumentationssicherung nicht deaktiviert.

## Entwicklungsbetrieb und Abgleich

1. Der Betreiber hat den zuvor angeordneten Entwicklungsstopp am 14.11.2026 ausdrücklich aufgehoben. Entwicklung, Tests und kontrollierte Deployments sind wieder freigegeben; technische Validierung und Schutz des laufenden Systems bleiben erforderlich.
2. Bestehenden Betrieb und den sicheren Fernwartungsweg nicht abschalten.
3. Keine lokalen Geheimnisse, API-Tokens, Zugangsdaten, privaten Zertifikate, Logs oder Datenbankinhalte in das öffentliche Repository übernehmen.
4. GitHub bleibt Dokumentations- und Quellreferenz. Ein selektiver Quellcode-Snapshot des Pi liegt unter `pi-snapshots/2026-11-14/` im Branch `archive/pi-live-2026-11-14`. Ein vollständiger Dateivergleich bleibt offen.
5. Die Test- und Releasepläne vom 12./13. November bleiben historische Planung; nicht als durchgeführt kennzeichnen.

## Git-Abgleich am 14.11.2026

- Installierter Pi-Quellcommit: `be24ba9097c2e98eb1e3f302b5992c004d2e6e29`; Betreiber-Build `operator-be24ba9097c2-base508`.
- GitHub `master` liegt bereits deutlich vor diesem Image-Basiscommit. Der Abgleich darf nicht durch einen pauschalen Reset auf den Pi-Stand erfolgen.
- Selektive Pi-Sicherung auf [`archive/pi-live-2026-11-14`](https://github.com/jygnw29kms-bit/135er-Grow-Central/tree/archive/pi-live-2026-11-14/pi-snapshots/2026-11-14) mit echten Laufzeitquelldateien.
- Nach Vergleich wurden die Pi-Versionen von `web/gc-final.html` und `web/gc-final.js` auf `master` übertragen: Gerätezuordnung pro Raum, Raum-Growbuch und Pflanzenauswahl im Tagebuch.
- `web/gc-final.css`, `web/gc-worker.js`, `web/gc-manifest.webmanifest`, Teile von `app/history_archive.py` und weitere Skripte waren bereits inhaltlich identisch (abgesehen von Dateiende-Zeilenumbrüchen).
- Einige Pi-Dateien weichen von der aktuellen Git-Version ab, unter anderem `app/entrypoint.py`, `app/mars_history.py`, `app/rooms.py` sowie lokale Fast-BLE-Module. Diese dürfen wegen neuerer GitHub-Änderungen, möglicher installierter Sonderkonfigurationen und nicht abgeschlossener Tests nicht ungeprüft überschrieben werden.
- **Keine erneute Pi-Installation und keine vollständige Datensicherung in diesem Git-Abgleich nachgewiesen.** Lokale Zugangsdaten, Datenbanken und gerätespezifische Konfigurationen gehören nicht ins öffentliche Repository.

## Letzter belegter Funktions-/Release-Stand

Der historische reale Pi-4-Sensortest vom 14. Oktober bestätigte Teile des USB-/MQTT-TLS-/Bodenfeuchte-Pfads. Build 461 ist laut [RELEASE_STATE.md](../RELEASE_STATE.md) der zuletzt dokumentierte Image-Candidate mit Sensor-Firmware 0.5.3. Ein vollständiger Test dieses Images auf allen Hardwareklassen und reale Schreibvalidierung der Mars-Hydro-Geräte sind offen.

Weitere technische Beschreibung und Roadmap siehe [README](../README.md), [Roadmap](ROADMAP.md), [Release State](../RELEASE_STATE.md) und [Pi-4-Testplan](de/PI4_END_TO_END_ABNAHME_2026-11-12.md).

## Pi ↔ GitHub-Dateiabgleich (14.11.2026)

Der Pi ist online und meldet `SOURCE_COMMIT=be24ba9097c2e98eb1e3f302b5992c004d2e6e29`, `BUILD=operator-be24ba9097c2-base508` und `IMAGE_DISTRIBUTION=OPERATOR_PROVISIONED`. Das ist der **installierte Betreiber-Build**, nicht der ältere öffentliche Image-Candidate 461.

Die tatsächlich gelesenen Dateien wurden unter [Pi-Live-Archiv](../pi-snapshots/2026-11-14/STATUS.md) im Branch `archive/pi-live-2026-11-14` festgehalten. Ein erneuter Inhaltsvergleich zeigte `web/gc-final.html`, `web/gc-final.js`, `web/gc-final.css`, `app/grow_photos.py` und `app/history_archive.py` bereits inhaltlich gleich zum aktuellen `master`. Die lokal erfassten Versionen von `app/mars_history.py`, `app/main.py` und `local/cloud_link/remote_agent.py` wurden separat archiviert und müssen vor Übernahme auf Verhalten/Unterschiede geprüft werden. Die Übertragung von `app/rooms.py` war nachweislich abgeschnitten; die ungültige Archivkopie wurde deshalb entfernt. Der aktuelle `master` enthält die vollständige Datei, eine unabhängige Identitätsprüfung gegen die Pi-Datei steht aus.

**Wichtig:** GitHub-Quellsicherung ist kein vollständiges Pi-Systembackup. Runtime-Daten, Pflanzenfotos, Historie und Secrets müssen separat und geschützt gesichert werden. Entwicklungsstopp: **aufgehoben**; laufende Entwicklung darf weitergehen.
