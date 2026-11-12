# GrowCentral Pi 4: End-to-End Testimage und Hardwareabnahme

**Datum:** 2026-11-12  
**Plattform:** Raspberry Pi 4B, Universal-Image, Raspberry Pi OS Lite arm64  
**Status:** Checkliste für die echte Hardwareabnahme, **noch nicht auf Zielhardware bestanden**.

Diese Anleitung gilt für einen frisch geflashten Test-Pi, nicht für eine produktive GrowCentral-Installation. Ältere Builds dürfen nicht als Erfolg eines neueren Builds gewertet werden. `CANDIDATE` erst nach erfolgreichem Image-CI-Build, `VALIDATED` nur nach realer Prüfung.

## 0. Bezugsquelle und Integrität

1. Aktuellen **erfolgreichen** Build auf [GitHub Releases](https://github.com/jygnw29kms-bit/135er-Grow-Central/releases) auswählen. Prüfen, dass Release-Quell-SHA den erwarteten aktuellen Quellstand enthält.
2. `*.img.xz` und passende `*.img.xz.sha256` herunterladen. Keine alten Builds als aktuellen Test deklarieren.
3. SHA256 der heruntergeladenen Datei gegen die Prüfsummendatei kontrollieren. Bei Abweichung **nicht flashen**.
4. `SOURCE.txt` und `CREDENTIALS.txt` lesen; sie gehören zur jeweiligen Buildnummer.
5. Test-SD-Karte mit mindestens 16 GB und Raspberry Pi Imager verwenden. Bei `*.img.xz` über **OS wählen → Eigenes Image verwenden** auswählen.
6. Sofern die Image-Ersteinrichtung eigene Netzwerk- und Benutzerkonten erzeugt: Imager-Voreinstellungen für WLAN/Benutzer/SSH nicht darüber schreiben. Nur eine ausdrücklich getestete Abweichung zulassen.

## 1. First Boot

- Pi mit korrekt angeschlossener Stromversorgung und SD-Karte starten, Ethernet optional.
- Auf Smartphone oder PC nach WLAN `135er-GrowCentral-Setup-XXXX` suchen; nur während Erstkonfiguration verfügbar, Setup-AP ist offen. `http://10.42.0.1/` öffnen.
- **DE/EN auswählen**, danach Netz (LAN oder WLAN), Administrator-Benutzername und **eigenes** Passwort konfigurieren.
- Lokales SSH ist bei normalen Images **standardmäßig aus** und lässt sich bei der Ersteinrichtung separat aktivieren. Für Wartungstest mit Schlüssel ab erstem Boot einen **manuell ausgelösten** Build mit `enable_test_maintenance=true` und gültigem `GC_TEST_PI_MAINTENANCE_PUBKEY` verwenden. Niemals Werkspasswort oder private SSH-Schlüssel im Image/Git speichern.
- Nach erfolgreichem Setup muss das Setup-AP verschwinden, die Weboberfläche über `http://135er-GrowCentral.local/` erreichbar sein und die Anmeldung funktionieren.
- Neustart durchführen; kontrollieren, dass Sprache, Benutzer, Netz und Geräte-/Räumeinstellungen bestehen bleiben.
- Negativtest: falsche WLAN-Daten dürfen Setup/Recovery nicht dauerhaft blockieren; zugehöriges Support-Bundle aufbewahren.

## 2. FC3000 und DF150-M einzeln aufnehmen

Die neuen realen Geräte des Testaufbaus sind **Mars Hydro FC3000 (ca. 300 W)** und **DF150-M (ca. 62 W, max. 402 CFM)**. Beide haben laut bestätigter Hardwareinformation **jeweils Bluetooth und ausschließlich 2,4-GHz-WLAN**.

1. Für beide Geräte eine kompatible **2,4-GHz-SSID** bereitstellen. Kein reines 5-GHz-Netz und keine ungeprüften Cloud-Zugangsdaten in öffentliches Git.
2. FC3000 und DF150-M nacheinander mit Strom versorgen; Steuerung zunächst nach Herstellerangabe manuell prüfen.
3. Bluetooth-Geräteliste im lokalen Pi erfassen. Werbe-Name, Herstellerkennung, MAC-Adresse (nur lokale Diagnose), Signalstärke und GATT-Dienste **lesend** ermitteln.
4. Zuordnen, welches erkannte Gerät tatsächlich zur FC3000 und welches zum DF150-M gehört; mehrfache Geräte nicht anhand ähnlicher Namen verwechseln.
5. In GrowCentral zwei Einträge anlegen bzw. prüfen: `mars-hydro-fc3000-2024` und `mars-hydro-df150m-bt`; die UI darf `online` oder `controllable` nur nach echtem Handshake melden.
6. WLAN-Verbindungsstatus und Bluetooth-Kopplung getrennt anzeigen. Bluetooth-Erkennung beweist **keine** dokumentierte lokale WLAN-API.
7. **Keine** unbestätigten BLE-GATT-Writes, keine blinden Dimmer- oder Lüfterbefehle. Automatik und Fernsteuerung erst nach protokollierter Hardwarevalidierung aktivieren.

## 3. Sensoren, HomeKit und UI

- XIAO ESP32-C3 / HW-390 per USB erkennen, gebündelte Firmware prüfen und ohne Downgrade anbieten.
- Sensoridentität über signierte Hardware-ID nachweisen; Sensor ausdrücklich annehmen. Kein pauschales Akzeptieren unbekannter Identitäten.
- Kalibrierung in der Reihenfolge **AIR_DRY → WATER_SATURATED → FRESH_SUBSTRATE_CC** durchführen, Messwerte und Raumzuordnung prüfen.
- MQTT-TLS-Verbindung und tatsächliche Werte nachweisen, keine simulierten Sensordaten als echte anzeigen.
- Apple Home: den **wirklichen** GrowCentral-HomeKit-QR-Code im UI anzeigen lassen, Home-App koppeln und prüfen, dass der Bodenfeuchtesensor nicht mit HomePod-Werten verwechselt wird.
- Final-Master-Dashboard auf iPhone und Desktop kontrollieren. CO₂ nur optional einblenden, Kamera nur bei tatsächlichem Gerät/Stream als live darstellen.

## 4. Abnahmekriterien und Sperren

| Prüfung | Erwartet | Status |
|---|---|---|
| SHA256/Image flashbar | verifizierte Image-Datei und SD-Start | OFFEN |
| First-Boot DE/EN und Netzwerk | alle Schritte ohne SSH-Verlust/Lockout | OFFEN |
| Login und Reboot-Persistenz | Benutzer/Sprache/WLAN bleiben erhalten | OFFEN |
| FC3000 BLE/WLAN | reale, getrennte Identität und Status | OFFEN |
| DF150-M BLE/WLAN | reale, getrennte Identität und Status | OFFEN |
| Sensor USB-Identität/Kalibrierung | gültig und vom Benutzer angenommen | OFFEN |
| Apple Home QR | sichtbarer echter Pairing-QR, Werte korrekt | OFFEN |
| Wartung/Support-Bundle | über vorgesehenen sicheren Zugang erreichbar | OFFEN |

**Regel:** Erst nach einer tatsächlichen Durchführung auf dem Pi 4 und Nachweis dieser Punkte darf ein neuer Build als hardware-validiert gelten. Der Image-Build selbst validiert nur CI/Userspace-Simulation. Nicht implementierte Gerätefunktionen müssen als `pending_validation` sichtbar bleiben.
