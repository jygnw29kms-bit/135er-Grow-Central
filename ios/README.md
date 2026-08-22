# 135er Grow Central iOS WebGUI client

The iOS application is a native SwiftUI/WKWebView client for the existing Grow Central web interface. It does not replace the Raspberry Pi and contains no device-control backend.

- Local mode: `http://135er-Grow-Central.local/` or a custom LAN address.
- Optional server mode: HTTPS-only access to the Grow Central server version from anywhere.
- Device integrations, history and automations remain on Grow Central Local/server.
- Web login cookies persist in the standard WebKit website data store.

Generate the Xcode project with `xcodegen generate`. See the [German Windows installation guide](../docs/de/IOS_PC_INSTALLATION.md).

