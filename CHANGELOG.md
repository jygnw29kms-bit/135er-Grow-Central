# Changelog

## v0.6 – Secure Smart-Home Platform (2026-08-09)

### Architecture
- Reframed GrowControl as a secure local-first automation platform while keeping the Raspberry Pi authoritative.
- Added normalized smart-home device/capability/command architecture.
- Selected Home Assistant as optional interoperability bridge for Apple Home/Siri, Tapo and FRITZ!SmartHome.
- Selected native local Shelly Gen2+ JSON-RPC as the first direct smart-plug adapter.
- Defined Matter as a future standards-based bridge target.

### Security
- Added fail-closed local write-token authentication.
- Added deny-by-default smart-home policy with global enable, approval and writable gates.
- Restricted Shelly destinations to configured private/link-local literal IP addresses.
- Restricted Home Assistant integration to configured `switch.*` entities and on/off services.
- Added read-only Home Assistant default.
- Added append-only smart-home command audit log.
- Protected DF100M speed/raw writes with local authentication in addition to the existing write-disable flag.

### Runtime
- Added smart-home registry, policy and adapter framework.
- Added Shelly switch adapter baseline.
- Added Home Assistant switch connector baseline.
- Added smart-home REST endpoints under `/api/v1/smarthome`.
- Aligned local HUD endpoints with the v0.6 local API.
- Added application package marker to make test/import behavior deterministic.

### Website
- Rebuilt the public project site as a domain-neutral professional static website with architecture SVG, smart-home integration presentation, security model and GUI preview.
- Added GitHub Pages deployment workflow.
- Removed old domain-specific Nginx configuration.

### CI / release engineering
- Removed obsolete Raspberry Pi image-builder v1 workflow to prevent unrelated pushes from launching large image builds.
- Kept corrected v2 builder as the supported image workflow.
- Fixed Python package import structure for CI.

### Documentation
- Added/updated smart-home architecture, integrations, security model, API, source register, decision log, status matrix, release/image process and bilingual DE/EN pages.
- Updated versioned wiki sources.

## v0.5
- Full-platform baseline: database schemas, installer/hardening direction, Local/Cloud separation, GUI baseline and bilingual platform documentation.

## v0.4.x
- Early FastAPI/Bleak DF100M research runtime and optional cloud-link alpha.
# 2026-08-09 – Brand and GUI comparison release

- established the signed **J. L. 1976** circuit emblem as the mandatory project logo
- applied the logo to the public website, local Raspberry Pi HUD, cloud HUD and repository documentation
- embedded both GUI milestones (original v0.5 and current power/cost v0.7) directly on the public website
- added responsive comparison layout, lazy loading and WebP delivery where appropriate
- retained the PNG master asset and documented brand-protection rules
