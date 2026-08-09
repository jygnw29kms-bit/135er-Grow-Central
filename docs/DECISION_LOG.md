# Architecture Decision Log

## ADR-001 – Raspberry Pi is the local master

**Decision:** All core local control/monitoring runs on Raspberry Pi.  
**Reason:** Linux tooling, BLE access, local DB, web server and maintainability.  
**Consequence:** No ESP32 dependency in core architecture.

## ADR-002 – Local-first, cloud optional

**Decision:** Cloud is an extension, not a requirement.  
**Reason:** Reliability, privacy, resilience against internet/vendor outages.  
**Consequence:** Local functions and automation must continue without VPS.

## ADR-003 – Outbound cloud connection

**Decision:** Pi initiates HTTPS communication to VPS.  
**Reason:** Avoid direct public Pi exposure.  
**Consequence:** Remote commands are represented as requests fetched/received and validated locally.

## ADR-004 – SQLite local / PostgreSQL cloud

**Decision:** SQLite for Pi-local state; PostgreSQL as cloud target.  
**Reason:** low operational overhead locally, stronger concurrency/querying centrally.

## ADR-005 – Experimental device writes default off

**Decision:** `DF100M_ALLOW_WRITES=false`.  
**Reason:** BLE protocol is not yet validated.  
**Consequence:** discovery/read/notify work can proceed safely before control validation.

## ADR-006 – Device protocol separated from UI

**Decision:** Device-specific code belongs behind adapters.  
**Reason:** DF100M is first device, not the entire platform.  
**Consequence:** later FC3000 or sensor adapters should not require UI rewrite.

## ADR-007 – Responsive futuristic HUD

**Decision:** Dark, future-oriented responsive UI supporting desktop through smartphone, including iPad-class tablet.  
**Reason:** intended permanent wall/tablet dashboard usage.

## ADR-008 – Versioned Wiki source

**Decision:** Canonical wiki content also lives inside main Git repository.  
**Reason:** GitHub Wiki uses a separate repository and can be unavailable/uninitialized; project knowledge must remain versioned with code.

## ADR-009 – Raspberry Pi image built in CI

**Decision:** Preinstalled `.img.xz` generated reproducibly through GitHub Actions.  
**Reason:** reduce setup friction for hardware tests and make build steps auditable.

## ADR-010 – Firewall initialized on physical first boot

**Decision:** Do not run UFW initialization in ARM chroot. Use first-boot systemd service.  
**Reason:** GitHub runner/chroot cannot reliably determine target iptables kernel behavior.
