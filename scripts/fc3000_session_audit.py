#!/usr/bin/env python3
"""Analyze Mars Legacy FC3000 HCI captures without publishing device/session secrets.
No BLE connection or GATT writes. Correlates controller connection handles and command
session tokens across captures; output is aggregate only, no raw identifiers.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import struct

MAX_BYTES = 100 * 1024 * 1024

def extract(path: Path) -> list[tuple[int, int, str, str, int, int]]:
    data = path.read_bytes()
    if len(data)>MAX_BYTES or len(data)<24:
        raise ValueError("unsupported PCAP size")
    end = {bytes.fromhex("d4c3b2a1"):"<",bytes.fromhex("a1b2c3d4"):">"}.get(data[:4])
    if end is None or struct.unpack_from(end+"I",data,20)[0]!=201:
        raise ValueError("expected H4-with-direction PCAP linktype 201")
    offset=24; writes=[]
    while offset+16<=len(data):
        sec,micro,n,_=struct.unpack_from(end+"IIII",data,offset); offset+=16
        if n>1048576 or offset+n>len(data):
            raise ValueError("invalid PCAP record")
        pkt=data[offset:offset+n];offset+=n
        if len(pkt)<16 or pkt[4]!=2: continue
        acl=pkt[5:]
        if len(acl)<4:continue
        raw_handle,alen=struct.unpack_from("<HH",acl)
        if alen>len(acl)-4:continue
        l2=acl[4:4+alen]
        if len(l2)<7:continue
        ll,cid=struct.unpack_from("<HH",l2)
        if cid!=4 or ll>len(l2)-4:continue
        att=l2[4:4+ll]
        if len(att)<4 or att[0] not in (0x12,0x52):continue
        handle=struct.unpack_from("<H",att,1)[0]
        if handle!=0x2D:continue
        try: cmd,field,session,device,value=att[3:].decode("ascii").split("|")
        except (UnicodeDecodeError,ValueError):continue
        if (cmd not in ("1","2") or field!="0" or not device.startswith("FC")
            or not value.isdecimal() or not (1<=len(session)<=64)):continue
        writes.append((sec,int(raw_handle & 0x0fff),session,device,int(cmd),int(value)))
    if offset!=len(data):raise ValueError("truncated PCAP")
    return writes

def analyze(files: list[Path]) -> dict:
    rows=[(f.name,extract(f)) for f in files]
    token_sets=[{x[2] for x in records} for _,records in rows]
    connections=[{x[1] for x in records} for _,records in rows]
    all_records=[x for _,records in rows for x in records]
    return {
        "capture_count":len(files),
        "files":[{
            "file":name,"valid_fc3000_writes":len(records),
            "unique_session_tokens":len({x[2] for x in records}),
            "unique_acl_handles":len({x[1] for x in records}),
            "session_lengths":sorted({len(x[2]) for x in records}),
            "action_values":[{"type":x[4],"value":x[5]} for x in records[:30]],
        } for name,records in rows],
        "session_token_shared_across_files":bool(token_sets) and bool(set.intersection(*token_sets)),
        "unique_session_tokens_overall":len({x[2] for x in all_records}),
        "unique_device_ids_overall":len({x[3] for x in all_records}),
        "all_known_tokens_private":True,
        "live_control_validated":False,
        "control_write_attempted":False,
        "note":"Shared session tokens in overlapping PCAPs do not establish a reusable authentication secret."
    }

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("pcap",type=Path,nargs="+")
    args=p.parse_args()
    try:print(json.dumps(analyze(args.pcap),indent=2,ensure_ascii=False))
    except (OSError, ValueError) as exc:
        print("Audit failed:",type(exc).__name__)
        return 2
    return 0

if __name__=="__main__":
    raise SystemExit(main())
