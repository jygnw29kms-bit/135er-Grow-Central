#!/usr/bin/env python3
"""Private, interactive one-time setup for optional Mars Hydro legacy fan cloud.

Run on the Grow-Central Raspberry Pi as root:
    sudo python3 /opt/135er-grow-central/scripts/configure-mars-hydro-cloud-fan.py

Does NOT contact Mars Hydro or modify the router. Account login happens only
after explicitly pressing cloud control or read in the GUI.
"""
from __future__ import annotations
import argparse
from getpass import getpass
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

CONFIG = Path("/etc/135er-grow-central/secrets/mars-cloud-fan.env")
DROPIN = Path("/etc/systemd/system/135er-grow-central.service.d/36-mars-cloud-fan.conf")


def quoted(value: str) -> str:
    if any(ord(c)<32 or ord(c)==127 for c in value):
        raise ValueError("Control characters are not permitted")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def atomic_secure_write(path: Path, text: str, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent,0o700 if path==CONFIG else 0o755)
    fd,temp=tempfile.mkstemp(prefix=".mars-fan-",dir=path.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as stream:
            os.fchmod(stream.fileno(),mode)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)


def main()->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--disable", action="store_true")
    args=ap.parse_args()
    if os.geteuid()!=0:
        print("Must run as root via sudo",file=sys.stderr)
        return 2
    if args.disable:
        DROPIN.unlink(missing_ok=True)
        CONFIG.unlink(missing_ok=True)
        subprocess.run(["systemctl","daemon-reload"],check=True)
        subprocess.run(["systemctl","restart","135er-grow-central.service"],check=True)
        print("Mars Hydro cloud fan integration disabled; credentials removed.")
        return 0
    if not sys.stdin.isatty():
        print("Requires an interactive console",file=sys.stderr)
        return 3
    print("Optional Mars Hydro LEGACY cloud fan. Your iPhone app may be logged out")
    print("when you later press Cloud Read / Control in Grow Central.")
    email=input("Mars Hydro app account email: ").strip()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",email):
        print("Invalid account email",file=sys.stderr);return 4
    password=getpass("Mars Hydro app password (hidden): ")
    if not password or len(password)>512:
        print("Invalid password",file=sys.stderr);return 4
    config=("GC_MARS_CLOUD_ENABLE=1\n"
            "GC_MARS_CLOUD_EMAIL="+quoted(email)+"\n"
            "GC_MARS_CLOUD_PASSWORD="+quoted(password)+"\n")
    atomic_secure_write(CONFIG,config,0o600)
    atomic_secure_write(DROPIN,
        "[Service]\nEnvironmentFile="+str(CONFIG)+"\n",0o644)
    subprocess.run(["systemctl","daemon-reload"],check=True)
    subprocess.run(["systemctl","restart","135er-grow-central.service"],check=True)
    print("Mars Hydro fan cloud configured. No login or fan command was sent.")
    print("Open Grow Central > Devices > Mars Hydro > Optional cloud control.")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
