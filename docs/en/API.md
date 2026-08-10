# API

## Local `:8080`

- `GET /api/health` – service health
- `GET /api/config` – test configuration
- `GET /api/status` – BLE state
- `GET /api/discover` – authenticated BLE discovery
- `POST /api/connect` – authenticated connect
- `POST /api/disconnect` – authenticated disconnect
- `GET /api/services` – authenticated GATT inspection
- `POST /api/notify/start` – start notifications
- `POST /api/notify/stop` – stop notifications
- `POST /api/speed` – experimental speed test
- `POST /api/raw` – raw payload test

Active discovery, connection management, GATT diagnostics, and writes require `GC_LOCAL_API_TOKEN`. Raw payloads remain separately locked by `DF100M_ALLOW_RAW_WRITES=false`.

## Cloud `:8090`

Header: `X-API-Token`

The cloud token must be at least 32 characters long; placeholders are rejected.

- `GET /api/health`
- `POST /api/v1/telemetry`
- `GET /api/v1/sites/{site_id}/latest`
- `GET /api/v1/sites/{site_id}/history`
- `POST /api/v1/commands`
- `GET /api/v1/sites/{site_id}/commands/pending`
- `POST /api/v1/commands/{id}/result`
