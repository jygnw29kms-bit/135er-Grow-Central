# Live-Pi-Quellstand vom 14. November 2026

**Gerät:** 135er-grow-central, Raspberry Pi 4 Model B, Debian 13, aarch64.  
**Installationsordner:** `/opt/135er-grow-central`  
**Vom Pi gelesener Source-Commit:** `be24ba9097c2e98eb1e3f302b5992c004d2e6e29`  
**Build:** `operator-be24ba9097c2-base508`  
**Image-Kennzeichnung:** `OPERATOR_PROVISIONED`

## Zweck

Der Ordner `pi-snapshots/2026-11-14/` enthält tatsächlich vom laufenden Pi gelesene, ausgewählte Quellcodedateien. Diese getrennte Sicherung bewahrt Pi-spezifische Änderungen, ohne den neueren `master` zu überschreiben. Die Dateien im Snapshot sind **kein neues Deployment**, kein Release und kein vollständig abgenommenes Image.

## Belegte Dateien

- `app/grow_photos.py`
- `app/mars_history.py`
- `app/mars_wifi_probe.py`
- `app/mars_fast_fan.py`
- `app/mars_fast_lamp.py`
- `app/history_compare.py`
- `app/mars_legacy_telemetry.py`
- `local/cloud_link/remote_agent.py`
- `scripts/mars_history_collect.py`
- `scripts/history_backup.py`
- `scripts/configure-mars-hydro-cloud-fan.py`
- `scripts/deploy-final-master-ui.sh`

Die tatsächliche Anwesenheit jeder Datei im Branch ist gesondert zu verifizieren. Die Aufzählung ist kein Nachweis der Vollständigkeit. Manche Dateien entsprechen bereits dem Quellstand von GitHub, andere weichen ab, beispielsweise `scripts/mars_history_collect.py`: auf dem Pi nur Lüfter, auf `master` auch Lampe.

## Noch nicht vollständig gesichert

- `app/rooms.py`, `app/camera.py` und weitere große Python-Dateien
- `web/gc-final.html`, `web/gc-final.css`, `web/gc-final.js`, `web/gc-worker.js` und Binärassets
- Gesamtes Dateiinventar, Prüfsummenabgleich und vollständiger Vergleich mit dem Quellcommit
- Ein offline wiederherstellbares Betreiber-Image und lokale Runtime-Daten (diese gehören **nicht** in das öffentliche GitHub-Repository)

Der Fernwartungs-Befehlskanal lief bei einem vollständigen Git-Vergleich in einen Timeout. Später meldete die MCP-Verbindung einen Initialisierungsfehler. Daher ist eine vollständige Sicherung sämtlicher Pi-Dateien **nicht bestätigt**.

## Sicherheitsgrenzen

Keine `.env`-Dateien, Tokens, persönlichen Schlüssel, Zertifikate, lokalen Datenbanken, History-Rohdaten, Logdateien, Hardwareidentitäten oder privaten Betreiberkonfigurationen in das **öffentliche** Repository kopieren. Für ein vollständiges Abbild ist ein getrenntes verschlüsseltes privates Backup nötig.

## Entwicklungsfreigabe und Synchronisierung

Der zuvor angeordnete Entwicklungsstopp wurde vom Betreiber am 14.11.2026 ausdrücklich aufgehoben. Die Entwicklung kann weiterlaufen. Der Archivbranch selbst ist eine Bestandsaufnahme, kein automatischer Deployment-Branch. Die erweiterten Pi-Oberflächendateien `web/gc-final.html` und `web/gc-final.js` wurden anschließend kontrolliert auf `master` übertragen; weitere Abweichungen erfordern gesonderte Prüfung.
