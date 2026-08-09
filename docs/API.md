# API – 135er-Grow Central v0.6

## Local health/config

- `GET /api/health`
- `GET /api/config` – never returns secrets

## DF100M research API

Legacy compatibility endpoints remain available during migration:

- `GET /api/status`
- `GET /api/discover`
- `POST /api/connect`
- `POST /api/disconnect`
- `GET /api/services`
- `POST /api/notify/start`
- `POST /api/notify/stop`
- `POST /api/speed` – protected write
- `POST /api/raw` – protected development write

HUD compatibility aliases:

- `GET /api/df100m/status`
- `GET /api/df100m/discover`
- `POST /api/df100m/connect?address=...`
- `GET /api/df100m/services`
- `POST /api/df100m/speed?percent=...` – protected write

Protected writes require `X-API-Token` or `Authorization: Bearer ...` matching `GC_LOCAL_API_TOKEN`. If no local token is configured, writes fail closed.

## Smart-home API

- `GET /api/v1/smarthome/status`
- `GET /api/v1/smarthome/devices`
- `GET /api/v1/smarthome/devices/{id}/state`
- `POST /api/v1/smarthome/devices/{id}/switch` – protected write

Switch commands are accepted only for a registered device that is both `approved` and `writable`, while `GC_SMARTHOME_ENABLED=true`.

The API does not expose arbitrary target URLs or arbitrary Home Assistant service calls.
