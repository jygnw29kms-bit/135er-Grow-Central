# GrowCentral Nexus UI · Design System

**Status:** verbindlich für das gesamte Projekt  
**Gültig für:** Raspberry-Pi-GUI, Boot-/Kiosk-Oberflächen, Mobile Apps, dezender.de, README/Repo-Präsentation, Screenshots, Release-Grafiken und Cloud-/APT-Präsentation.

## Unveränderliche Marke

- offizielles Logo / Lockup bleibt erhalten;
- kompaktes Markenzeichen darf als App-/Favicon-/System-Seal genutzt werden;
- Projektname `135er-Grow Central` bleibt konsistent;
- bestehende Brand-Assets werden nicht stilistisch ersetzt.

## Nexus-Grundstil

- Local-first Control-Center statt generischer Smart-Home-Look;
- dunkle Graphit-/Near-Black-Basis;
- Cyan für Daten, Navigation und technische Information;
- Lime für OK/aktiv/validiert;
- Amber für Warnung/Test/Alpha;
- Rot nur für Fehler, deny oder kritische Zustände;
- klare Hierarchie, geringe visuelle Unruhe, dezenter Glow;
- Panels/Karten mit konsistenten Radien, Linien, Innenabständen und Statuschips;
- responsive Desktop-, Tablet- und Mobile-Layouts aus derselben Komponentenfamilie.

## Design Tokens

```text
Near Black       #020608
Background       #02070A
Panel Graphite   #061015
Panel Elevated   #0A1820
Border           #17414A
Data Cyan        #2AE5FF / #35E8DA
Neon Lime        #71FF3B
Diagnostic Amber #FFB52B
Danger           #FF6877
Primary Text     #EDF8F6
Muted Text       #7EA1A8
```

## Layout

### Desktop / Pi / Website

- linke modulare Navigation;
- kompakte Topbar mit Status, Build, Uhrzeit und Aktionen;
- zentrale Hero-/Statusfläche nur dort, wo sie Informationswert hat;
- Metric Cards für Livewerte;
- System-/Feature-Cards für Details;
- tabellarische Daten und Charts in denselben Panel-Rahmen;
- Footer/Statusleiste nur mit echtem Kontext.

### Tablet / 7-Zoll Kiosk

- Navigation darf auf kompakte Leiste oder reduzierte Sidebar wechseln;
- Touch-Ziele mindestens ca. 44 px;
- Kernmetriken zuerst, Detaildaten nachgelagert;
- keine horizontale Pflichtscrollfläche für Hauptbedienung.

### Mobile

- eigenständige mobile Informationshierarchie, keine verkleinerte Desktop-Seite;
- Safe-Area-Unterstützung;
- große primäre Aktionen;
- lokale Pi-Verbindung und Remote-Ziel klar getrennt;
- Remote ausschließlich HTTPS; lokale private Netze dürfen HTTP verwenden.

## Komponenten

### Statuschips

- `ONLINE`, `READY`, `VALID`, `ACTIVE`: Lime
- `ALPHA`, `TEST`, `CANDIDATE`, `PENDING`: Amber
- `LOCAL`, `INFO`, `SYNC`: Cyan
- `OFFLINE`, `FAILED`, `DENY`: Rot

### Karten

Jede Karte hat genau einen Hauptzweck. Eine Karte soll nicht gleichzeitig Navigation, mehrere Tabellen und primäre Aktionen enthalten. Titel, Substatus und Action-Zone bleiben an allen Oberflächen gleich angeordnet.

### Typografie

- UI: moderne System-Sans-Serif;
- technische Meta-/Build-Angaben dürfen Monospace nutzen;
- keine dekorativen Fonts in der Bedienoberfläche;
- deutsche und englische Begriffe innerhalb einer Ansicht nicht unnötig mischen.

## Bild- und Screenshot-Regeln

- alle aktuellen Vorschaubilder müssen Nexus UI zeigen;
- veraltete GUI-Screenshots werden als `legacy`/`historical` markiert oder ersetzt;
- keine erfundenen Hardware-Validierungswerte in Release-Grafiken;
- Mockup-Telemetrie muss als Konzept-/Demo-Wert erkennbar sein;
- App-, Website- und Pi-Mockups nutzen dieselben Farben, Karten und Statussemantik.

## Repo-Präsentation

- README-Banner, Badges und Screenshots müssen zum aktuellen Release-State passen;
- aktuelle Build-/Kandidateninformation kommt aus `RELEASE_STATE.md`;
- historische Build-Dokumente bleiben für Nachvollziehbarkeit erhalten, werden jedoch nicht als aktueller Stand verlinkt;
- neue Dokumente verwenden dieselben Statusbegriffe wie Release-Pipeline und Website.

## Verbindliche Regel

> Neue oder überarbeitete Oberflächen, Webseiten, Mobile Screens, Boot-/Kiosk-Ansichten, Repo-Grafiken und Dokumentationsbilder müssen sich am GrowCentral Nexus UI orientieren. Abweichungen benötigen einen technischen Grund, keinen rein visuellen Sonderweg.
