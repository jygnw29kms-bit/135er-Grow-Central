# Grow-Central Profile Library Architecture

## Ziel
Grow-Central ist eine universelle Grow-Plattform. Kulturprofile bilden den Einstiegspunkt in die Bedienung und dürfen nicht auf eine einzelne Kulturart zugeschnitten sein.

## Schichten
1. **Official Base Profile**: versionierte, schreibgeschützte Profile aus dem Repository mit Quellen, Phasen, Richtwerten und Aufgaben.
2. **User Recipe / Overlay**: bestehende `/api/v1/recipes`-Daten für persönliche Sollwerte, Notizen und Anpassungen.
3. **Grow Instance**: ein konkreter Grow bindet Profil, optionales Overlay, Raum, Geräte und aktuelle Phase.
4. **Automation**: getrennte Sicherheitsdomäne. Profilwerte lösen niemals automatisch Schreibzugriffe auf Aktoren aus.

## Profilinhalt
Jedes Basisprofil enthält mindestens:
- ID, Name, wissenschaftlichen Namen und Kategorie
- Schwierigkeits- und Lichtbedarf
- unterstützte Anbausysteme
- Phasen mit Aufgaben und optionalen Richtwerten
- nachvollziehbare öffentliche Quellen
- druckbare Checkliste

## Phasen
Phasen sind kulturabhängig und werden nicht künstlich auf Cannabis-Begriffe reduziert. Beispiele sind Vorbereitung, Keimung, Sämling, vegetatives Wachstum, Blüte, Fruchtbildung, Ernte, Ruhephase oder Nachernte.

## GUI-Workflow
`Profil wählen -> Kulturinformationen -> Phase -> To-dos -> Richtwerte -> Druck/PDF -> optional eigenes Rezept -> Grow starten`

Die GUI soll offene Aufgaben, aktuelle Phase, nächste Aktion und relevante Messwerte profilbezogen anzeigen. Nicht vorhandene Sensoren oder Aktoren werden nicht erfunden.

## Cannabis
Cannabis ist ein vollständig unterstütztes Kulturprofil, aber weder Hauptzweck noch primäre Positionierung von Grow-Central. Die Plattform bleibt kulturübergreifend.

## Daten- und Sicherheitsprinzipien
- Local First: Profilbibliothek und aktive Grow-Daten funktionieren ohne Cloud.
- Quellenpflicht für offizielle Richtwerte.
- Sorten- und systemspezifische Abweichungen müssen möglich sein.
- Richtwerte sind Orientierung, keine unveränderlichen Sicherheitsgrenzen.
- Aktorsteuerung erfordert eigene validierte Regeln und Benutzerfreigabe.
- Nutzerprofile überschreiben niemals stillschweigend offizielle Quelldaten.

## Nächste Ausbaustufen
- mehr offizielle Kulturprofile
- profilbezogene Bild- und PDF-Assets
- persistente To-do-Erledigung pro Grow
- Phasenwechsel und Erinnerungen
- Varianten für Erde, Coco, Hydroponik, Gewächshaus und Controlled Environment
- Community-Profile mit klarer Trennung zu offiziellen Grow-Central-Profilen
- Quellen- und Versionshistorie pro Profil
