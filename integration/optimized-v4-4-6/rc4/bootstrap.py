#!/usr/bin/env python3
"""Restore the pinned, repository-owned RC4 source/test/release kit."""
from pathlib import Path
import base64, hashlib, io, tarfile
H = Path(__file__).resolve().parent
EXPECTED = '831232a932230d6ea29a09448d8be421314d2912657eff3f3bfa29df9f5ae91a'
NAMES = {'source_tools.py', 'test_rc4.py', 'audit.py', 'build.sh', 'run_smoke.py',
         'runtime_lifecycle.py', 'pipeline.py', 'rc4.patch', 'rc4-lock.json',
         'AUDIT_RC4.md', 'README_INSTALL_RU.md'}
encoded = ''.join((H / ('kit.part%02d.b64' % i)).read_text(encoding='ascii').strip() for i in range(6))
data = base64.b64decode(encoded, validate=True)
if hashlib.sha256(data).hexdigest() != EXPECTED:
    raise SystemExit('RC4 kit checksum mismatch')
payload = {}
with tarfile.open(fileobj=io.BytesIO(data), mode='r:xz') as archive:
    for member in archive:
        if member.name not in NAMES or not member.isfile() or member.size > 2000000 or member.name in payload:
            raise SystemExit('Unexpected RC4 kit member: ' + member.name)
        payload[member.name] = archive.extractfile(member).read()
if set(payload) != NAMES:
    raise SystemExit('Incomplete RC4 source kit')
for name, content in payload.items():
    (H / name).write_bytes(content)
print('RC4_SOURCE_KIT_VERIFIED', EXPECTED, 'files', len(payload), flush=True)
