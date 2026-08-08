# Security

135er GrowControl v0.3 ist eine frühe Testversion.

## Netzwerk

Port 8080 nicht direkt ins öffentliche Internet freigeben.

Für Remote-Zugriff besser:

- WireGuard
- Tailscale
- Reverse Proxy + TLS + Auth

## BLE

Experimentelle Schreibbefehle nur am eigenen Gerät testen.

## Secrets

Nicht committen:

- `.env`
- API Tokens
- WLAN-Passwörter
- private Schlüssel
- Accountsitzungen
