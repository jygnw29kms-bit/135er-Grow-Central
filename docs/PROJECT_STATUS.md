# Project Status – 135er-Grow Central

- **Stand:** 14. Oktober 2026
- **Version:** `alpha-0.7.5`
- **Hauptbranch:** `master`
- **Veröffentlichter Pi-Candidate:** **Build 375**; enthält Firmware 0.4.1 und aktuelle Korrekturen
- **Aktuelle Sensor-Firmware im Git-Quellstand:** **0.4.1**
- **Status:** `CANDIDATE` – reale Teilprüfung auf Pi 4 bestätigt, vollständige Hardwarevalidierung offen
- **Entwicklungsmodus:** Open Source

Kanonische Quellen: [Release State](../RELEASE_STATE.md) und [Hardware Support Policy](HARDWARE_SUPPORT_POLICY.md).

## Architektur

Grow Central ist eine dauerhaft headless, lokale Raspberry-Pi-Zentrale mit Desktop-/Mobile-Weboberfläche, Räumen, Sensoren, Automationen und optionaler Cloud. Ein Universal-Image nutzt zentrale Hardwareprofile: Pi 3B/3B+ = Legacy/Lite; Pi 4/400/CM4 = Full Support Standard; Pi 5/CM5 = Full Support Performance. Drucker- und 3D-Druck-Funktionen gehören nicht zu Grow Central.

## Bestätigte reale Teilprüfung

Ein Pi 4 mit Build 369 und Hotfixes nimmt den XIAO ESP32-C3 / HW-390 per USB auf. Firmware 0.4.1 verbindet sich mit dem lokalen MQTT-Broker über TLS; Bodenfeuchte wird in der Raum-Sensorhistorie angezeigt. Die Nutzer-Rückmeldungen bestätigen Aufnahme und Anzeige. Der Befund gilt für diese Kombination und ersetzt keinen vollständigen Plattformtest.

Der ursprüngliche Fehler war ein abgeschnittener CA-Transfer über USB. Das Firmware-Log meldete einen X509-Formatfehler und 307 statt 554 gespeicherte PEM-Bytes. Paketweise Übertragung stellte die Verbindung her. Der aktuelle Backendcode überträgt lange Befehle in kleinen Paketen und prüft die gespeicherte CA-Länge.

## Implementiert, nicht pauschal hardwarevalidiert

- First Boot ohne Factory-Passwörter; Setup-AP, LAN/WLAN, SSH opt-in;
- signierte Sensoridentität, individuelle MQTT-Zugänge und TLS, geführte USB-Einrichtung;
- Räume, Zuordnungen, Sensorhistorie und Bodenfeuchte-Anzeige;
- Kamera-, Geräte- und Automationspfade mit modellabhängigen Berechtigungen;
- FRITZ!, Tapo, Shelly, Home Assistant und weitere Providerpfade;
- installierbare Home-Assistant-Komponente; Apple Home/Siri, Alexa und Google über gesondert einzurichtende HA-Brücken;
- optionaler Cloud-Link, Diagnose und Supportarchive.

## Offen

- vollständiger Pi-4-Installations-, Neustart- und Dauerbetriebtest; separate Pi-3-/Pi-5-Tests;
- reale AIR/WATER- und Substratkalibrierung sowie validierte Bewässerungsgrenzen;
- WYSIWYG-Menüeditor als lokaler Layoutentwurf hinzugefügt; keine bestätigte Übernahme in die produktive Navigation;
- komfortable Kalibrierungs- und Diagnoseansicht: Befehle/Telemetrie existieren, entsprechende UI ist noch nicht implementiert;
- BLE-Provisionierung und weitere Sensorhardware für Temperatur, pH oder EC;
- Ende-zu-Ende-Tests der Sprachassistenten und optionalen Cloud;
- vollständiger Realtest des neu veröffentlichten Image-Candidates 375.

Anleitungen: [Bodensensor](de/SOIL_SENSOR_GUIDE.md), [Hardwarebefund](de/SENSOR_HARDWARE_TEST_2026-10-14.md), [Known Limitations](KNOWN_LIMITATIONS.md).
