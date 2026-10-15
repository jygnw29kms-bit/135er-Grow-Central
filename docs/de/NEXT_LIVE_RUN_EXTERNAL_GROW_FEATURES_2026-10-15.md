# Next Live Run – externe Grow-App-Funktionen

Stand: 2026-10-15
Status: **VERBINDLICHER INTEGRATIONS-AUFTRAG FÜR DEN NÄCHSTEN LIVE-RUN**
Zielbranch: `master`

## Ziel

Die drei geprüften öffentlichen Projekte werden als Referenzquellen genutzt, um bestehende Grow-Central-Funktionen gezielt zu vervollständigen und zu optimieren. Es wird **kein fremdes UI als neuer Master übernommen**. Der aktuelle Grow-Central Final-Master für Dashboard/Navigation bleibt verbindlich; neue Funktionen werden in dessen Struktur integriert.

Der Live-Run soll zuerst vorhandene Grow-Central-Funktionalität wiederverwenden und erweitern. Bereits vorhandene Räume, Pflanzen, Pflanzentagebuch, Sensorhistorie, Gerätezuteilung, VPD, PPFD, Bodenfeuchte, Kalibrierung und Automationspfade dürfen nicht durch parallele Zweitsysteme ersetzt werden.

## Geprüfte Quellen

### 1. Shannon-Goddard/grow_app

Quelle: https://github.com/Shannon-Goddard/grow_app
Lizenz: **MIT**.

Besonders relevant:

- `medium-feeding/medium-feeding.html`: Grow-Setup / Grow-Builder
- `medium-feeding/schedule-viewer.html`: Tages-/Wochenplan, Karten- und Tabellenansicht
- `medium-feeding/mytask.html`: tägliche Soll-/Ist-Erfassung
- `medium-feeding/mydiary.html`: Foto-Tagebuch mit Datenbezug
- IndexedDB-basierte lokale Grow-Datenhaltung
- Licht-/DLI-Werkzeuge
- Luftstrom-/CFM-Rechner
- Grow-Space-Rechner
- `plant-doctor/`: regelbasierte Symptomdiagnose
- `harvest-window/`: lokale TensorFlow.js-Bildanalyse für Entwicklungs-/Trichomzustände
- 2.800+ Sortendatensätze sowie Zeitplan-/Nährstofflogik

Lizenzregel: MIT-Code darf technisch übernommen/portiert werden, wenn Copyright- und Lizenzhinweise für substanzielle übernommene Teile erhalten bleiben. Vor jeder direkten Codeübernahme muss geprüft werden, ob externe Daten/Modelle/Bilder innerhalb dieses Repos eigene Nutzungsbedingungen besitzen.

### 2. jnrabit/chlorophyll-chronik

Quelle: https://github.com/jnrabit/chlorophyll-chronik
Lizenz: **GPL-3.0**.

Besonders relevant als Architektur-/Funktionsreferenz:

- FastAPI-Aufteilung für Plants / Logs / Images / Environment / Diagnosis / Sensors
- VPD-Berechnung und Umweltbewertung
- Sensor-Historie
- Pflanzen- und Fotologs
- regelbasierte Diagnose
- Turgor-/Blattwinkel-Auswertung
- Self-hosted / privacy-first Ausrichtung
- vorbereitete ESP32-Sensor-Bridge
- optionale lokale Verschlüsselung

**Wichtig:** Grow Central ist MIT-lizenziert. GPL-3.0-Code darf daher **nicht direkt in den MIT-Kern kopiert oder abgeleitet übernommen werden**, wenn dadurch der MIT-Gesamtcode ohne GPL-Pflichten weitergeführt werden soll. Funktionen aus diesem Projekt werden deshalb ausschließlich als Verhalten/Architektur analysiert und in Grow Central eigenständig neu implementiert. Kein Copy/Paste aus GPL-Dateien.

### 3. xn4k/GrowApp

Quelle: https://github.com/xn4k/GrowApp

Relevante Konzepte:

- benutzergetrennte Grow-Liste
- Zyklusfortschritt / Restzeit / Erntefenster
- Notizen und Status pro Grow
- geplante Cabinets/Zelte
- einzelne Pflanzen mit tatsächlichem Phasenbeginn
- frei definierbare Zyklusvorlagen
- Ereignis-Timeline für Gießen, Düngung, Fotos und Beobachtungen

Bei der Prüfung war im Root keine eindeutig nutzbare Lizenz als Grundlage für Codeübernahmen ersichtlich. Daher: **nur Konzepte verwenden, keinen Code kopieren**, solange keine kompatible Lizenz zweifelsfrei nachgewiesen ist.

## Abgleich mit aktuellem Grow-Central

Bereits vorhanden und zu erhalten:

- Räume anlegen und verwalten
- Geräte Räumen zuordnen
- Pflanzen pro Raum
- Raum- und Pflanzentagebuch
- lokale Sensorhistorie
- Temperatur, Luftfeuchte, VPD
- PPFD als Capability
- Bodenfeuchte und Bodentemperatur
- EC und pH als Capability
- aktuelle GC-ESP32-Sensoraufnahme und sichere Pairing-/Kalibrierpfade
- Bodenfeuchte-Kalibrierung mit persistenten Kalibrierdaten
- Automationen / Zeitpläne / Gerätesteuerung
- lokale Kernfunktion ohne Cloud-Zwang

Daraus folgt: **keine neue parallele Grow-Datenbank und kein zweites Sensor-Backend bauen.** Neue Funktionen werden auf den bestehenden `rooms`, `devices`, Sensor-/History- und Automationsmodellen aufgebaut.

## Verbindlicher Funktionsumfang für den nächsten Live-Run

### P0 – direkt integrieren

1. **Grow-Zyklus und Pflanzenphasen**
   - pro Pflanze `start_date`, `phase`, `phase_started_at`, optionale erwartete Phasendauer
   - Phasen mindestens: Keimling/Seedling, Vegetation, Blüte, Spülen/Finish, Ernte/Abgeschlossen
   - tatsächlicher Phasenwechsel muss unabhängig von der Prognose speicherbar sein
   - Zyklusfortschritt und erwartetes Erntefenster ableiten, aber immer als Prognose kennzeichnen

2. **Ereignis-Timeline pro Pflanze**
   - ein gemeinsames Eventmodell statt separater Insellösungen
   - Typen mindestens: Gießen, Düngen, Umtopfen, Training, Phase geändert, Foto, Beobachtung, Diagnose, Ernte
   - Event speichert Zeitstempel, Benutzer/Quelle, Notiz und optional Messwert-Snapshot

3. **Sensor-Snapshot an Tagebuch/Fotos**
   Beim Erstellen eines Pflanzen- oder Raumtagebuch-Eintrags automatisch die zum Zeitpunkt verfügbaren Werte mitschreiben:
   - Temperatur
   - Luftfeuchte
   - VPD
   - Bodenfeuchte
   - Bodentemperatur
   - PPFD, sofern vorhanden
   - EC/pH, sofern vorhanden
   - relevante Geräte-/Licht-/Lüfterzustände

   Historische Tagebucheinträge müssen ihren Snapshot behalten und dürfen nicht rückwirkend mit aktuellen Livewerten überschrieben werden.

4. **Heute / Daily Check-in**
   - innerhalb des vorhandenen Final-Master-Layouts eine kompakte Tagesansicht
   - geplante Aufgaben und heutige Grow-Ereignisse
   - Soll gegen Ist, soweit Sollwerte definiert sind
   - schneller Log-Button für Gießen, Düngen, Foto, Beobachtung
   - automatische Sensorwerte ohne doppelte manuelle Eingabe

5. **Grow-Profile / Zyklusvorlagen**
   Nicht die starre Fremd-Schedule-Engine kopieren, sondern ein Grow-Central-eigenes Profilmodell schaffen:
   - Phasen und typische Dauer
   - Zielbereiche für Temperatur/RH/VPD
   - optional PPFD/DLI
   - optionale Aufgaben/Erinnerungen
   - profilbasierte Warnschwellen
   - frei editierbar; keine harte Bindung an eine Sorte oder Düngerfirma

### P1 – im selben Entwicklungszug vorbereiten

6. **DLI-Berechnung**
   - vorhandene PPFD-Capability verwenden
   - bei ausreichend kontinuierlichen PPFD-Werten DLI aus der realen Historie integrieren
   - bei Einzelmessung nur eine klar gekennzeichnete Schätzung anbieten
   - Tages-DLI in Historie und Pflanzenkontext darstellen

7. **VPD nicht nur anzeigen, sondern bewerten**
   - VPD-Zielbereiche aus Grow-Profil/Phase
   - Abweichung als niedrig / im Ziel / hoch
   - keine zweite VPD-Berechnung, wenn Grow Central bereits den Wert liefert
   - Blatt-Temperaturkorrektur später optional ergänzbar

8. **Regelbasierter Plant Doctor**
   - eigene MIT-kompatible Implementierung
   - Symptome + betroffene Pflanzenzone + Medium + reale Sensorhistorie kombinieren
   - Ergebnis als mögliche Ursachen mit Begründung, Gegenprüfung und Maßnahmen ausgeben
   - keine Diagnose als sichere Gewissheit darstellen
   - Diagnose als Timeline-Event speicherbar

9. **Foto-Tagebuch verbessern**
   - Kamera/Upload
   - Pflanzenzuordnung
   - Datum/Phase/Tag im Zyklus
   - Sensor-Snapshot
   - optionale Notiz/Tags
   - zukünftige Bildanalyse über klar getrennte Provider-Schnittstelle

### P2 – danach / experimentell

10. **Lokale Bildanalyse**
    - Architektur für lokale/on-device Analyse vorbereiten
    - Trichom-/Entwicklungsstadium und Blattzustand nur als Assistenzfunktion
    - keine Abhängigkeit von einem extern fremdgehosteten Modell im Kern
    - Modelllizenz und Trainingsdaten müssen vor Distribution geklärt sein

11. **Turgor-/Blattwinkel-Auswertung**
    - nur als experimenteller eigener Algorithmus
    - Verlauf ist wichtiger als Einzelwert
    - Kamera- und Lichtwinkelabhängigkeit berücksichtigen

12. **Strain-/Sortendatenbank**
    - nicht ungeprüft 2.800 Fremddatensätze importieren
    - zunächst eigenes neutrales Datenmodell und Importer definieren
    - Herkunft/Lizenz jedes Datensatzes dokumentieren

## UI-Regeln

- Der aktuelle Grow-Central **Final-Master bleibt optisch verbindlich**.
- Keine Übernahme fremder Navigationsleisten, Farben, Kartenstile oder Fonts.
- Neue Funktionen werden in die bestehende Desktop-/Mobile-Struktur eingefügt.
- CO2 bleibt standardmäßig ausgeblendet und wird nur optional auf Benutzeraktion/aktivierter Capability sichtbar.
- Livewerte müssen reale Backend-/Sensorwerte verwenden; keine Demo-/Placeholder-Werte im Produktivpfad.
- Auf iPhone/WebKit und Desktop testen.

## Datenmodell – Zielrichtung

Bestehende Room-/Plant-Daten nicht ersetzen, sondern migrationsfähig ergänzen.

Empfohlene neue logische Objekte:

```text
GrowProfile
  id
  name
  phases[]
  targets{}
  tasks[]

PlantCycle
  plant_id
  profile_id?
  start_date
  phase
  phase_started_at
  expected_harvest_from?
  expected_harvest_to?

GrowEvent
  id
  room_id
  plant_id?
  type
  timestamp
  note?
  payload{}
  sensor_snapshot{}
```

Persistenz muss mit bestehender lokaler Grow-Central-Datenhaltung kompatibel bleiben. Vor Schemaänderung Migration und Rückwärtskompatibilität testen.

## Automations-Optimierung

Grow-Profile dürfen Automationen **nicht direkt ungeprüft schalten**. Trennung:

1. Profil definiert Ziele.
2. Sensorik liefert Istwerte.
3. bestehende Automation Engine bewertet Regeln.
4. Sicherheits-/Gerätegrenzen bleiben vorrangig.

Beispiele für spätere Regeln:

- Bodenfeuchte unter pflanzenspezifischer Schwelle -> Hinweis; automatische Bewässerung nur bei ausdrücklich konfigurierter Hardware/Sicherheitsregel.
- VPD außerhalb Zielbereich -> Lüftung/Feuchte/Licht als mögliche Stellgrößen anzeigen.
- DLI-Ziel erreicht -> Lichtsteuerung nur über bestehende sichere Device-Automation.

## Datenschutz / Local First

- Tagebuch, Fotos, Sensor-Snapshots und Profile standardmäßig lokal auf Grow Central.
- Cloud-Sync bleibt optional.
- Externe KI-/Bildanalyse darf ohne ausdrückliche Aktivierung keine Bilder übertragen.
- lokale Analyse wird bevorzugt, sofern Modell/Hardware dies zuverlässig erlauben.

## Lizenz- und Herkunfts-Gate

Vor Merge einer Fremdübernahme muss im PR/Commit dokumentiert sein:

- Quellrepository
- konkrete Quelldatei / Commit
- Lizenz
- ob Code übernommen, portiert oder nur das Verhalten neu implementiert wurde
- erforderlicher Copyright-Hinweis

Für `jnrabit/chlorophyll-chronik`: standardmäßig **clean-room/Neuimplementierung**, kein GPL-Code in MIT-Dateien.

Für `Shannon-Goddard/grow_app`: direkte MIT-Übernahme nur wenn technisch sinnvoll; bevorzugt auf Grow-Central-Modelle portieren statt Fremdarchitektur einzubauen.

Für `xn4k/GrowApp`: bis zur zweifelsfreien Lizenzklärung nur Verhalten/Konzepte.

## Akzeptanzkriterien für den nächsten Live-Run

Der Run gilt für dieses Paket als erfolgreich, wenn mindestens:

- bestehende Räume/Pflanzen nach Update unverändert vorhanden sind
- ein Pflanzenevent erstellt und wieder geladen werden kann
- ein Event einen echten Sensor-Snapshot erhält
- Bodenfeuchte aus dem aktuellen GC-ESP32-Pfad korrekt im Snapshot erscheint
- Tagesansicht reale Werte und Events zeigt
- Grow-Profil einer Pflanze zugeordnet werden kann
- Phasenwechsel persistiert wird
- VPD-Zielbewertung aus Profil + Live-/Historienwert funktioniert
- CO2 im Standard-Dashboard weiterhin verborgen bleibt, solange nicht optional aktiviert
- kein Cloud-Dienst für Kernfunktionen erforderlich ist
- Mobile/iPhone und Desktop funktionieren
- bestehende Pairing-, Kalibrier-, MQTT-TLS- und Sensorhistorienpfade nicht regressieren
- Tests für Migration, Eventmodell, Snapshot und Zielwertbewertung ergänzt wurden

## Nicht tun

- kein Komplett-Fork einer der drei Apps
- kein Fremd-UI als Ersatz des Final-Masters
- keine zweite Sensor-Datenbank neben Grow Central
- keine zweite Geräte-/Automationsengine
- kein ungeprüfter Import fremder Sorten-, Nährstoff- oder Bilddaten
- kein GPL-Copy/Paste in den MIT-Kern
- keine simulierten Livewerte in produktiven Karten
- bestehende Bodenfeuchte-Kalibrierung nicht umgehen

## Reihenfolge für den nächsten Live-Run

1. aktuellen `master` und aktuellen Hardware-/Sensorstand prüfen
2. Migrationstests für bestehende Räume/Pflanzen anlegen
3. `GrowEvent` + Sensor-Snapshot implementieren
4. PlantCycle/Phasen ergänzen
5. GrowProfile + Zielbereiche ergänzen
6. Daily-Check-in in Final-Master integrieren
7. Foto-Tagebuch auf Event/Snapshot umstellen
8. VPD/DLI-Auswertung ergänzen
9. Plant-Doctor-Grundgerüst als eigene Implementierung
10. vollständige Regression für Sensoraufnahme, Kalibrierung, Pairing, MQTT-TLS, History, Mobile/Desktop
11. erst danach neuen Image-/Live-Candidate erzeugen

## Quellenstand der Grow-Central-Prüfung

Grow Central wurde beim Erstellen dieses Auftrags auf `master` gegen den Repository-Stand vom 2026-10-15 geprüft. Der bisherige Release-Candidate Build 375 bleibt dadurch unverändert ein `CANDIDATE`; diese Datei behauptet **keine bereits erfolgte Implementierung** der oben neu beschriebenen Funktionen.
