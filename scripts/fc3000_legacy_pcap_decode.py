#!/usr/bin/env python3
"""Read-only FC3000 Mars Legacy HCI PCAP decoder (no BLE device interaction).

Evidence source: iPhone idevicebtlogger HCI H4-with-direction pcap, 2026-11-12.
Shows observed ATT Write Request values on handle 0x002d, NOT a validated
replay implementation. Raw captures can contain secrets: never commit them.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import struct
import sys

MAX_FILE = 100 * 1024 * 1024
H4_WITH_PHDR = 201
FC_ID = re.compile(r"^FC[A-F0-9]{10}$")
SESSION = re.compile(r"^[0-9A-Za-z_-]{1,64}$")


def decode_mars_legacy(payload: bytes):
    """Return redacted evidence or None. Never expose ID or session string."""
    try:
        parts = payload.decode("ascii").split("|")
    except UnicodeDecodeError:
        return None
    if len(parts) != 5:
        return None
    command, field2, session, device, value = parts
    if command not in ("1", "2") or field2 != "0":
        return None
    if not SESSION.fullmatch(session) or not FC_ID.fullmatch(device):
        return None
    if not value.isascii() or not value.isdecimal():
        return None
    number = int(value)
    if command == "1" and number in (0, 1):
        action = "light_on" if number == 1 else "light_off"
    elif command == "2" and 0 <= number <= 100:
        action = "brightness_candidate"
    else:
        return None
    return {
        "command_type": int(command),
        "action": action,
        "value": number,
        "target_redacted": True,
        "session_redacted": True,
        "second_field": field2,
        "verified_replay": False,
    }


def parse_pcap(data: bytes):
    if len(data) < 24:
        raise ValueError("PCAP header missing")
    endian = {b"\xa1\xb2\xc3\xd4": ">", b"\xd4\xc3\xb2\xa1": "<"}.get(data[:4])
    if endian is None:
        raise ValueError("unsupported PCAP magic")
    link = struct.unpack(endian + "I", data[20:24])[0]
    if link != H4_WITH_PHDR:
        raise ValueError(f"unsupported PCAP linktype {link}, expected HCI H4 with phdr (201)")
    offset = 24
    packets = 0
    att_writes = 0
    events = []
    while offset + 16 <= len(data):
        sec, micros, incl, original = struct.unpack(endian + "IIII", data[offset:offset + 16])
        offset += 16
        if incl > 1048576 or offset + incl > len(data):
            raise ValueError("invalid or truncated packet")
        raw = data[offset:offset + incl]
        offset += incl
        packets += 1
        if len(raw) < 14 or raw[4] != 0x02:
            continue
        acl = raw[5:]
        h, acl_len = struct.unpack("<HH", acl[:4])
        # Ignore fragmented packets: never interpret continuation fragments as ATT.
        pb_flag = (h >> 12) & 3
        if pb_flag not in (0, 2) or acl_len > len(acl) - 4:
            continue
        l2 = acl[4:4 + acl_len]
        if len(l2) < 7:
            continue
        l2_len, cid = struct.unpack("<HH", l2[:4])
        if cid != 4 or l2_len > len(l2) - 4:
            continue
        att = l2[4:4 + l2_len]
        if len(att) < 3 or att[0] not in (0x12, 0x52):
            continue
        att_writes += 1
        handle = struct.unpack("<H", att[1:3])[0]
        if handle != 0x002d:
            continue
        decoded = decode_mars_legacy(att[3:])
        if decoded is None:
            continue
        decoded.update({
            "timestamp_utc": datetime.fromtimestamp(sec + micros / 1e6, timezone.utc).isoformat(),
            "gatt_handle": "0x002d",
            "att_opcode": f"0x{att[0]:02x}",
            "packet_number": packets,
        })
        events.append(decoded)
    if offset != len(data):
        raise ValueError("trailing truncated PCAP record")
    return {
        "format": "fc3000_legacy_observed_v1",
        "total_hci_packets": packets,
        "att_write_packets": att_writes,
        "fc3000_candidate_writes": len(events),
        "observed_actions": dict(Counter(x["action"] for x in events)),
        "events": events,
        "safety": "Offline observation only; commands not approved for replay. Identifiers redacted.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pcap", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.pcap.stat().st_size > MAX_FILE:
            raise ValueError("PCAP larger than 100 MiB")
        result = parse_pcap(args.pcap.read_bytes())
        encoded = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as f:
                f.write(encoded)
        else:
            print(encoded, end="")
    except (OSError, ValueError) as exc:
        print(f"FC3000 decode failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
