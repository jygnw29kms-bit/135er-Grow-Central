# Sicherheit

## Betriebssystem

- regelmäßige APT-Sicherheitsupdates
- `unattended-upgrades`
- minimale Paketbasis
- eigener Service-User ohne interaktiven Login
- restriktive Datei- und Verzeichnisrechte

## Netzwerk

- keine direkte Internetfreigabe des lokalen Port 8080
- Cloud nur über Nginx/HTTPS
- TLS-Zertifikate über Let's Encrypt oder gleichwertig
- Firewall mit minimal nötigen Ports
- Fail2ban auf öffentlich erreichbaren Diensten

## Anwendung

- RBAC statt globaler Administratorrechte
- Passwörter nur gehasht
- Sessions zeitlich begrenzen und widerrufbar machen
- API-/Device-Tokens getrennt behandeln
- Secrets nie committen
- Remote-Commands standardmäßig aus
- Audit-Log für sicherheitsrelevante Aktionen
- Rate Limits und Eingabevalidierung

## DF100M

`DF100M_ALLOW_WRITES=false` bleibt der sichere Standard, solange das BLE-Protokoll nicht validiert ist.
