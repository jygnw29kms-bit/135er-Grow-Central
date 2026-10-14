# GUI-Zusammenführung vom 14. Oktober 2026

Verbindliche Grundlage ist der Git-Master `1979d30` (Final Master mit
Mobiloptimierungen). Das Master-Layout, seine Bildmotive und die produktive
Route `/ui` bleiben erhalten.

Die ergänzende Raumverwaltung ist unter `/rooms` erreichbar. Raumkarten im
Master und in der mobilen Oberfläche verlinken direkt zu den Sensordaten des
jeweiligen Raums. Die Raumverwaltung bietet ein validiertes Formular,
Rückmeldungen zur Messwerterfassung und eine aufklappbare Sensor-Diagnose.
Verspätete Antworten für einen zuvor ausgewählten Raum überschreiben die
aktuelle Auswahl nicht.

Die Kalibrierungsregel des Masters gilt auch in der Raumverwaltung:
Vorläufige Bodenfeuchte-Prozentwerte werden nicht als kalibrierte Messung
angezeigt. Stattdessen erscheint „Kalibrierung erforderlich“. ADC-Werte,
Signalqualität, Referenzen und weitere vom Sensor gelieferte Diagnosedaten
bleiben sichtbar. Fehlende Klima- und Energiewerte erscheinen als „—“.

Der WYSIWYG-Editor speichert Textwerte korrekt und weist leere bzw.
strukturell ungültige Layoutimporte zurück. Ein ungültiger gespeicherter
Entwurf verhindert den Start des Editors nicht.

## Prüfung

- `python -m pytest -q`: 323 Tests bestanden, einschließlich MQTT-TLS und
  Routen-/Authentifizierungsprüfung für `/ui` und `/rooms`.
- `node tests/browser/gui-smoke.cjs`: Chromium-Prüfungen mit synthetischen
  API-Daten, einschließlich Master-Navigation und Raumverwaltung bei 390,
  768 und 1440 Pixeln. Voraussetzungen siehe `tests/browser/README.md`.
- JavaScript-Syntax, Python-Kompilierung und Projektgrenzen geprüft.
- Deployment-Helfer um die zusammengehörigen GUI-Dateien und eine Prüfung
  von `/rooms` ergänzt; Shell-Syntax geprüft.

Diese Prüfungen ersetzen keinen Test am realen Pi. Ein Deployment auf
Website oder Pi und ein Sensorflash sind kein Bestandteil dieser
Git-Zusammenführung.
