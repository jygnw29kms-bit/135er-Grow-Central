# Website Design – English

## Goal

The public 135er-Grow Central project site follows the same structural and visual language as the local control GUI while preserving the trust boundary between both surfaces.

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

## Logo and graphics formats

The public website uses the PNG logo at `website/assets/brand/135er-grow-central-logo.svg`.

PNG is the standard raster format. WebP is no longer used because it did not render reliably on the production hosting path. ICO remains allowed for favicons, and SVG remains allowed for technical vector diagrams.

The original GUI preview is loaded directly from `assets/gui-preview-v0.5.png`; there is no WebP source or WebP fallback logic.

## Security boundary

The public website remains fully static. It contains no tokens, passwords, device commands or direct local API endpoints. The Raspberry Pi and local control UI remain separate trust zones.

## Production deployment

The absolute Plesk web root for `dezender.de`, confirmed through SSH, is:

`/var/www/vhosts/dezender.de/httpdocs`

The `dezender` system user sees the same directory as `~/httpdocs`.

The contents of `website/` are copied directly into this web root.
