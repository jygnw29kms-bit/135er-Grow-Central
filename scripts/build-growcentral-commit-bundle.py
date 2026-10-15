#!/usr/bin/env python3
"""Build a Linux-safe Grow-Central deployment archive from one exact Git commit."""
from __future__ import annotations
import argparse, hashlib, subprocess, tarfile
from pathlib import Path

TEXT_SUFFIXES={'.py','.sh','.js','.css','.html','.json','.yml','.yaml','.toml','.ini','.conf','.service'}
TEXT_NAMES={'Dockerfile','Makefile'}

def git(*args: str) -> bytes:
    return subprocess.check_output(['git',*args])

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('commit')
    ap.add_argument('output',type=Path)
    args=ap.parse_args()
    commit=git('rev-parse','--verify',f'{args.commit}^{{commit}}').decode().strip()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(['git','archive','--format=tar.gz','-o',str(args.output),commit],check=True)
    checked=0
    with tarfile.open(args.output,'r:gz') as tf:
        for member in tf.getmembers():
            if not member.isfile():
                continue
            path=Path(member.name)
            if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in TEXT_NAMES:
                continue
            archived=tf.extractfile(member).read()
            blob=git('show',f'{commit}:{member.name}')
            if b'\r\n' in archived:
                raise SystemExit(f'CRLF forbidden in Linux bundle: {member.name}')
            if archived != blob:
                raise SystemExit(f'Git blob mismatch in bundle: {member.name}\narchive={sha256(archived)}\nblob={sha256(blob)}')
            checked+=1
    if checked == 0:
        raise SystemExit('No Linux text files validated; refusing empty validation set')
    print(f'commit={commit}')
    print(f'validated_text_files={checked}')
    print(f'sha256={sha256(args.output.read_bytes())}')
    print(f'output={args.output}')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
