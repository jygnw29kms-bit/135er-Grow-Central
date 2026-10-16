# NEXT LIVE RUN — CANONICAL HANDOFF

Stand: 2026-10-16
Status: **VERBINDLICH FÜR DEN NÄCHSTEN GROW-CENTRAL LIVE-RUN**

## Primärer Auftrag

Vor Beginn der nächsten produktiven Live-Umsetzung muss folgende Integrationsdatei vollständig berücksichtigt werden:

- `docs/de/NEXT_LIVE_RUN_EXTERNAL_GROW_FEATURES_2026-10-15.md`

Diese Datei dokumentiert die Prüfung der Referenzprojekte:

- `Shannon-Goddard/grow_app` — MIT, selektiv portierbare Funktionen
- `jnrabit/chlorophyll-chronik` — GPL-3.0, nur Architektur/Verhalten als Basis für eigenständige Neuimplementierung
- `xn4k/GrowApp` — Konzepte nutzen, keinen Code ohne zweifelsfrei kompatible Lizenz übernehmen

## Reihenfolge — aktueller Erfüllungsstand

1. [ ] aktuellen `master` mit dem **real laufenden Pi**, Hardware-/Sensorstand und installiertem Live-SHA vergleichen
2. [x] bestehende Räume/Pflanzen migrationssicher halten
3. [x] gemeinsames `GrowEvent`-Modell + echter Sensor-Snapshot
4. [x] PlantCycle / Pflanzenphasen
5. [x] GrowProfile / Zielbereiche
6. [x] Daily Check-in innerhalb des verbindlichen Grow-Central Final-Masters
7. [x] Foto-Tagebuch mit realem Bild, Pflanzenzuordnung, Phase/Zyklustag und Event-/Sensor-Snapshot
8. [x] VPD-Zielbewertung + DLI aus realen PPFD-Historienwerten; Schätz-/Teilwerte werden gekennzeichnet
9. [x] eigener regelbasierter Plant Doctor inkl. Final-Master-UI und Timeline-Event
10. [ ] Regression auf **realem Pi**: GC-ESP32, Pairing, Kalibrierung, MQTT-TLS, History, Foto, Plant Doctor, HomeKit, Cloud-Link, Mobile/iPhone/Desktop
11. [ ] erst nach bestandenen realen Pi-Gates neuen Live-/Image-Candidate erzeugen

## Am 2026-10-16 zusätzlich erledigt

- local-first Foto-Tagebuch in `master` gemergt (`c058ed8`)
- Plant-Doctor-UI in `master` gemergt (`94602a9`)
- Live-Run-Migrations-/History-Gates in `master` gemergt (`288e6a7`)
- `cryptography` Runtime + Cloud-Link auf `>=50,<51` angehoben; Security-Audit wieder grün
- Regression-Gates prüfen explizit:
  - Legacy-`rooms.json` wird erweitert statt ersetzt
  - Räume, Zuordnungen, Journale, Pflanzen und Sensorhistorie bleiben erhalten
  - kaputte Zustandsdatei wird nicht still durch leere Daten ersetzt
  - historische GrowEvent-Sensor-Snapshots bleiben unveränderlich
  - CO2 bleibt im Final Master standardmäßig verborgen

## Noch offen vor produktivem Live-Candidate

- BnD/Grow-Central-Arbeitsrechner wieder online bringen und `master` gegen den tatsächlich installierten Pi-Stand vergleichen
- Pi vor dem Update sichern: Datenzustand + aktuelle Runtime/Version/Live-SHA
- notwendige Python-Abhängigkeiten kontrolliert auflösen; **kein Downgrade auf anfällige cryptography-46.x-Linie**
- Cloud-Core-Plesk-Installer ebenfalls von `cryptography>=45,<47` auf die freigegebene 50.x-Linie umstellen und testen (GitHub Issue #76)
- vollständiger realer Pi-Regressionslauf und erst danach Markierung als Live-/Image-Candidate

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
- vor jedem produktiven Pi-Update erst Backup, Preflight, kontrollierter Restart und Health-/Regression-Check

## Definition of Done für diesen Handoff

Dieser Handoff ist abgearbeitet, wenn die Akzeptanzkriterien in
`docs/de/NEXT_LIVE_RUN_EXTERNAL_GROW_FEATURES_2026-10-15.md`
erfüllt und auf dem realen Pi getestet sind.

Bis dahin darf diese Datei nicht als „erledigt“ entfernt oder in historischen Status verschoben werden.
