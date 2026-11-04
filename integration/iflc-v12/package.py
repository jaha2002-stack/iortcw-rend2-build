#!/usr/bin/env python3
"""Full test distribution from exact Clean Production 41758201175."""
from pathlib import Path
import hashlib,json,subprocess,zipfile,io,os,tarfile
src=Path('source');ev=Path('evidence');out=Path('dist');out.mkdir(exist_ok=True)
base=ev/'clean-production.zip'
with base.open('wb') as f:subprocess.run(['gh','api','repos/jaha2002-stack/iortcw-rend2-build/actions/artifacts/13289146159/zip'],stdout=f,check=True)
assert hashlib.sha256(base.read_bytes()).hexdigest()=='4a422c28e17195c84df426ff2fb2339bd37545d4f4ea7104f794138c8cee8c82'
with zipfile.ZipFile(base) as z:raw=z.read(next(n for n in z.namelist() if n.endswith('DarkWolf_IFLC_V1.1_Clean_Production_Win64.zip')))
assert hashlib.sha256(raw).hexdigest()=='ed9551bb8bf931507c65103bcd7ac98da13c2df22885e5e9c761a6c21864abf0'
with zipfile.ZipFile(io.BytesIO(raw)) as z:
 assert z.testzip() is None
 entries={n.split('/',1)[1]:z.read(n) for n in z.namelist() if not n.endswith('/')}
accepted=json.loads(entries['RELEASE_MANIFEST.json']);assert accepted['packaging_run']=='41758201175'
code={p.relative_to(src).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (src/'SP/code').rglob('*') if p.is_file()}
before=json.loads((ev/'IFLC12_BASE_SHA256.json').read_text());changed=[k for k in sorted(set(code)|set(before)) if code.get(k)!=before.get(k)]
assert changed==['SP/code/rend2/tr_iflc_fixture.inc'],changed
bins=list((src/'SP/build').rglob('renderer_sp_rend2_x64.dll'));assert len(bins)==1;dll=bins[0].read_bytes()
for hook in (b'r_iflc12Legacy',b'r_iflc12CastleMask',b'dw_fl12_audit',b'dw_fl12_mode',b'IFLC12_OWNER',b'r_iflcFixtureTestBypass',b'r_iflcShadowAudit'):assert hook not in dll,hook
assert b'dw_fl_select' in dll and b'fixtureSelfCasters' in dll
entries['docs/base-41758201175/RELEASE_MANIFEST.json']=entries.pop('RELEASE_MANIFEST.json')
entries['docs/base-41758201175/README_RU.txt']=entries.pop('README_RU.txt')
entries.pop('SHA256SUMS.txt',None);entries['renderer_sp_rend2_x64.dll']=dll
entries['README_RU.txt']=('''DarkWolf IFLC V1.2 — исправление длинной рукояти факела / TEST
База: полный Clean Production Run #41758201175.
Изменён только алгоритм распознавания собственного крепления opt-in DLight.
Сначала применяется прежнее распознавание V1.1; при отказе отдельно проверяются
связная узкая рукоять под пламенем и её непрозрачный светящийся торец.
Стена, колонны, двери, чужие источники, FireVol, PCF и бюджеты не изменены.
Нет привязки к картам, ID или названиям материалов. У Crypt1 surface2933
ожидается fixtureSelfCasters=13 вместо 0: рукоять и непрозрачные угли.

Установка: закройте игру, сохраните прежнюю renderer_sp_rend2_x64.dll.
Для установленного #41758201175 достаточно заменить только эту DLL рядом с EXE.
Полный архив также содержит все прежние компоненты: они сохранены побитово.
Не удаляйте Main и не меняйте fs_homepath. Ваши CFG, firelights, MapLighting,
StaticPromote и сохранения не входят в архив и не перезаписываются.
Используйте прежний EXE/способ запуска. Новую команду исправления включать не надо.
/r_dwFireLightControl 1
/dw_fl_select
/dw_fl_info
Ранее сохранённые direct/radius/volume остаются прежними. Если проблемный факел
выключался временно: /dw_fl_set enabled 1, затем /dw_fl_save.

Castle: подвесной native-фонарь этой коррекцией не изменяется. Диагностические
отключения дна/решётки существуют только в изолированном TestLab, не в этой DLL.
Оценку правильности тени читайте в отдельном отчёте по реальным кадрам.
Никакие тени Castle не удалены лишь потому, что выглядят крупными.

Это отдельный тестовый кандидат, не замена опубликованного production-тега.
Компиляция и CPU-тесты не подменяют визуальную проверку. Изображения и журналы
Crypt1/Crypt2/Castle опубликованы отдельными артефактами того же Run.
Windows GPU/FPS не проверялись на компьютере пользователя.
''').encode('utf-8-sig')
manifest={'status':'TEST_CANDIDATE_PENDING_VISUAL_REVIEW','base_run':41758201175,'run':os.environ.get('GITHUB_RUN_ID'),'commit':os.environ.get('GITHUB_SHA'),'changed_source_files':changed,'renderer_sha256':hashlib.sha256(dll).hexdigest(),'unchanged_base_runtime':True,'new_production_cvars':[],'native_castle_lantern_changed':False,'diagnostic_hooks_in_shipped_dll':False}
entries['BUILD_STATUS.json']=(json.dumps(manifest,indent=2)+'\n').encode()
entries['IFLC12_SOURCE_PROOF.json']=(ev/'IFLC12_SOURCE_PROOF.json').read_bytes()
entries['SHA256SUMS.txt']=''.join(hashlib.sha256(v).hexdigest()+'  '+n+'\n' for n,v in sorted(entries.items())).encode()
name='DarkWolf_IFLC_V1.2_FROM_41758201175_Win64_TEST'
with zipfile.ZipFile(out/(name+'.zip'),'w',zipfile.ZIP_DEFLATED) as z:
 for n,v in sorted(entries.items()):z.writestr(name+'/'+n,v)
with zipfile.ZipFile(out/(name+'.zip')) as z:assert z.testzip() is None
with tarfile.open(out/'IFLC_V12_EXACT_SOURCE.tar.gz','w:gz') as t:
 t.add(src/'SP/code',arcname='SP/code');t.add(src/'SP/Makefile',arcname='SP/Makefile')
(ev/'IFLC12_SOURCE_SHA256.json').write_text(json.dumps(code,indent=2)+'\n')
(out/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file() and p.name!='SHA256SUMS.txt'))
print('FULL_TEST_PACKAGE_READY',name,manifest['renderer_sha256'])
