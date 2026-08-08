# Zeitpläne und Automationen

## Zeitpläne

Zeitbasierte Aktionen wie Lüfter-Sollwerte oder Betriebsfenster werden lokal gespeichert und ausgeführt.

## Automationen

Regeln kombinieren Bedingungen und Aktionen, zum Beispiel:

- Temperatur über Grenzwert -> Lüfterleistung erhöhen
- Luftfeuchtigkeit über Grenzwert -> Alarm erzeugen
- Zeitfenster + Sensorbedingung -> Aktion ausführen

## Sicherheitslogik

- Hysterese gegen schnelles Ein-/Ausschalten
- Cooldown-Zeiten
- minimale/maximale Stellwerte
- Fail-Safe-Zustände
- lokale Validierung jeder Aktion
- Audit-Eintrag für relevante Änderungen

Cloud-Regeln dürfen lokale Sicherheitsgrenzen nicht umgehen.
