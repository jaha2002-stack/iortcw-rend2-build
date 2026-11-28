"""Create one diagnostic Win64 package over the verified Production runtime."""
from argparse import ArgumentParser
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory

DOCS = Path(__file__).resolve().parent
sys.path.insert(0, str(DOCS.parent / 'localvol-production'))
from prepare import (BUNDLED_IMPORTS, SYSTEM_IMPORTS, RUNTIME_SUFFIXES, VOLUMETRIC_SHADERS,
                     checksum_index, digest, inspect_binaries, inspect_configs, unpack, write_zip)

BASE_RUN = 45990828104
BASE_COMMIT = '77de4465581e9e104a6110a3cb97a37ee5a3d602'
BASE_ZIP = '1cdf83aed0a0d740b028a62797fce3238d8e02cddff793845505ead9656ebacb'
BASE_INDEX = 'c302ebf4887a78d3dae719b39f3636ad01775e483f4474c451e645ddd2a91715'
RENDERER = 'renderer_sp_rend2_x64.dll'
ENGINE = 'ioWolfSP_Diagnostics.x64.exe'
ADDED = {'SP/code/qcommon/dw_perf_main.inc', 'SP/code/qcommon/dw_perf_io.inc', 'SP/code/rend2/tr_dw_perf.inc'}
CHANGED = {'SP/code/qcommon/common.c'} | {f'SP/code/rend2/{name}' for name in (
    'tr_backend.c', 'tr_cmds.c', 'tr_flares.c', 'tr_init.c', 'tr_local.h', 'tr_main.c', 'tr_scene.c'
)}


def main():
    parser = ArgumentParser(description=__doc__)
    for name in ('baseline', 'engine', 'renderer', 'source', 'output'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--run', type=int, required=True)
    args = parser.parse_args()

    assert digest(args.baseline.read_bytes()) == BASE_ZIP
    base = unpack(args.baseline)
    assert base['SHA256SUMS.txt'] == checksum_index({n: d for n, d in base.items() if n != 'SHA256SUMS.txt'})
    production = json.loads(base['PRODUCTION_MANIFEST.json'])
    assert production['promotion_run'] == BASE_RUN and production['promotion_commit'] == BASE_COMMIT
    index = (args.source / 'SOURCE_SHA256SUMS.txt').read_bytes()
    assert digest(index) == BASE_INDEX
    indexed = dict((name, sha) for sha, name in (line.split('  ', 1) for line in index.decode().splitlines()))
    assert {name for name, old in indexed.items() if digest((args.source / name).read_bytes()) != old} == CHANGED
    source_paths = {p.relative_to(args.source).as_posix() for p in (args.source / 'SP').rglob('*')
                    if p.is_file() and p.relative_to(args.source / 'SP').parts[0] != 'build'}
    assert source_paths == indexed.keys() | ADDED
    runtime = {n: d for n, d in base.items() if Path(n).suffix.lower() in RUNTIME_SUFFIXES}
    assert len(runtime) == 30
    inspect_configs(runtime)

    renderer = args.renderer.read_bytes()
    engine = args.engine.read_bytes()
    assert b'DARKWOLF_PERF_DIR' in engine and b'DARKWOLF_PERF_DIR' in renderer
    assert renderer != runtime[RENDERER]
    for name in VOLUMETRIC_SHADERS:
        shader = (args.source / f'SP/code/rend2/glsl/{name}.glsl').read_bytes()
        assert b''.join(line.rstrip() + b'\n' for line in shader.splitlines()) in renderer, name

    expected = production['binary_and_import_audit']
    expected[RENDERER]['sha256'] = digest(renderer)
    runtime[RENDERER] = renderer
    with TemporaryDirectory() as directory:
        inspect_binaries(Path(directory), runtime, {'architecture_and_imports': expected})
    offset, = struct.unpack_from('<I', engine, 0x3c)
    assert engine[:2] == b'MZ' and engine[offset:offset + 4] == b'PE\x00\x00'
    assert struct.unpack_from('<H', engine, offset + 4) == (0x8664,)
    assert struct.unpack_from('<H', engine, offset + 24) == (0x20b,)
    imports = {name.lower() for name in re.findall(r'^\s*DLL Name:\s*(\S+)', subprocess.check_output(
        ['objdump', '-p', args.engine], text=True), re.M)}
    assert imports <= SYSTEM_IMPORTS | BUNDLED_IMPORTS, imports
    assert {name for name in runtime if runtime[name] != base[name]} == {RENDERER}

    files = dict(base)
    files.update(runtime)
    files[ENGINE] = engine
    for name in ['RUN_DARKWOLF_PERF.bat', 'DarkWolf_Performance.ps1', 'README_RU.md', 'PERFORMANCE_AUDIT_RU.md']:
        files[name] = (DOCS / name).read_bytes()
    files['docs/BASE_PRODUCTION_MANIFEST.json'] = files.pop('PRODUCTION_MANIFEST.json')
    files.pop('PRODUCTION_RELEASE_FINALIZATION_REPORT_RU.md')
    files['PERFORMANCE_TEST_MANIFEST.json'] = (json.dumps({
        'status': 'PERFORMANCE_DIAGNOSTIC',
        'base_run': BASE_RUN,
        'base_commit': BASE_COMMIT,
        'base_zip_sha256': BASE_ZIP,
        'base_source_index_sha256': BASE_INDEX,
        'diagnostic_run': args.run,
        'diagnostic_commit': args.commit,
        'patch_sha256': digest((DOCS / 'instrumentation.patch').read_bytes()),
        'source_paths': sorted(CHANGED | ADDED),
        'renderer_sha256': digest(renderer),
        'diagnostic_engine_sha256': digest(engine),
        'diagnostic_engine_imports': sorted(imports),
        'baseline_runtime_files_preserved': {name: digest(data) for name, data in runtime.items() if name != RENDERER},
    }, indent=2) + '\n').encode()
    files.pop('SHA256SUMS.txt')
    files['SHA256SUMS.txt'] = checksum_index(files)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_zip(args.output, files, root=args.output.stem)
    args.output.with_suffix('.zip.sha256').write_text(
        f'{digest(args.output.read_bytes())}  {args.output.name}\n', encoding='utf-8')
    print('Verified all shaders are unchanged in the source tree, 29 original runtime files, and two diagnostic PE binaries.')


if __name__ == '__main__':
    main()
