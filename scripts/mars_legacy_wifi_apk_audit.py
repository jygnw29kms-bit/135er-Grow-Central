#!/usr/bin/env python3
"""Offline Mars Legacy XAPK WiFi evidence audit: no secrets, network or device IO."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sys
from zipfile import ZipFile

EVIDENCE={
 "wifi_remote_setup":"Setup WiFi to enable remote control",
 "wifi_configuration":"api/ios/dnet/configWifi/v1",
 "wifi_mesh_key":"api/ios/dnet/getMeshKey/v1",
 "fan_speed_command_name":"wind_set_speed",
 "fan_mode_name":"wind_mode",
 "fan_rpm_name":"wind_speed_num",
 "ble_write_function":"writeCharacteristicWithResponse",
 "legacy_cloud_fan_speed_route":"api/ios/udm/adjustLight/v1",
 "legacy_cloud_power_route":"api/ios/udm/lampSwitch/v1",
 "legacy_cloud_subdevice_route":"api/ios/udm/subDeviceSwitch/v1",
 "social_login_route":"api/ios/tlogin/unionLogin/v1",
 "ble_service":"83677baa-3eb8-4866-b6b6-96e5ed5cc48d",
 "ble_notify":"6f588463-f8f1-44f8-bdae-a1272a1b0f6e",
 "ble_write":"f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d",
}
def audit(path: Path) -> dict:
    raw=path.read_bytes()
    if len(raw)>140*1024*1024:raise ValueError("Archive too large")
    libraries=[]
    with ZipFile(BytesIO(raw)) as xapk:
        for name in xapk.namelist():
            if not name.endswith(".apk"):continue
            info=xapk.getinfo(name)
            if info.file_size>140*1024*1024:continue
            with ZipFile(BytesIO(xapk.read(name))) as apk:
                name="lib/arm64-v8a/libapp.so"
                if name in apk.namelist() and apk.getinfo(name).file_size<=35*1024*1024:
                    libraries.append(apk.read(name))
    if len(libraries)!=1:raise ValueError("Expected one Flutter ARM64 library")
    data=libraries[0]
    return {
        "format":"mars_legacy_static_wifi_evidence_v1",
        "package_sha256":hashlib.sha256(raw).hexdigest(),
        "app_library_bytes":len(data),
        "signals":{name:needle.encode("ascii") in data for name,needle in EVIDENCE.items()},
        "wifi_control_route_verified":False,
        "fan_write_payload_verified":False,
        "credentials_or_mesh_key_collected":False,
        "any_network_or_device_command":False,
    }
if __name__=="__main__":
    try:print(json.dumps(audit(Path(sys.argv[1])),indent=2))
    except (OSError,ValueError,IndexError) as ex:
        print("APK audit failed:",type(ex).__name__,file=sys.stderr)
        sys.exit(2)
