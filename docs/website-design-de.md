# Website-Design – Deutsch

## Ziel

Die öffentliche 135er-GrowControl-Projektseite verwendet ab v0.6 dieselbe visuelle Sprache wie die lokale Steuer-GUI, ohne deren Vertrauensgrenze zu überschreiten.

## Gestaltungsprinzipien

- dunkle Control-Plane-/HUD-Flächen
- technische Linien und Raster
- grüne Status-/Freigabesignale
- cyanfarbene Integrations-/Bridge-Signale
- monospace Systemlabels
- große, klare Typografie
- responsive Darstellung für iPhone, iPad, Desktop
- Statusdarstellung statt übertriebener Produktversprechen

## Sicherheitsgrenze

Die öffentliche Website ist rein statisch. Sie enthält keine Tokens, Kennwörter, Gerätebefehle oder direkten lokalen API-Endpunkte. Raspberry Pi und lokale Steuerung bleiben getrennte Vertrauensbereiche.

## GUI-Vorschau

Die GUI-Vorschau nutzt WebP mit PNG-Fallback. Dadurch wird ein Ausfall der Vorschaugrafik durch unvollständige MIME-/WebP-Konfiguration des Hostings vermieden.

## Deployment

Das aktuelle Plesk-Webroot ist `/httpdocs`. Der Inhalt von `website/` wird dorthin kopiert.
