from argparse import ArgumentParser
from pathlib import Path, PurePosixPath
from hashlib import sha256
import json
import re
import struct
import subprocess
import tempfile
import zipfile

parser = ArgumentParser(description='Package a Win64 candidate over the accepted Run 43414829881 ZIP.')
parser.add_argument('baseline', type=Path)
parser.add_argument('renderer', type=Path)
parser.add_argument('output', type=Path)
parser.add_argument('--commit', required=True)
parser.add_argument('--run', required=True)
args = parser.parse_args()
base, dll, output = args.baseline, args.renderer, args.output
output.parent.mkdir(parents=True, exist_ok=True)
renderer = 'renderer_sp_rend2_x64.dll'
archive_root = output.stem
digest = lambda data: sha256(data).hexdigest()

assert digest(base.read_bytes()) == '2066f01817327d8815caa6b8e47e293b0e407e55fac069aaa36090850ef2ab0d'
with zipfile.ZipFile(base) as z:
    assert z.testzip() is None
    baseline = {name.split('/', 1)[1]: z.read(name) for name in z.namelist() if not name.endswith('/')}
    assert len(baseline) == len(z.namelist())
baseline_sums = {rel: h for h, rel in (line.split('  ', 1) for line in baseline['SHA256SUMS.txt'].decode().splitlines())}
assert baseline_sums == {n: digest(d) for n, d in baseline.items() if PurePosixPath(n).name != 'SHA256SUMS.txt'}
assert digest(baseline[renderer]) == 'b333bfb9d451875c9d37221f6e6ed5b2d0091f207b15230f3409987bebea5eec'

def omitted(name):
    key = name.lower()
    return key.endswith(('.pk3', '.pk4')) or key.startswith('main/dw_ai/')

files = {n: d for n, d in baseline.items() if not omitted(n) and n != 'SHA256SUMS.txt'}
files[renderer] = dll.read_bytes()
assert files[renderer] != baseline[renderer]
for marker in ('stableLampJitter', 'DW_LAMP_CONTROL_V12', 'r_dwElectricPhysicalOwner', 'DWTR AI B2 V2.4.1:'):
    assert marker.encode() in files[renderer], marker

required = {'Main/cgame_sp_x64.dll', 'Main/qagame_sp_x64.dll', 'Main/ui_sp_x64.dll',
            'OpenAL64.dll', 'SDL264.dll', 'ioWolfSP.x64.exe', 'renderer_sp_opengl1_x64.dll', renderer}
assert required == {n for n in files if n.lower().endswith(('.exe', '.dll'))}
audit = {}
with tempfile.TemporaryDirectory(dir=output.parent) as td:
    root = Path(td)
    for name in sorted(required):
        path = root / PurePosixPath(name).name
        data = files[name]
        path.write_bytes(data)
        pe_offset, = struct.unpack_from('<I', data, 0x3c)
        assert data[:2] == b'MZ' and data[pe_offset:pe_offset+4] == b'PE\0\0', name
        machine, = struct.unpack_from('<H', data, pe_offset + 4)
        magic, = struct.unpack_from('<H', data, pe_offset + 24)
        flags, = struct.unpack_from('<H', data, pe_offset + 22)
        assert (machine, magic) == (0x8664, 0x20b), name
        assert bool(flags & 0x2000) == name.lower().endswith('.dll'), name

        def inspect():
            text = subprocess.check_output(['x86_64-w64-mingw32-objdump', '-p', path], text=True)
            imports = sorted(re.findall(r'^\s*DLL Name:\s*(\S+)', text, re.M), key=str.lower)
            exports = sorted(re.findall(r'^\s*\[\s*\d+\]\s+(?:\+base\[\s*\d+\]\s+[0-9a-fA-F]+\s+)?(\w+)\s*$', text, re.M))
            return imports, exports

        imports, exports = inspect()
        if name == renderer:
            path.write_bytes(baseline[name])
            original_imports, original_exports = inspect()
            assert list(map(str.lower, imports)) == list(map(str.lower, original_imports))
            assert exports == original_exports and 'GetRefAPI' in exports, (sorted(set(exports)-set(original_exports)), sorted(set(original_exports)-set(exports)))
        else:
            assert data == baseline[name]
        audit[name] = {'architecture': 'AMD64 PE32+', 'sha256': digest(data), 'imports': imports, 'export_count': len(exports), 'GetRefAPI': 'GetRefAPI' in exports}

files['README_LOCALVOL_TEST_RU.txt'] = Path(__file__).with_name('README_LOCALVOL_TEST_RU.txt').read_bytes()
files['CHANGELOG_LOCALVOL_RU.md'] = Path(__file__).with_name('CHANGELOG_RU.md').read_bytes()
files['LOCALVOL_TEST_MANIFEST.json'] = (json.dumps({
    'status': 'WIN64_TEST_CANDIDATE',
    'base_run': 43414829881,
    'previous_mode5_release_run': 45774590836,
    'covered_local_volumetric_modes': [2, 3, 5],
    'build_commit': args.commit,
    'build_run': args.run,
    'accepted_source_run': 43411054498,
    'accepted_source_commit': '250669a231dc7bd571b4e2b3405c045f90ba64c1',
    'base_artifact': 14030454225,
    'base_zip_sha256': digest(base.read_bytes()),
    'base_renderer_sha256': digest(baseline[renderer]),
    'renderer_sha256': digest(files[renderer]),
    'only_replaced_binary': renderer,
    'omitted_base_files': sorted(n for n in baseline if omitted(n)),
    'architecture_and_imports': audit,
    'in_game_acceptance': 'PENDING',
}, ensure_ascii=False, indent=2) + '\n').encode()
files['SHA256SUMS.txt'] = ''.join(f'{digest(d)}  {n}\n' for n, d in sorted(files.items())).encode()
temporary = output.with_suffix('.zip.tmp')
with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name, data in sorted(files.items()):
        z.writestr(f'{archive_root}/{name}', data)

with zipfile.ZipFile(temporary) as z:
    assert z.testzip() is None
    actual = {n.removeprefix(archive_root + '/'): z.read(n) for n in z.namelist()}
    assert actual == files
    assert not any(omitted(n) for n in actual)
    assert all(actual[n] == d for n, d in baseline.items() if not omitted(n) and n not in (renderer, 'SHA256SUMS.txt'))
temporary.replace(output)
output.with_name('pe-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
output.with_suffix('.zip.sha256').write_text(f'{digest(output.read_bytes())}  {output.name}\n')
print(f'PASS ZIP {len(files)} files, {len(required)} AMD64 PE, {sum(map(omitted, baseline))} exclusions')
print(f'PASS 7 inherited EXE/DLL byte-identical, renderer imports and exports match baseline')
print(f'{digest(output.read_bytes())}  {output.name}')
