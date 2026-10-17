# Mobile architecture

Grow Central is **PWA-first**. The responsive Web/PWA client is the canonical user interface on iPhone, iPad, Android, desktop and the Raspberry Pi browser surface.

```text
iOS / iPadOS / Android / Desktop
              |
          Grow Central PWA
              |
        authenticated API
              |
       Raspberry Pi 3B/4
          (authority)
              |
FRITZ! / Tapo / Mars Hydro / Sensorik / Kamera
```

## Binding rules

- Device discovery, Smart-Home credentials, automation, policy enforcement, camera access and hardware writes stay on the Raspberry Pi or the explicitly configured secured server path.
- The PWA must not store application passwords in plaintext or in `localStorage`. Credential saving is delegated to the browser/OS password manager; the application uses server-side sessions with opaque HttpOnly cookies.
- Remote access is HTTPS-only. Local HTTP remains permitted only for the local appliance/first-boot path where TLS is not yet available.
- Native iOS/Android shells are **fallback/legacy test clients only**. They must not duplicate business logic and may only be revived when a required platform capability cannot be implemented safely with Web/PWA APIs.
- No native client may bypass Grow-Central API policy gates.

This file is the canonical mobile architecture statement. Older documentation describing the native Nexus client as the primary mobile application is obsolete.
