# API – 135er-Grow Central alpha-0.7.1

## Local health/config

- `GET /api/health`
- `GET /api/config` – never returns secrets

## DF100M research API

Legacy compatibility endpoints remain available during migration:

- `GET /api/status`
- `GET /api/discover` – authenticated active scan
- `POST /api/connect` – authenticated state change
- `POST /api/disconnect` – authenticated state change
- `GET /api/services` – authenticated diagnostic read
- `POST /api/notify/start` – authenticated state change
- `POST /api/notify/stop` – authenticated state change
- `POST /api/speed` – protected write
- `POST /api/raw` – protected development write; separately gated by `DF100M_ALLOW_RAW_WRITES`

HUD compatibility aliases:

- `GET /api/df100m/status`
- `GET /api/df100m/discover`
- `POST /api/df100m/connect?address=...`
- `GET /api/df100m/services`
- `POST /api/df100m/speed?percent=...` – protected write

Protected writes, active discovery, connection management and diagnostic GATT inspection require `X-API-Token` or `Authorization: Bearer ...` matching `GC_LOCAL_API_TOKEN`. If no local token is configured, these operations fail closed.

## Smart-home API

- `GET /api/v1/smarthome/status`
- `GET /api/v1/smarthome/devices`
- `GET /api/v1/smarthome/devices/{id}/state`
- `POST /api/v1/smarthome/devices/{id}/switch` – protected write

Switch commands are accepted only for a registered device that is both `approved` and `writable`, while `GC_SMARTHOME_ENABLED=true`.

The API does not expose arbitrary target URLs or arbitrary Home Assistant service calls.
