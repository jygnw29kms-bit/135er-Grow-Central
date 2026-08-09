# Website-Design – Deutsch

## Ziel

Die öffentliche 135er-GrowControl-Projektseite verwendet ab v0.6 dieselbe grundlegende visuelle und strukturelle Sprache wie die lokale Steuer-GUI, ohne deren Vertrauensgrenze zu überschreiten.

## Gestaltungsprinzipien

Die Website orientiert sich direkt an `web/index.html` und `web/app.css`:

- feste Sidebar bzw. mobile Bottom-Navigation
- technische Statuskarten im oberen Bereich
- dunkle Control-Plane-/HUD-Flächen
- Ringanzeige als zentrales Systemelement
- Diagnostik-/Telemetry-Panel
- grüne, cyanfarbene, violette und amberfarbene Statussignale
- monospace Systemlabels
- responsive Darstellung für iPhone, iPad und Desktop
- Statusdarstellung statt übertriebener Produktversprechen

Die öffentliche Seite ist damit nicht nur farblich, sondern auch in Aufbau, Panels und Navigationslogik an das Ziel-GUI angelehnt.

## Branding und Repository-Artwork

Die Website verwendet weiterhin das signierte **J. L. 1976** Master-Logo als sichtbare Projektmarke. Zusätzlich wurden zwei Repository-Assets ergänzt:

- `website/assets/brand/135er-growcontrol-repo-banner.webp` – GitHub-/Social-Banner
- `website/assets/brand/135er-growcontrol-repo-mark.png` – quadratische Marke für Avatar/App-Icon
- `website/assets/brand/favicon.ico` – Browser-Favicon aus der quadratischen Marke

Das Banner wird im Repository-README und als Social-/OpenGraph-Grafik verwendet. Die quadratische Marke wird als Favicon/App-Icon eingebunden. Diese Assets ersetzen das signierte Master-Logo nicht.

## Sicherheitsgrenze

Die öffentliche Website ist rein statisch. Sie enthält keine Tokens, Kennwörter, Gerätebefehle oder direkten lokalen API-Endpunkte. Raspberry Pi und lokale Steuerung bleiben getrennte Vertrauensbereiche.

## GUI-Vorschau

Die GUI-Vorschau wird direkt als PNG geladen:

`assets/gui-preview-v0.5.png`

PNG ist primär, um Hosting-Probleme mit WebP/MIME-Konfiguration auszuschließen.

## Produktions-Deployment

Der per SSH bestätigte absolute Plesk-Webroot für `dezender.de` lautet:

`/var/www/vhosts/dezender.de/httpdocs`

Der Benutzer `dezender` erreicht dasselbe Verzeichnis über `~/httpdocs`.

Der Inhalt von `website/` wird direkt in diesen Webroot kopiert.
