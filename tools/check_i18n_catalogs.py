from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOGS = {
    "en": ROOT / "i18n" / "en" / "messages.json",
    "de": ROOT / "i18n" / "de" / "messages.json",
}


def load(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: catalog must be a JSON object")
    for key, value in data.items():
        if not isinstance(key, str) or not key.strip():
            raise SystemExit(f"{path}: invalid key {key!r}")
        if not isinstance(value, str) or not value.strip():
            raise SystemExit(f"{path}: empty/non-string value for {key}")
    return data


catalogs = {locale: load(path) for locale, path in CATALOGS.items()}
canonical = set(catalogs["en"])
failed = False
for locale, catalog in catalogs.items():
    keys = set(catalog)
    missing = sorted(canonical - keys)
    extra = sorted(keys - canonical)
    if missing:
        failed = True
        print(f"{locale}: missing {len(missing)} key(s):")
        for key in missing:
            print(f"  - {key}")
    if extra:
        failed = True
        print(f"{locale}: extra {len(extra)} key(s) not present in canonical English:")
        for key in extra:
            print(f"  - {key}")

if failed:
    raise SystemExit(1)

print(f"i18n catalogs OK: {len(canonical)} canonical key(s), DE/EN parity confirmed")
