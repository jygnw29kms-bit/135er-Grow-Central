# Grow Central Cloud – Server-Administration und Freischaltungen

Stand: 2026-08-27

## Zielbild

Die Cloud besitzt genau eine Geräte- und Freischaltungslogik im Cloud-Core. Plesk und das Standalone-Webinterface sind lediglich unterschiedliche Administrationsoberflächen und greifen auf dieselben Daten zu.

## Installationsmodi

- `standalone`: eigenes Grow-Central-Webinterface
- `plesk`: Plesk-Integration als primäre Administration
- `both`: beide Oberflächen, gemeinsame Datenbasis

Der gewählte Modus wird in `/etc/135er-growcentral-cloud/admin-mode` gespeichert und bei APT-Upgrades nicht neu abgefragt oder überschrieben.

`configure-cloud-admin-mode.sh` erkennt Plesk. Bei einer interaktiven Erstinstallation mit vorhandenem Plesk kann zwischen Plesk, Standalone und beiden Varianten gewählt werden. Ohne Plesk ist Standalone der sichere Standard.

## Geräte-Lebenszyklus

1. Ein bisher unbekannter Pi meldet Telemetrie oder fragt seine Freischaltungen ab.
2. Der Cloud-Core legt das Gerät automatisch als `pending` / `BASIC` an.
3. Der Administrator ordnet Name, Kunde, Gruppe und Paket zu.
4. Der Administrator setzt den Status auf `active` und aktiviert optionale Features.
5. Der Pi liest seine effektiven Rechte über `/api/v1/devices/{device_id}/entitlements`.
6. Eine abgelaufene zeitliche Freischaltung wird serverseitig als `expired` behandelt.

## Pakete und Features

Pakete:

- BASIC
- PLUS
- PRO
- INTERNAL

Unabhängige Feature-Flags:

- `remote_control`
- `camera`
- `history_extended`
- `alerts`
- `automation_pro`
- `api_access`
- `beta_features`

Dadurch können zeitlich begrenzte Testfreigaben oder einzelne Zusatzfunktionen vergeben werden, ohne verschiedene Raspberry-Pi-Images zu pflegen.

## Administration

Das Standalone-Interface liegt unter `/admin`. Die Admin-API liegt unter `/api/admin/*` und verlangt `X-Admin-Token`. Das Token muss mindestens 32 Zeichen lang sein und wird bei der Serverkonfiguration erzeugt, falls noch keines vorhanden ist.

## APT-Upgrade-Regeln

Bestehende Serverinstanzen müssen mit demselben Paketnamen aktualisiert werden können. Ein Upgrade darf insbesondere nicht:

- Geräte- oder Freischaltungsdaten löschen,
- vorhandene Secrets ersetzen,
- den gewählten Admin-Modus zurücksetzen,
- Plesk ungefragt aktivieren/deaktivieren,
- eine Neuinstallation der Pis erfordern.

Schema-Erweiterungen werden idempotent mit `CREATE TABLE IF NOT EXISTS` vorgenommen. Vor produktiven Schema-Migrationen ist weiterhin ein Serverbackup vorgesehen.

## Nächste Produktionsstufe

Die aktuelle Grundlage erweitert den im Repository vorhandenen FastAPI-Cloud-Core. Die produktive V6-Bootstrap-Installation besitzt zusätzlich eigene Account-, Ed25519- und WSS-Relay-Logik. Für die nächste Serverpaketversion muss diese Freischaltungslogik in den V6/V7-Produktionspfad übernommen und über das bestehende APT-Paket `135er-growcentral-cloud` ausgeliefert werden, damit vorhandene V6-Instanzen ohne Neuinstallation migrieren.
