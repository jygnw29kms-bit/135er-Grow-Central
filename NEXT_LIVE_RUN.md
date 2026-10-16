# NEXT LIVE RUN — CANONICAL HANDOFF

Stand: 2026-10-15
Status: **VERBINDLICH FÜR DEN NÄCHSTEN GROW-CENTRAL LIVE-RUN**

## Primärer Auftrag

Vor Beginn der nächsten produktiven Live-Umsetzung muss folgende Integrationsdatei vollständig berücksichtigt werden:

- `docs/de/NEXT_LIVE_RUN_EXTERNAL_GROW_FEATURES_2026-10-15.md`

Diese Datei dokumentiert die Prüfung der Referenzprojekte:

- `Shannon-Goddard/grow_app` — MIT, selektiv portierbare Funktionen
- `jnrabit/chlorophyll-chronik` — GPL-3.0, nur Architektur/Verhalten als Basis für eigenständige Neuimplementierung
- `xn4k/GrowApp` — Konzepte nutzen, keinen Code ohne zweifelsfrei kompatible Lizenz übernehmen

## Reihenfolge — nicht überspringen

1. aktuellen `master` und aktuellen Hardware-/Sensorstand prüfen
2. bestehende Räume/Pflanzen migrationssicher halten
3. gemeinsames `GrowEvent`-Modell + echter Sensor-Snapshot
4. PlantCycle / Pflanzenphasen
5. GrowProfile / Zielbereiche
6. Daily Check-in innerhalb des verbindlichen Grow-Central Final-Masters
7. Foto-Tagebuch mit Event-/Sensor-Snapshot
8. VPD-Zielbewertung + DLI aus realen PPFD-Historienwerten
9. eigener regelbasierter Plant Doctor
10. Regressionstest für GC-ESP32, Pairing, Kalibrierung, MQTT-TLS, History, Mobile/iPhone/Desktop
11. erst nach bestandenen Gates neuen Live-/Image-Candidate erzeugen

## Verbindliche Schutzregeln

- bestehendes Room-/Plant-/Device-/Sensor-/History-/Automation-System **erweitern, nicht ersetzen**
- keine parallele zweite Grow-Datenbank
- keine parallele zweite Sensor- oder Automation-Engine
- Grow-Central Final-Master bleibt optisch verbindlich
- reale Livewerte, keine Demo-/Placeholder-Werte im Produktivpfad
- CO2 standardmäßig verborgen; nur optional bei aktivierter Capability/Benutzeraktion sichtbar
- bestehende Bodenfeuchte-Kalibrierung und sichere GC-ESP32-Aufnahme nicht umgehen
- Kernfunktionen local-first; Cloud nur optional
- keine GPL-Codeübernahme in den MIT-Kern

## Definition of Done für diesen Handoff

Dieser Handoff ist abgearbeitet, wenn die Akzeptanzkriterien in
`docs/de/NEXT_LIVE_RUN_EXTERNAL_GROW_FEATURES_2026-10-15.md`
erfüllt und getestet sind.

Bis dahin darf diese Datei nicht als „erledigt“ entfernt oder in historischen Status verschoben werden.
