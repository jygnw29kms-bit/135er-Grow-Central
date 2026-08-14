# Native iOS client

Native SwiftUI alternative for direct local control on iPhone and iPad. Generate the Xcode project with `xcodegen generate` from this directory. See [German PC installation guide](../docs/de/IOS_PC_INSTALLATION.md).

Security boundaries:

- FRITZ! credentials use the iOS Keychain (`ThisDeviceOnly`).
- Local state uses complete file protection and atomic writes.
- The unsigned CI IPA must be signed by the device owner's Apple ID during sideloading.
- Tapo/KLAP and unvalidated Mars Hydro writes are not claimed as implemented.

