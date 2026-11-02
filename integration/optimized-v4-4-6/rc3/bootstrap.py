#!/usr/bin/env python3
"""Restore the checksum-pinned RC3 CI/source kit from repository-owned chunks."""
from pathlib import Path
import hashlib,io,tarfile
H=Path(__file__).resolve().parent
EXPECTED='7800fd97e7c3e748e44e96486a435d8b5c477636e4e632bdaf43038a320608b2'
data=b''.join((H/('kit.tar.xz.part%02d'%i)).read_bytes() for i in range(6))
if hashlib.sha256(data).hexdigest()!=EXPECTED:raise SystemExit('RC3 kit checksum mismatch')
payload={}
with tarfile.open(fileobj=io.BytesIO(data),mode='r:xz') as archive:
    for info in archive:
        p=Path(info.name)
        if not info.isfile() or p.is_absolute() or '..' in p.parts or p.suffix not in {'.py','.c','.sh','.md','.json','.patch'} or info.size>2000000 or info.name in payload:
            raise SystemExit('Unexpected source-kit member')
        payload[info.name]=archive.extractfile(info).read()
if len(payload)!=23:raise SystemExit('Unexpected source-kit file count')
for name,body in payload.items():
    p=H/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body)
print('RC3_SOURCE_KIT_VERIFIED',EXPECTED,'files',len(payload),flush=True)
