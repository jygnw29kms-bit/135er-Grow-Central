# Grow Central Mobile

Grow Central follows a **PWA-first** architecture. The installable Web/PWA interface is the canonical mobile client for iPhone, iPad and Android. This avoids Apple signing/provisioning overhead, keeps one UI code path for mobile and desktop, and prevents native clients from drifting away from the Raspberry-Pi/WebGUI feature set.

## Canonical client

- iPhone / iPad: Grow Central PWA added to the Home Screen.
- Android: the same Grow Central PWA can be installed from the browser.
- Desktop: the same responsive WebGUI/PWA is used directly in the browser.
- Raspberry Pi: the Pi remains the local authority for devices, automation, Smart Home, camera, rooms, sensor data and audit.
- Remote access: HTTPS only.

## Login and credentials

- Login fields use standard browser autocomplete semantics so iOS/Android/browser password managers can offer to save credentials.
- Grow Central itself does not persist plaintext passwords in browser storage.
- Application sessions use opaque HttpOnly cookies.
- The optional "Angemeldet bleiben" mode extends the server-side session lifetime without storing the password in application JavaScript storage.

## Native clients

The historical Capacitor/Nexus iOS and Android packages remain only as **legacy/fallback test clients**. They are not the primary product path and must not receive duplicated business logic. Native code is justified only when a required feature cannot be implemented safely through current Web/PWA APIs.

The native CI workflow is therefore manual-only. No native iOS/Android package is built automatically for normal mobile/Web changes.

## Security rules

- no FRITZ!Box, Tapo or device credentials in client packages;
- no passwords or long-lived secrets in URLs;
- no plaintext credential persistence in `localStorage`;
- local HTTP only for explicit local/first-boot appliance access;
- non-local access requires HTTPS;
- server-side permissions and Grow-Central sessions remain authoritative;
- native fallback clients may not bypass API policy gates.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the binding architecture statement.
