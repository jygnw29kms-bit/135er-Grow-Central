# Website Design – English

## Goal

Starting with v0.6, the public 135er GrowControl project website follows the same visual language as the local control GUI while preserving the trust boundary between both surfaces.

## Design principles

- dark control-plane / HUD surfaces
- technical lines and grids
- green status and approval signals
- cyan integration and bridge signals
- monospace system labels
- large, clear typography
- responsive iPhone, iPad and desktop layouts
- status communication instead of overpromising

## Security boundary

The public website remains fully static. It contains no tokens, passwords, device commands or direct local API endpoints. The Raspberry Pi and local control UI remain separate trust zones.

## GUI preview

The GUI preview uses WebP with a PNG fallback to avoid broken rendering on hosting environments with incomplete MIME or WebP configuration.

## Deployment

The current Plesk web root is `/httpdocs`. The contents of `website/` are copied there.
