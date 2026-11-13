#!/usr/bin/env python3
"""Read-only Mars Legacy firmware/OTA evidence audit of an owner-supplied XAPK.

Does NOT perform vendor API requests, retrieve private firmware, or send
update commands. Prints no credentials, tokens, mesh secrets, or binary code.
"""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

MARKERS = {
    "ota_product_list": b"api/ios/udm/getUpgradeProduct/v1",
    "ota_upgrade_command": b"api/ios/udm/getUpgradeCommand/v1",
    "ota_data_key": b"upgradeData",
    "ota_download_key": b"downLoadUrl",
    "wifi_provisioning": b"api/ios/dnet/configWifi/v1",
    "mesh_key_route": b"api/ios/dnet/getMeshKey/v1",
    "fan_speed_symbol": b"wind_set_speed",
}
FIRMWARE_SUFFIXES = (".fw", ".ota", ".hex", ".uf2", ".dfu", ".img")
def audit(p: Path) -> dict:
    raw = p.read_bytes()
    if not (0 < len(raw) <= 160*1024*1024):
        raise ValueError("Invalid XAPK size")
    libraries=[]
    potential_fw=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as outer:
        for name in outer.namelist():
            if not name.endswith(".apk"):
                continue
            entry=outer.getinfo(name)
            if entry.file_size>120*1024*1024:
                raise ValueError("Oversized split APK")
            with zipfile.ZipFile(io.BytesIO(outer.read(name))) as inner:
                for file in inner.infolist():
                    lower=file.filename.lower()
                    if lower.endswith(FIRMWARE_SUFFIXES) and not lower.endswith("assetmanifest.bin"):
                        potential_fw.append({"split":name,"path":file.filename,"size":file.file_size})
                    if file.filename=="lib/arm64-v8a/libapp.so":
                        libraries.append(inner.read(file))
    if len(libraries)!=1:
        raise ValueError("Expected exactly one ARM64 Flutter AOT snapshot")
    blob=libraries[0]
    return {
        "format":"gc_mars_firmware_offline_audit_v1",
        "xapk_sha256":hashlib.sha256(raw).hexdigest(),
        "flutter_aot_size":len(blob),
        "marker_present":{name:word in blob for name,word in MARKERS.items()},
        "embedded_firmware_candidates":potential_fw,
        "firmware_image_downloaded":False,
        "device_update_performed":False,
        "api_authentication_attempted":False,
        "warning":"An OTA API route is not itself a publicly downloadable firmware image.",
    }
if __name__=="__main__":
    if len(sys.argv)!=2:
        print("Usage: mars_legacy_firmware_audit.py owner-file.xapk",file=sys.stderr)
        raise SystemExit(2)
    try:
        print(json.dumps(audit(Path(sys.argv[1])),indent=2,ensure_ascii=False))
    except (OSError,ValueError,zipfile.BadZipFile) as exc:
        print("Audit failed:",type(exc).__name__,file=sys.stderr)
        raise SystemExit(2)
