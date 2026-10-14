# Roadmap – 135er-Grow Central

**Stand:** 14. Oktober 2026. Verbindlicher Release-Status:
[`RELEASE_STATE.md`](../RELEASE_STATE.md).

`alpha-0.7.5`, Pi-Candidate **Build 375**, Sensor-Firmware **0.4.1**.
Quellcodeverbesserungen auf `master` erzeugen kein neues Pi-Image und ersetzen
keine Hardwarevalidierung. Build 369 mit Hotfixes bleibt der dokumentierte
reale Pi-4-Sensorteiltest.

## Im aktuellen Quellstand umgesetzt

- Final-Master-Oberfläche unter `/ui`, mobile Oberfläche und ergänzende
  Raumverwaltung mit Sensor-Diagnose unter `/rooms`.
- Validiertes Raumformular, aktuelle Messzeitpunkte, Schutz vor verspäteten
  Antworten nach einem Raumwechsel und verständliche Fehlermeldungen.
- Transaktionale Änderungen an Raumdaten, Pflanzen, Tagebüchern und
  Sensorzuordnungen; Sensorabfragen erhalten zwischenzeitliche Änderungen.
- Plausibilitätsprüfung von Messwerten und Übernahme der Temperatur-/Feuchte-
  Felder vorhandener Smart-Home-Adapter.
- CSV-Export der Raumhistorie mit expliziter Kennzeichnung unkalibrierter
  Bodenfeuchte-Referenzwerte. UI standardmäßig bis zu 5000 Messpunkte;
  API maximal 50000. Aufbewahrung derzeit maximal 50000 Messpunkte insgesamt.
- Warnungsanzeigen aus dem Laufzeitstatus und sichtbare Unterscheidung
  zwischen frischen und älteren gespeicherten Messungen.
- Manuelle Sensoraufnahme, signierte Identität, individuelle MQTT-TLS-
  Zugänge und geführte USB-Einrichtung. BLE-Provisionierung bleibt gesperrt.
- Lokale Automationsdefinitionen: Speicherung implementiert; ein allgemeiner
  Scheduler bzw. automatische Ausführung ist damit nicht bestätigt.
- WYSIWYG-Layoutentwurf mit Import/Export; produktive Layoutübernahme offen.
- GitHub-Workflow für synthetische Chromium-Prüfungen bei GUI-Änderungen, mit
  festgelegter Playwright-Version und ohne Produktionszugänge.

## Priorität 1: Nachweisbarer Betrieb auf Zielhardware

Build 375 auf Pi 4 frisch installieren, Einrichtung, Neustart, Netzwerkübergang,
MQTT-TLS, Sensoraufnahme und Dauerbetrieb prüfen. Pi 3 und Pi 5 separat prüfen.
Kamera, LED-Steuerung, FRITZ!/Tapo und weitere Geräte nur mit passender realer
Hardware validieren. Prüfergebnisse und Supportarchive dokumentieren.

## Priorität 2: Kalibrierung und sichere Automationen

AIR/WATER-Referenzen und Substrat-Grenzwerte am realen Sensor prüfen. Die
Diagnoseansicht bietet Anleitung und Messdaten; serielle Kalibrierbefehle werden
noch nicht im Browser ausgeführt. Danach ein explizites Kalibrierungsmodell und
nachvollziehbare Freigabe der Prozentanzeige entwickeln.

Einen lokalen Scheduler erst mit gültigen Zeit-/Temperaturbedingungen,
Berechtigungsprüfung, Hysterese, Ausfallgrenzen und Tests für Neustart sowie
veraltete Sensorwerte ergänzen. Unvalidierte Aktorbefehle bleiben gesperrt.

## Priorität 3: Historie und Betrieb

- Zeitfilter, echte Diagramme, konfigurierbare Retention und belastbare
  Energie-/Kostenberechnung auf Basis realer Zählerdaten.
- Backup und geprüfte Wiederherstellung, kontrollierte Updates und Rollback.
- Aktuelle Datenquellen vollständig in Klima-, Bewässerungs- und Geräteansichten
  zusammenführen; geplante Funktionen weiterhin sichtbar kennzeichnen.
- Bestehende Chromium-CI um weitere Abläufe ergänzen und auf echten iOS-/Android-Geräten prüfen.

## Optionale Erweiterungen

Cloud **V7**, Home Assistant und Sprachassistenten bleiben zusätzliche Wege;
der Pi bleibt die lokale Autorität. Ende-zu-Ende-Prüfungen benötigen die
jeweiligen Dienste und Konten. Temperatur, pH und EC benötigen zusätzliche
Sensorhardware. Projektfremde Dienste bleiben getrennt.

## Release-Gate

Kein Beta-/Stable-Status allein aufgrund erfolgreicher Softwaretests. Es gelten
[Hardware Support Policy](HARDWARE_SUPPORT_POLICY.md),
[Hardware Test Plan](HARDWARE_TEST_PLAN.md) und
[Known Limitations](KNOWN_LIMITATIONS.md).
