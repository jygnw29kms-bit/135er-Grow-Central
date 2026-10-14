# Projektprüfung – 14. Oktober 2026

Verbindliche Grundlage ist der aktuelle Git-Master mit Final Master unter `/ui`.
Build 375 und Firmware 0.4.1 bleiben Candidates. Diese Quellcodeänderungen
veröffentlichen kein neues Image und bestätigen keine zusätzlichen Hardwaretests.

## Umgesetzt

Raum-, Pflanzen-, Tagebuch- und Zuordnungsänderungen sperren den gesamten
Lese-/Änderungs-/Schreibvorgang. Auch USB- und Netzwerk-Sensoraufnahme verwenden
diesen Pfad. Die Sensorerfassung lädt nach Netzwerkabfragen den aktuellen
Raumstand erneut. Zwischenzeitliche Änderungen und Löschungen bleiben erhalten.
Beschädigte Datenstrukturen werden nicht stillschweigend durch leere Daten ersetzt.

Messwerte werden auf endliche Zahlen und zulässige Bereiche geprüft. Temperatur
und Luftfeuchte vorhandener Smart-Home-Adapter werden übernommen. Ungültige oder
fehlende Werte erscheinen weiterhin nicht als erfundene Nullmessung.

Der authentifizierte CSV-Export unter
`/api/v1/rooms/{room_id}/sensors.csv` exportiert standardmäßig die letzten 5000,
maximal 50000 Messpunkte eines Raums. Der Download ist unter `/rooms` eingebunden.
Quelltexte sind gegen Tabellenkalkulations-Formeln abgesichert. Bodenfeuchte heißt
im CSV `soil_reference_percent` und bleibt als `calibration_required` gekennzeichnet.

Dashboard-Hinweise stammen aus dem Laufzeitstatus; feste Warnungszahlen und
unbelegte Aktiv-/Optimal-Angaben wurden entfernt. Räume mit älteren Messungen
gelten nicht als aktuell gemessen. Kamera-Snapshots und lediglich gespeicherte
Automationsdefinitionen werden entsprechend bezeichnet.

Ein GitHub-Actions-Workflow führt die synthetischen Chromium-Prüfungen bei
GUI-Änderungen mit festgelegter Playwright-Version aus. Die Suite wurde lokal
geprüft; der erste Lauf des neuen Workflows auf GitHub steht noch aus.

## Offene Arbeit

Die [Roadmap](../ROADMAP.md) priorisiert Hardwarevalidierung, Substratkalibrierung,
einen abgesicherten Scheduler, Backup/Wiederherstellung, echte Zeitdiagramme und
Tests optionaler Cloud-/Assistentenpfade. Der Layouteditor bleibt ein Entwurfseditor.

## Prüfung

`python -m pytest -q` inklusive nativer MQTT-TLS-Tests sowie
`node tests/browser/gui-smoke.cjs`. Neue Prüfungen erfassen Datenänderungen während
der Geräteabfrage, parallele Schreibvorgänge, Abbruch ohne Speicherung,
beschädigte Daten, unplausible Messwerte, CSV-Begrenzung/Maskierung und
Laufzeitfehler samt Wiederherstellung. Details: `tests/browser/README.md`.

Keine Website-/Pi-Veröffentlichung und kein Sensorflash als Teil dieser Prüfung.
