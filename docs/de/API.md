# API

## Local `:8080`

- `GET /api/health` – Dienststatus
- `GET /api/config` – Testkonfiguration
- `GET /api/status` – BLE-Zustand
- `GET /api/discover` – authentifizierte BLE-Suche
- `POST /api/connect` – authentifiziert verbinden
- `POST /api/disconnect` – authentifiziert trennen
- `GET /api/services` – authentifiziert GATT auslesen
- `POST /api/notify/start` – Notifications starten
- `POST /api/notify/stop` – Notifications stoppen
- `POST /api/speed` – experimenteller Speed-Test
- `POST /api/raw` – Roh-Payload-Test

Aktive Suche, Verbindungsverwaltung, GATT-Diagnose und Schreibzugriffe benötigen `GC_LOCAL_API_TOKEN`. Roh-Payloads bleiben zusätzlich mit `DF100M_ALLOW_RAW_WRITES=false` gesperrt.

## Cloud `:8090`

Header: `X-API-Token`

Der Cloud-Token muss mindestens 32 Zeichen lang sein; Platzhalter werden abgewiesen.

- `GET /api/health`
- `POST /api/v1/telemetry`
- `GET /api/v1/sites/{site_id}/latest`
- `GET /api/v1/sites/{site_id}/history`
- `POST /api/v1/commands`
- `GET /api/v1/sites/{site_id}/commands/pending`
- `POST /api/v1/commands/{id}/result`
