#!/usr/bin/env python3
"""Private read-only audit of FAN HCI data path, without raw bytes/identifiers.

Does not connect to any device or issue writes. Summarizes ATT opcodes and
controller handles around observed MZF002 status changes.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import struct

def analyze(path):
    b=Path(path).read_bytes()
    end={bytes.fromhex('d4c3b2a1'):'<',bytes.fromhex('a1b2c3d4'):'>'}.get(b[:4])
    if not end or len(b)<24 or struct.unpack_from(end+'I',b,20)[0]!=201:raise ValueError('invalid capture')
    i=24;op=Counter();by_conn=defaultdict(Counter);directions=defaultdict(Counter);notifies=[];writes=[]
    while i+16<=len(b):
        sec,micro,n,_=struct.unpack_from(end+'IIII',b,i);i+=16
        if n>1048576 or i+n>len(b):raise ValueError('corrupt')
        pkt=b[i:i+n];i+=n
        if len(pkt)<17 or pkt[4]!=2:continue
        acl=pkt[5:];ch,sz=struct.unpack_from('<HH',acl)
        if sz>len(acl)-4:continue
        l=acl[4:4+sz]
        if len(l)<7:continue
        plen,cid=struct.unpack_from('<HH',l)
        if cid!=4 or plen>len(l)-4:continue
        a=l[4:4+plen]
        if len(a)<1:continue
        opcode=a[0];conn=ch&0xfff
        op[f'{opcode:02x}']+=1
        by_conn[str(conn)][f'{opcode:02x}']+=1
        directions[str(conn)][str(int.from_bytes(pkt[:4],'big'))+':'+f'{opcode:02x}']+=1
        handle=struct.unpack_from('<H',a,1)[0] if len(a)>=3 else None
        if opcode in (0x12,0x52,0x16,0x18):
            writes.append({'time':sec+micro/1e6,'conn':conn,'op':f'{opcode:02x}','handle':handle})
        if opcode==0x1b and handle==0x2a and len(a)>3:
            try:parts=a[3:].decode('ascii').strip().split('|')
            except UnicodeDecodeError:continue
            if len(parts)==23 and parts[3]=='MZF002' and parts[12] in ('0','1') and parts[13].isdigit():
                notifies.append({'time':sec+micro/1e6,'conn':conn,'on':int(parts[12]),'level':int(parts[13])})
    if i!=len(b):raise ValueError('trailing bytes')
    transitions=[]
    for r in notifies:
        key=(r['on'],r['level'])
        if not transitions or transitions[-1]['level']!=key[1] or transitions[-1]['on']!=key[0]:
            near=[x for x in writes if abs(x['time']-r['time'])<=5]
            transitions.append({'on':r['on'],'level':r['level'],'nearby_writes':len(near),
                                'nearby_write_opcodes':dict(Counter(w['op'] for w in near))})
    return {'all_att_opcodes':dict(op),'per_connection_att_opcodes':{k:dict(v) for k,v in by_conn.items()},
            'direction_opcode_counts':{k:dict(v) for k,v in directions.items()},
            'mzf002_notifications':len(notifies),'mzf002_transitions':transitions,
            'write_like_att_packets':len(writes),'write_like_att_opcodes':dict(Counter(w['op'] for w in writes)),
            'secrets_exposed':False,'device_write_performed':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pcap');args=p.parse_args()
    print(json.dumps(analyze(args.pcap),indent=2))
