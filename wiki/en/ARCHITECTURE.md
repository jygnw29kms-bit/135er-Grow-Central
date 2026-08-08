# Architecture

The Raspberry Pi is the local control node. Device access, schedules and automation continue to operate without the cloud. The optional Debian/Ubuntu VPS receives telemetry over outbound HTTPS and can provide longer history, users/RBAC and remote overview.

Remote commands are requests only: they require cloud and local opt-in and are validated again on the Pi.
