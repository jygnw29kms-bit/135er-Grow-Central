# 135er GrowControl – Full Platform Baseline v0.5

## Unterstützte Systeme

Verbindliche Zielplattformen:

- Debian 12
- Debian 13
- Ubuntu Server 22.04 LTS
- Ubuntu Server 24.04 LTS
- Raspberry Pi OS 64-bit auf Debian-Basis

Andere Distributionen gelten zunächst als nicht unterstützt.

## Rollen der Systeme

### Local Node / Raspberry Pi

Der Pi bleibt Master für:

- BLE-Gerätekommunikation
- lokale Sensoren
- lokale Zeitpläne
- lokale Automationen
- Fail-Safe-Verhalten
- lokale Historie/Pufferung
- Cloud-Synchronisation

Ein Ausfall von Internet oder VServer darf lokale Regeln nicht stoppen.

### Cloud Node / VServer

Der VServer übernimmt optional:

- Benutzer und Rollen
- Remote-Dashboard
- Langzeithistorie
- Multi-Site
- Alerts
- Audit-Log
- Remote-Command-Queue
- zentrale Backups/Exporte

## Dienste

```text
Raspberry Pi
├── growcontrol-local.service
├── growcontrol-cloud-link.service
├── BlueZ
├── SQLite
└── systemd

VServer
├── Nginx
├── GrowControl Cloud API
├── PostgreSQL
├── Fail2ban
├── Firewall
├── Certbot / ACME
└── systemd oder Docker Compose
```

## Installer

Der Installer muss:

1. OS und Version prüfen.
2. APT aktualisieren.
3. benötigte Pakete installieren.
4. dedizierten Systembenutzer `growcontrol` anlegen.
5. Verzeichnisse und Rechte setzen.
6. Python-vEnv erzeugen.
7. Konfiguration in `/etc/135er-growcontrol` anlegen.
8. Daten nach `/var/lib/135er-growcontrol` schreiben.
9. Logs über journald führen.
10. systemd-Units installieren.
11. optional Firewall/Fail2ban aktivieren.
12. bei Cloud: Domain, Nginx und TLS konfigurieren.
13. Healthchecks durchführen.

## APT-/OS-Härtung

Vorgesehen:

- `unattended-upgrades`
- `apt-listchanges`
- regelmäßiges `apt update`
- kontrolliertes `apt full-upgrade`
- `apt autoremove`
- Sicherheitsupdates automatisch
- Service-Neustarts nachvollziehbar

## Dateirechte

Empfohlen:

```text
/opt/135er-growcontrol       root:growcontrol 0750
/etc/135er-growcontrol       root:growcontrol 0750
/var/lib/135er-growcontrol   growcontrol:growcontrol 0750
```

Secrets erhalten 0640 oder restriktiver.

## Netzwerk und Domain

Cloud öffentlich nur über HTTPS:

```text
Internet
  │
  ▼
TCP 443
  │
Nginx
  │
GrowControl Cloud API
  │
PostgreSQL nur intern
```

Nicht öffentlich freigeben:

- PostgreSQL
- lokale Pi-API
- Docker interne Ports
- Debug-Endpunkte

## Datenhaltung

Lokal: SQLite.

Cloud: PostgreSQL.

Details: `docs/de/DATENBANK_UND_RECHTE.md`.

## Remote Commands

Ein Remote-Befehl darf nur ausgeführt werden, wenn:

1. der Cloud-Server Remote Commands erlaubt,
2. der konkrete Local Node Remote Commands erlaubt,
3. Benutzer/Rolle die benötigte Permission besitzt,
4. der Befehl nicht abgelaufen ist,
5. Zielgerät und Wertebereich lokal validiert wurden.

## Fail-Safe

Bei Cloud-Ausfall:

- lokale UI bleibt erreichbar,
- Zeitpläne laufen weiter,
- Automationen laufen weiter,
- Sensoren werden weiter gespeichert,
- Telemetrie wird lokal gepuffert,
- Sync setzt später fort.
