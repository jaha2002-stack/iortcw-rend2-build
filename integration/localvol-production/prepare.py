"""Promote the user-validated runtime without changing its functional files."""

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import struct
import subprocess
import tarfile
from tempfile import TemporaryDirectory
import zipfile

BUILD_COMMIT = 'e5b1938884bc09abc1fe649bd0af854f41caf05f'
TESTED_SHA = '1d6c7b93157cc6f8b1856c0328498a86bab11fe217a79c4c69bbf668614e5caf'
SOURCE_INDEX_SHA = 'f46bb39dd4ff7f6d31564f3147ba22c72787d8c516c91d7b093f84cadfb980e8'
PATCH_SHA = '467854b3e2a32450968497d95f7404ce30343501ee0d6033e1189a7e957683db'
TAG = 'darkwolf-localvol-modes-235-clean-production-20261126'
ZIP_NAME = 'DarkWolf_Rend2_LocalVol_Modes_2_3_5_Clean_Production_Win64'
SOURCE_NAME = 'DarkWolf_Rend2_LocalVol_Modes_2_3_5_Exact_Renderer_Source'
DOC = Path(__file__).resolve().parent
REQUIRED_BINARIES = {
    'ioWolfSP.x64.exe', 'renderer_sp_rend2_x64.dll', 'renderer_sp_opengl1_x64.dll',
    'SDL264.dll', 'OpenAL64.dll', 'Main/cgame_sp_x64.dll',
    'Main/qagame_sp_x64.dll', 'Main/ui_sp_x64.dll',
}
VOLUMETRIC_SHADERS = (
    'volumetriclocal_fp', 'volumetriclocal_vp', 'volumetriclocal_upscale_fp',
    'volumetricsun_fp', 'volumetricsun_vp',
)
RUNTIME_SUFFIXES = {'.exe', '.dll', '.cfg', '.bat', '.glsl'}
BUNDLED_IMPORTS = {'sdl264.dll', 'openal64.dll'}
SYSTEM_IMPORTS = {
    'advapi32.dll', 'gdi32.dll', 'imm32.dll', 'kernel32.dll', 'msvcrt.dll',
    'ole32.dll', 'oleaut32.dll', 'psapi.dll', 'setupapi.dll', 'shell32.dll',
    'user32.dll', 'version.dll', 'winmm.dll', 'ws2_32.dll',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checksum_index(files):
    return ''.join(f'{digest(data)}  {name}\n' for name, data in sorted(files.items())).encode()


def unpack(path):
    files = {}
    names = set()
    root = None
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        for entry in archive.infolist():
            member = PurePosixPath(entry.filename)
            assert not member.is_absolute() and len(member.parts) >= 2, entry.filename
            assert '..' not in member.parts and '\\' not in entry.filename and ':' not in entry.filename
            assert not entry.is_dir() and (entry.external_attr >> 16) & 0o170000 != 0o120000
            root = root or member.parts[0]
            assert member.parts[0] == root
            relative = PurePosixPath(*member.parts[1:]).as_posix()
            assert relative.casefold() not in names, relative
            names.add(relative.casefold())
            files[relative] = archive.read(entry)
    return files


def inspect_binaries(staged_path, files, tested_manifest):
    binary_names = {name for name in files if PurePosixPath(name).suffix.lower() in {'.exe', '.dll'}}
    assert binary_names == REQUIRED_BINARIES
    audit = {}
    for name in sorted(binary_names):
        data = files[name]
        offset, = struct.unpack_from('<I', data, 0x3c)
        assert data[:2] == b'MZ' and data[offset:offset+4] == b'PE\0\0'
        machine, = struct.unpack_from('<H', data, offset + 4)
        magic, = struct.unpack_from('<H', data, offset + 24)
        flags, = struct.unpack_from('<H', data, offset + 22)
        assert (machine, magic) == (0x8664, 0x20b)
        assert bool(flags & 0x2000) == name.lower().endswith('.dll')
        path = staged_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        text = subprocess.check_output(['objdump', '-p', path], text=True)
        imports = {dll.lower() for dll in re.findall(r'^\s*DLL Name:\s*(\S+)', text, re.M)}
        assert imports <= BUNDLED_IMPORTS | SYSTEM_IMPORTS, (name, imports)
        previous = tested_manifest['architecture_and_imports'][name]
        assert digest(data) == previous['sha256'] and imports == {dll.lower() for dll in previous['imports']}
        if name.startswith('renderer_sp_'):
            assert re.search(r'\bGetRefAPI$', text, re.M), name
        sections = subprocess.check_output(['objdump', '-h', path], text=True)
        audit[name] = {**previous, 'embedded_debug_sections': len(re.findall(r'^\s*\d+\s+\.debug_', sections, re.M))}
    return audit


def inspect_configs(runtime):
    configs = {name.lower() for name in runtime if name.lower().endswith('.cfg')}
    executables = 0
    for name, data in runtime.items():
        if not name.lower().endswith(('.cfg', '.bat')):
            continue
        text = data.decode('utf-8-sig')
        for referenced in re.findall(r'\bexec\s+["\']?([\w.]+\.cfg)', text, re.I):
            assert f'main/{referenced.lower()}' in configs, (name, referenced)
        if name.lower().endswith('.bat'):
            assert 'ioWolfSP.x64.exe' in text and 'fs_homepath' in text
            executables += 1
        for var, value in re.findall(r'^\s*seta?\s+(\S*(?:debug|diag|audit|proof)\S*)\s+"?([^"\s]+)', text, re.I | re.M):
            assert value == '0', (name, var, value)
    assert len(configs) == 19 and executables == 3


def collect_source(source, renderer, expected_index_sha=SOURCE_INDEX_SHA):
    files = {}
    for path in (source / 'SP').rglob('*'):
        relative = path.relative_to(source)
        if 'build' in relative.parts[1:] or not path.is_file():
            continue
        assert not path.is_symlink(), path
        assert path.suffix.lower() not in {'.pk3', '.pk4', '.bsp', '.log', '.o', '.pdb'}, path
        files[relative.as_posix()] = path.read_bytes()
    index = checksum_index(files)
    assert len(files) == 1691 and digest(index) == expected_index_sha, (len(files), digest(index))
    shader_hashes = {}
    for shader in VOLUMETRIC_SHADERS:
        relative = f'SP/code/rend2/glsl/{shader}.glsl'
        data = files[relative]
        embedded = b''.join(line.rstrip() + b'\n' for line in data.splitlines())
        assert embedded in renderer, relative
        shader_hashes[relative] = digest(data)
    return files, index, shader_hashes


def write_zip(path, files, root=ZIP_NAME):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            entry = zipfile.ZipInfo(f'{root}/{name}', (2026, 11, 26, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)
    assert unpack(path) == files


def write_source_archive(path, files, root=SOURCE_NAME):
    with path.open('wb') as handle, gzip.GzipFile(filename='', mode='wb', fileobj=handle, mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode='w') as archive:
            for name, data in sorted(files.items()):
                entry = tarfile.TarInfo(f'{root}/{name}')
                entry.size = len(data)
                entry.mode = 0o755 if name.endswith('.sh') else 0o644
                archive.addfile(entry, io.BytesIO(data))
    with tarfile.open(path, 'r:gz') as archive:
        assert len(archive.getmembers()) == len(files)
        for member in archive:
            assert archive.extractfile(member).read() == files[member.name.removeprefix(f'{root}/')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tested', type=Path)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    assert digest(args.tested.read_bytes()) == TESTED_SHA
    patch = DOC.parent / 'localvol-lamps/fix.patch'
    assert digest(patch.read_bytes()) == PATCH_SHA
    files = unpack(args.tested)
    expected = {n: h for h, n in (line.split('  ', 1) for line in files['SHA256SUMS.txt'].decode().splitlines())}
    assert expected == {n: digest(data) for n, data in files.items() if n != 'SHA256SUMS.txt'}
    tested = json.loads(files['LOCALVOL_TEST_MANIFEST.json'])
    assert tested['build_commit'] == BUILD_COMMIT and tested['build_run'] == '45778124832'
    assert tested['covered_local_volumetric_modes'] == [2, 3, 5]
    runtime = {n: data for n, data in files.items() if PurePosixPath(n).suffix.lower() in RUNTIME_SUFFIXES}
    inspect_configs(runtime)
    with TemporaryDirectory() as directory:
        binary_audit = inspect_binaries(Path(directory), runtime, tested)

    source, source_index, shader_hashes = collect_source(args.source, files['renderer_sp_rend2_x64.dll'])
    args.output.mkdir(parents=True, exist_ok=True)
    source_archive = args.output / f'{SOURCE_NAME}.tar.gz'
    write_source_archive(source_archive, {
        **source,
        'SOURCE_SHA256SUMS.txt': source_index,
        'README_SOURCE_RU.md': (DOC / 'README_SOURCE_RU.md').read_bytes(),
        'integration/fix.patch': patch.read_bytes(),
    })
    docs_to_keep = {'LICENCE.md', 'docs/IFLC_COMMANDS_RU.md'}
    clean = {
        n: data for n, data in files.items()
        if n in runtime or n in docs_to_keep or n.startswith('docs/licenses/')
        or n.startswith('Main/') and n.endswith('_README.txt')
    }
    assert docs_to_keep <= clean.keys() and 'docs/licenses/SDL_copying.h' in clean
    manifest = {
        'status': 'CLEAN PRODUCTION — STABLE',
        'strategy': 'Clean Packaging & Promotion',
        'user_validation': {'accepted': True, 'scope': 'Local volumetric wave banding in modes 2, 3 and 5'},
        'production_tag': TAG,
        'promotion_commit': args.commit,
        'promotion_run': args.run,
        'tested_zip_sha256': TESTED_SHA,
        'tested_tag': 'dw-localvol-modes-2-3-5-fix-run43414829881',
        'tested_build_commit': BUILD_COMMIT,
        'tested_build_run': 45778124832,
        'tested_build_job_attempt': 1,
        'tested_release_run_attempt': 2,
        'donor_run': 43414829881,
        'integration_source_commit': '250669a231dc7bd571b4e2b3405c045f90ba64c1',
        'upstream': '438e7d413b5f7277187c35b032eb0ef9093ae778',
        'patch_sha256': PATCH_SHA,
        'source_index_sha256': SOURCE_INDEX_SHA,
        'exact_renderer_source_asset': source_archive.name,
        'exact_renderer_source_sha256': digest(source_archive.read_bytes()),
        'binary_and_import_audit': binary_audit,
        'embedded_shader_source_sha256': shader_hashes,
        'runtime_files_byte_identical': {n: digest(data) for n, data in sorted(runtime.items())},
        'removed_test_and_history_docs': sorted(set(files) - set(clean) - {'SHA256SUMS.txt'}),
        'runtime_recompiled': False,
    }
    report = DOC / 'PRODUCTION_RELEASE_FINALIZATION_REPORT_RU.md'
    clean.update({
        'README_RU.md': (DOC / 'README_RU.md').read_bytes(),
        'CHANGELOG_RU.md': (DOC / 'CHANGELOG_RU.md').read_bytes(),
        report.name: report.read_bytes(),
        'PRODUCTION_MANIFEST.json': (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode(),
    })
    assert all(clean[name] == data for name, data in runtime.items())
    assert not any(name.lower().endswith(('.pk3', '.pk4', '.pdb', '.log', '.o')) or
                   name.lower().startswith('main/dw_ai/') for name in clean)
    clean['SHA256SUMS.txt'] = checksum_index(clean)
    write_zip(args.output / f'{ZIP_NAME}.zip', clean)
    production_zip = args.output / f'{ZIP_NAME}.zip'
    publication = (
        '\n## Идентификация Production-артефактов\n\n'
        f'- SHA-256 окончательного ZIP `{digest(production_zip.read_bytes())}`.\n'
        f'- SHA-256 снимка исходников `{digest(source_archive.read_bytes())}`.\n'
        f'- Коммит продвижения `{args.commit}`.\n'
        f'- Запуск упаковки и публикации `{args.run}`. '
        f'[GitHub Actions](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/{args.run})\n'
    )
    (args.output / report.name).write_bytes(report.read_bytes() + publication.encode())
    (args.output / 'PRODUCTION_MANIFEST.json').write_bytes(clean['PRODUCTION_MANIFEST.json'])
    releases = {p.name: p.read_bytes() for p in args.output.iterdir() if p.is_file() and p.name != 'SHA256SUMS.txt'}
    (args.output / 'SHA256SUMS.txt').write_bytes(checksum_index(releases))
    print(f'PASS {len(runtime)} functional files, {len(binary_audit)} AMD64 binaries, '
          f'{len(shader_hashes)} embedded shaders, {len(source)} source files')
    print(f'PASS {len(clean)} production ZIP files. The tested runtime was preserved byte for byte.')


if __name__ == '__main__':
    main()
