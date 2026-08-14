# Changelog

## alpha-0.7.5 – Build 67 manufacturer model previews (2026-08-14)

- add optimized, offline manufacturer model images to device-search results for the Mars Hydro FC3000 family, Mars Hydro DF150-M/iFresh 6-inch fan, Logitech C920 and FRITZ!DECT 210
- map images only from sufficiently specific model identifiers and retain a neutral placeholder for unresolved devices
- show the C920 manufacturer image in the compact camera selector and the exact FRITZ!DECT 210 image in its registered plug card
- record the official manufacturer product pages and original image sources alongside the local assets

## alpha-0.7.5 – Build 66 complete FRITZ! plug telemetry (2026-08-14)

- read each imported FRITZ! smart plug through the complete local `getdeviceinfos` AHA response instead of five reduced switch commands
- identify the exact plug model and expose its live name, AIN, internal ID, manufacturer, firmware and advertised function classes
- show ambient temperature and configured temperature offset whenever the FRITZ! plug includes its temperature sensor block
- display switch mode, UI/device locks, transmission state, power, lifetime energy, voltage and a clearly labelled current calculated from power and voltage
- retain explicit unsupported/unknown states rather than fabricating measurements the connected FRITZ! device does not publish

## alpha-0.7.5 – Build 65 system and camera controls (2026-08-14)

- reorganize the sidebar and place host, network, WLAN, setup, support and diagnostics settings under **System** while keeping FRITZ!Box onboarding with **Devices**
- expose hostname, Pi model, OS, kernel, uptime, build and all IPv4/IPv6 interface addresses on the Dashboard and System pages
- replace the large camera device block with a compact webcam graphic and a small three-button camera command pad
- populate selectable resolutions from native discrete MJPEG modes actually advertised by V4L2 and reject unadvertised modes server-side
- make manual C920 focus usable by switching off autofocus first, applying the requested step-aligned value and reading the effective value back from the camera

## alpha-0.7.5 – Build 64 simple login URL (2026-08-14)

- make the appliance GUI available at `http://135er-grow-central.local/` and `http://<PI-IP>/` without requiring users to remember port 8080
- retain port 8080 as a compatibility endpoint while forwarding port 80 locally through systemd socket activation
- isolate the forwarding service with a dynamic user and systemd filesystem, device, privilege and address-family restrictions
- verify both port 80 and port 8080 during the automated image boot and reboot tests

## alpha-0.7.5 – Build 63 hardware recovery (2026-08-14)

- correct the AVM PBKDF2 login response for FRITZ!OS 7.24+ and report unknown users, lockouts, bad credentials and missing Smart Home permission without exposing credentials
- filter internal Raspberry Pi codec/ISP and metadata nodes from camera discovery and select the Logitech C920 deterministically
- replace stale camera streams instead of returning HTTP 409, add an authenticated stop endpoint and keep live video on native MJPEG without transcoding
- cache camera discovery, refresh it explicitly from the GUI and invalidate the browser cache for the repaired camera controls
- fix invalid NetworkManager diagnostics, label unavailable optional host tools cleanly and include redacted audit events plus camera-process ownership in future support bundles
- install the lightweight diagnostics used by support collection and enforce secure `0600` permissions for generated Netplan YAML during image creation

## alpha-0.7.5 – Hardware feedback follow-up

- add an on-demand, single-client Logitech C920 MJPEG live view at 640×480/10 fps without transcoding the camera's native MJPEG stream
- reduce GUI background work: 15-second polling, pause hidden tabs, prevent overlapping refreshes, cache Smart-Home reads for 10 seconds and rebuild device cards only when their state changes
- remove continuous scanline repainting and sidebar blur from the appliance UI
- show the detected Raspberry Pi model, kernel, architecture, application version and exact GitHub image build number under System
- honor the FRITZ!Box login `BlockTime`, detect unknown FRITZ!Box usernames and distinguish bad credentials from missing Smart Home permissions
- install only the required NetworkManager PolicyKit actions and verify effective service groups, file ownership, read/write boundaries and systemd sandbox paths during every image build
- extend the permanent support bundle with build identity, sandbox settings, PolicyKit state and positive/negative service-user permission probes

## alpha-0.7.5 – Secure onboarding, native FRITZ!, network control and camera panel (2026-08-13)

- integrated first-boot configuration into the authenticated main GUI and fixed the permanent local domain to `135er-Grow-Central.local`
- added persistent, bounded multi-boot journaling plus automatic/manual redacted support bundles covering systemd, network, hardware, Bluetooth, camera, storage, database and application state
- added GUI creation and download of `Grow-Central-Support-latest.tar.gz`; future problem reports require this bundle
- fixed the real-hardware runtime race by retrying GUI health for 60 seconds instead of failing immediately after service restart
- defer the system-password change until runtime validation succeeds and roll GUI runtime settings back after a failed setup
- report the Raspberry Pi 3B single-radio AP scan limitation and retain explicit manual SSID entry

- rebuilt first boot as a mandatory four-stage setup: system password, LAN/WLAN, optional dedicated FRITZ!Box user, mandatory Grow-Central GUI credentials
- automatically detects active Ethernet; without LAN, presents a scanned WLAN list plus manual SSID fallback
- keeps the normal GUI inaccessible to clients of the temporary setup subnet until provisioning is complete
- added PBKDF2-SHA256 GUI password verifiers, HttpOnly GUI sessions and API protection for normal LAN/remote-facing use
- retained explicit API-token authentication for non-browser/test clients while authenticated GUI sessions can perform approved writes without prompting for the factory test token
- added a post-setup **Network** GUI section with interface state, WLAN scan, explicit scan/error feedback and WLAN join
- added limited NetworkManager/Polkit permissions for the `growcentral` service account instead of unrestricted root networking
- added native FRITZ!Box presence detection and local AVM/AHA login
- added FRITZ!SmartHome switch import with name, presence, state, current power, energy and ON/OFF control where the device exposes those functions
- added server-side FRITZ credential storage paths and automatic GUI login prompt when a FRITZ!Box is clearly detected
- added authenticated local Tapo adapter and retained Tapo as a hybrid local/WAN architecture goal; Grow Central does not claim an unimplemented WAN transport
- added directly testable Logitech C920/UVC support: `/dev/video*` enumeration, C920 identification, snapshot capture and dynamic V4L2 control discovery
- camera GUI exposes only controls actually advertised by each camera and validates ranges/menu values before writes
- camera control changes are audited and arbitrary browser-supplied device paths/control names are rejected
- synchronized the Raspberry Pi image workflow, health tests, artifacts and prerelease naming to `alpha-0.7.5`
- image installs `ffmpeg`, `v4l-utils` and PolicyKit; runtime gets only required `video`/`netdev` access
- restored smart-home source policy to deny-by-default; the appliance image explicitly enables Smart Home behind GUI/API authentication and per-device approval/write gates
- retained Mars Hydro FC3000 2024 + iFresh/DF100 as the iConnect target family and DF100M BLE as experimental diagnostics/fallback
- recorded current real-hardware observation: first-boot/basic image functions and Bluetooth scanning/device communication are working; FRITZ/Tapo/C920/Mars-Hydro end-to-end validation remains part of Alpha testing

## alpha-0.7.4 – Mars Hydro/iConnect architecture alignment (2026-08-12)

- defined the authoritative lighting target as **Mars Hydro FC3000 model year 2024 with USB port and iConnect support**
- defined **DF100** as the **Mars Hydro iFresh series using iConnect**
- moved FC3000 2024 and iFresh/DF100 into one shared Mars-Hydro/iConnect device-family model
- reclassified the existing DF100M / `MZ_MZF002` BLE implementation as experimental diagnostics, reverse engineering and fallback instead of the primary Mars-Hydro integration
- added `app/mars_hydro.py` as a non-secret hardware-profile and abstraction baseline without inventing an unverified iConnect write protocol
- exposed the Mars-Hydro hardware profile through the local `/api/config` response
- kept `/api/df100m/*` compatibility endpoints while explicitly labeling them as BLE diagnostics/fallback
- updated the local HUD, public website, README, architecture, integrations, protocol notes and wiki terminology
- explicitly documented that **ESP32 is not part of the target architecture**
- retained deny-by-default write behavior until real target-hardware communication is reproduced and validated
- recorded the current Raspberry Pi image as positive in its **first basic functions from first boot**, while keeping repeatability, networking, Bluetooth, camera and device communication in Alpha validation

## Unreleased – Build 13 hardware follow-up

- correct the duplicated smart-home onboarding API prefix that blocked LAN discovery and Tapo account search from the GUI
- scan TP-Link/Tapo discovery broadcasts on every active IPv4 interface and verify account credentials with a real device update
- make first-boot WLAN scanning interface-specific and parse escaped SSIDs safely
- publish the appliance over mDNS as `http://135er-grow-central.local:8080` and use `135er-grow-central` as its default hostname
- retain the hardware-confirmed setup AP/DHCP and named Bluetooth discovery behavior from build 13

## alpha-0.7.4 build 13

- Run the two-stage systemd-nspawn boot test on a sparse copy instead of the release image.
- Reject release images containing generated machine IDs, SSH host keys or completed first-boot markers.
- Preserve the published image as a genuine first-boot appliance while retaining real boot/reboot health checks.

## alpha-0.7.4 – Boot and UI recovery (2026-08-12)

- start the main web UI independently of the provisioning marker so setup failures cannot leave port 8080 permanently closed
- restart and verify the main service after setup instead of accepting an unverified transition
- add a boot-time and periodic local health watchdog with one automatic recovery attempt
- verify systemd units and the installed image application's real HTTP health endpoint during the image build
- include Logitech C920 runtime tools (`ffmpeg`, `v4l-utils`) and grant the service access to the `video` group
- prevent setup-AP and Bluetooth/SSH initialization from holding the main UI in an indefinite systemd ordering job

## alpha-0.7.3 – Provisioning network and live-test fixes (2026-08-11)

- allow DHCP and DNS only on the temporary `wlan0` setup interface
- verify the `10.42.0.10–250` DHCP service before exposing the setup portal
- redesign first-boot provisioning in the Grow Central show-and-test HUD style
- grant the diagnostics service durable read access to the system journal
- unblock and power Bluetooth during the first boot sequence
- distinguish generic BLE devices from DF100M candidates and improve errors
- report completed one-shot initialization services as healthy
- commit the provisioning marker atomically and reject failed setup jobs instead of showing a false success page
- keep the setup AP as a DHCP-enabled rescue network after successful Ethernet provisioning
- show advertised Bluetooth names first and add conservative device-type/manufacturer hints when names are missing

## alpha-0.7.2 – First-boot and device onboarding reliability (2026-08-11)

- use Debian's native `python3-pam` binding for first-boot portal authentication
- present scanned WLANs as a selectable, refreshable list with signal and security details
- keep `/etc/hosts` synchronized with the configured hostname
- discover Tapo devices across every active IPv4 interface without storing credentials
- show boot status messages with the Grow Central brand mark until login

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
