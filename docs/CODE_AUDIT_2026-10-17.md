# Grow Central Code Audit – 2026-10-17

This document is the cleanup baseline for the current `master` branch. Its purpose is to keep architecture, CI and runtime behavior understandable while Grow Central moves toward productive use.

## Canonical architecture

- Raspberry Pi remains the local authority for device access, automation, policy, credentials, camera and sensor hardware.
- Cloud is optional and connects through the documented outbound HTTPS path.
- The responsive Web/PWA client is the canonical UI on iOS, iPadOS, Android and desktop.
- Native mobile shells are fallback/test clients only and must not duplicate application business logic.
- Browser credential saving is delegated to the OS/browser password manager. Grow Central must not store plaintext passwords in `localStorage` or equivalent application storage.

## Changes applied during this audit

1. `app/gui_auth.py`
   - added `remember` session support with a separate 30-day TTL;
   - retained opaque HttpOnly session cookies and hashed persistent session identifiers;
   - replaced blocking `time.sleep()` in the async login route with `await asyncio.sleep()`;
   - added explicit/automatic Secure-cookie handling through `GC_GUI_COOKIE_SECURE` (`auto`, true, false);
   - HTTPS requests now receive Secure cookies while local first-boot HTTP remains possible.

2. Mobile architecture
   - `mobile/ARCHITECTURE.md` now defines PWA-first as binding architecture;
   - `mobile/README.md` no longer describes the native Nexus application as the primary mobile product;
   - native business-logic duplication is explicitly prohibited.

3. CI cleanup
   - `.github/workflows/mobile-build.yml` is manual-only; normal pushes no longer build unsigned native iOS/Android packages automatically;
   - the historical `.github/workflows/recover-build13-release.yml` was removed. It referenced the obsolete alpha-0.7.4 Build 13, a fixed old workflow run and a fixed old release ID.

## Audit findings

### Confirmed clean/security-positive patterns

- no repository code-search hit for `verify=False`;
- no repository code-search hit for `shell=True`;
- the legacy mobile endpoint normalizer rejects credentials embedded in URLs;
- localStorage usage found in the login page is for the intro-screen marker, not password persistence;
- persistent GUI sessions store a SHA-256 hash of the opaque session token rather than the raw token on disk.

### Remaining inconsistencies to remove or consolidate

1. **Historical mobile documentation**
   - `mobile/STATUS.md`, `mobile/INSTALLATION.md`, `mobile/RELEASE_GATE.md` and related historical files still describe native Nexus artifacts, unsigned IPA handling and Build-118 mobile validation.
   - They should either be rewritten as legacy/fallback documentation or moved to a clearly marked archive location.

2. **Release-state duplication**
   - Build 118 / `alpha-0.7.5` / anchor `e339602` is repeated in multiple docs and wiki pages.
   - `RELEASE_STATE.md` is already intended as the canonical source; other files should link to it instead of repeating mutable release facts wherever possible.

3. **Workflow inventory**
   - The repository contains multiple image force-build, smoke, preflight, deployment and compatibility workflows.
   - Each workflow needs one of three labels: `ACTIVE`, `MANUAL/RECOVERY`, or `ARCHIVE/REMOVE`.
   - Recovery workflows must not contain stale fixed run IDs or release IDs on the active path.

4. **Authentication tests**
   - Add explicit tests for standard 12-hour login, 30-day remember-login, logout invalidation, HTTP cookie behavior and HTTPS Secure-cookie behavior.

5. **PWA completeness**
   - Verify manifest, service worker, installability, offline shell behavior, update strategy and iOS Home-Screen behavior against the final WebGUI rather than maintaining a parallel mobile UI.

6. **Pi/cloud rebuild behavior**
   - The next live Pi pass must verify that a clean image provisions maintenance SSH access, cloud device identity and cloud link reproducibly after first boot.
   - A rebuilt Pi must not depend on manually restoring machine-specific state unless that state is intentionally backed up/restored by the documented flow.

## Cleanup rules from now on

- one canonical source for each mutable fact;
- no feature implemented separately in native mobile when the PWA can provide it;
- no old release recovery logic on an automatically triggered path;
- no hard-coded historical run/release IDs in active production workflows;
- no blocking sleep or blocking network/subprocess work directly inside async request handlers;
- no plaintext passwords, API secrets or long-lived tokens in browser storage, source code, URLs or logs;
- new production behavior requires a test or an explicit documented hardware-validation step;
- historical material that is still useful belongs in an archive/history document, not mixed with current operating instructions.

## Current audit status

The repository is **not declared fully cleaned yet**. The first pass has removed one confirmed obsolete workflow, corrected the mobile architecture direction and fixed two concrete authentication/runtime issues. Remaining work is primarily consistency cleanup, test coverage and validation of the new-image Pi/cloud path.
