# 135er-Grow Central – öffentliche Produktseite

Die statische Seite unter `website/` ist die öffentliche, bewusst reduzierte Produktdarstellung von **135er-Grow Central**.

**Öffentliche URL:** `https://grow-central.de/`

## Kommunikationsziel

Die Seite erklärt verständlich:

- den Local-First-Ansatz;
- die Raspberry-Pi-Zentrale ohne eigenen Desktop;
- die Bedienung auf Desktop, Tablet und Smartphone;
- Räume, Geräte, Messwerte, Kamera, Zeitpläne und Automationen;
- die herstellerübergreifende Ausrichtung;
- die Hardwareklassen Pi 3 Legacy/Lite, Pi 4 Full Support und Pi 5 Performance;
- die gemeinsame Universal-Image-Strategie für die unterstützten Raspberry-Pi-Klassen;
- die geschlossene Entwicklungs- und Hardwaretestphase.

## Vertraulichkeitsgrenze

Die öffentliche Seite veröffentlicht ausdrücklich **nicht**:

- Repository- oder Quellcode-Links;
- Buildnummern, Commit-IDs oder Workflow-Run-IDs;
- Images, App-Pakete oder Installationsskripte;
- API-Namen, interne Protokolle oder konkrete Betriebsendpunkte;
- lokale Adressen, Ports, Zugangsdaten, Tokens oder Diagnosedaten;
- interne Release-, Hardware- oder Architektur-Dokumente.

Hersteller- und Produktnamen beschreiben Integrationspfade. Sie sind keine pauschale Zusage, dass jedes Modell und jede Firmware bereits vollständig unterstützt wird.

## Öffentliche Dateien

Der Deployment-Workflow veröffentlicht ausschließlich eine feste Positivliste:

- `index.html`
- `styles.css`
- benötigte Markenbilder;
- eine ausgewählte, bereits freigegebene GUI-Vorschau.

Alle früher öffentlich abgelegten Installationsskripte, Release-Dateien, Prüfsummen und internen Dokumente werden beim nächsten Deployment aus dem Webverzeichnis entfernt.

## Deployment

Zielverzeichnis:

```text
/var/www/vhosts/grow-central.de/httpdocs/
```

Der Workflow `.github/workflows/deploy-website-sftp.yml` veröffentlicht die Positivliste nach `https://grow-central.de/` und bereinigt Dateien, die nicht mehr zu dieser Liste gehören.

## Gestaltung

Branding, Logo und Wiedererkennungswert von **135er-Grow Central** bleiben unverändert. Die Seite folgt weiterhin dem GrowCentral Nexus UI, konzentriert sich jedoch auf Produktnutzen statt auf interne Implementierungsdetails.
