# 135er GrowControl – Project Website

Die statische Projektseite unter `website/` ist die öffentliche, domain-neutrale Präsentationsfläche von 135er GrowControl.

## Design

Seit v0.6 folgt die Website visuell derselben HUD-/Control-Plane-Sprache wie die lokale GrowControl-GUI: dunkle technische Panels, grün-cyanfarbene Statussignale, monospace Systemlabels und responsive Tablet-/Smartphone-Layouts.

Die öffentliche Website bleibt technisch und sicherheitlich vollständig von der lokalen Steueroberfläche getrennt. Sie enthält keine Zugangsdaten, keine Steuerendpunkte und keine direkte Verbindung zum Raspberry Pi.

## Assets und Bild-Fallback

Die GUI-Vorschau wird bevorzugt als WebP geladen. Für Hosting-Umgebungen mit fehlerhafter WebP-/MIME-Konfiguration ist zusätzlich ein PNG-Fallback vorgesehen:

- `assets/gui-preview-v0.5.webp`
- `assets/gui-preview-v0.5.png`

Das HTML verwendet dafür ein `<picture>`-Element. Damit bleibt die Vorschau auch auf konservativ konfigurierten Webservern und Browsern sichtbar.

## Lokale Vorschau

```bash
cd website
python3 -m http.server 8000
```

Danach `http://localhost:8000` im Browser öffnen.

## Deployment

Das Webroot auf dem aktuellen Plesk-Webspace ist `/httpdocs`. Für eine manuelle Aktualisierung vom Server aus:

```bash
cd /tmp
rm -rf 135er_GrowControl
git clone https://github.com/jygnw29kms-bit/135er_GrowControl.git
cp -a 135er_GrowControl/website/. /httpdocs/
```

## GitHub Pages

Die Pages-Workflow-Datei liegt unter `.github/workflows/pages.yml`. Der Workflow wird manuell gestartet. Für die erstmalige Nutzung muss GitHub Pages unter **Settings → Pages → Source: GitHub Actions** aktiviert werden.

Es ist kein Custom-Domain-Setup im Repository hinterlegt.
