#!/usr/bin/env python3
"""Read-only verification of deployed Grow Central Cloud Final Master assets.

Run on the Plesk host against a checkout of the desired Git revision:
  python3 scripts/verify_cloud_final_master_deployment.py --cloud-root /var/www/vhosts/grow-central.de/135ercloud.grow-central.de
Exit 0 only if the live static files match the checkout byte-for-byte.
No credentials, network access, or third-party Python packages required.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

SOURCE_TO_LIVE = {
    "cloud/portal/index.html": "index.html",
    "cloud/portal/cloud-master.html": "cloud-master.html",
    "cloud/portal/cloud-portal.js": "cloud-portal.js",
    "cloud/portal/gc-final-cloud.js": "static/gc-final.js",
    "cloud/portal/gc-final-cloud.css": "static/gc-final.css",
    "cloud/portal/cloud-master-bridge.js": "static/cloud-master-bridge.js",
    "cloud/portal/growbook-plants-wiki.js": "static/growbook-plants-wiki.js",
    "cloud/portal/growbook-plants-wiki.css": "static/growbook-plants-wiki.css",
    "cloud/portal/climate-stage.js": "static/climate-stage.js",
    "cloud/portal/climate-stage.css": "static/climate-stage.css",
    "cloud/portal/tent-growing-wiki.js": "static/tent-growing-wiki.js",
    "cloud/portal/tent-growing-wiki.css": "static/tent-growing-wiki.css",
    "cloud/portal/room-setup.js": "static/room-setup.js",
    "cloud/portal/room-setup.css": "static/room-setup.css",
    "web/soil-sensor-reference.jpg": "static/soil-sensor-reference.jpg",
    "cloud/portal/gc-manifest-cloud.webmanifest": "static/gc-manifest.webmanifest",
    "web/device-images/mars-hydro-fc3000.webp": "static/mars-hydro-fc3000.webp",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(source_root: Path, cloud_root: Path) -> int:
    failures = 0
    for source_name, live_name in SOURCE_TO_LIVE.items():
        source, live = source_root / source_name, cloud_root / live_name
        if not source.is_file() or not live.is_file():
            print(f"MISSING {live_name} (source={source.is_file()}, deployed={live.is_file()})")
            failures += 1
        elif sha256(source) != sha256(live):
            print(f"DIFF    {live_name}")
            failures += 1
        else:
            print(f"MATCH   {live_name}")
    # A publicly served backup may expose outdated forms and server metadata.
    # Never delete it automatically: archive outside the document root first.
    for path in sorted(cloud_root.iterdir()):
        if path.is_file() and (
            path.name.endswith((".backup.html", ".bak.html", ".old.html", ".orig.html"))
        ):
            print(f"EXPOSED_BACKUP {path.name} (move outside document root)")
            failures += 1
    print(f"RESULT: {len(SOURCE_TO_LIVE) - failures}/{len(SOURCE_TO_LIVE)} deployed files match")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cloud-root", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    return verify(args.source_root.resolve(), args.cloud_root.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
