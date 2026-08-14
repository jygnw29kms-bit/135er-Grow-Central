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

FRITZ!Box-Zugangsdaten werden nach einer erfolgreichen Anmeldung ausschließlich
im lokalen Credential Store unter `/var/lib/135er-grow-central` gespeichert. Der
Payload ist per Fernet verschlüsselt, Schlüssel und Payload haben Modus `0600`,
das Passwort wird nie über Status-APIs ausgegeben und beide Dateien sind von
Support-Archiven ausgeschlossen.
