#!/usr/bin/env python3
"""Private, read-only FC3000 HCI notify structure audit.

Only aggregate field-type frequencies and candidate correlations are printed.
Raw bytes, device identifiers, tokens and field contents are never displayed.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import struct

def examine(path:Path)->dict:
    b=path.read_bytes()
    if len(b)>100*1024*1024 or len(b)<24 or b[:4] not in (bytes.fromhex("d4c3b2a1"),bytes.fromhex("a1b2c3d4")):
        raise ValueError("unsupported PCAP")
    end="<" if b[:4]==bytes.fromhex("d4c3b2a1") else ">"
    if struct.unpack_from(end+"I",b,20)[0]!=201:raise ValueError("wrong PCAP link type")
    i=24;notifies=[];writes=[];unique=Counter();nonascii=0
    while i+16<=len(b):
        sec,micro,size,original=struct.unpack_from(end+"IIII",b,i);i+=16
        if size>1048576 or i+size>len(b):raise ValueError("corrupt frame")
        p=b[i:i+size];i+=size
        if len(p)<17 or p[4]!=2:continue
        acl=p[5:]
        if len(acl)<4:continue
        h,n=struct.unpack_from("<HH",acl)
        if n>len(acl)-4:continue
        l=acl[4:4+n]
        if len(l)<7:continue
        ln,cid=struct.unpack_from("<HH",l)
        if cid!=4 or ln>len(l)-4:continue
        a=l[4:4+ln]
        if len(a)<3:continue
        handle=struct.unpack_from("<H",a,1)[0]
        payload=a[3:]
        if a[0]==0x1B and handle==0x2A:
            try:
                vals=payload.decode("ascii").strip("\r\n").split("|")
            except UnicodeDecodeError:
                nonascii+=1;continue
            notifies.append((sec+micro/1000000, vals))
            unique[len(vals)]+=1
        elif a[0] in (0x12,0x52) and handle==0x2D:
            try:parts=payload.decode("ascii").split("|")
            except UnicodeDecodeError:continue
            if len(parts)==5 and parts[0] in ("1","2") and parts[3].startswith("FC") and parts[4].isdigit():
                writes.append((sec+micro/1000000,int(parts[0]),int(parts[4])))
    if i!=len(b):raise ValueError("truncated file")
    fieldtypes={}
    for width,count in unique.most_common(3):
        rows=[values for _,values in notifies if len(values)==width]
        desc=[]
        for k in range(width):
            col=[row[k] for row in rows]
            nums=[]
            for value in col:
                try:nums.append(float(value))
                except ValueError:pass
            desc.append({"index":k,"numeric_fraction":round(len(nums)/len(col),3),
                         "distinct_values":len(set(col)),
                         "min_number":round(min(nums),2) if nums and len(nums)==len(col) else None,
                         "max_number":round(max(nums),2) if nums and len(nums)==len(col) else None})
        fieldtypes[str(width)]=desc
    windows=[]
    for ts,kind,val in writes:
        within=[values for t,values in notifies if 0<=t-ts<2.5]
        windows.append({"action_type":kind,"value":val,"notifications":len(within),
                        "field_counts":dict(Counter(len(x) for x in within))})
    return {"notify_count":len(notifies),"nonascii_notifications":nonascii,
            "field_count_distribution":dict(unique),"field_profiles":fieldtypes,
            "fc3000_commands":len(writes),"command_windows":windows,
            "raw_identifiers_exposed":False,"hardware_writes_attempted":False,
            "note":"Field index correlations are candidates, not proof of a measured output or controller ACK."}

def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pcap",type=Path)
    a=parser.parse_args()
    try:print(json.dumps(examine(a.pcap),indent=2,ensure_ascii=False))
    except (ValueError,OSError) as e:
        print("Audit failed: "+type(e).__name__);return 2
    return 0
if __name__=="__main__":raise SystemExit(main())
