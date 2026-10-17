# Grow-Central Enclosures FreeCAD V2

Komplett neu konstruierte Gehaeusefamilie fuer Raspberry Pi 4 und Seeed XIAO ESP32-C3.

## Modelle

- `GrowCentral_Pi4_V2.FCStd`
- `GrowCentral_XIAO_Node_V2.FCStd`
- `GrowCentral_XIAO_Hub_V2.FCStd`

Zu jedem produktiven Druckteil liegen STEP und STL unter `models/`.

## Hardware-Referenzen

Die Konstruktionen wurden um reale STEP-Referenzkoerper herum aufgebaut. Beim XIAO sind zusaetzlich zwei 2,54-mm-Pfostenleisten als Kollisionskoerper modelliert, inklusive Kunststoffkoerper und Pin-Ueberstand ober- und unterhalb der Platine.

Die Referenzdateien unter `references/` bleiben lokal und werden wegen Fremdlizenzen nicht automatisch mitversioniert.

## Verifikation

`validate_v2.py` prueft:

- Shape-Gueltigkeit
- Anzahl der Solids
- Bounding Box
- Kollision Hardware gegen Base
- Kollision Hardware gegen Deckel

Aktueller Stand: Pi4, XIAO Node und XIAO Hub jeweils Base und Deckel als einzelner gueltiger Solid; Referenzhardware gegen Base und Deckel jeweils `0.0 mm3` unerwuenschte Kollision.

## 0,4-mm-Duese / FDM

Die sichtbaren Branding-Details sind bewusst fuer eine 0,4-mm-Duese ausgelegt:

- keine absichtlich filigranen Einlinien-Schriften
- gravierte Beschriftungen statt freistehender Schriftinseln
- Gravurtiefe etwa 0,68 bis 0,78 mm
- grosse Produktkennzeichnung: `GROW CENTRAL / PI4`, `GC NODE`, `GC HUB`
- abgerundete Lueftungsschlitze mit deutlich groesserer Breite als eine einzelne Extrusionslinie
- Deckel- und Gehaeusekanten fuer PETG/ASA und normale 0,20-mm-Schichthoehe ausgelegt

Empfohlener erster P2S-Testdruck: 0,4-mm-Duese, 0,20-mm-Layer, 4 Waende, PETG. Vor Seriennutzung folgt ein realer Fit-/Drucktest.

## Render

`render_blender.py` rendert direkt aus den produktiven STL-Geometrien. Die Bilder unter `previews/` und `previews/hero/` sind daher echte Modellvorschauen und keine generierten Konzeptbilder.


## Branding / dual-colour FDM rule

Grow-Central enclosure branding is raised/extruded, never engraved. It is exported as a separate branding body/STL so Bambu Studio/AMS can assign a second filament colour without painting individual faces. For the 0.4 mm nozzle family the current raised height is 0.85 mm and lettering is sized for robust FDM readability. On the Pi4 lid, branding must remain on the free side of the lid and outside the GPIO/pin-header service opening.

For Bambu/Orca print projects, generate the final 3MF through the slicer itself rather than hand-building the 3MF metadata container. The Bambu-native export is the validated reference path.
