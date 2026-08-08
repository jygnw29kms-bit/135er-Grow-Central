# Code Guide

## Comment standard

Core code uses bilingual comments:

```python
# DE: Verbindung lokal prüfen.
# EN: Validate the connection locally.
```

Important interfaces receive bilingual docstrings.

## Security rules

- Never hardcode secrets.
- Do not commit `.env`.
- Keep BLE writes disabled by default.
- Cloud failure must not stop local features.
- Validate remote commands locally.
- Use raw payloads only in test mode.

## Directory roles

- `app/` – local Raspberry Pi API
- `web/` – local UI
- `cloud/` – optional VPS
- `local/cloud_link/` – Pi-to-cloud synchronization
- `shared/` – shared data models
- `deploy/` – deployment examples
