# Grow-Central – vollständiger Chat-Handoff

Stand: 2026-10-15
Repo: `jygnw29kms-bit/135er-Grow-Central`
Branch: `master`

Dieses Dokument übergibt den in diesem Chat bekannten Arbeitsstand an parallele bzw. weitere ChatGPT-Sitzungen. Vor jedem Commit/Deploy zuerst den aktuellen `master` ziehen und neue Änderungen integrieren, da mehrere Sitzungen gleichzeitig am selben Projekt arbeiten. Keine alten Stände blind überschreiben.

## 1. Verbindliche Projektregeln

- Produktname: **Grow-Central**.
- Canonical Domain: `grow-central.de`.
- GitHub-Repo ist Source of Truth.
- Unfertige Funktionen sichtbar mit **`In Arbeit`** markieren.
- Optionale Hardware/Funktionen mit **`Optional`** markieren.
- **Keine Fake-Sensorwerte, keine erfundenen Historien/Charts.** Fehlen reale Daten: `—`, `Keine Daten`, `Kalibrierung erforderlich` oder `In Arbeit`.
- Final-Master bedeutet **exakter Soll-/Endstand**, nicht Inspiration und nicht „ähnlich“.
- Desktop und Mobile verwenden dasselbe visuelle Final-Master-System, aber jeweils gerätegerecht umgesetzt.
- Parallele Chats arbeiten gleichzeitig: immer aktuellen `master` prüfen und Änderungen klar abgrenzen.

## 2. Aktueller Parallelstand auf master

Beim Erstellen dieses Handoffs wurde `master` zuerst aktualisiert. Aktueller HEAD zu diesem Zeitpunkt:

`fd053c1 Clean sensor commissioning documentation`

Direkt davor kamen aus der parallelen Sitzung u. a.:

- `7da62c9 Document USB-first sensor commissioning`
- `83dec25 Update USB onboarding state regression`
- `43fe73c Make USB sensor onboarding identity and calibration gated`
- `38005fe Prevent USB sensor firmware downgrade`
- `23194ce Block USB sensor firmware downgrades`

Betroffene aktuelle Dateien u. a.:

- `app/devices/gc_esp32_protocol.py`
- `app/devices/gc_trust.py`
- `app/provisioning/usb.py`
- `docs/de/SENSOR_PAIRING.md`
- `docs/de/USB_SENSOR_SETUP.md`
- `firmware/gc-soil-node/src/ble_provisioning.h`
- `firmware/gc-soil-node/src/main.cpp`
- `tests/test_usb_onboarding.py`
- `web/usb_onboarding.js`

Diese parallelen Änderungen sind neuer als die UI-/Kamera-Arbeit dieses Chats und dürfen nicht zurückgedreht werden.

## 3. Verbindlicher Final-Master UI

Die verbindliche Master-Referenz ist das bereitgestellte Bild `GrowCentral_ Intelligente Grow-Steuerung.png` aus dem Chat.

Visuelle Merkmale:

- dunkles petrol/schwarzes Dashboard
- GrowCentral-Grün/Türkis, dezente Glows
- linke Sidebar
- Topbar mit Suche, Systemstatus, Geräte/Warnungen, Datum/Uhrzeit, Benutzer
- großes fotografisches Grow-Hero
- sechs Messkarten: Temperatur, Luftfeuchte, VPD, CO₂, Lichtstärke, Bodenfeuchte
- Hauptzeile 1: Räume / Live-Kamera / Schnellsteuerung
- Hauptzeile 2: Klima-Verlauf / Zeitpläne & Automationen / Energie & Leistung
- Hauptzeile 3: Letzte Ereignisse / Gerätestatus / Nährstoffe / Wetter
- Rezepte und unfertige Funktionen mit `In Arbeit`
- Wetter aktuell für **13593 Berlin-Spandau**

### Desktop

Verbindlich:

- **kein CSS `zoom`**
- keine künstliche feste 1546-px-Miniaturfläche
- Sidebar fest, Hauptbereich fluid über verfügbare Browserbreite
- Final-Master-Proportionen über responsive Grids erhalten
- Ultra-Wide darf NICHT zu einer links oben klebenden Miniatur mit großer rechter Leerfläche führen
- Unterseiten müssen dieselbe volle Arbeitsbreite nutzen
- Bilder niemals aus LowRes-Quellen hochskalieren

Letzter UI-Desktop-Fix aus diesem Chat: `49bf0a9 Make Final Master desktop layout fluid`.

### Mobile

Verbindlicher Mobile-Stand:

- keine alte `/mobile`-Sonder-UI mehr
- gleiche Final-Master-Oberfläche responsiv
- nativ rendern (`zoom=1`), keine verkleinerte Desktop-Canvas
- kompakter Header
- Hamburger/Off-Canvas Drawer
- Hero mobile komponiert
- Messkarten horizontal wischbar
- große Touch-Ziele
- Panels einspaltig
- kein horizontaler Overflow
- getestet bei 390x844 / DPR 3

Bekannter Mobile-Final-Master-Commit: `1979d30`.

## 4. HighRes-Bildstrategie – verbindlich

Die alten kleinen Master-Crops (`hero_clean2.jpg`, `room_clean.jpg`) sind qualitativ zu klein und dürfen nicht mehr auf Desktop/Ultra-Wide hochskaliert werden.

Im Chat wurden neue HighRes Grow-Room-Bilder erzeugt. Anforderungen für die Integration:

- responsive ohne Verzerrung
- `object-fit: cover` bzw. `background-size: cover`
- Seitenverhältnis niemals durch feste Breite/Höhe verzerren
- `object-position` / `background-position` pro Einsatzzweck setzen
- Hero für Ultra-Wide crop-safe
- Raumkarte und Kamera-Fallback in geeignetem 16:9
- `srcset`/`sizes` bzw. mehrere WebP/AVIF-Derivate verwenden
- Original-HighRes als Source behalten; Derivate daraus erzeugen
- Mobil soll keine unnötig riesigen Assets laden
- Cache-Busting per Hash/Version

Neue Chat-Bilddateien:

- `file_00000000609c81f4a1e2e3bcc3de8025`
- `file_00000000326882108e322f9df5606ee0`
- `file_00000000d05481f4802ff4c1e908772d`

Diese HighRes-Bilder waren beim Handoff noch nicht vollständig als responsive Asset-Pipeline ins Repo integriert.

## 5. Wetter

Wetterkarte wurde für **13593 Berlin-Spandau** mit Open-Meteo umgesetzt.

Bekannte feste UI-Koordinate: ungefähr `52.515, 13.167`.

Live-Felder:

- Temperatur
- gefühlte Temperatur
- Wetterzustand/Wettercode
- Luftfeuchtigkeit
- Wind

Bei Fehler: `Wetter nicht erreichbar`, keine Demo-/Fake-Werte.

## 6. Test-Pi / Live-System

Testgerät: `135er-grow-central`

Installationspfad:

- `/opt/135er-grow-central`
- Webfiles: `/opt/135er-grow-central/web`

Relevante Services:

- `135er-grow-central.service`
- `grow-central-http.service`
- Desktop Commander User-Service

Health:

- `/api/health`
- `/ui` ist authentifiziert und kann unauthentifiziert `303` liefern

Wichtig: `/opt/135er-grow-central` ist ein installierter Release-Stand, **kein Git Checkout**. Dort nicht `git pull` ausführen.

### Remote/Deploy

Auf dem Test-Pi eingerichtet:

- Desktop Commander bootfest per User-Systemd
- Node 22.14 für Desktop Commander
- `Linger=yes`
- GitHub Self-Hosted Runner `135er-grow-central-test-pi`
- Labels u. a. `self-hosted,Linux,ARM64,growcentral,test-pi`
- Wartungs-SSH-Key vom autorisierten Windows-PC zum Pi
- eingeschränkter Root-Wrapper `/usr/local/sbin/growcentral-maint`

Der Wartungswrapper ist absichtlich eng begrenzt. **Kein `NOPASSWD: ALL`.**

Keine Secrets, Tokens oder private Schlüssel in Git dokumentieren.

## 7. Richtiger UI-Analysefilm

Der korrekte Video-Upload für die Maus-/UX-Analyse ist:

`135er Grow Central - Google Chrome 2026-10-15 08-23-35.mp4`

Chat file id:

`file_00000000e9ac8243950033508f682eb0`

Das zuvor erwähnte andere Video ist für diese Aufgabe ausdrücklich NICHT gemeint.

Videoeigenschaften laut Analyse:

- 2480x1044
- ca. 1:48 min

Im Video navigiert der Benutzer durch die reale Grow-Central-Oberfläche und kreist/markiert mit dem Mauszeiger Stellen, an denen Funktionen oder Informationen erwartet werden. Diese Mausbewegungen sind als UX-Anforderung zu interpretieren.

Leere Flächen sollen sinnvoll funktional belegt werden, besonders dort, wo Sensor-/Bodenfeuchteinformationen logisch passen.

## 8. Kamera – aktueller Live-Hardwarestand

Am Test-Pi erkannt:

- **Logitech HD Pro Webcam C920**
- `/dev/video0` und `/dev/video1`

V4L2 bestätigt:

- MJPEG
- H264
- YUYV
- bis **1920x1080 @ 30 fps**
- höhere Auflösungen mit reduzierter FPS möglich

Empfehlung für Live-UI:

- **1920x1080 MJPEG @ 30 fps**
- kein digitaler Zoom (`zoom_absolute=100`)
- UI mit `object-fit: cover`, nicht Bild verzerren

Bereits gesetzte Basiskorrekturen:

- `power_line_frequency=1` = **50 Hz**
- `exposure_dynamic_framerate=0`
- Auto-Exposure zunächst aktiv
- Auto White Balance zunächst aktiv
- Continuous Autofocus zunächst aktiv
- brightness=128
- contrast=128
- saturation=128
- sharpness=128
- gain=0
- backlight_compensation=0

Kamera erst anhand echtem Grow-Livebild weiter feintrimmen. Falls Autofokus unter Grow-LEDs pumpt, nach sauberem Fokus ggf. Autofokus deaktivieren und festen Fokus verwenden.

Backend-Dateien:

- `app/camera.py`
- `app/camera_policy.py`
- `app/camera_led.py`
- API Prefix `/api/v1/camera`

Unauthentifizierter lokaler Zugriff auf Camera-Status ergab `401`; Auth beachten.

## 9. Sensor-Onboarding – verbindlicher Zielablauf

1. Neuer Sensor per USB an Grow-Central anschließen.
2. GC prüft, ob es ein unterstützter echter Sensor ist.
3. Firmware wird installiert/geprüft.
4. Geräteidentität/Fingerprint kryptographisch prüfen.
5. Clone/falsches Gerät ausschließen.
6. WLAN/TLS-MQTT sicher provisionieren.
7. Benutzer vergibt Sensorname.
8. Raumzuweisung.
9. vollständige Kalibrierung durchführen und verifizieren.
10. Erst danach Status **voll einsatzbereit**.
11. Danach Sensor abziehen, in Raum bringen und an Pflanze/Substrat installieren.

Ein Sensor darf nicht allein wegen MQTT-Erreichbarkeit oder eines Prozentwerts als produktiv gelten.

Wichtig: Die parallele Sitzung hat diesen USB-first/gated Workflow bereits weiterentwickelt; siehe aktuellen `master` ab `43fe73c` bis `fd053c1`.

## 10. Bodenfeuchtesensor / Firmware

Referenzhardware:

- Seeed XIAO ESP32-C3
- Bodenfeuchtesensor
- Firmware: `firmware/gc-soil-node/src/main.cpp`
- Stable ID aus ESP32 MAC (`gc-soil-...`)
- signierte Geräteidentität / Challenge-Proof
- MQTT-Protokoll `gc-esp32-mqtt-v1`

Firmware kennt bereits technische Air/Water-Referenzkalibrierung:

- `CAL AIR`
- `CAL WATER`
- `RESET CAL`
- `calibrationSnapshot()` mittelt mehrere Messfenster
- NVS speichert `air_raw` und `water_raw`

Telemetrie enthält u. a.:

- raw
- median
- filtered_raw
- min/max
- sigma
- quality
- moisture_state
- sensor_ok
- air_raw
- water_raw
- rssi_dbm
- uptime_ms
- firmware

Wichtig: Die aktuelle Air/Water-Normalisierung ist eine **Engineering-Referenz**, nicht automatisch finale volumetrische Wassergehaltskalibrierung des echten Substrats. Wasser-Referenz nie als `100% Substrat-VWC` darstellen.

## 11. Verbindlicher Punkt „Sensor-Kalibrierung“

Benutzeranforderung: Es muss einen eigenen Punkt **Sensor-Kalibrierung** geben.

### Navigation

Sinnvoll unter `ANBAU`, nahe Geräte/Sensoren, z. B.:

- Räume
- Geräte
- **Sensor-Kalibrierung**
- Klima
- Bewässerung
- Beleuchtung
- ...

### Listenansicht

Automatisch Sensoren anzeigen, deren Kalibrierung nicht vollständig/aktuell ist:

- Nicht kalibriert
- Kalibrierung erforderlich
- Kalibrierung unvollständig
- Kalibrierung ungültig
- nach Firmware-/Sensorwechsel erneut erforderlich
- optional: Rekalibrierung bald fällig

Pro Sensor anzeigen:

- Sensorname
- Gerätetyp/Modell
- Raum
- stabile Device-ID / gekürzter Fingerprint
- online/offline
- Firmware
- Signalqualität
- Kalibrierstatus
- letzter Kalibrierzeitpunkt
- Grund für Kalibrierbedarf
- Button **Kalibrieren**

### Kalibrierungs-Assistent Soil

Mindestens:

1. Identität/Hardware prüfen.
2. Sensor sauber/trocken/in Luft -> Trocken-/Luftreferenz messen.
3. Stabilität und Signalqualität automatisch prüfen.
4. definierte Nass-/Wasser-Engineering-Referenz messen; Elektronik trocken halten.
5. Plausibilität prüfen: ausreichender Raw-Span, keine Sensorfehler, akzeptable Sigma/Qualität.
6. Werte im Sensor persistent speichern.
7. Werte erneut auslesen und verifizieren.
8. Kalibrierstatus serverseitig speichern.
9. abschließenden Live-Proof / Messwertprüfung durchführen.
10. erst dann **Kalibriert / einsatzbereit**.

Bei Fehler bleibt Sensor unkalibriert; Ursache anzeigen und Wiederholen ermöglichen.

### Serverseitiger Calibration Record

Soll first-class werden, mindestens:

- device_id
- Fingerprint/Public-Key-Bindung
- Sensor-Capability
- Schema/Version
- Kalibrierart
- Kalibrierpunkte / Raw-Referenzen
- Quality-Metriken
- calibrated_at
- Firmware-Version
- valid true/false
- invalidation_reason

Die Room/UI-Schicht darf Bodenfeuchte-% nur als validiert darstellen, wenn dieser Record gültig ist. Sonst `Kalibrierung erforderlich`.

### Sicherheitsregel

Nicht einfach allgemeine Remote-Command-Schreibrechte für native Sensoren aktivieren.

Kalibrierung bevorzugt:

- im sicheren USB-Onboarding über `app/provisioning/usb.py`, oder
- über einen explizit begrenzten, signierten Kalibrierpfad mit ACK + Identitätsproof.

Der aktuelle native MQTT-Sensorprovider ist bewusst read-only.

## 12. Sensorstatus / freie UI-Flächen aus Video

Aus dem richtigen Video sollen markierte freie Stellen mit sinnvollen Funktionen belegt werden.

Naheliegende Informationen/Funktionen:

- Bodenfeuchte
- Sensor-Kalibrierstatus
- Signalqualität
- Sensor online/offline
- letzter Messzeitpunkt
- Raum-/Pflanzenzuordnung
- direkter Einstieg **Kalibrieren**, wenn erforderlich

Raw-/Diagnosedaten nur in Detail-/Debugansicht, nicht Hauptdashboard überladen.

## 13. Produktive UI-Dateien

- `web/platform.html`
- `web/platform-master.css`
- `web/platform-master.js`
- `web/platform-visual.css`
- `web/room_views.js`

Weitere relevante UI-Dateien:

- `web/ui-editor.html`
- `web/ui-editor.css`
- `web/ui-editor.js`
- `web/usb_onboarding.js`

`/ui` muss `platform.html` bedienen. `/legacy` ist alte Konsole und darf Final-Master nicht ersetzen.

## 14. Bekannte technische Risiken

- Bei parallelen Chats immer aktuellen `master` prüfen.
- Nicht direkt in `/opt/...` entwickeln und dann vergessen, Änderungen zurück ins Repo zu übertragen.
- Kamera-Snapshot-Code kann aktive Streams stoppen; nicht aggressiv periodisch pollen.
- C920 kann 1080p30 MJPEG; Hardware-Profile dürfen gewünschte Auflösung nicht unnötig reduzieren.
- Auth-Middleware kann lokalen API-Zugriff ohne Session mit 401/303 blockieren.
- Keine LowRes-Assets auf Ultra-Wide hochskalieren.
- Keine dekorativen Fake-Charts.
- Quick-Control nur aktivieren, wenn Schreibfähigkeit validiert und bestätigt ist.

## 15. Wichtige frühere Commits aus diesem Chat

Nur Orientierung; aktueller `master` hat immer Vorrang:

- `e937f54...` Soil UI: `—` + `Kalibrierung erforderlich`
- `d45593e...` `/ui` Routing
- `49763e9...` erste Visual-CSS-Schicht
- `f2d9fd3...` Visual-CSS-Einbindung
- `58f4d66...` Deployment-Script mit Assets
- `8301017...` Test-Pi-Dokumentation
- `e20bfe9` Final-Master/Wetter Cache-Bust
- `c8b8bbf` Master-v5 UI
- `1979d30` Mobile Final-Master
- `49bf0a9` Fluid Desktop / Ultra-Wide Fix

## 16. Nächste Arbeiten

Priorität:

1. aktuellen `master` der parallelen Sitzung respektieren
2. Sensor-Kalibrierung Backend + UI vollständig integrieren
3. prüfen, wie weit `43fe73c..fd053c1` den gated Calibration-Onboarding-Ablauf bereits umgesetzt haben
4. first-class Calibration Record ergänzen, falls noch nicht vorhanden
5. Soil-Telemetrie um expliziten Kalibrierstatus erweitern
6. richtigen UI-Film framegenau für Cursor-Markierungen weiter auswerten
7. C920 1080p30 im echten Live-UI testen und Exposure/WB/Focus anhand realem Grow-Licht optimieren
8. neue HighRes-Bilder als responsive WebP/AVIF/srcset-Pipeline integrieren
9. Desktop, Ultra-Wide, iPhone und Android Regression testen
10. auf Test-Pi deployen und live prüfen

## 17. Sicherheitsregeln

- keine Passwörter/Tokens/private Keys in Repo
- neue Sensoren nur nach kryptographischer Identitätsprüfung akzeptieren
- rejected/revoked identities nicht stillschweigend reaktivieren
- kein allgemeines Remote-Shell-/Sensor-Schreibrecht als Kalibrier-Abkürzung
- `sudo` auf Test-Pi nur über eingeschränkten Wartungswrapper
- kein `NOPASSWD: ALL`

## 18. Startanweisung für den anderen Chat

1. Dieses Dokument vollständig lesen.
2. `git pull --ff-only origin master`.
3. `git log -10 --oneline` und `git status` prüfen.
4. neue parallele Änderungen seit diesem Handoff erkennen.
5. aktuellen Onboarding-/Calibration-Code zuerst lesen, bevor etwas geändert wird.
6. dann bei **Sensor-Kalibrierung + Kamera + Video-UX-Markierungen + HighRes-Assets** fortsetzen.
7. Final-Master und Mobile-Final-Master nicht verwässern.

## Verbindlich: privates Fortsetzungs-Testimage
- Das spezielle Testimage fuer den aktuell verwendeten Grow-Central-Test-Pi ist **kein Factory-/Pristine-Image**.
- Es muss den Zustand **nach erfolgreichem Boot und abgeschlossener Einrichtung** enthalten, damit nach einem Restore auf denselben Pi **keine erneute Ersteinrichtung** notwendig ist.
- Persistieren: bestehende Grow-Central-Konfiguration, Netzwerkprofile, Sensor-/Kalibrierzustand, lokale Daten sowie die bestehende Remote-Desktop-Commander-Identitaet unter `/home/GrowCentral/.desktop-commander-device` und die dazugehoerige Benutzerumgebung.
- Ziel: Nach Einschalten/Restore startet Grow-Central direkt produktiv und die bestehende Remote-Verbindung kann wieder anknuepfen, sodass die Arbeit unmittelbar fortgesetzt werden kann.
- Dieses personalisierte Fortsetzungsimage darf **niemals** in ein oeffentliches GitHub-Artefakt, Release oder Repo committed werden, da es private Konfiguration/Identitaet enthalten kann.
- Das oeffentliche Release-/Factory-Image bleibt davon getrennt und weiterhin pristine mit normalem First-Boot-Setup.
- Restore ist fuer **denselben physischen Test-Pi** vorgesehen; nicht parallel auf mehrere Geraete klonen (Identitaets-/Machine-ID-/Remote-Agent-Kollisionen vermeiden).
