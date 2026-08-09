# 135er-Grow Central – Project Website

Die statische Projektseite unter `website/` ist die öffentliche Präsentationsfläche von 135er-Grow Central.

**Website-Version:** `alpha-0.7.1`

> **Status: WORK IN PROGRESS** – die Projektseite zeigt bewusst den aktiven Entwicklungsstand und darf nicht als Hinweis auf vollständig validierte Produktionsreife verstanden werden.

## Design

Die Website orientiert sich direkt an der lokalen Grow Central-Ziel-GUI: feste Navigation/Sidebar, technische Statuskarten, HUD-Panels, Ringanzeige, Diagnostikflächen sowie grün-cyanfarbene Zustände. Das Layout ist für Desktop, iPad und Smartphone responsive ausgelegt.

Die öffentliche Website bleibt technisch und sicherheitlich vollständig von der lokalen Steueroberfläche getrennt. Sie enthält keine Zugangsdaten, keine Steuerendpunkte und keine direkte Verbindung zum Raspberry Pi.

## Branding und Grafikformate

Die öffentliche Website verwendet das PNG-Logo:

- `assets/brand/135er-grow-central-logo.png`
- `assets/brand/135er-grow-central-mark.png`

WebP wird nicht mehr verwendet. Rastergrafiken werden als PNG eingebunden; ICO ist für das Browser-Favicon zulässig. SVG bleibt für technische Vektorgrafiken und Diagramme erlaubt.

## GUI-Vorschau

- `assets/gui/local-desktop-v0.8.png`
- `assets/gui/local-tablet-v0.8.png`
- `assets/gui/local-mobile-v0.8.png`
- `assets/gui/cloud-desktop-v0.8.png`

Alle vier vorhandenen GUI-Demos werden direkt als PNG geladen. Es gibt keine WebP- oder GUI-SVG-Referenzen mehr.

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

**Wichtig:** Der Verzeichnisname lautet `vhosts` (Plural). Der Login-Benutzer `dezender` sieht denselben Bereich als `~/httpdocs`.

### Deployment als root

```bash
set -e
WEBROOT=/var/www/vhosts/dezender.de/httpdocs
TMP=/tmp/135er-Grow-Central

rm -rf "$TMP"
git clone --depth 1 https://github.com/jygnw29kms-bit/135er-Grow-Central.git "$TMP"
mkdir -p "$WEBROOT"
cp -a "$TMP/website/." "$WEBROOT/"
```

### Eigentümer und sichere Standardrechte

Nach einem Root-Deployment werden Eigentümer und Rechte auf den Systembenutzer `dezender` zurückgesetzt. Die primäre Gruppe wird dynamisch ermittelt, damit keine Plesk-Gruppenbezeichnung geraten werden muss:

```bash
WEBROOT=/var/www/vhosts/dezender.de/httpdocs
DEZENDER_GROUP="$(id -gn dezender)"

chown -R dezender:"$DEZENDER_GROUP" "$WEBROOT"
find "$WEBROOT" -type d -exec chmod 755 {} +
find "$WEBROOT" -type f -exec chmod 644 {} +
```

Für diese statische Website werden keine ausführbaren Dateien im Webroot benötigt. Deshalb sind `755` für Verzeichnisse und `644` für reguläre Dateien die vorgesehenen Standardrechte.

### Prüfung

```bash
stat -c '%U:%G %a %n' \
  /var/www/vhosts/dezender.de/httpdocs \
  /var/www/vhosts/dezender.de/httpdocs/index.html \
  /var/www/vhosts/dezender.de/httpdocs/styles.css

find /var/www/vhosts/dezender.de/httpdocs -maxdepth 2 -type f | sort
```

Danach sollten insbesondere folgende Dateien vorhanden sein:

```text
/var/www/vhosts/dezender.de/httpdocs/index.html
/var/www/vhosts/dezender.de/httpdocs/styles.css
/var/www/vhosts/dezender.de/httpdocs/assets/architecture.svg
/var/www/vhosts/dezender.de/httpdocs/assets/gui/local-desktop-v0.8.png
/var/www/vhosts/dezender.de/httpdocs/assets/brand/135er-grow-central-logo.png
/var/www/vhosts/dezender.de/httpdocs/assets/brand/135er-grow-central-mark.png
```

## GitHub Pages

Die Pages-Workflow-Datei liegt unter `.github/workflows/pages.yml`. Der Workflow wird manuell gestartet. Für die erstmalige Nutzung muss GitHub Pages unter **Settings → Pages → Source: GitHub Actions** aktiviert werden.
