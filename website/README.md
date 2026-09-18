# 135er-Grow Central – öffentliche Produktseite

Öffentliche URL: `https://grow-central.de/`

Grow Central wird vollständig Open Source entwickelt. Die Seite erklärt Local First, die optionale Cloud, unterstützte Hardwareklassen und Geräteintegrationen und verlinkt das öffentliche Repository sowie veröffentlichte Releases. Ein CANDIDATE wird erst nach realen Hardwaretests als VALIDATED eingestuft.

## Öffentliche Dateien

Das Deployment veröffentlicht ausschließlich `index.html`, `styles.css`, `impressum.html`, `datenschutz.html` und die benötigten Markenbilder sowie eine freigegebene GUI-Vorschau. Projektquellcode wird über GitHub bereitgestellt. Zugangsdaten, private Schlüssel und personenbezogene Diagnosedaten werden nicht ins Webverzeichnis übernommen.

## Deployment

Ziel: `/var/www/vhosts/grow-central.de/httpdocs/`.

Der Workflow `.github/workflows/deploy-website-sftp.yml` erstellt die öffentliche Dateiliste und veröffentlicht sie per SFTP. `scripts/deploy-public-website.sh` stellt dieselben Dateien bei einem Plesk-Git-Deployment bereit; das vollständige Checkout liegt außerhalb von `httpdocs`.

Die Gestaltung bleibt beim GrowCentral Nexus UI.
