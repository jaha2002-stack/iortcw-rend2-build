"""Promote the accepted SunVol runtime without rebuilding it."""
from argparse import ArgumentParser
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
from tempfile import TemporaryDirectory

DOC = Path(__file__).resolve().parent
sys.path.insert(0, str(DOC.parent / 'localvol-production'))
from prepare import (RUNTIME_SUFFIXES, checksum_index, collect_source, digest, inspect_binaries,
                     inspect_configs, unpack, write_source_archive, write_zip)

BUILD_COMMIT = 'c7e13e20bda4fe6671f4fd16791b03247bb087b2'
BUILD_RUN = 45788582832
TESTED_SHA = 'f8eebd3bc2e6df0efa97132d8ff1bb7149e60c4bea5236660b180bec83760c75'
SOURCE_INDEX_SHA = '3f9ce111861ac4ec31b57382f98db9c9e8677b1caa20be991e074fcb1b422e3a'
PATCH_SHA = '64e90851328f373c0971cedb86cb78d034d62a5d271c843903cfe92967e57025'
PREVIOUS_SOURCE_SHA = '72ea6460b216e1f52d8bd755f52bc92be84779a47f60e0bf5e4b32aaa852c8c6'
TAG = 'darkwolf-sun-volumetric-silhouette-aa-clean-production-20261126'
ZIP_NAME = 'DarkWolf_Rend2_Sun_Volumetric_AA_Clean_Production_Win64'
SOURCE_NAME = 'DarkWolf_Rend2_Sun_Volumetric_AA_Exact_Renderer_Source'
RENDERER = 'renderer_sp_rend2_x64.dll'
CHANGED_SOURCE = {
    'SP/code/rend2/glsl/volumetricsun_fp.glsl',
    'SP/code/rend2/glsl/volumetricsun_vp.glsl',
    'SP/code/rend2/tr_backend.c', 'SP/code/rend2/tr_fbo.c',
    'SP/code/rend2/tr_glsl.c', 'SP/code/rend2/tr_local.h',
}


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('tested', type=Path)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--run', required=True)
    args = parser.parse_args()

    assert digest(args.tested.read_bytes()) == TESTED_SHA
    patch = DOC.parent / 'sun-volumetric-edge/fix.patch'
    assert digest(patch.read_bytes()) == PATCH_SHA
    subprocess.run(['git', '-C', args.source, 'apply', '--reverse', '--check', patch], check=True)

    files = unpack(args.tested)
    assert checksum_index({n: d for n, d in files.items() if n != 'SHA256SUMS.txt'}) == files['SHA256SUMS.txt']
    tested = json.loads(files['SUN_EDGE_TEST_MANIFEST.json'])
    assert tested['test_build_run'] == str(BUILD_RUN) and tested['test_build_commit'] == BUILD_COMMIT
    assert tested['patch_sha256'] == PATCH_SHA and tested['accepted_base_run'] == 45778124832
    assert tested['binary_audit'][RENDERER]['sha256'] == '0ebd4fa980087249346550c9f545bed0f7ed63e74844e11bd274b18bc804fe7b'

    runtime = {n: d for n, d in files.items() if PurePosixPath(n).suffix.lower() in RUNTIME_SUFFIXES}
    assert len(runtime) == 30
    inspect_configs(runtime)
    with TemporaryDirectory() as directory:
        audit = inspect_binaries(Path(directory), runtime, {'architecture_and_imports': tested['binary_audit']})

    source, index, shaders = collect_source(args.source, files[RENDERER], SOURCE_INDEX_SHA)
    prior_index = {n: h for h, n in (line.split('  ', 1) for line in
                   (args.source / 'SOURCE_SHA256SUMS.txt').read_text().splitlines())}
    assert source.keys() == prior_index.keys()
    assert {n for n, d in source.items() if digest(d) != prior_index[n]} == CHANGED_SOURCE

    args.output.mkdir(parents=True, exist_ok=True)
    source_path = args.output / f'{SOURCE_NAME}.tar.gz'
    write_source_archive(source_path, {
        **source,
        'SOURCE_SHA256SUMS.txt': index,
        'README_SOURCE_RU.md': (DOC / 'README_SOURCE_RU.md').read_bytes(),
        'integration/localvol-235.patch': (DOC.parent / 'localvol-lamps/fix.patch').read_bytes(),
        'integration/sun-volumetric-edge.patch': patch.read_bytes(),
    }, root=SOURCE_NAME)

    replaced_docs = {'README_RU.md', 'CHANGELOG_RU.md', 'SHA256SUMS.txt',
                     'SUN_EDGE_TECH_REPORT_RU.md', 'SUN_EDGE_TEST_MANIFEST.json',
                     'docs/BASE_PRODUCTION_MANIFEST.json'}
    assert replaced_docs <= files.keys()
    clean = {n: d for n, d in files.items() if n not in replaced_docs}
    assert all(clean[n] == data for n, data in runtime.items())
    assert {'LICENCE.md', 'docs/licenses/SDL_copying.h'} <= clean.keys()
    assert not any(n.lower().endswith(('.pk3', '.pk4', '.pdb', '.log', '.o')) or
                   n.lower().startswith('main/dw_ai/') for n in clean)
    manifest = {
        'status': 'CLEAN PRODUCTION — STABLE',
        'strategy': 'Clean Packaging & Promotion',
        'user_validation': {'accepted': True, 'scope': 'Sun volumetric silhouette aliasing with r_volumetricSun 1'},
        'production_tag': TAG,
        'promotion_commit': args.commit,
        'promotion_run': args.run,
        'tested_tag': 'dw-sun-volumetric-silhouette-aa-test-20261126',
        'tested_branch': 'fix/dw-sun-volumetric-silhouette-aa',
        'tested_build_commit': BUILD_COMMIT,
        'tested_build_run': BUILD_RUN,
        'tested_artifact': 15102136592,
        'tested_zip_sha256': TESTED_SHA,
        'previous_production_run': 45778124832,
        'previous_source_archive_sha256': PREVIOUS_SOURCE_SHA,
        'upstream': '438e7d413b5f7277187c35b032eb0ef9093ae778',
        'changed_sources_in_tested_run': sorted(CHANGED_SOURCE),
        'patch_sha256': PATCH_SHA,
        'source_index_sha256': SOURCE_INDEX_SHA,
        'exact_renderer_source_asset': source_path.name,
        'exact_renderer_source_sha256': digest(source_path.read_bytes()),
        'binary_and_import_audit': audit,
        'embedded_shader_source_sha256': shaders,
        'runtime_files_byte_identical': {n: digest(data) for n, data in sorted(runtime.items())},
        'replaced_or_archived_docs': sorted(replaced_docs),
        'runtime_recompiled': False,
    }
    report = DOC / 'PRODUCTION_RELEASE_FINALIZATION_REPORT_RU.md'
    clean.update({
        'README_RU.md': (DOC / 'README_RU.md').read_bytes(),
        'CHANGELOG_RU.md': (DOC / 'CHANGELOG_RU.md').read_bytes() + b'\n\n' + files['CHANGELOG_RU.md'],
        report.name: report.read_bytes(),
        'PRODUCTION_MANIFEST.json': (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode(),
    })
    clean['SHA256SUMS.txt'] = checksum_index(clean)
    production_zip = args.output / f'{ZIP_NAME}.zip'
    write_zip(production_zip, clean, root=ZIP_NAME)
    publication = (
        '\n## Идентификация Production-артефактов\n\n'
        f'- SHA-256 Production ZIP `{digest(production_zip.read_bytes())}`.\n'
        f'- SHA-256 архива исходников `{digest(source_path.read_bytes())}`.\n'
        f'- Коммит продвижения `{args.commit}`.\n'
        f'- Запуск упаковки и публикации `{args.run}`. '
        f'[GitHub Actions](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/{args.run})\n'
    )
    (args.output / report.name).write_bytes(report.read_bytes() + publication.encode())
    (args.output / 'PRODUCTION_MANIFEST.json').write_bytes(clean['PRODUCTION_MANIFEST.json'])
    release_files = {p.name: p.read_bytes() for p in args.output.iterdir() if p.is_file() and p.name != 'SHA256SUMS.txt'}
    (args.output / 'SHA256SUMS.txt').write_bytes(checksum_index(release_files))
    print(f'PASS {len(runtime)} unchanged runtime files, {len(audit)} AMD64 modules, '
          f'{len(shaders)} embedded shaders, {len(source)} source files, {len(clean)} ZIP entries')


if __name__ == '__main__':
    main()
