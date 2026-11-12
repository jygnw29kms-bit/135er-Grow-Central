#!/usr/bin/env python3
"""FC3000 Mars Legacy: offline notification timing audit of iPhone HCI PCAP.

Outputs ONLY aggregate metadata: no raw payload, device ID or session secret.
Reads actual H4-with-direction PCAP (linktype 201), no BLE communication.
Timing proximity to ATT writes does not prove an acknowledgment.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import struct
import sys

MAX_SIZE = 100 * 1024 * 1024


def att_records(blob: bytes):
    if len(blob) < 24:
        raise ValueError("truncated PCAP header")
    endian = {bytes.fromhex("a1b2c3d4"): ">", bytes.fromhex("d4c3b2a1"): "<"}.get(blob[:4])
    if not endian:
        raise ValueError("unsupported PCAP format")
    if struct.unpack(endian + "I", blob[20:24])[0] != 201:
        raise ValueError("expected HCI H4-with-direction PCAP")
    off = 24
    rows = []
    while off < len(blob):
        if off + 16 > len(blob):
            raise ValueError("truncated packet header")
        sec, us, size, original = struct.unpack(endian + "IIII", blob[off:off + 16])
        off += 16
        if size > 1048576 or off + size > len(blob):
            raise ValueError("invalid packet length")
        pkt = blob[off:off + size]
        off += size
        if len(pkt) < 14 or pkt[4] != 2:
            continue
        acl = pkt[5:]
        h, n = struct.unpack("<HH", acl[:4])
        if (h >> 12) & 3 not in (0, 2) or n > len(acl) - 4:
            continue
        l2 = acl[4:4 + n]
        if len(l2) < 7:
            continue
        length, cid = struct.unpack("<HH", l2[:4])
        if cid != 4 or length > len(l2) - 4:
            continue
        data = l2[4:4 + length]
        if len(data) < 3:
            continue
        opcode, handle = data[0], struct.unpack("<H", data[1:3])[0]
        if (opcode, handle) not in ((0x12, 0x002d), (0x1b, 0x002a)):
            continue
        rows.append((sec + us / 1e6, opcode, handle, data[3:]))
    return rows


def summarize(rows):
    try:
        from scripts.fc3000_legacy_pcap_decode import decode_mars_legacy
    except ModuleNotFoundError:
        from fc3000_legacy_pcap_decode import decode_mars_legacy
    writes = [(ts, decode_mars_legacy(payload))
              for ts, op, _, payload in rows if op == 0x12]
    writes = [(ts, item) for ts, item in writes if item is not None]
    notifications = [(ts, len(payload))
                     for ts, op, _, payload in rows if op == 0x1b]
    # Two-second windows are bounded by the next command, if any.
    report = []
    for i, (ts, command) in enumerate(writes):
        until = min(ts + 2.0, writes[i + 1][0] if i + 1 < len(writes) else float("inf"))
        near = [(t, n) for t, n in notifications if ts <= t < until]
        report.append({
            "action": command["action"], "value": command["value"],
            "seconds_from_first_command": round(ts - writes[0][0], 3),
            "notify_within_2s": len(near),
            "notify_lengths": dict(sorted(Counter(n for _, n in near).items())),
            "ack_verified": False,
        })
    return {
        "scope": "FC3000 only",
        "commands": len(writes),
        "notifications": len(notifications),
        "notify_lengths": dict(sorted(Counter(n for _, n in notifications).items())),
        "events": report,
        "warning": "Notifications may be periodic telemetry, not acknowledgements. No replay enabled.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pcap", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.pcap.stat().st_size > MAX_SIZE:
            raise ValueError("capture exceeds 100 MiB")
        report = summarize(att_records(args.pcap.read_bytes()))
        text = json.dumps(report, indent=2) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as f:
                f.write(text)
        else:
            print(text, end="")
    except (ValueError, OSError) as exc:
        print(f"notify audit failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
