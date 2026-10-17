# Grow-Central enclosure V4 - PROTOTYP

> **STATUS: PROTOTYP / KEINE SERIENFREIGABE**
>
> Dieser komplette Ordner ist Entwicklungs-CAD. FCStd/STEP sind Konstruktionsdaten; STL und P2S-3MF sind lediglich Rapid-Prototyping-Ausgaben. Das spaetere Endprodukt muss nicht 3D-gedruckt werden.

## Varianten
- Pi4 PROTOTYP: Raspberry Pi 4 Gehaeuse, zweifarbig erhabenes Grow-Central Branding.
- Node FPC PROTOTYP: XIAO Node mit robuster abnehmbarer 44 x 24 mm Antennenplatte fuer die originale 40 x 20 mm Klebeantenne.
- Node EXT PROTOTYP: XIAO Node mit verstaerkter 6,5 mm SMA/RP-SMA Bulkhead-Aufnahme.
- Hub FPC PROTOTYP: Hub mit abnehmbarer FPC-Antennenplatte.
- Hub EXT PROTOTYP: Hub mit verstaerkter SMA/RP-SMA Bulkhead-Aufnahme.

## Universal-Montage Node/Hub
Jede Node-/Hub-Base besitzt zwei unabhaengige M4-Montagesysteme:
- **Liegend:** 2 x M4, vertikale Schraubachse, massive Boden-/Seitenohren.
- **Stehend:** 2 x M4, horizontale Schraubachse, massive seitliche Boss-/Web-Aufnahmen.

Bohrung: 4,3 mm fuer M4-Prototypmontage. Mindestmaterial um die Bohrung im CAD: ca. 3,05 bis 3,35 mm. Keine filigranen Federlaschen.

## Antenne
### FPC
- Originale Klebeantenne: 40 x 20 mm Referenz.
- Traeger: 44 x 24 mm mit 2 mm Rand ringsum.
- Traeger sitzt an der Rueckseite der Base und ist unabhaengig vom Deckel.
- Koaxdurchgang/Zugentlastung so positioniert, dass liegende und stehende Montage frei bleiben.

### EXT
- 6,5 mm SMA/RP-SMA Bulkhead-Bohrung.
- Mittig auf der Rueckseite und vertikal mittig angeordnet, damit beide Montagearten funktionieren.
- Verstaerkter Sitz fuer Mutter/Koax.

## Validierung
`validate_v4_PROTOTYP.py` prueft Geometrie, Single-Solid-Bases, Hardwarekollisionen, Deckel, Branding, vier M4-Referenzen, freie Schraubkanaele, FPC-Traeger und SMA-Aufnahme.

Aktueller Stand: **PASS / keine CAD-Fehler**.
- je Node/Hub: 2 liegende + 2 stehende M4-Punkte
- M4-Bohrungen: 0,0 mm3 blockiert
- Board/Base: 0,0 mm3 Kollision
- Board/Deckel: 0,0 mm3 Kollision
- Base/Deckel: 0,0 mm3 Kollision
- FPC-Traeger/Deckel/XIAO: 0,0 mm3 Kollision
- SMA-Referenz/Base: 0,0 mm3 blockiert

`validate_p2s_v4_PROTOTYP.py` prueft P2S 0,4 mm, 0,20 Standard, PROTOTYP-Dateinamen, Objektzahl, Branding-Ausrichtung und den Antennentraeger als viertes Objekt der FPC-Projekte.

## Fertigung
Der P2S dient aktuell ausschliesslich zur schnellen Prototypenpruefung. Geometrie und Wandaufbau duerfen spaeter fuer ein anderes Fertigungsverfahren grundlegend ueberarbeitet werden.
