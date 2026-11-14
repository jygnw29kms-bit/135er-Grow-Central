# Grow Central · Pi ↔ GitHub-Vollabgleich (14.11.2026)

## Bezugsstand und Quelle

- **Pi:** Raspberry Pi 4 Model B, Debian 13, aarch64, Betreiberinstallation unter `/opt/135er-grow-central`.
- **Pi-`SOURCE_COMMIT`:** `be24ba9097c2e98eb1e3f302b5992c004d2e6e29`.
- **Pi-`BUILD`:** `operator-be24ba9097c2-base508`.
- **Pi-`IMAGE_DISTRIBUTION`:** `OPERATOR_PROVISIONED`.
- **Git-Referenz:** `master` als Ausgangsbasis, anschließend `sync/pi-live-2026-11-14`; historischer öffentlicher Image-Candidate Build 461 bleibt eine eigene Release-Referenz.
- **Verfahren:** Vollständige Inventur der 871 auf GitHub versionierten Dateipfade durch direkten SHA-256-Vergleich auf dem Pi mit einem frischen GitHub-Checkout. Änderungen wurden über Git-Blobs übertragen und gegen `git hash-object` der lokalen Pi-Originaldateien verifiziert. Der produktive Pi wurde nicht deployt oder neu gestartet.

## Dateiabgleich

| Kategorie | Anzahl | Behandlung |
|---|---:|---|
| Von `master` getrackte Dateien | 871 | Vollständig gescannt |
| Im Pi-Installationsordner abweichend | 19 | Untersucht und dokumentiert |
| Im Pi-Installationsordner fehlende Git-Dateien | 102 | Beibehalten; überwiegend CI, Cloud und Dokumentation, keine automatische Löschung |
| Zusätzliche Dateien auf dem Pi (ohne venv, Cache und Laufzeit-Datenordner) | 27 | Inventar erstellt, öffentliche und private Daten getrennt |
| Ausgewählte Pi-Laufzeitdateien | 18 | Original-Hash-Abgleich; kontrollierte Test- und Dokumentationsanpassungen nachgeführt |

### Nach Git übernommene Pi-Funktionen

`app/entrypoint.py`, `app/gui_auth.py`, `app/gui_shell.py`, `app/homekit_bridge.py`, `app/main.py`, `app/mars_history.py`, `app/mars_hydro_ble.py`, `app/homekit_mars_accessories.py`, `app/mars_fast_fan.py`, `app/mars_fast_lamp.py`, `scripts/mars_history_collect.py` und `web/gc-final.html`, `web/gc-final.css`, `web/gc-final.js`.

Bereits identische Versionen, darunter `app/rooms.py`, `app/grow_photos.py`, `app/history_archive.py`, wurden nicht blind überschrieben. Zwei PWA-Grafiken (`web/gc-icon-192.png`, `web/gc-icon-512.png`) wurden als originale, hash-geprüfte Binärblobs gesichert. Außerdem wurde das ESP32-C3-Firmware-`manifest.json` (0.5.3) übernommen.

### Bewusst beibehaltene neuere GitHub-Sicherheits- und Projektdateien

- `image-builder/firstboot/gc-operator-image-check.sh`: Git-Stand kontrolliert zusätzlich Wartungs-/sudo-Zugang und Netzwerkbereitschaft.
- `scripts/build-private-pi-image.sh`: Git-Stand kontrolliert Betreiber-Provisionierung beim Erststart. Dieser Stand darf nicht automatisch durch das ältere Pi-Skript ersetzt werden.
- `image-builder/README.md`, `README.md`, `RELEASE_STATE.md`, `docs/PROJECT_STATUS.md`: neuere Dokumentation und Releasesicherheit erhalten, Pi-Livestand ergänzend dokumentiert.
- Gezielte Tests wurden für den tatsächlich vorhandenen Final Master, Mars-Hydro-HomeKit-Zubehör, den echten Fotosnapshot, die private Image-Distribution und den persistenten SSH-Wartungszugang aktualisiert. Dies sind dokumentierte Testkorrekturen und keine ungeprüfte Pi-Überschreibung.

### Nicht ins öffentliche Repository übernommen

- `.env`-Dateien, Schlüssel, Tokens, Betreiber-Provisionierungsdateien, Zugangsdaten, Pflanzenfotos, SQLite-Laufzeitdaten und private Messhistorie.
- Temporäre Sicherheits-/GUI-Vorher-Versionen sowie Build-Metadaten und automatisch erzeugte Firmware-Binärdateien. Das Firmware-Prüfsummenmanifest ist abgelegt.
- Herstellerbilder ohne bestätigte Weiterverteilungsrechte. Quelle und Einschränkungen siehe `docs/GUI_MANUFACTURER_IMAGES.md`. Das öffentliche Repository darf nicht automatisch eine nicht vorhandene Bildlizenz behaupten.

### Nachgewiesene Pi-Dateihashes (nicht mit Geheimnissen verwechselt)

| Originaldatei | SHA-256 |
|---|---|
| `web/gc-hero-leaf.jpg` | `a5220534bc92fbdd16497e041dc6df6cfc6ef32ff83e8eb8a4142fea82177f0f` |
| `web/mars-fc3000-transparent.png` | `b0447a626bbe206f471ff07d2bb5498f907c02b0c280ee96f3597164996601d1` |
| `web/mars-fc3000-hires.jpg` | `7769719469de26cd2774c7a7af92be5d18146f886bed39ab5b5a14eb630ed0b4` |
| `web/mars-df150m-hires.jpg` | `1de559b5b86c14b563d131430ccffbb65021e5f18aae9aa1eda8bf2e702db64f` |
| `web/mars-fc3000-official.jpg` | `28f8a210f3f02f019aaa948f305a28793d24bea984dd816d9be53b89d44ffc67` |
| `web/mars-df150m-official.jpg` | `2f3fac3d8da06d268582411621312ca77e2994061f2c961ab48b40cd205bf22a` |
| `firmware/gc-soil-node/dist/firmware.bin` | `07b5daa279be6e94ea3ca0dde0d1f114305124381160fcbfe9a4780772c2b746` |

## Validierung

- Die Original-Git-Objekthashes wurden für die übernommene Pi-Laufzeit, Weboberfläche, neue HomeKit-/Mars-Hydro-Dateien und PWA-Icons bestätigt.
- Python-Module und Shell-Dateien bestanden die Syntaxprüfung in einer separaten QA-Kopie.
- Gezielt korrigierte Integrationssuite: **50 bestanden**.
- Abschließende Gesamtsuite in isolierter Pi-QA-Kopie: **507 bestanden, 2 native Broker-Tests unter root bewusst ausgenommen**, zusätzlich **26 Untertests bestanden**.
- Beide nativen Broker-Testdateien unter dem Systembenutzer `mosquitto`: **13 bestanden**. Die ursprünglichen Ausfälle wurden durch Dateirechte temporärer root-Testverzeichnisse verursacht, nicht durch einen fehlerhaften produktiven Broker.
- Der abschließende direkte Git-Blobvergleich zeigte **755 identische Dateien**, **102 nur in Git vorhandene Dateien** und **20 erklärte Dokumentations-/Test-/Sicherheitsunterschiede**. Kein offener ungeklärter Quellcode-Diff in den geprüften Pi-Laufzeitpfaden.
- Quellscan der geänderten Dateien auf private Schlüssel und typische eingebettete Tokenmuster: keine Treffer bei den verwendeten Prüfregeln. Dies ist kein vollständiger Secrets-Audit.

Drei zusätzliche, rein kommentierende Bandit-Erklärungen in `app/history_archive.py`, `app/homekit_mars_accessories.py` und `local/cloud_link/remote_agent.py` erläutern fest begrenzte SQL-Fragmente, lokale API-Aufrufe und ausgehende Quelladress-Bindung. Sie verändern keine Steuerungslogik.\n\n## Abgrenzung

**Quellcodeabgleich ist nicht identisch mit einem vollständigen Pi-Datenträger-Backup.** Die Entwicklung ist ausdrücklich freigegeben. Das Produktivsystem darf nicht aus einem Git-Commit unkontrolliert überschrieben werden. GitHub soll den geprüften Pi-Funktionsstand repräsentieren, vorhandene zusätzliche Projektmodule und neuere Sicherheitsfunktionen aber behalten.
