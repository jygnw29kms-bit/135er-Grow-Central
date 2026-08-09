# Website-Design – Deutsch

## Ziel

Die öffentliche 135er-Grow Central-Projektseite verwendet dieselbe grundlegende visuelle und strukturelle Sprache wie die lokale Steuer-GUI, ohne deren Vertrauensgrenze zu überschreiten.

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

Die Website verwendet in Navigation und Footer die kombinierte PNG-Wort-Bild-Marke `website/assets/brand/135er-grow-central-lockup-v0.9.png`.

Für Rastergrafiken gilt **PNG als Standardformat**. WebP wird nicht mehr eingesetzt, da es auf dem produktiven Hosting nicht zuverlässig dargestellt wurde. ICO bleibt für Favicons und SVG für technische Vektorgrafiken/Diagramme zulässig.

Die aktuelle GUI-Familie wird direkt über `assets/gui/*-v0.9.png` geladen. Es gibt keine WebP-Quelle oder WebP-Fallback-Logik.

## Sicherheitsgrenze

Die öffentliche Website ist rein statisch. Sie enthält keine Tokens, Kennwörter, Gerätebefehle oder direkten lokalen API-Endpunkte. Raspberry Pi und lokale Steuerung bleiben getrennte Vertrauensbereiche.

## Produktions-Deployment

Der per SSH bestätigte absolute Plesk-Webroot für `dezender.de` lautet:

`/var/www/vhosts/dezender.de/httpdocs`

Der Benutzer `dezender` erreicht dasselbe Verzeichnis über `~/httpdocs`.

Der Inhalt von `website/` wird direkt in diesen Webroot kopiert.
