# Website-Design – Deutsch

## Ziel

Die öffentliche 135er-GrowControl-Projektseite verwendet dieselbe grundlegende visuelle und strukturelle Sprache wie die lokale Steuer-GUI, ohne deren Vertrauensgrenze zu überschreiten.

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

## Logo und Grafikformate

Die Website verwendet in der Navigation das PNG-Logo `website/assets/brand/135er-growcontrol-repo-mark.png`.

Für Rastergrafiken gilt **PNG als Standardformat**. WebP wird nicht mehr eingesetzt, da es auf dem produktiven Hosting nicht zuverlässig dargestellt wurde. ICO bleibt für Favicons und SVG für technische Vektorgrafiken/Diagramme zulässig.

Die ursprüngliche GUI-Vorschau wird direkt über `assets/gui-preview-v0.5.png` geladen. Es gibt keine WebP-Quelle oder WebP-Fallback-Logik mehr.

## Sicherheitsgrenze

Die öffentliche Website ist rein statisch. Sie enthält keine Tokens, Kennwörter, Gerätebefehle oder direkten lokalen API-Endpunkte. Raspberry Pi und lokale Steuerung bleiben getrennte Vertrauensbereiche.

## Produktions-Deployment

Der per SSH bestätigte absolute Plesk-Webroot für `dezender.de` lautet:

`/var/www/vhosts/dezender.de/httpdocs`

Der Benutzer `dezender` erreicht dasselbe Verzeichnis über `~/httpdocs`.

Der Inhalt von `website/` wird direkt in diesen Webroot kopiert.
