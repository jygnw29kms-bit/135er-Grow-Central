# Code-Leitfaden

## Kommentarstandard

Kern-Code verwendet zweisprachige Kommentare:

```python
# DE: Verbindung lokal prüfen.
# EN: Validate the connection locally.
```

Funktionen erhalten bei wichtigen Schnittstellen zweisprachige Docstrings.

## Sicherheitsregeln

- Secrets niemals hardcoden.
- `.env` nicht committen.
- BLE Writes standardmäßig deaktivieren.
- Cloud-Ausfall darf lokale Funktionen nicht stoppen.
- Remote Commands lokal validieren.
- Roh-Payloads nur im Testmodus verwenden.

## Verzeichnisrollen

- `app/` – lokale Raspberry-Pi-API
- `web/` – lokale Oberfläche
- `cloud/` – optionaler VServer
- `local/cloud_link/` – Pi-zu-Cloud-Synchronisation
- `shared/` – gemeinsame Datenmodelle
- `deploy/` – Deployment-Beispiele
