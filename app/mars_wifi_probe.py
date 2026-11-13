"""Read-only Mars Legacy WiFi access point inventory. No network changes."""
from __future__ import annotations
import re
import subprocess

def split_nmcli(line: str) -> list[str]:
    fields, current, escaped = [], [], False
    for c in line:
        if escaped:
            current.append(c)
            escaped = False
        elif c == "\\":
            escaped = True
        elif c == ":":
            fields.append("".join(current)); current=[]
        else:
            current.append(c)
    return fields+["".join(current)]

def role_for(bssid: str) -> str:
    # Installation-specific BLE/WiFi hardware prefix observation.
    value = bssid.upper()
    if value.startswith("A0:A3:B3:5E:FD:"): return "DF150-M / MZF002-Kandidat"
    if value.startswith("FC:B4:67:AE:C2:"): return "FC3000 / MARS-Kandidat"
    return "nicht zugeordnet"

def wifi_status() -> dict:
    command=["nmcli","-t","--escape","yes","-f",
             "SSID,BSSID,CHAN,SIGNAL,SECURITY","device","wifi","list",
             "ifname","wlan0","--rescan","no"]
    try:
        p=subprocess.run(command, capture_output=True, text=True, timeout=8, check=False)
    except (OSError,subprocess.TimeoutExpired):
        return {"ok":False,"reason":"wifi_adapter_unavailable","access_points":[]}
    if p.returncode!=0:
        return {"ok":False,"reason":"wifi_cache_unavailable","access_points":[]}
    found=[]
    for line in p.stdout.splitlines():
        fields=split_nmcli(line)
        if len(fields)!=5:continue
        ssid,bssid,channel,signal,security=fields
        if not re.fullmatch(r"MZ-AP-MASTER-[0-9]{3,10}",ssid):continue
        if not re.fullmatch(r"(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}",bssid):continue
        try: chan=int(channel);strength=int(signal)
        except ValueError:continue
        if not (1<=chan<=196 and 0<=strength<=100):continue
        found.append({"ssid":ssid,"bssid":bssid.upper(),"signal_percent":strength,
                      "channel":chan,"security":security[:50],"device_hint":role_for(bssid),
                      "connection_verified":False,"control_verified":False})
    return {"ok":True,"access_points":found,"source":"NetworkManager cached scan",
            "wifi_connection_changed":False,
            "note":"WLAN-Sichtbarkeit beweist keine Verbindung oder Steuerbarkeit."}
