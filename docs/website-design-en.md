# Website Design – English

## Goal

Starting with v0.6, the public 135er GrowControl project website follows the same structural and visual language as the local control GUI while preserving the trust boundary between both surfaces.

## Design principles

The public website mirrors the patterns used by `web/index.html` and `web/app.css`:

- fixed sidebar and mobile bottom navigation
- technical status cards at the top
- dark control-plane / HUD surfaces
- circular system indicator
- diagnostics / telemetry panel
- green, cyan, violet and amber status signals
- monospace system labels
- responsive iPhone, iPad and desktop layouts
- explicit status communication instead of overpromising

The site is therefore aligned with the target GUI not only by color, but also by navigation, panel hierarchy and dashboard structure.

## Branding and repository artwork

The public site keeps the signed **J. L. 1976** master logo as the visible project trademark. Two additional repository presentation assets are maintained alongside it:

- `website/assets/brand/135er-growcontrol-repo-banner.webp` – GitHub/social banner
- `website/assets/brand/135er-growcontrol-repo-mark.png` – square repository mark / app icon
- `website/assets/brand/favicon.ico` – browser favicon generated from the square mark

The banner is used in the repository README and social/OpenGraph metadata. The square mark is used for favicon/app-icon purposes. These assets complement the signed master logo and do not replace it.

## Security boundary

The public website remains fully static. It contains no tokens, passwords, device commands or direct local API endpoints. The Raspberry Pi and local control UI remain separate trust zones.

## GUI preview

The GUI reference image is loaded directly as PNG:

`assets/gui-preview-v0.5.png`

PNG is the primary format to avoid WebP/MIME hosting issues.

## Production deployment

The absolute Plesk web root for `dezender.de`, confirmed through SSH, is:

`/var/www/vhosts/dezender.de/httpdocs`

The `dezender` system user sees the same directory as `~/httpdocs`.

The contents of `website/` are copied directly into this web root.
