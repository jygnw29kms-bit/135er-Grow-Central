# Security

135er-Grow Central `alpha-0.7.1` befindet sich in der Hardware-Validierung.

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
