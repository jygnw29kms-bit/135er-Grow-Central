# Mobile architecture

The mobile clients are presentation clients only. Device discovery, Smart Home credentials, automation, policy enforcement, camera access and hardware writes stay on the Raspberry Pi / optional secured server path.

```text
iOS / Android
     |
 WebGUI session
     |
Raspberry Pi 3B (authority)
     |
FRITZ! / Tapo / Mars Hydro / C920
```

No native mobile code may bypass the Grow-Central API policy gates.
