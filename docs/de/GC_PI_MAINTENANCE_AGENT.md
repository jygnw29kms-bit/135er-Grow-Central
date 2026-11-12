# Grow Central Pi: schlüsselgebundener Wartungsagent

**Status 2026-11-12:** Installer und Rückbau liegen im Git. **Noch nicht auf Pi 192.168.178.98 installiert**: Der Jens-PC erreicht die Pi-Dienste (22, 80, 8080), aber der vermittelte SSH-Befehl wurde vom Fernwartungskanal abgelehnt. HTTP-BLE-Status auf 8080 gibt ohne Auth korrekt 401 zurück. Keine Behauptung eines abgeschlossenen Deployments.

## Ziel und Sicherheit

- Dedizierter Linux-Benutzer `gc-maint`, persönlicher OpenSSH-Public-Key, Passwortlogin für diesen Benutzer durch gesperrtes Passwort unterbunden.
- Administrativer Zugriff auf ausdrücklichen Wunsch des Gerätebesitzers mittels passwortlosem sudo; damit faktisch **voller Root-Zugriff**. **Nur Schlüssel von autorisierten Administratoren verwenden**; Verlust des Schlüssels entspricht einem vollständigen Gerätekompromiss.
- Ein systemd-Timer prüft im Minutenrhythmus den vorhandenen SSH-Dienst und startet ihn neu, falls er ausgefallen ist. Der Timer verändert weder andere Dienste noch Gerätekonfiguration.
- Keine privaten Schlüssel, Host-Passwörter, festcodierten Tokens, Remote-MCP-Credentials oder öffentlich geöffnete Ports im Image/Git.
- Für dauerhaften Zugriff von außerhalb des LAN ist ein **authentifiziertes VPN/Overlay** oder MeshCentral mit individueller Agent-Registrierung nötig; das ist **nicht automatisch Teil dieses Installers**. Port 22 keinesfalls pauschal am Router freigeben.
- Keine Änderungen an bestehenden Grow-Central-Benutzern, HomeKit oder Sensoren. Kein automatischer Neustart des Pi.

## Einmalige Installation am Pi nach manueller Prüfung

Dateien im öffentlichen Git:

- [Installer](../../scripts/install-gc-maintenance-agent.sh)
- [Rückbau](../../scripts/uninstall-gc-maintenance-agent.sh)

Einen öffentlichen Schlüssel des tatsächlich autorisierten Wartungsclients auf dem Pi bereitstellen, z.B. `/tmp/gc-maint.pub` (nur `.pub`, **niemals** einen privaten Schlüssel). Dann auf dem Pi:

```bash
curl -fL https://raw.githubusercontent.com/jygnw29kms-bit/135er-Grow-Central/master/scripts/install-gc-maintenance-agent.sh -o /tmp/install-gc-maintenance-agent.sh
bash -n /tmp/install-gc-maintenance-agent.sh
sudo bash /tmp/install-gc-maintenance-agent.sh --public-key-file /tmp/gc-maint.pub
systemctl status gc-maintenance-ssh-check.timer --no-pager
```

Beim ersten Funktionsnachweis von einem **wirklich autorisierten** Client Login mit zugehörigem privaten SSH-Schlüssel verifizieren und `sudo -n true` ausführen. Niemals einen Zugangserfolg ausschließlich aus installiertem Skript ableiten. Fehlende Verbindung kann an Firewall, sshd-Konfiguration, VPN oder Netzwerk liegen und muss separat untersucht werden.

## Rückbau

```bash
sudo bash /tmp/uninstall-gc-maintenance-agent.sh
```

Der Rückbau entfernt Timer, Dienst und sudo-Sonderregel. Benutzer und Public-Key-Datei werden bewusst zur Prüfung belassen. Für vollständige Deaktivierung zusätzlich die spezifische `authorized_keys`-Zeile entfernen beziehungsweise das Wartungskonto sperren.

## Pi-Update

Das Upgrade auf den **aktuellen** Grow-Central-master ist bis zur Feststellung der laufenden Versions-SHA und einem getesteten Backup-Restore **nicht ausgeführt**. Der bestehende Build-461-Image-Candidate ist kein Beweis für den Live-Code auf der .98. Vor einer Aktualisierung sind Git-Stand, Datenverzeichnis, aktueller Service und Migrationsbedarf auf dem Pi zu verifizieren. Danach Änderungen mit Test, Health-Check und automatischem Rollback ausrollen; Sensorschnittstellen und HomeKit müssen intakt bleiben.
