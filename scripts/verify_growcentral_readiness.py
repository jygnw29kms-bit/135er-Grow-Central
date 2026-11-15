#!/usr/bin/env python3
"""Non-invasive Grow Central readiness check for the Pi and Cloud.

No authentication, BLE control, device changes or data mutation. Intentionally
disconnected Mars Hydro devices are not considered failed hardware.
Run on the Pi with --mode all; use --mode cloud on a Cloud-only machine.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

PI_SERVICES = (
    "135er-grow-central", "grow-central-homekit", "grow-central-provisioning",
    "135er-grow-central-cloud-link", "135er-grow-central-remote-channel",
    "mosquitto",
)
CLOUD_SERVICES = (
    "nginx", "135er-growcentral-cloud",
    "135er-growcentral-cloud-admin", "135er-growcentral-cloud-platform",
)


def http(url: str, *, method: str = "GET") -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url, method=method, headers={"User-Agent": "GrowCentral-Readiness/1"})
    try:
        with urllib.request.urlopen(request, timeout=7) as response:
            return response.status, dict(response.headers.items()), response.read(32768)
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers.items()), b""


def check(mode: str, *, check_services: bool = True, cloud_origin: str = "https://135ercloud.grow-central.de") -> dict:
    result = {"mode": mode, "checks": {}, "warnings": []}

    def record(name: str, passed: bool, message: str = "") -> None:
        result["checks"][name] = {"ok": bool(passed), "detail": message}

    if check_services:
        service_set = (*PI_SERVICES, *(CLOUD_SERVICES if mode in ("cloud", "all") else ())) if mode == "all" else PI_SERVICES if mode == "pi" else CLOUD_SERVICES
        for name in service_set:
            status = subprocess.run(["systemctl", "is-active", name], capture_output=True, text=True, timeout=5)
            record(f"service:{name}", status.returncode == 0 and status.stdout.strip() == "active", status.stdout.strip())
    if mode in ("pi", "all"):
        try:
            code, _, payload = http("http://127.0.0.1:8080/api/health")
            health = json.loads(payload) if code == 200 else {}
            record("pi:health", code == 200 and health.get("ok") is True, f"HTTP {code}")
        except (OSError, ValueError, KeyError) as exc:
            record("pi:health", False, type(exc).__name__)
        try:
            code, _, _ = http("http://127.0.0.1:8080/api/v1/rooms")
            record("pi:rooms-auth-protection", code in (401, 403), f"HTTP {code}")
        except OSError as exc:
            record("pi:rooms-auth-protection", False, type(exc).__name__)
        # These are presence checks, not proof of valid measurements.
        if not list(Path("/dev/serial/by-id").glob("*")):
            result["warnings"].append("no USB serial sensor currently present")
        if not list(Path("/dev").glob("video*")):
            result["warnings"].append("no camera device node currently present")
    if mode in ("cloud", "all"):
        try:
            code, headers, _ = http(cloud_origin + "/", method="HEAD")
            lowercase = {key.lower(): value for key, value in headers.items()}
            record("cloud:login", code == 200, f"HTTP {code}")
            record("cloud:nosniff", lowercase.get("x-content-type-options") == "nosniff")
            code, _, data = http(cloud_origin + "/static/gc-manifest.webmanifest")
            manifest = json.loads(data) if code == 200 else {}
            record("cloud:pwa-start", code == 200 and manifest.get("start_url") == "/", f"HTTP {code}")
            code, _, _ = http(cloud_origin + "/cloud-master.html", method="HEAD")
            record("cloud:final-master", code == 200, f"HTTP {code}")
            for old in ("/static/gc-final.html", "/static/gc-worker.js", "/index.plesk-original.backup.html"):
                code, _, _ = http(cloud_origin + old, method="HEAD")
                record(f"cloud:legacy-not-public:{old}", code in (404, 410), f"HTTP {code}")
        except (OSError, ValueError, KeyError) as exc:
            record("cloud:availability", False, type(exc).__name__)
    result["ok"] = all(value["ok"] for value in result["checks"].values())
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("pi", "cloud", "all"), default="all")
    parser.add_argument("--skip-services", action="store_true", help="for network-only checks")
    parser.add_argument("--cloud-origin", default="https://135ercloud.grow-central.de")
    args = parser.parse_args()
    output = check(args.mode, check_services=not args.skip_services, cloud_origin=args.cloud_origin.rstrip("/"))
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
