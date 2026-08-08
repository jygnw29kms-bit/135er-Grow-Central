# API

## Local `:8080`

- `GET /api/health` – service health
- `GET /api/config` – test configuration
- `GET /api/status` – BLE state
- `GET /api/discover` – BLE discovery
- `POST /api/connect` – connect
- `POST /api/disconnect` – disconnect
- `GET /api/services` – inspect GATT
- `POST /api/notify/start` – start notifications
- `POST /api/notify/stop` – stop notifications
- `POST /api/speed` – experimental speed test
- `POST /api/raw` – raw payload test

## Cloud `:8090`

Header: `X-API-Token`

- `GET /api/health`
- `POST /api/v1/telemetry`
- `GET /api/v1/sites/{site_id}/latest`
- `GET /api/v1/sites/{site_id}/history`
- `POST /api/v1/commands`
- `GET /api/v1/sites/{site_id}/commands/pending`
- `POST /api/v1/commands/{id}/result`
