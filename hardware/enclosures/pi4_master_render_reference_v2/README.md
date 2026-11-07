# GrowCentral Pi 4 | Bild-Master CAD V2

**Verbindliche optische Referenz:** das vom Benutzer freigegebene, dunkel-anthrazit/gruene Produkt-Rendering des GrowCentral Pi4-Gehäuses. Dieses Verzeichnis ist die auf Jens-PC mit FreeCAD 1.1 erstellte CAD-Nachkonstruktion, kein anderes Design.

## Umgesetzte, sichtbar verbindliche Merkmale
- anthrazitfarbenes, deutlich abgerundetes und abgeschraegtes Gehäuse
- zweistufiger skulpturierter Deckel mit erhoehtem Mittelfeld und umlaufender Vertiefung
- zwei diagonale Oberseiten-Lueftungsgruppen und seitliche Ventilation
- eingelassene vier Eckverschraubungen, Schraubenkopf-Referenzen
- gruen umlaufendes Fugenband, grüne Eckakzente und vier grüne Standfuesse
- erhabener GrowCentral-Schriftzug und eigenstaendiges grünes Blattmotiv
- Pi4-Anschlussaussparungen auf den tatsaechlichen zwei Portseiten, interne Gewindevorbereitung/Montagebohrungen
- optionale separate GPIO-Klappe als eigenstaendiges CAD-Teil, **noch nicht als funktionierender Ausschnitt in den Deckel integriert**

## Dateien
- `GrowCentral_Pi4_Master_V2.FCStd` bearbeitbares FreeCAD Hauptmodell
- `build_master_v2.FCMacro` generiert den Stand reproduzierbar
- `_01_*.stl` bis `_09_*.stl` getrennte Bauteile und Hardware-Referenz
- STEP zur Weiterkonstruktion, Vorschaubild PNG

## Konstruktion / Prüfungen
- Umriss 105 x 75 mm, Gehäuse-Unterteil ca. 28.55 mm hoch, dazu modellierter Deckel.
- PCBA-Referenz Raspberry Pi 4: 85 x 56 mm, Mount-Lochbild 58 x 49 mm (Modell-Sollwerte).
- Rahmenwand etwa 2.8 mm, Boden 3 mm.
- Alle 9 exportierten Formen `isValid=True`, Hauptkoerper je genau ein Solid.
- **Boden/Deckel-Kollisionsvolumen laut FreeCAD 0.0 mm³.**
- Realer Raspberry-Pi-4-STEP-Referenzkörper aus `prototype_v5/references`: **0.0 mm³ Kollision mit Boden und Deckel**, nach lokaler 0.65-mm-Freistellung am hinteren rechten Montagepfosten. Prüfbelege `validate_pi4_fit.FCMacro`, `pi4_fit.log` und `GrowCentral_Pi4_Master_V2_WithHardware.FCStd`.
- `GrowCentral_Pi4_ActualCAD_Studio.png` und `GrowCentral_Pi4_ActualCAD_Exploded.png` wurden in Blender direkt aus den exportierten STL-Dateien gerendert. Die bearbeitbare Render-Szene liegt als `.blend` bei.

## P2S-3MF-Druckplatte
- `GrowCentral_Pi4_P2S_FinalMaster_Plate.3mf` ist eine Standard-3MF-Geometrieplatte mit 7 separaten Objekten auf einer 256 x 256 mm Druckfläche; die vier Füße sind als Multibody-Druckobjekt gruppiert.
- Enthält Boden, umlaufende grüne Ziernaht, Deckel, grüne Ecken, reparierten erhabenen Schriftzug, grünes Blatt und grüne Füße. Schraubenreferenzen und nicht integrierte GPIO-Klappe sind ausgeschlossen.
- Bambu Studio: **P2S**, **0,4-mm-Düse**, **PETG**, Schwarz/Grün per AMS zuordnen, Stützen für Deckelüberhang kontrollieren und **vor dem Druck slicen**. Diese Datei enthält kein freigegebenes Bambu-Druckprofil und keinen G-Code.
- Die ZIP-/3MF-Struktur wurde wieder eingelesen und auf 7 Objekte, geometrisch gültige/wasserdichte Druckmesh-Körper sowie Plattenbegrenzung überprüft (`p2s_3mf_validation.txt`).

## Vor Freigabe
Die Render-Vorlage ist perspektivisch, zeigt Anschlüsse teils auf unmoeglichen Seiten und enthält keine technische Bemaßung. Damit ist eine hundertprozentig pixel- und maßgetreue Umsetzung aus dem Bild allein geometrisch nicht belegbar. Die CAD-Form ist deshalb ein **Bild-Master-Konstruktionsstand, noch keine mechanische Fertigungsfreigabe**.
Offen: reale Pi4-Platinen-Passprobe, genaue Steckerkonturen/Höhen, Verschraubung/Heat-Set, Deckelauflage/Klemmen, real funktionale GPIO-Klappe, Druckprobe (P2S / 0.4 mm / PETG), Farbe / AMS, optischer Side-by-Side Vergleich mit Render.
Hardware-Schrauben sind **nur Referenzkoerper, keine FDM-Teile**.
