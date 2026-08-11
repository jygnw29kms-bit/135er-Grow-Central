# Changelog

## Unreleased

- fixed first-boot access-point DHCP by installing the explicit NetworkManager shared-mode DHCP dependency
- made the setup AP self-repair its complete static `10.42.0.1/24` IPv4 profile on every start
- enabled dual-stack setup and uplink networking while retaining static IPv4 and DHCP as the reliable provisioning path

## Unreleased – First-boot configuration portal

- added a temporary Raspberry Pi setup access point with a device-specific SSID suffix
- added a GUI-aligned HTTPS portal authenticated against the real `GrowCentral` system user through PAM
- added WLAN/LAN, hostname, timezone and mandatory device-password provisioning
- gated the main service until setup succeeds and restored the access point automatically after WLAN failures
- restricted setup ports to the provisioning subnet and kept WLAN secrets out of process arguments and logs
- updated German and English image documentation and CI coverage

## alpha-0.7.1 – Repository and Raspberry Pi identity synchronization (2026-08-09)

- redesigned the GitHub README around a dedicated technical repository banner and structured project overview
- synchronized combined PNG branding across local GUI, cloud GUI and documentation
- added a full-screen v0.9 Plymouth boot splash and refreshed console banner for the Raspberry Pi image
- updated the image workflow to install the PNG splash directly instead of decoding the obsolete Base64 logo
- refreshed German and English GUI-preview documentation to the current v0.9 interface family

## alpha-0.7.1 – Professional JARVIS-style interface refresh (2026-08-09)

- introduced detailed v0.9 desktop, tablet, mobile and cloud GUI concept images
- combined the project symbol, `135er-Grow Central` wordmark and graphic `J.L.` signet into one brand lockup
- replaced the separate branding elements inside all four v0.9 GUI images with the approved combined logo
- rebuilt the public website with stronger hierarchy, restrained HUD styling and responsive interface showcases
- retained local-first messaging, deny-by-default security and PNG-only runtime assets

## alpha-0.7.1 – Website stabilization (2026-08-09)

- converted the available logo, project mark and four GUI demo graphics to PNG
- removed SVG and missing legacy GUI references from the public website and its documentation
- unified logo and project-mark usage across header, hero, call-to-action and footer
- corrected responsive logo sizing and added a responsive four-client preview gallery
- aligned repository and website documentation with `alpha-0.7.1`

## 2026-08-09 – WIP repository presentation refresh

- marked the repository and public project interface clearly as **Work in Progress**
- redesigned the repository front page to visually match the dark HUD/control-plane identity of 135er-Grow Central
- added project status, architecture, integration, security and repository-map blocks to the README
- embedded the PNG GUI reference directly in the repository front page
- updated public website status indicators to show `WIP · v0.7` instead of implying production completion
- retained PNG/ICO as the raster branding standard

## 2026-08-09 – PNG-only branding migration

- removed WebP usage from the public website, local HUD and cloud HUD
- switched website branding to the PNG 135er-Grow Central logo
- changed OpenGraph/social preview to the PNG logo
- removed the WebP `<picture>` source from the v0.5 GUI preview
- added PNG logo aliases for local GUI, cloud GUI and documentation
- removed obsolete WebP branding and preview assets from the repository
- documented PNG as the standard raster format; ICO remains allowed for favicons and SVG for technical vector graphics

## v0.6 – Secure Smart-Home Platform (2026-08-09)

### Architecture
- Reframed Grow Central as a secure local-first automation platform while keeping the Raspberry Pi authoritative.
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

## 2026-08-09 – Brand and GUI comparison release

- established the signed **J. L. 1976** circuit emblem as the initial project brand reference
- applied branding to the public website, local Raspberry Pi HUD, cloud HUD and repository documentation
- embedded both GUI milestones (original v0.5 and current power/cost v0.7) directly on the public website
- added responsive comparison layout and lazy loading
- later superseded WebP delivery with the PNG-only branding policy above
