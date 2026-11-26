"""Package the approved Win64 files with the new Rend2 DLL and test documentation."""

from argparse import ArgumentParser
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

DOCS = Path(__file__).resolve().parent
sys.path.insert(0, str(DOCS.parent / 'localvol-production'))
from prepare import (RUNTIME_SUFFIXES, checksum_index, digest, inspect_binaries, inspect_configs,
                     unpack, write_zip)

BASE_RUN = 45818977157
BASE_COMMIT = '7fde9422a937a0967b44cde626b06873a210ca8a'
BASE_ZIP_SHA = 'e262481aa80e09c1493553f16cc3ae80abe8445c3cc676010b0f1f93ee7e2a13'
BASE_SOURCE_SHA = '35548b1ea71619eda2ed4df35bd8feae12a0136b1a6cf9cbc22db830c9cc90c4'
RENDERER = 'renderer_sp_rend2_x64.dll'
SOURCE_CHANGES = {
    'SP/code/rend2/tr_backend.c',
    'SP/code/rend2/tr_local.h',
    'SP/code/rend2/tr_scene.c',
}


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('renderer', type=Path)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--run', type=int, required=True)
    args = parser.parse_args()

    assert digest(args.baseline.read_bytes()) == BASE_ZIP_SHA
    base = unpack(args.baseline)
    assert base['SHA256SUMS.txt'] == checksum_index({
        name: data for name, data in base.items() if name != 'SHA256SUMS.txt'
    })
    production = json.loads(base['PRODUCTION_MANIFEST.json'])
    assert production['promotion_run'] == BASE_RUN and production['promotion_commit'] == BASE_COMMIT
    assert production['exact_renderer_source_sha256'] == BASE_SOURCE_SHA

    current_source_check = (args.source / 'SOURCE_SHA256SUMS.txt').read_text().splitlines()
    source_index = {name: sha for sha, name in (line.split('  ', 1) for line in current_source_check)}
    assert len(source_index) == 1691
    assert {name for name, sha in source_index.items()
            if digest((args.source / name).read_bytes()) != sha} == SOURCE_CHANGES

    files = dict(base)
    rebuilt = args.renderer.read_bytes()
    assert rebuilt != base[RENDERER]
    for resource in ('volumetricsun_coverage', 'USE_SUN_MULTISAMPLE_DEPTH', 'tableLampJitter'):
        assert resource.encode() in rebuilt, resource
    files[RENDERER] = rebuilt
    runtime = {name: data for name, data in files.items() if Path(name).suffix.lower() in RUNTIME_SUFFIXES}
    assert len(runtime) == 30
    assert {name for name, data in runtime.items() if data != base[name]} == {RENDERER}
    inspect_configs(runtime)

    expected_audit = production['binary_and_import_audit']
    expected_audit[RENDERER]['sha256'] = digest(rebuilt)
    with TemporaryDirectory() as directory:
        audit = inspect_binaries(Path(directory), files, {'architecture_and_imports': expected_audit})

    files.pop('SHA256SUMS.txt')
    files.pop('PRODUCTION_RELEASE_FINALIZATION_REPORT_RU.md')
    files['docs/BASE_PRODUCTION_MANIFEST.json'] = files.pop('PRODUCTION_MANIFEST.json')
    files['README_RU.md'] = (DOCS / 'README_RU.md').read_bytes()
    files['CHANGELOG_RU.md'] = (
        '## Исправление переключения r_forceSun\n\n'
        '- Актуальность каскадных теней привязана к источнику солнца и команде отрисовки.\n'
        '- Предыдущие настройки и файлы игры сохранены. Заменена DLL Rend2.\n\n'
    ).encode() + base['CHANGELOG_RU.md']
    files['FORCESUN_TEST_MANIFEST.json'] = (json.dumps({
        'status': 'WIN64_TEST_CANDIDATE',
        'accepted_base_run': BASE_RUN,
        'accepted_base_commit': BASE_COMMIT,
        'base_production_zip_sha256': BASE_ZIP_SHA,
        'base_source_archive_sha256': BASE_SOURCE_SHA,
        'upstream': production['upstream'],
        'patch_sha256': digest((DOCS / 'fix.patch').read_bytes()),
        'source_files_changed': sorted(SOURCE_CHANGES),
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
