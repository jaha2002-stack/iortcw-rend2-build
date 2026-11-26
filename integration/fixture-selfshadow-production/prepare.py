"""Promote the approved Win64 runtime and verify source and binary provenance."""

from argparse import ArgumentParser
import json
from pathlib import Path, PurePosixPath
import sys
from tempfile import TemporaryDirectory

DOCS = Path(__file__).resolve().parent
FIXTURE = DOCS.parent / 'fixture-selfshadow'
sys.path.insert(0, str(DOCS.parent / 'localvol-production'))
from prepare import (RUNTIME_SUFFIXES, checksum_index, collect_source, digest, inspect_binaries,
                     inspect_configs, unpack, write_source_archive, write_zip)

REPOSITORY = 'https://github.com/jaha2002-stack/iortcw-rend2-build'
BUILD_RUN = 45806188774
BUILD_COMMIT = '1713c867b7c87d682e4b12314a6d4be0ae19702f'
BASE_RUN = 45799720282
BASE_COMMIT = '88d667dcfd49e42910209fa9ad11f31a8bd96ebc'
UPSTREAM = '438e7d413b5f7277187c35b032eb0ef9093ae778'
TESTED_SHA = 'b92f73056b42c4c6df068e3d2ebe624b8a531bb064ddb3e6677850f437d86283'
BASE_ZIP_SHA = '3917b3718f62e7b57d4e272fb97480fa89497112e6c5ccc8d2e49e3f0e4b74d0'
BASE_SOURCE_SHA = 'bcc469c60955b3fe34f6b12452f5c5ce4f9fc4c6a521c6cce84264d03a769fbd'
PATCH_SHA = '5bd7273a1b7fd7fa72f685f8cdc55dfdbaf1c67bca8c82a02c74a911a26505d1'
SOURCE_INDEX_SHA = 'ac580605c6d7c4c72871f3d14f9b0cf77503adaef52514d97c3fd3c3cd46d496'
TAG = 'darkwolf-fixture-selfshadow-clean-production-20261126'
ZIP_NAME = 'DarkWolf_Rend2_Fixture_SelfShadow_Clean_Production_Win64'
SOURCE_NAME = 'DarkWolf_Rend2_Fixture_SelfShadow_Exact_Renderer_Source'
REPORT = 'PRODUCTION_RELEASE_FINALIZATION_REPORT_RU.md'
RENDERER = 'renderer_sp_rend2_x64.dll'
CHANGED_SOURCE = {
    f'SP/code/rend2/{name}' for name in (
        'tr_main.c', 'tr_local.h', 'tr_scene.c', 'tr_elss.inc', 'tr_iflc.inc', 'tr_iflc_self.inc',
    )
}
EXCLUDED_DOCS = {
    'README_RU.md', 'CHANGELOG_RU.md', 'SHA256SUMS.txt',
    'FIXTURE_SELFSHADOW_TECH_REPORT_RU.md', 'FIXTURE_SELFSHADOW_TEST_MANIFEST.json',
    'docs/BASE_PRODUCTION_MANIFEST.json',
}


def load_verified_zip(path, expected_sha):
    assert digest(path.read_bytes()) == expected_sha, path
    files = unpack(path)
    assert files['SHA256SUMS.txt'] == checksum_index({
        name: data for name, data in files.items() if name != 'SHA256SUMS.txt'
    }), path
    return files


def runtime_files(files):
    return {name: data for name, data in files.items()
            if PurePosixPath(name).suffix.lower() in RUNTIME_SUFFIXES}


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('tested', type=Path)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--run', required=True)
    args = parser.parse_args()

    tested = load_verified_zip(args.tested, TESTED_SHA)
    baseline = load_verified_zip(args.baseline, BASE_ZIP_SHA)
    build = json.loads(tested['FIXTURE_SELFSHADOW_TEST_MANIFEST.json'])
    assert int(build['test_build_run']) == BUILD_RUN and build['test_build_commit'] == BUILD_COMMIT
    assert build['accepted_base_run'] == BASE_RUN and build['accepted_base_commit'] == BASE_COMMIT
    assert build['upstream'] == UPSTREAM and build['base_production_zip_sha256'] == BASE_ZIP_SHA
    assert build['only_runtime_file_replaced'] == RENDERER
    assert tested['docs/BASE_PRODUCTION_MANIFEST.json'] == baseline['PRODUCTION_MANIFEST.json']
    patch = (FIXTURE / 'fix.patch').read_bytes()
    assert digest(patch) == PATCH_SHA == build['patch_sha256']

    runtime = runtime_files(tested)
    base_runtime = runtime_files(baseline)
    assert len(runtime) == 30 and runtime.keys() == base_runtime.keys()
    assert {name for name, data in runtime.items() if data != base_runtime[name]} == {RENDERER}
    inspect_configs(runtime)
    with TemporaryDirectory() as directory:
        audit = inspect_binaries(Path(directory), runtime, {'architecture_and_imports': build['binary_audit']})

    source, source_index, shaders = collect_source(args.source, runtime[RENDERER], SOURCE_INDEX_SHA)
    prior_index = {name: sha for sha, name in (
        line.split('  ', 1) for line in (args.source / 'SOURCE_SHA256SUMS.txt').read_text().splitlines()
    )}
    assert source.keys() == prior_index.keys()
    assert {name for name, data in source.items() if digest(data) != prior_index[name]} == CHANGED_SOURCE

    args.output.mkdir(parents=True, exist_ok=True)
    source_path = args.output / f'{SOURCE_NAME}.tar.gz'
    write_source_archive(source_path, {
        **source,
        'SOURCE_SHA256SUMS.txt': source_index,
        'README_SOURCE_RU.md': (DOCS / 'README_SOURCE_RU.md').read_bytes(),
        'integration/localvol-235.patch': (args.source / 'integration/localvol-235.patch').read_bytes(),
        'integration/sun-volumetric-edge.patch': (args.source / 'integration/sun-volumetric-edge.patch').read_bytes(),
        'integration/fixture-selfshadow.patch': patch,
    }, root=SOURCE_NAME)
    source_archive_sha = digest(source_path.read_bytes())

    assert EXCLUDED_DOCS <= tested.keys()
    clean = {name: data for name, data in tested.items() if name not in EXCLUDED_DOCS}
    assert {'LICENCE.md', 'docs/licenses/SDL_copying.h'} <= clean.keys()
    manifest = {
        'status': 'CLEAN PRODUCTION — STABLE',
        'strategy': 'Clean Packaging & Promotion',
        'approval': {'accepted': True, 'scope': 'Win64 ZIP from Actions Run 45806188774'},
        'production_tag': TAG,
        'promotion_commit': args.commit,
        'promotion_run': int(args.run),
        'tested_tag': 'dw-fixture-selfshadow-test-20261126',
        'tested_build_commit': BUILD_COMMIT,
        'tested_build_run': BUILD_RUN,
        'tested_artifact': 15108804696,
        'tested_release_asset': 795481097,
        'tested_zip_sha256': TESTED_SHA,
        'previous_production_run': BASE_RUN,
        'previous_production_commit': BASE_COMMIT,
        'previous_production_zip_sha256': BASE_ZIP_SHA,
        'previous_source_archive_sha256': BASE_SOURCE_SHA,
        'upstream': UPSTREAM,
        'changed_sources_in_tested_run': sorted(CHANGED_SOURCE),
        'patch_sha256': PATCH_SHA,
        'source_index_sha256': SOURCE_INDEX_SHA,
        'exact_renderer_source_asset': source_path.name,
        'exact_renderer_source_sha256': source_archive_sha,
        'binary_and_import_audit': audit,
        'embedded_shader_source_sha256': shaders,
        'runtime_files_byte_identical': {name: digest(data) for name, data in sorted(runtime.items())},
        'only_runtime_file_changed_from_previous_production': RENDERER,
        'runtime_recompiled': False,
    }
    heading = '## Собственная тень светильников · Clean Production'
    changelog = tested['CHANGELOG_RU.md'].decode().partition('\n')[2]
    test_instructions = (FIXTURE / 'README_RU.md').read_text(encoding='utf-8')
    verification = test_instructions.split('## Проверка в игре\n', 1)[1].split('\n\nИнструменты', 1)[0]
    technical_notes = tested['FIXTURE_SELFSHADOW_TECH_REPORT_RU.md'].decode().split(
        '## Причина и правка\n', 1)[1].split('\n## Проверки и границы', 1)[0].strip()
    report = f"""# Аудит выпуска DarkWolf Fixture Self-Shadow

## Источники

- Утверждённый Win64 ZIP собран в Run `{BUILD_RUN}` на коммите `{BUILD_COMMIT}`. SHA-256 `{TESTED_SHA}`. [Сборка]({REPOSITORY}/actions/runs/{BUILD_RUN})
- Production-пакет подготовлен в Run `{args.run}` на коммите `{args.commit}`. [Упаковка и публикация]({REPOSITORY}/actions/runs/{args.run})
- Предыдущий Production Run `{BASE_RUN}` даёт исходную точку для сравнения и отката. [Предыдущий run]({REPOSITORY}/actions/runs/{BASE_RUN})

## Результаты проверок

- Все {len(runtime)} файлов runtime совпадают с утверждённым ZIP побайтно. С предыдущим Production-пакетом совпадают {len(runtime) - 1} из {len(runtime)} файлов runtime. Изменился `{RENDERER}`.
- Проверены архитектура AMD64 и импорты {len(audit)} PE-модулей, ссылки на CFG, внутренние SHA-256 и состав нового ZIP.
- Снимок из {len(source)} исходных файлов воспроизведён из прежнего снимка и патча Fixture Self-Shadow. Изменения затрагивают {len(CHANGED_SOURCE)} файлов Rend2. {len(shaders)} встроенных GLSL-шейдеров сверены с DLL.
- Упаковка выполнена без повторной компиляции. Команды проверки ELSS и IFLC приведены в `docs/FIXTURE_SELFSHADOW_VERIFICATION_RU.md`.

## Изменения и область действия

{technical_notes}

Ручной выбор относится к геометрии BSP. Запечённые тени и отдельно движущиеся модели находятся вне области этого инструмента.
"""
    clean.update({
        'README_RU.md': (DOCS / 'README_RU.md').read_bytes(),
        'CHANGELOG_RU.md': f'{heading}\n{changelog}'.encode(),
        'docs/FIXTURE_SELFSHADOW_VERIFICATION_RU.md': f'# Проверка в игре\n{verification}\n'.encode(),
        REPORT: report.encode(),
        'PRODUCTION_MANIFEST.json': (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode(),
    })
    assert runtime_files(clean) == runtime
    assert not any(name.lower().endswith(('.pk3', '.pk4', '.bsp', '.pdb', '.log', '.o')) or
                   name.lower().startswith('main/dw_ai/') for name in clean)
    clean['SHA256SUMS.txt'] = checksum_index(clean)
    production_zip = args.output / f'{ZIP_NAME}.zip'
    write_zip(production_zip, clean, root=ZIP_NAME)
    (args.output / REPORT).write_text(
        report + f'\n## Контрольные суммы\n\n'
        f'- Production ZIP SHA-256 `{digest(production_zip.read_bytes())}`.\n'
        f'- Архив исходников SHA-256 `{source_archive_sha}`.\n', encoding='utf-8',
    )
    (args.output / 'PRODUCTION_MANIFEST.json').write_bytes(clean['PRODUCTION_MANIFEST.json'])
    release_files = {
        path.name: path.read_bytes() for path in args.output.iterdir()
        if path.is_file() and path.name != 'SHA256SUMS.txt'
    }
    (args.output / 'SHA256SUMS.txt').write_bytes(checksum_index(release_files))
    print(f'PASS {len(runtime)} byte-identical runtime files, {len(audit)} AMD64 modules, '
          f'{len(shaders)} embedded shaders, {len(source)} source files; no recompilation')


if __name__ == '__main__':
    main()
