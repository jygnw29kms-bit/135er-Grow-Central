# 135er GrowControl – Project Website

Die statische Projektseite unter `website/` ist die öffentliche Präsentationsfläche von 135er GrowControl.

## Design

Die Website orientiert sich direkt an der lokalen GrowControl-Ziel-GUI: feste Navigation/Sidebar, technische Statuskarten, HUD-Panels, Ringanzeige, Diagnostikflächen sowie grün-cyanfarbene Zustände. Das Layout ist für Desktop, iPad und Smartphone responsive ausgelegt.

Die öffentliche Website bleibt technisch und sicherheitlich vollständig von der lokalen Steueroberfläche getrennt. Sie enthält keine Zugangsdaten, keine Steuerendpunkte und keine direkte Verbindung zum Raspberry Pi.

## Branding und Grafikformate

Die öffentliche Website verwendet das PNG-Logo:

- `assets/brand/135er-growcontrol-repo-mark.png`
- `assets/brand/favicon.ico`

WebP wird nicht mehr verwendet. Rastergrafiken werden als PNG eingebunden; ICO ist für das Browser-Favicon zulässig. SVG bleibt für technische Vektorgrafiken und Diagramme erlaubt.

## GUI-Vorschau

- `assets/gui-preview-v0.5.png`
- `assets/gui-power-preview-v0.7.svg`

Die v0.5-Vorschau wird direkt als PNG geladen. Es gibt kein `<picture>`-Element mit WebP-Quelle mehr.

## Lokale Vorschau

```bash
cd website
python3 -m http.server 8000
```

Danach `http://localhost:8000` im Browser öffnen.

## Produktions-Deployment auf dezender.de

Der per SSH bestätigte absolute Plesk-Webroot ist:

```text
/var/www/vhosts/dezender.de/httpdocs
```

Der Login-Benutzer sieht dasselbe Verzeichnis als `~/httpdocs`.

Für eine vollständige Aktualisierung vom Server aus:

```bash
cd /tmp
rm -rf 135er_GrowControl
git clone https://github.com/jygnw29kms-bit/135er_GrowControl.git
cp -a 135er_GrowControl/website/. /var/www/vhosts/dezender.de/httpdocs/
```

Danach sollten insbesondere folgende Dateien vorhanden sein:

```text
/var/www/vhosts/dezender.de/httpdocs/index.html
/var/www/vhosts/dezender.de/httpdocs/styles.css
/var/www/vhosts/dezender.de/httpdocs/assets/architecture.svg
/var/www/vhosts/dezender.de/httpdocs/assets/gui-preview-v0.5.png
/var/www/vhosts/dezender.de/httpdocs/assets/brand/135er-growcontrol-repo-mark.png
/var/www/vhosts/dezender.de/httpdocs/assets/brand/favicon.ico
```

## GitHub Pages

Die Pages-Workflow-Datei liegt unter `.github/workflows/pages.yml`. Der Workflow wird manuell gestartet. Für die erstmalige Nutzung muss GitHub Pages unter **Settings → Pages → Source: GitHub Actions** aktiviert werden.
