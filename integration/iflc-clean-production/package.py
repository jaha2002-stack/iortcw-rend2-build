#!/usr/bin/env python3
"""Package the accepted V1.1, without rebuilding or changing any game code.

All inputs are pinned GitHub artifacts with verified SHA256. Runtime files and
five quality profiles come from the complete accepted base; only rend2 is
replaced. TestLab code is not executed or packaged. This is a release assembly
and integrity check, NOT a new visual or Windows performance test.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import struct
import subprocess
import tarfile
import zipfile

REPO = 'jaha2002-stack/iortcw-rend2-build'
UPSTREAM = '438e7d413b5f7277187c35b032eb0ef9093ae778'
ACCEPTED_COMMIT = '9834c53c1b97984f40a04657f7278f539aa15379'
DLL_SHA = '2177779114b0edf0c327e09ba8bafda04d0569e721b1a7ac08237521c7a5029b'
TAG = 'darkwolf-iflc-v1.1-clean-production-20261104'
NAME = 'DarkWolf_IFLC_V1.1_Clean_Production_Win64'
INPUTS = {
    'base': (13079039927, 'a9effc51c683a2f5417e3fc116f73da447a07a9182cb0a438009a479ff9b9f6b'),
    'candidate': (13267868062, '9ef54ed73bb333f9e1bc2c6e9c765a07741b3f1deea358b0ea8293129b0e92ca'),
    'source': (13266298036, '185613e04e60fbe5cf931ba8f2e4a2a95c57dfec4715295812040276e4d15dad'),
}
PROFILES = ('PERFORMANCE', 'BALANCED', 'QUALITY', 'HIGH', 'ULTRA')
FORBIDDEN = (b'r_iflcFixtureTestBypass', b'dw_fl_test_audit', b'r_iflcShadowAudit',
             b'IFLC_SHADOW_AUDIT shot=', b'IFLC11_OWNER map=')
SYSTEM_DLLS = {'advapi32.dll','kernel32.dll','msvcrt.dll','psapi.dll','shell32.dll',
               'user32.dll','winmm.dll','ws2_32.dll','gdi32.dll','imm32.dll','ole32.dll',
               'oleaut32.dll','setupapi.dll','version.dll'}

README = '''DarkWolf IFLC V1.1 — FINAL CLEAN PRODUCTION
Windows x64 / Return to Castle Wolfenstein Single Player
Дата фиксации: 4 ноября 2026 года.

ПОЛНЫЙ КОМПЛЕКТ
Это полный комплект движка, а не патч с одной DLL: ioWolfSP.x64.exe,
оба рендерера, cgame/qagame/ui, SDL264/OpenAL64, пять профилей качества,
принятый дополнительный PK3 и команды IFLC. Лицензионные игровые pak*.pk3
в поставку не входят; используются ваши существующие игровые ресурсы.

КАКОЙ КОД ЗАФИКСИРОВАН
Полный runtime-комплект: Clean Production #41297344177.
Принятая линия рендерера: #41408153237 (Fire World PCF4x4 V1.4),
затем IFLC V1 и IFLC V1.1, итоговый Run #41710067608.
DLL V1.1 включена побитово, без перекомпиляции. Все остальные игровые
бинарники и пять профилей также сохранены побитово из полного baseline.
Новые изменения игрового кода в этом релизе не делались. Это окончательная
компоновка принятого результата, а не новая экспериментальная версия.

ПРИНЯТЫЙ ОБЪЁМ ИСПРАВЛЕНИЯ
IFLC выбирает один стационарный источник огня и независимо регулирует
Direct, Radius и Fire Volumetric, сохраняет параметры по карте.
V1.1 убирает дополнительный большой силуэт собственного компактного
настенного крепления только из двух теневых захватов СВОЕГО opt-in Direct.
Крепление остаётся видимым и отбрасывает тени от других источников.
Алгоритм не содержит имён карт и номеров поверхностей. На неподтверждённой
геометрии исходные тени сохраняются: это не обещание исправления всех
разновидностей ламп, напольных чаш или любого теневого дефекта игры.
Native/promoted свет и synthetic FireVol не получают эту новую политику.

СОХРАНЕНО
PCF4x4 V1.4, Bloom v2 HDR Pyramid, ToneMap/Exposure, частицы, Sun/Local/Fire
Volumetric, SSGI, CSM Guard, принятые Texture/Material V2, CAS, осторожный
model-only A2C, нейтральный LUT и исправления принятой базовой линии.
Лимиты не повышены: 32 DLight / 32 StaticPromote и 3 ordinary shadow slots.
Не включены отклонённые Fire Motion V1.5–V1.7, новые PCPS/worklamp ветки,
PBR, Bloom v3 и диагностические вставки IFLC TestLab.

ОБНОВЛЕНИЕ СУЩЕСТВУЮЩЕЙ ИГРЫ — РЕКОМЕНДУЕМЫЙ ПУТЬ
1. Закройте игру. Сохраните резервную копию текущих бинарников.
2. Скопируйте содержимое папки релиза в корень рабочей установки,
   объединяя Main с существующей Main, а не удаляя её.
3. Продолжайте запускать игру ПРЕЖНИМ способом и с прежним fs_homepath.
   В архиве нет autoexec.cfg, wolfconfig.cfg, сохранений, maplighting,
   StaticPromote или firelights: ваши данные не перезаписываются.
4. Сохранённые firelights/<map>.iflc совместимы с V1.1 без конвертации.
5. Если IFLC ещё не включён: /exec DW_IFLC_V11_ENABLE.cfg.
   Это включает только IFLC, не меняя графические параметры.
Не удаляйте и не меняйте homepath ради обновления. Для проверки текущего
каталога используйте /fs_homepath. При смене папки установки перенесите
свои пользовательские данные либо явно укажите прежний homepath.

НОВАЯ УСТАНОВКА / НОВЫЙ ЗАПУСКАТЕЛЬ
Распакуйте комплект и положите собственные RTCW pak*.pk3 в Main.
RUN_DARKWOLF_IFLC_CLEAN.bat использует существующий локальный homepath
DW_IFLC_Clean_Home, затем DW_TM_Fidelity_FINAL_Clean_Home, затем
DW_September_FourWeek_Home. Если их нет, создаёт DW_IFLC_Clean_Home.
Можно передать точный прежний homepath первым аргументом BAT.
Существующий homepath не инициализируется и не перенастраивается.
Только при СОЗДАНИИ нового homepath один раз применяется чистый стартовый
CFG: принятой базовый visual + Sun/Fire, production FireVol fixture path,
IFLC=1, r_forceSun=1, r_dlightMode=2. Диагностика не включается.
При запуске через прежний EXE/BAT действуют ваши сохранённые значения;
скомпилированный default IFLC остаётся 0, как у принятой DLL.
Старые два BAT сохранены без изменения для совместимости.

ПЯТЬ ПРОФИЛЕЙ — БЕЗ ИЗМЕНЕНИЯ ПРЕЖНИХ ЗНАЧЕНИЙ
/exec DW_HDR16F_V1_PERFORMANCE.cfg
/exec DW_HDR16F_V1_BALANCED.cfg
/exec DW_HDR16F_V1_QUALITY.cfg
/exec DW_HDR16F_V1_HIGH.cfg
/exec DW_HDR16F_V1_ULTRA.cfg
После выбора: /vid_restart. Профили не применяются автоматически поверх
существующих настроек. SSGI и остальные эффекты регулируются прежними
командами; новые скрытые коррекции экспозиции или радиусов не добавлены.
При необходимости отдельно включить именно production FireVol fixture
path: /exec DW_IFLC_FIREVOL_PRODUCTION.cfg. Это не запускает диагностику.

БЫСТРЫЙ ПРИМЕР IFLC
/r_dwFireLightControl 1
/dw_fl_select
/dw_fl_info
Для route=VOLUME_ONLY: /dw_fl_set enabled 1
/dw_fl_set direct 1.80
/dw_fl_set radius 1.30
/dw_fl_set volume 1.00
/dw_fl_save
При неоднозначном выборе: /dw_fl_next.
Сброс выбранного: /dw_fl_reset, затем /dw_fl_save.
Отключить IFLC без удаления профилей: /r_dwFireLightControl 0.
fixtureSelfCasters=0 означает, что компактное настенное крепление не
подтверждено; это не отключение теней и не ошибка сохранения.
Полное описание команд: docs/IFLC_COMMANDS_RU.md.

ПРИЁМКА И ПРОВЕРКИ
Пользователь принял изображения Crypt1/Crypt2 и запросил Clean Production.
Основание: принятый Run #41710067608; 346 CPU-проверок, 74 кадра Crypt1
и 47 кадров Crypt2. В этом packaging run заново проверяются хеши исходников,
совпадение DLL, полный состав, PE x64/imports, отсутствие IFLC test hooks,
неизменность профилей, целостность ZIP и полный индекс SHA256.
Новый визуальный прогон и измерение FPS на Windows GPU не заявляются.
Статус CLEAN_PRODUCTION означает фиксацию принятой версии, а не новое
доказательство отсутствия любого дефекта на любой карте.

ИСХОДНИКИ И ЛИЦЕНЗИИ
Точный архив исходников V1.1 опубликован отдельно с этим релизом.
LICENCE.md — исходная лицензия ioRTCW; SDL notice находится в docs/licenses.
Исторические README/manifest baseline перенесены в docs/history/base;
они описывают прежние этапы и не заменяют текущий RELEASE_MANIFEST.json.
SHA256SUMS.txt содержит контрольные суммы всех остальных файлов пакета.
'''

LAUNCHER = r'''@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if not exist "ioWolfSP.x64.exe" exit /b 1
if not exist "renderer_sp_rend2_x64.dll" exit /b 1
set "DW_HOME=%CD%\DW_IFLC_Clean_Home"
if not exist "%DW_HOME%" (
  if exist "%CD%\DW_TM_Fidelity_FINAL_Clean_Home" (
    set "DW_HOME=%CD%\DW_TM_Fidelity_FINAL_Clean_Home"
  ) else if exist "%CD%\DW_September_FourWeek_Home" (
    set "DW_HOME=%CD%\DW_September_FourWeek_Home"
  )
)
if not "%~1"=="" set "DW_HOME=%~f1"
set "DW_INIT="
if not exist "%DW_HOME%" set "DW_INIT=+exec DW_IFLC_CLEAN_STARTUP.cfg"
if not exist "%DW_HOME%\Main" mkdir "%DW_HOME%\Main"
if not exist "%DW_HOME%\Main" exit /b 1
"%CD%\ioWolfSP.x64.exe" +set fs_basepath "%CD%" +set fs_homepath "%DW_HOME%" +set cl_renderer rend2 +set r_renderer rend2 +set com_recommendedSet 1 %DW_INIT%
exit /b %errorlevel%
'''
CONFIGS = {
    'DW_IFLC_V11_ENABLE.cfg': '// Enable only IFLC. Existing per-map profiles and graphics remain unchanged.\nseta r_dwFireLightControl "1"\n',
    'DW_IFLC_V11_DISABLE.cfg': '// Bypass only IFLC without deleting any saved profile.\nseta r_dwFireLightControl "0"\n',
    'DW_IFLC_FIREVOL_PRODUCTION.cfg': '// Accepted production fixture path, no TestLab controls.\nseta r_volumetricFire "1"\nseta r_volumetricFireV07Mode "2"\nseta r_volumetricFireSourceMode "2"\nseta r_volumetricFireMode "2"\nseta r_volumetricFireMaxActive "8"\n',
    'DW_IFLC_CLEAN_STARTUP.cfg': '// NEW home only; never auto-apply over an existing user home.\nexec DW_SEPTEMBER_FOURWEEK_VISUAL_BASE.cfg\nexec DW_SUN3_FIRE_E_PRODUCTION.cfg\nexec DW_IFLC_FIREVOL_PRODUCTION.cfg\nexec DW_IFLC_V11_ENABLE.cfg\nseta r_externalGLSL "0"\n',
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def download(url: str, path: Path, auth: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    args = ['curl','--fail','--silent','--show-error','--location','--retry','3','--max-time','180']
    if auth:
        token = os.environ.get('GH_TOKEN', '')
        require(bool(token), 'GH_TOKEN is required to fetch pinned artifacts')
        # curl strips Authorization on cross-host redirects (no --location-trusted).
        args += ['--header', 'Authorization: Bearer ' + token]
    args += ['--output', str(path), url]
    result = subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    require(result.returncode == 0, 'Download failed for pinned input: ' + path.name)


def unpack(data: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        require(archive.testzip() is None, 'ZIP CRC mismatch')
        output = {}
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            p = PurePosixPath(entry.filename)
            require(not p.is_absolute() and '..' not in p.parts and '\\' not in entry.filename,
                    'Unsafe archive path')
            require(entry.filename not in output, 'Duplicate ZIP member')
            output[entry.filename] = archive.read(entry)
        return output


def one(files: dict[str, bytes], suffix: str) -> bytes:
    matches = [v for k,v in files.items() if k.endswith(suffix)]
    require(len(matches) == 1, 'Expected one archive member: ' + suffix)
    return matches[0]


def put(root: Path, name: str, data: bytes) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs', type=Path, default=Path('release-inputs'))
    parser.add_argument('--output', type=Path, default=Path('dist'))
    parser.add_argument('--fetch', action='store_true')
    args = parser.parse_args()
    args.inputs.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    blobs = {}
    for key,(artifact,digest) in INPUTS.items():
        path = args.inputs / (key + '.zip')
        if not path.exists() and args.fetch:
            download(f'https://api.github.com/repos/{REPO}/actions/artifacts/{artifact}/zip', path, True)
        require(path.exists(), 'Missing input: ' + key)
        raw = path.read_bytes()
        require(sha(raw) == digest, 'Pinned input SHA256 mismatch: ' + key)
        blobs[key] = unpack(raw)

    baseline = unpack(one(blobs['base'], '_Win64.zip'))
    prefix = next(iter(baseline)).split('/')[0] + '/'
    require(all(k.startswith(prefix) for k in baseline), 'Baseline has multiple roots')
    baseline = {k[len(prefix):]:v for k,v in baseline.items()}
    accepted = unpack(one(blobs['candidate'], '_Win64_TEST.zip'))
    dll = accepted['renderer_sp_rend2_x64.dll']
    require(sha(dll) == DLL_SHA, 'Accepted renderer mismatch')
    status = json.loads(accepted['BUILD_STATUS.json'])
    require(status['commit'] == ACCEPTED_COMMIT and status['build_run'] == '41710067608', 'Wrong V1.1 build')
    require(all(marker not in dll for marker in FORBIDDEN), 'Diagnostic hooks found in renderer')
    require(all(marker in dll for marker in (b'dw_fl_select',b'r_dwFireLightControl',b'fixtureSelfCasters')), 'IFLC features missing')

    source_archive = one(blobs['source'], 'IFLC_V11_EXACT_SOURCE.tar.gz')
    manifest = json.loads(one(blobs['source'], 'IFLC_V11_SOURCE_SHA256.json'))
    with tarfile.open(fileobj=io.BytesIO(source_archive), mode='r:gz') as archive:
        code = {m.name:archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}
    actual = {n:sha(v) for n,v in code.items() if n.startswith('SP/code/')}
    require(actual == manifest and len(actual) == 1649, 'Corresponding source manifest mismatch')
    require(all(marker not in code['SP/code/rend2/tr_iflc_fixture.inc'] for marker in FORBIDDEN), 'Test source in archive')
    require(b'crypt1' not in code['SP/code/rend2/tr_iflc_fixture.inc'] and b'crypt2' not in code['SP/code/rend2/tr_iflc_fixture.inc'], 'Map-specific IFLC correction')

    license_path = args.inputs / 'LICENCE.md'
    if not license_path.exists() and args.fetch:
        download(f'https://raw.githubusercontent.com/iortcw/iortcw/{UPSTREAM}/LICENCE.md', license_path)
    license_data = license_path.read_bytes()
    git_blob = b'blob ' + str(len(license_data)).encode() + b'\0' + license_data
    require(hashlib.sha1(git_blob).hexdigest() == '746a2556e25ad97946f19e51f5ff82e1e303c5a5', 'Upstream licence mismatch')

    stage = args.output / NAME
    require(not stage.exists(), 'Output staging directory already exists; use a new output directory')
    stage.mkdir()
    base_map = {}
    for name, raw in baseline.items():
        if name == 'renderer_sp_rend2_x64.dll':
            continue
        dest = 'docs/history/base/' + name if name.startswith('docs/') or name.startswith('README') else name
        put(stage, dest, raw)
        base_map[name] = {'path':dest, 'sha256':sha(raw)}
    put(stage,'renderer_sp_rend2_x64.dll',dll)
    put(stage,'README_RU.txt',README.replace('\n','\r\n').encode('utf-8-sig'))
    put(stage,'RUN_DARKWOLF_IFLC_CLEAN.bat',LAUNCHER.replace('\n','\r\n').encode('ascii'))
    put(stage,'LICENCE.md',license_data)
    put(stage,'docs/licenses/SDL_copying.h',code['SP/code/SDL2/include/SDL_copying.h'])
    put(stage,'docs/IFLC_COMMANDS_RU.md',accepted['README_COMMANDS_V1_RU.md'])
    # Preserve the original candidate proofs as historical input, never relabel them.
    for name in ('BUILD_STATUS.json','IFLC_SOURCE_PROOF.json','IFLC_V11_SOURCE_PROOF.json','README_V11_RU.md'):
        put(stage,'docs/accepted-v11/'+name,accepted[name])
    for name,text in CONFIGS.items():
        put(stage,'Main/'+name,text.replace('\n','\r\n').encode('ascii'))

    required = ('ioWolfSP.x64.exe','renderer_sp_rend2_x64.dll','renderer_sp_opengl1_x64.dll',
                'SDL264.dll','OpenAL64.dll','Main/cgame_sp_x64.dll','Main/qagame_sp_x64.dll','Main/ui_sp_x64.dll')
    pe_results = {}
    shipped = {p.name.lower() for p in stage.rglob('*.dll')}
    for name in required:
        path = stage/name
        raw = path.read_bytes()
        require(raw[:2] == b'MZ', 'Missing PE header: '+name)
        offset = struct.unpack_from('<I',raw,0x3c)[0]
        require(raw[offset:offset+4] == b'PE\0\0' and struct.unpack_from('<H',raw,offset+4)[0] == 0x8664
                and struct.unpack_from('<H',raw,offset+24)[0] == 0x20b, 'Not PE32+ x64: '+name)
        text = subprocess.check_output(['objdump','-p',str(path)],text=True)
        imports = re.findall(r'DLL Name:\s*(\S+)', text)
        require(all(x.lower() in shipped|SYSTEM_DLLS for x in imports), 'Missing non-system dependency: '+name)
        pe_results[name] = {'sha256':sha(raw),'size':len(raw),'imports':imports,'x64':True,
                            'origin_run':41710067608 if name.endswith('rend2_x64.dll') else 41297344177}
    for name,record in base_map.items():
        require(sha((stage/record['path']).read_bytes()) == record['sha256'], 'Baseline file changed: '+name)
    profile_hashes = {}
    for profile in PROFILES:
        name = 'Main/DW_HDR16F_V1_' + profile + '.cfg'
        require((stage/name).read_bytes() == baseline[name], 'Quality profile changed')
        profile_hashes[profile] = sha(baseline[name])

    # Resolve nested exec commands, ensuring fresh-home settings remain within budgets.
    def resolve(name: str, stack: tuple[str,...] = ()) -> dict[str,str]:
        require(name not in stack, 'CFG exec cycle')
        text = (stage/'Main'/name).read_text()
        values = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            match = re.fullmatch(r'exec\s+(\S+)',line)
            if match:
                values.update(resolve(match[1],stack+(name,)))
                continue
            match = re.fullmatch(r'seta?\s+(\S+)\s+"([^"\n]*)"',line)
            require(bool(match),'Unvalidated CFG command: '+line)
            values[match[1].lower()] = match[2]
        return values
    fresh = resolve('DW_IFLC_CLEAN_STARTUP.cfg')
    expected = {'r_dwfirelightcontrol':'1','r_dlightmode':'2','r_forcesun':'1',
                'r_dlightshadowmaxlights':'3','r_staticpromotemaxlights':'32',
                'r_volumetricfirev07mode':'2','r_volumetricfiresourcemode':'2',
                'r_volumetricfiremaxactive':'8','r_volumetriclocal':'1','r_externalglsl':'0'}
    require(all(fresh.get(k)==v for k,v in expected.items()), 'Fresh startup settings mismatch')
    require(all(value=='0' for key,value in fresh.items() if any(x in key for x in ('diag','proof','debug','marker'))), 'Diagnostics enabled by fresh startup')
    for p in stage.rglob('*'):
        if p.is_file():
            lower = p.relative_to(stage).as_posix().lower()
            require(p.name.lower() not in ('wolfconfig.cfg','autoexec.cfg'), 'User settings would be overwritten')
            require(not re.match(r'main/(firelights|maplighting|staticpromote|save|profiles)/',lower), 'User data in runtime package')
            require(not re.search(r'/(?:sp_)?pak\d+\.pk3$',lower), 'Retail assets in runtime package')

    release = {
        'status':'CLEAN_PRODUCTION_USER_ACCEPTED', 'date':'2026-11-04',
        'packaging_run':os.environ.get('GITHUB_RUN_ID','local-verification'),
        'packaging_commit':os.environ.get('GITHUB_SHA','local-verification'),
        'tag':TAG, 'accepted_renderer_run':41710067608, 'accepted_renderer_commit':ACCEPTED_COMMIT,
        'accepted_base_run':41408153237, 'complete_runtime_base_run':41297344177,
        'assembly_mode':'BINARY_FREEZE_NO_RECOMPILE_NO_SOURCE_CHANGES',
        'renderer_sha256':DLL_SHA, 'source_files_verified':len(actual),
        'diagnostic_iflc_hooks_present':False, 'quality_profiles_unchanged':profile_hashes,
        'other_baseline_files_byte_identical':len(base_map), 'baseline_file_mapping':base_map,
        'runtime_files':pe_results, 'fresh_home_config':fresh,
        'existing_user_data_policy':'No user CFG/profiles/save files packaged; retain existing launch method and fs_homepath.',
        'acceptance':'User accepted the existing Crypt1/Crypt2 screenshots and requested final Clean Production on 2026-11-04.',
        'inherited_tests':{'run':41710067608,'cpu_assertions_passed':346,'crypt1_frames':74,'crypt2_frames':47},
        'new_visual_run':False, 'windows_gpu_fps_benchmark':'NOT_PERFORMED',
        'scope':'Geometry-qualified wall-mounted opt-in VOLUME_ONLY Direct only; not all lamp types.',
        'inputs':{key:{'artifact_id':value[0],'sha256':value[1]} for key,value in INPUTS.items()},
    }
    put(stage,'RELEASE_MANIFEST.json',(json.dumps(release,ensure_ascii=False,indent=2)+'\n').encode())
    entries = {p.relative_to(stage).as_posix():p.read_bytes() for p in stage.rglob('*') if p.is_file()}
    sums = ''.join(sha(data)+'  '+name+'\n' for name,data in sorted(entries.items())).encode()
    put(stage,'SHA256SUMS.txt',sums)
    runtime_zip = args.output/(NAME+'.zip')
    with zipfile.ZipFile(runtime_zip,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(stage.rglob('*')):
            if not p.is_file():
                continue
            info = zipfile.ZipInfo(NAME+'/'+p.relative_to(stage).as_posix(),(2026,11,4,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info,p.read_bytes())
    check = unpack(runtime_zip.read_bytes())
    require(len(check)==len(entries)+1, 'Final ZIP file count mismatch')
    for name,data in entries.items():
        require(check[NAME+'/'+name]==data,'Final ZIP content mismatch: '+name)
    source_asset = args.output/'DarkWolf_IFLC_V1.1_Exact_Source.zip'
    source_asset.write_bytes((args.inputs/'source.zip').read_bytes())
    (args.output/'RELEASE_MANIFEST.json').write_bytes((stage/'RELEASE_MANIFEST.json').read_bytes())
    notes = '# DarkWolf IFLC V1.1 — Clean Production\n\n'+README
    (args.output/'RELEASE_NOTES_RU.md').write_text(notes,encoding='utf-8')
    assets = (runtime_zip,source_asset,args.output/'RELEASE_MANIFEST.json',args.output/'RELEASE_NOTES_RU.md')
    (args.output/'SHA256SUMS.txt').write_text(''.join(sha(p.read_bytes())+'  '+p.name+'\n' for p in assets))
    print(json.dumps({'status':release['status'],'runtime_zip':str(runtime_zip),
        'runtime_zip_sha256':sha(runtime_zip.read_bytes()),'runtime_zip_bytes':runtime_zip.stat().st_size,
        'files':len(check),'renderer_sha256':DLL_SHA,'source_files_verified':len(actual),
        'inherited_runtime_files_verified':len(base_map),'profiles_verified':len(PROFILES),
        'pe_modules_verified':len(required),'new_game_code':False},indent=2),flush=True)


if __name__ == '__main__':
    main()
