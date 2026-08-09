# Known Limitations and Open Risks

## DF100M protocol

- write UUID is not yet validated on hardware;
- notification UUID is not yet conclusively mapped;
- speed packet format remains experimental;
- RPM decoding is not established;
- Legacy cloud/API observations may not be required for local BLE and may change independently.

## Application runtime

- one BLE client is intended at a time in current baseline;
- notification retention is limited/in-memory in current research path;
- full production RBAC/login/session enforcement is not yet complete;
- cloud Alpha uses static token authentication;
- PostgreSQL target architecture is not equivalent to full PostgreSQL runtime integration;
- migrations/Alembic are future work;
- WebSocket live updates are future work;
- automation/schedule engine is not yet fully executed in production runtime;
- executable backup/restore workflow needs further implementation and testing.

## Hardware test image

- credentials `test/test` are insecure by design and temporary;
- image is a prerelease/hardware-test artifact;
- Wi-Fi onboarding is not assumed as fully automated; Ethernet is preferred for first boot;
- first-boot firewall service has to be verified on real Raspberry Pi kernel;
- successful CI build does not substitute for physical boot validation.

## GUI

- preview image is a design reference, not proof every visual element is wired to live data;
- generated preview previously contained placeholder device/date details; authoritative device data is Device ID `A0A3B35EFDC8`, firmware `V1.8`.

## Cloud

- must never be treated as local master;
- direct Pi port exposure is unsupported/insecure;
- remote control remains disabled until both cloud and Pi opt-in conditions and local validation are present.

## Documentation risk

Any feature marked `baseline`, `planned`, `target` or `experimental` must not be presented as production-complete without code and test evidence.
