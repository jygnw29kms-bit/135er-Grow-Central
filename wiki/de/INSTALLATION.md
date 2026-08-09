# Installation

## Zielsysteme

Der Installer ist für Debian/Ubuntu-basierte Systeme vorgesehen. Nicht unterstützte Distributionen sollen mit einer klaren Fehlermeldung abbrechen.

## Basis-Pakete

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y git curl ca-certificates python3 python3-pip python3-venv bluetooth bluez unattended-upgrades apt-listchanges
```

Cloud/VServer ergänzt typischerweise Nginx, PostgreSQL, Fail2ban und Firewall-Werkzeuge.

## Installer

```bash
git clone https://github.com/jygnw29kms-bit/135er-Grow-Central.git
cd 135er-Grow-Central
sudo ./install/install.sh
```

Der Installer soll OS erkennen, Pakete installieren, Service-User anlegen, Verzeichnisse/Rechte setzen, Python-Umgebung vorbereiten, systemd-Units installieren und Healthchecks ausführen.

## Nach der Installation

- Secrets in `.env` bzw. dedizierten Environment-Dateien setzen.
- DF100M BLE Writes standardmäßig deaktiviert lassen.
- Cloud-Remote-Commands nur bei Bedarf freischalten.
- Domain/DNS vor TLS-Ausstellung prüfen.
