# 135er-Grow Central – Project Website

Die statische Projektseite unter `website/` ist die öffentliche Präsentationsfläche von 135er-Grow Central.

**Website-Version:** `alpha-0.7.5`

**Öffentlicher Raspberry-Pi-Teststand:** `Build 70`

> **Status: ALPHA / HARDWAREVALIDIERUNG** – geplante Builds und Mobile-Pakete werden ausdrücklich von veröffentlichten Downloads getrennt dargestellt.

## Aktuelle Release-Pipeline

Die öffentliche Seite bildet ab 2026-08-16 die verbindliche Reihenfolge ab:

1. Build 71 sichern;
2. Build 72 ausschließlich auf Build 71 aufsetzen;
3. Mobile v0.1 auf iPhone und Android testen;
4. Prüfen → Probieren/Testen → Optimieren → Absichern → Abschlussprüfung;
5. Build 72 und Mobile v0.1 veröffentlichen;
6. Installationslinks und QR-Codes für iPhone und Android bereitstellen.

Details: [`docs/RELEASE_PIPELINE.md`](../docs/RELEASE_PIPELINE.md)

## Mobile-Architektur

Mobile v0.1 ist ein WebGUI-Client und **kein Ersatz für den Raspberry Pi**. Der Raspberry Pi bleibt die autoritative lokale Instanz für Gerätezugriff, Policy und Automation. Optional kann die Server-Version später einen abgesicherten Remote-Zugriff bereitstellen.

## Design

Die Website orientiert sich direkt an der lokalen Grow-Central-Ziel-GUI: technische Statuskarten, HUD-Panels, grün-cyanfarbene Zustände sowie responsive Ansichten für Desktop, iPad und Smartphone.

Die öffentliche Website bleibt technisch und sicherheitlich vollständig von der lokalen Steueroberfläche getrennt. Sie enthält keine Zugangsdaten, keine lokalen Steuerendpunkte und keine direkte Verbindung zum Raspberry Pi.

## Branding und GUI-Vorschau

Verwendete Markenassets:

- `assets/brand/135er-grow-central-lockup-v0.9.png`
- `assets/brand/135er-grow-central-logo.png`
- `assets/brand/135er-grow-central-mark.png`

GUI-Vorschauen:

- `assets/gui/local-desktop-v0.9.png`
- `assets/gui/local-tablet-v0.9.png`
- `assets/gui/local-mobile-v0.9.png`
- `assets/gui/cloud-desktop-v0.9.png`

## Produktions-Deployment auf dezender.de

Der bestätigte Plesk-Webroot lautet:

```text
/var/www/vhosts/dezender.de/httpdocs
```

Das Repository enthält `.github/workflows/deploy-website-sftp.yml`. Jeder Push auf `master`, der `website/**` verändert, veröffentlicht den Inhalt des Website-Verzeichnisses automatisch per SFTP nach dezender.de.

Die Zugangsdaten liegen ausschließlich als GitHub Actions Secrets vor und werden nicht in Website oder Repository geschrieben.

## Lokale Vorschau

```bash
cd website
python3 -m http.server 8000
```

Danach `http://localhost:8000` im Browser öffnen.
