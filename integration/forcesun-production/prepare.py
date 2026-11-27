"""Promote the approved Win64 runtime and verify source and binary provenance."""

from argparse import ArgumentParser
import json
from pathlib import Path, PurePosixPath
import sys
from tempfile import TemporaryDirectory

DOCS = Path(__file__).resolve().parent
FIX = DOCS.parent / 'forcesun-transition'
sys.path.insert(0, str(DOCS.parent / 'localvol-production'))
from prepare import (RUNTIME_SUFFIXES, checksum_index, collect_source, digest, inspect_binaries,
                     inspect_configs, unpack, write_source_archive, write_zip)

REPOSITORY = 'https://github.com/jaha2002-stack/iortcw-rend2-build'
BUILD_RUN = 45835840244
BUILD_COMMIT = '30a77cb8b0ae7410fc4796adcee8ed6751626b06'
BASE_RUN = 45818977157
BASE_COMMIT = '7fde9422a937a0967b44cde626b06873a210ca8a'
UPSTREAM = '438e7d413b5f7277187c35b032eb0ef9093ae778'
TESTED_SHA = 'a23b7980c4828e614052aa19a93d382dfd05ad1b491b9fc5c1588e3dfbe5dd60'
BASE_ZIP_SHA = 'e262481aa80e09c1493553f16cc3ae80abe8445c3cc676010b0f1f93ee7e2a13'
BASE_SOURCE_SHA = '35548b1ea71619eda2ed4df35bd8feae12a0136b1a6cf9cbc22db830c9cc90c4'
PATCH_SHA = '44e460a08e1ee3c572eb65cb60759423d2174a4ca12eccded2e334a4f9326165'
DLIGHT_PATCH_SHA = 'a369d5a48520309436680fa3a8dd3ee421359a5d43770fc0724c0aae220761e4'
SOURCE_INDEX_SHA = '13f27e8ed16538f0480594429045c8decfb6e7b778096b38fdd3e42a351a5104'
TAG = 'darkwolf-forcesun-dlight-cubemap-clean-production-20261127'
ZIP_NAME = 'DarkWolf_Rend2_ForceSun_Dlight_Cubemap_Clean_Production_Win64'
SOURCE_NAME = 'DarkWolf_Rend2_ForceSun_Dlight_Cubemap_Exact_Renderer_Source'
REPORT = 'PRODUCTION_RELEASE_FINALIZATION_REPORT_RU.md'
RENDERER = 'renderer_sp_rend2_x64.dll'
CHANGED_SOURCE = {
    f'SP/code/rend2/{name}' for name in (
        'tr_backend.c', 'tr_local.h', 'tr_scene.c', 'tr_shade.c',
    )
}
EXCLUDED_DOCS = {
    'README_RU.md', 'CHANGELOG_RU.md', 'SHA256SUMS.txt',
    'FORCESUN_TEST_MANIFEST.json',
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
    build = json.loads(tested['FORCESUN_TEST_MANIFEST.json'])
    assert int(build['test_build_run']) == BUILD_RUN and build['test_build_commit'] == BUILD_COMMIT
    assert build['accepted_base_run'] == BASE_RUN and build['accepted_base_commit'] == BASE_COMMIT
    assert build['upstream'] == UPSTREAM and build['base_production_zip_sha256'] == BASE_ZIP_SHA
    assert build['only_runtime_file_replaced'] == RENDERER
    assert tested['docs/BASE_PRODUCTION_MANIFEST.json'] == baseline['PRODUCTION_MANIFEST.json']
    assert build['base_source_archive_sha256'] == BASE_SOURCE_SHA
    assert set(build['source_files_changed']) == CHANGED_SOURCE
    cascade_patch = (FIX / 'fix.patch').read_bytes()
    dlight_patch = (FIX / 'dlight-cubemap.patch').read_bytes()
    assert digest(cascade_patch) == PATCH_SHA == build['patch_sha256']
    assert digest(dlight_patch) == DLIGHT_PATCH_SHA == build['dlight_cubemap_patch_sha256']

    runtime = runtime_files(tested)
    base_runtime = runtime_files(baseline)
    assert len(runtime) == 30 and runtime.keys() == base_runtime.keys()
    assert {name for name, data in runtime.items() if data != base_runtime[name]} == {RENDERER}
    assert build['unchanged_runtime_sha256'] == {
        name: digest(data) for name, data in runtime.items() if name != RENDERER
    }
    assert tested['docs/FIXTURE_SELFSHADOW_VERIFICATION_RU.md'] == baseline['docs/FIXTURE_SELFSHADOW_VERIFICATION_RU.md']
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
        'integration/fixture-selfshadow.patch': (args.source / 'integration/fixture-selfshadow.patch').read_bytes(),
        'integration/forcesun-csm-transition.patch': cascade_patch,
        'integration/forcesun-dlight-cubemap.patch': dlight_patch,
    }, root=SOURCE_NAME)
    source_archive_sha = digest(source_path.read_bytes())

    assert EXCLUDED_DOCS <= tested.keys()
    clean = {name: data for name, data in tested.items() if name not in EXCLUDED_DOCS}
    assert {'LICENCE.md', 'docs/licenses/SDL_copying.h'} <= clean.keys()
    manifest = {
        'status': 'CLEAN PRODUCTION — STABLE',
        'strategy': 'Clean Packaging & Promotion',
        'approval': {
            'accepted': True,
            'scope': 'Owner confirmed that the wall stripes disappeared in Win64 Run 45835840244',
        },
        'production_tag': TAG,
        'promotion_commit': args.commit,
        'promotion_run': int(args.run),
        'tested_tag': 'dw-forcesun-dlight-cubemap-test-20261126',
        'tested_build_commit': BUILD_COMMIT,
        'tested_build_run': BUILD_RUN,
        'tested_artifact': 15125246888,
        'tested_release_asset': 796196167,
        'tested_zip_sha256': TESTED_SHA,
        'previous_production_run': BASE_RUN,
        'previous_production_commit': BASE_COMMIT,
        'previous_production_zip_sha256': BASE_ZIP_SHA,
        'previous_source_archive_sha256': BASE_SOURCE_SHA,
        'upstream': UPSTREAM,
        'changed_sources_in_tested_run': sorted(CHANGED_SOURCE),
        'applied_patch_sha256': {
            'forcesun-csm-transition.patch': PATCH_SHA,
            'forcesun-dlight-cubemap.patch': DLIGHT_PATCH_SHA,
        },
        'source_index_sha256': SOURCE_INDEX_SHA,
        'exact_renderer_source_asset': source_path.name,
        'exact_renderer_source_sha256': source_archive_sha,
        'binary_and_import_audit': audit,
        'embedded_shader_source_sha256': shaders,
        'runtime_files_byte_identical': {name: digest(data) for name, data in sorted(runtime.items())},
        'only_runtime_file_changed_from_previous_production': RENDERER,
        'runtime_recompiled': False,
    }
    heading = '## r_forceSun и точечный свет · Clean Production'
    changelog = tested['CHANGELOG_RU.md'].decode().partition('\n')[2]
    changed_sources = ', '.join(f'`{Path(name).name}`' for name in sorted(CHANGED_SOURCE))
    report = f"""# Аудит выпуска DarkWolf r_forceSun и точечных теней

## Источники

- Утверждённый Win64 ZIP собран в Run `{BUILD_RUN}` на коммите `{BUILD_COMMIT}`. SHA-256 `{TESTED_SHA}`. [Сборка]({REPOSITORY}/actions/runs/{BUILD_RUN})
- Production-пакет подготовлен в Run `{args.run}` на коммите `{args.commit}`. [Упаковка и публикация]({REPOSITORY}/actions/runs/{args.run})
- Предыдущий Production Run `{BASE_RUN}` даёт исходную точку для сравнения и отката. [Предыдущий run]({REPOSITORY}/actions/runs/{BASE_RUN})

## Результаты проверок

- Все {len(runtime)} файлов runtime совпадают с утверждённым ZIP побайтно. С предыдущим Production-пакетом совпадают {len(runtime) - 1} из {len(runtime)} файлов runtime. Изменился `{RENDERER}`.
- Проверены архитектура AMD64 и импорты {len(audit)} PE-модулей, ссылки на CFG, внутренние SHA-256 и состав нового ZIP.
- Снимок из {len(source)} исходных файлов воспроизведён из прежнего снимка и двух патчей r_forceSun. Изменения затрагивают {changed_sources}. {len(shaders)} встроенных GLSL-шейдеров сверены с DLL.
- Упаковка выполнена без повторной компиляции. Команды проверки ELSS и IFLC приведены в `docs/FIXTURE_SELFSHADOW_VERIFICATION_RU.md`.

## Изменения и область действия

Владелец подтвердил исчезновение полос на стене при проверке Win64-сборки Run `{BUILD_RUN}`.
Проход точечного освещения сбрасывает параметры непрямого света предыдущего материала перед чтением кубической карты точечной тени.
Рендерер обновляет каскады при смене источника солнца и использует готовые каскады в соответствующих проходах.
В исходной сборке проверены переключение источников, восстановление состояния точечного света и варианты GLSL.
"""
    clean.update({
        'README_RU.md': (DOCS / 'README_RU.md').read_bytes(),
        'CHANGELOG_RU.md': f'{heading}\n{changelog}'.encode(),
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
