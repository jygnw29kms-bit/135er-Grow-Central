# Native sensor trust · 13 October 2026

Discovery is automatic; acceptance/rejection is always manual. Desktop, mobile
and legacy UI expose persistent DISCOVERED/TRUSTED/REJECTED/REVOKED states. Name,
room and the physical device fingerprint's final 16 hex characters must be
confirmed. A fresh signed nonce response is required before acceptance, state
reads and health. Untrusted devices cannot enter native room data/history or
control actuators. Rejected/revoked devices remain blocked across rediscovery.

Firmware 0.3.0 uses individually generated P-256 keys and a `gc-signed-v1`
envelope: algorithm `ecdsa-p256-sha256`, base64 DER public key and signature, and
an exactly signed UTF-8 JSON `message` containing `device_id`, `kind`, `seq` and
`body`. No reserialization is performed for signature verification. Identity,
topic and message kind must agree. Sequence/digest receipts persist in SQLite;
proofs additionally contain a fresh 256-bit server nonce and are never retained.
NVS reserves sequence ranges across reboots. The private key is never logged or
returned; flash/NVS encryption and secure boot are not configured.

The operator can explicitly release blocked devices without granting trust. A
full identity reset first requires rejection/revocation and old-fingerprint
confirmation, permanently retires the former key and requires new acceptance.
`NET CLEAR` preserves identity/calibration. Preserve the trust database during
updates; existing room assignments are not silently grandfathered into trust.

Network MQTT now requires TLS/8883, a real CA and per-device credentials with
own-topic ACLs. The Pi image's anonymous development listener binds to loopback
only. Templates are under `deploy/mqtt`. Firmware Wi-Fi/MQTT/CA configuration is
currently local USB; `NET CA` accepts a base64 DER public CA certificate. TLS
requires clock synchronization and does not disable certificate verification.
Backend TLS is configurable through GC_MQTT_TLS/PORT/CA_FILE and private login
bindings. Real certificates/accounts still need configuration on the target Pi.

**BLE discovery/provisioning is not implemented.** Firmware 0.4.0 adds guided
USB onboarding on the Pi, including local certificates and individual MQTT
accounts. API reports `ble_available=false`, `credential_transfer=usb_only`.
See [USB sensor setup](../de/USB_SENSOR_SETUP.md). The existing network acceptance
endpoint itself does not transfer credentials.
This is not yet the desired first-contact BLE path without Wi-Fi setup. No
plaintext MQTT secret transfer is substituted for it.

Sampling runs in a separate FreeRTOS task while network work retries with
independent backoff. Proofs use a bounded queue and publish outside MQTT callbacks
as required by MQTT 2.5.3. Current snapshots include allowlisted raw/quality data;
invalid moisture values are rejected. Air/water percentages are engineering
references, not verified VWC. Offline history backfill, advanced calibration,
watchdog/brownout diagnostics and physical reliability tests remain separate work.

Validated: Python/security tests, a real TLS Mosquitto broker with a software
sensor and ACL/auth checks, desktop/mobile browser interactions, and the XIAO
firmware build (PlatformIO 6.2.0, espressif32 7.1.3, MQTT 2.5.3; approximately 12.4%
RAM, 68.4% flash). No actual sensor flash, physical radio/ADC/long-duration test,
Pi image release or production deployment was performed. See the
[detailed German review](../de/SENSOR_PAIRING.md).
