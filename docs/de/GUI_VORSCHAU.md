# GUI-Zielbild und Responsive Design

Dieses Dokument definiert das aktuelle Vorschaubild als **verbindliche Design-Referenz** für die fertige Benutzeroberfläche von 135er GrowControl.

## Aktueller Stand v0.7

![135er GrowControl GUI v0.7 mit Power- und Kostenhochrechnung](../../website/assets/gui-power-preview-v0.7.svg)

## Ursprünglicher Stand v0.5

![135er GrowControl GUI Basis-HUD v0.5](../assets/gui/gui-preview-v0.5.png)

Die v0.7-Referenz erweitert das Basis-HUD um Steckdosen-Schaltzustände,
Leistungsdaten, einen frei einstellbaren Strompreis und Hochrechnungen für
Stunde, Tag, Woche, Monat und Jahr. Beide Bilder bleiben als nachvollziehbare
Entwicklungsstände erhalten.

## Zielbild

Die finale Oberfläche soll sich optisch und funktional an dieser Referenz orientieren. Das Dashboard bleibt dunkel, futuristisch, übersichtlich und für dauerhafte Nutzung auf Desktop, Tablet/iPad und Smartphone geeignet.

Kernelemente der Referenz:

- linke Hauptnavigation für Dashboard, Geräte, Sensoren, Historie, Zeitpläne, Automationen, Cloud und System
- zentrale Live-Karten für Temperatur, Luftfeuchtigkeit, VPD, Lüfterstatus, Cloud-Sync und Systemstatus
- DF100M-Gerätesteuerung mit Gerätestatus, BLE-Status, Geschwindigkeit und Diagnosefunktionen
- Local-/Cloud-Architekturstatus auf einen Blick
- Verlaufskurven für Sensor- und Systemdaten
- Zeitpläne und Automationen direkt im Dashboard
- Sicherheits- und Plattformstatus sichtbar, ohne die Hauptbedienung zu überladen
- klare Statusfarben für OK, Warnung, Offline und experimentelle Funktionen

## Responsive Vorgaben

Die GUI darf nicht nur verkleinert werden. Sie muss sich je nach verfügbarem Platz strukturell anpassen.

### Große Desktop-Auflösungen — ab 1400 px

- feste Seitenleiste
- 3- bis 4-spaltiges Dashboard-Grid
- große Verlaufsgrafiken
- Geräte-, Cloud- und Automationskarten nebeneinander
- vollständige Status- und Diagnoseinformationen sichtbar

### Desktop / Notebook — 1024 bis 1399 px

- Seitenleiste bleibt sichtbar oder kann kompakt dargestellt werden
- 2- bis 3-spaltiges Grid
- sekundäre Informationen dürfen in Details/Drawer verschoben werden
- Charts skalieren ohne horizontales Scrollen

### Tablet / iPad — 768 bis 1023 px

- touch-optimierte Bedienflächen
- 2-spaltiges Grid, bei Bedarf einzelne Vollbreiten-Karten
- Seitenleiste einklappbar oder als kompakte Icon-Navigation
- zentrale Werte, Alarmstatus und Geräteaktionen bleiben ohne zusätzliche Navigation erreichbar
- Mindestgröße interaktiver Ziele: ungefähr 44 x 44 CSS-Pixel
- keine Hover-only-Funktionen

### Smartphone — unter 768 px

- 1-spaltiges Kartenlayout
- Navigation als Drawer/Hamburger oder untere Hauptnavigation
- Priorität auf Live-Status, Alarme, Geräte, Schnellaktionen und Zeitpläne
- komplexe Tabellen werden als Karten/Listen dargestellt
- Diagramme passen sich an die Breite an und dürfen horizontal zoombar sein, wenn sinnvoll
- sekundäre Diagnosedaten werden in Detailansichten verschoben

## Technische Frontend-Regeln

- CSS Grid/Flexbox statt fixer Pixel-Layouts
- `clamp()`, relative Einheiten und responsive Typografie
- keine feste Dashboard-Gesamtbreite
- Karten müssen bei schmalen Viewports automatisch umbrechen
- Diagramm-Komponenten müssen ihre Containerbreite beobachten
- Navigation muss per Tastatur und Touch bedienbar sein
- Kontrast und Schriftgrößen müssen auch bei Dauerbetrieb auf einem Tablet gut lesbar bleiben
- Safe-Area-Inset für iPhone/iPad berücksichtigen
- Browser-Zoom darf das Layout nicht zerstören

## Priorität der Inhalte

Bei kleiner werdender Auflösung gilt folgende Reihenfolge:

1. Alarm- und Systemstatus
2. Temperatur, Luftfeuchtigkeit, VPD und zentrale Sensorwerte
3. aktive Geräte und aktuelle Sollwerte
4. Schnellsteuerung und Zeitpläne
5. Historie/Charts
6. Cloud- und Diagnoseinformationen

## Design-Grenze

Das Vorschaubild ist eine **visuelle Zielreferenz**, kein pixelgenaues Mockup für jede Auflösung. Die tatsächliche Implementierung darf Elemente verschieben, zusammenfassen oder in Detailansichten auslagern, solange Bedienlogik, Informationshierarchie und der charakteristische 135er-GrowControl-Look erhalten bleiben.
