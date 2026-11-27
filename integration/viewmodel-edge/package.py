"""Package the approved Win64 files with the new Rend2 DLL and test documentation."""

from argparse import ArgumentParser
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

DOCS = Path(__file__).resolve().parent
sys.path.insert(0, str(DOCS.parent / 'localvol-production'))
from prepare import (RUNTIME_SUFFIXES, VOLUMETRIC_SHADERS, checksum_index, digest,
                     inspect_binaries, inspect_configs, unpack, write_zip)

BASE_RUN = 45953757143
BASE_COMMIT = 'f577f184e629426880a374616428848f64e8bb29'
BASE_ZIP_SHA = '3701374b08f7fa9bd6fa7795f3161130b112c85a1417d2ddb56f0f0ffc58aca5'
BASE_SOURCE_SHA = 'c83d0bbcddd66be007dbc8c9392986a3926f13adc4140499bdb027be67fe96c7'
RENDERER = 'renderer_sp_rend2_x64.dll'
SOURCE_CHANGES = {
    'SP/code/rend2/tr_backend.c',
    'SP/code/rend2/tr_local.h',
    'SP/code/rend2/tr_fbo.c',
    'SP/code/rend2/tr_glsl.c',
    'SP/code/rend2/tr_init.c',
    'SP/code/rend2/tr_shade.c',
    'SP/Makefile',
}
NEW_SHADER = 'SP/code/rend2/glsl/viewmodeledge_fp.glsl'


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('renderer', type=Path)
    parser.add_argument('source', type=Path)
    parser.add_argument('accepted_index', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--run', type=int, required=True)
    args = parser.parse_args()

    assert digest(args.baseline.read_bytes()) == BASE_ZIP_SHA
    base = unpack(args.baseline)
    assert base['SHA256SUMS.txt'] == checksum_index({
        name: data for name, data in base.items() if name != 'SHA256SUMS.txt'
    })
    production = json.loads(base['LOCALVOL_EDGE_TEST_MANIFEST.json'])
    assert production['test_build_run'] == BASE_RUN and production['test_build_commit'] == BASE_COMMIT
    assert production['base_source_archive_sha256'] == BASE_SOURCE_SHA

    current_source_check = args.accepted_index.read_text().splitlines()
    source_index = {name: sha for sha, name in (line.split('  ', 1) for line in current_source_check)}
    assert len(source_index) == 1691
    assert {name for name, sha in source_index.items()
            if digest((args.source / name).read_bytes()) != sha} == SOURCE_CHANGES

    source_paths = {path.relative_to(args.source).as_posix() for path in (args.source / 'SP').rglob('*')
                    if path.is_file() and path.relative_to(args.source / 'SP').parts[0] != 'build'}
    assert source_paths - source_index.keys() == {NEW_SHADER}

    files = dict(base)
    rebuilt = args.renderer.read_bytes()
    assert rebuilt != base[RENDERER]
    for define in (b'#define USE_LOCAL_MULTISAMPLE_COVERAGE', b'#define USE_SUN_MULTISAMPLE_DEPTH'):
        assert define in rebuilt, define
    embedded_shaders = {}
    for shader in (*VOLUMETRIC_SHADERS, 'viewmodeledge_fp'):
        path = f'SP/code/rend2/glsl/{shader}.glsl'
        content = (args.source / path).read_bytes()
        embedded = b''.join(line.rstrip() + b'\n' for line in content.splitlines())
        assert embedded in rebuilt, path
        embedded_shaders[path] = digest(content)
    files[RENDERER] = rebuilt
    runtime = {name: data for name, data in files.items() if Path(name).suffix.lower() in RUNTIME_SUFFIXES}
    assert len(runtime) == 30
    assert {name for name, data in runtime.items() if data != base[name]} == {RENDERER}
    inspect_configs(runtime)

    expected_audit = production['binary_audit']
    expected_audit[RENDERER]['sha256'] = digest(rebuilt)
    with TemporaryDirectory() as directory:
        audit = inspect_binaries(Path(directory), files, {'architecture_and_imports': expected_audit})

    files.pop('SHA256SUMS.txt')
    files['docs/BASE_LOCALVOL_MANIFEST.json'] = files.pop('LOCALVOL_EDGE_TEST_MANIFEST.json')
    files['README_RU.md'] = (DOCS / 'README_RU.md').read_bytes()
    files['CHANGELOG_RU.md'] = (
        '## Сглаживание силуэта оружия от первого лица\n\n'
        '- Фильтр учитывает покрытие видимой геометрии оружия при HDR и MSAA.\n'
        '- Для сравнения на лету используется `r_viewmodelEdgeAA 0/1`.\n\n'
    ).encode() + base['CHANGELOG_RU.md']
    files['VIEWMODEL_EDGE_TEST_MANIFEST.json'] = (json.dumps({
        'status': 'WIN64_TEST_CANDIDATE',
        'accepted_base_run': BASE_RUN,
        'accepted_base_commit': BASE_COMMIT,
        'accepted_zip_sha256': BASE_ZIP_SHA,
        'base_source_archive_sha256': BASE_SOURCE_SHA,
        'upstream': production['upstream'],
        'patch_sha256': digest((DOCS / 'fix.patch').read_bytes()),
        'source_files_changed': sorted(SOURCE_CHANGES | {NEW_SHADER}),
        'embedded_shader_source_sha256': embedded_shaders,
        'test_build_commit': args.commit,
        'test_build_run': args.run,
        'only_runtime_file_replaced': RENDERER,
        'unchanged_runtime_sha256': {name: digest(data) for name, data in runtime.items() if name != RENDERER},
        'binary_audit': audit,
    }, ensure_ascii=False, indent=2) + '\n').encode()

    assert not any(name.lower().endswith(('.pk3', '.pk4', '.bsp', '.log', '.pdb', '.o')) or
                   name.lower().startswith('main/dw_ai/') for name in files)
    files['SHA256SUMS.txt'] = checksum_index(files)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_zip(args.output, files, root=args.output.stem)
    args.output.with_suffix('.zip.sha256').write_text(
        f'{digest(args.output.read_bytes())}  {args.output.name}\n', encoding='utf-8',
    )
    print(f'PASS {len(runtime) - 1} unchanged runtime files and {len(audit)} AMD64 modules')


if __name__ == '__main__':
    main()
