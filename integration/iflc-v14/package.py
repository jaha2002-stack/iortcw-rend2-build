#!/usr/bin/env python3
"""Separate V1.4 Windows TEST package; never replace accepted production."""
from pathlib import Path
import hashlib,io,json,os,struct,subprocess,tarfile,zipfile
src=Path('source');ev=Path('evidence');out=Path('dist');out.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
a=ev/'runtime13.zip'
with a.open('wb') as f:subprocess.run(['gh','api','repos/jaha2002-stack/iortcw-rend2-build/actions/artifacts/13305220146/zip'],stdout=f,check=True)
assert sha(a.read_bytes())=='80f8dd33718ecbd6eebd01ccfd3bfa49b38859e3776a3df666de5dc75ad130f3'
with zipfile.ZipFile(a) as z:raw=z.read(next(n for n in z.namelist() if n.endswith('_Win64_TEST.zip')))
assert sha(raw)=='54ed3a4007322f9298515bc68781854d379bcb4628f58410fea1b53e0ef5fa9a'
with zipfile.ZipFile(io.BytesIO(raw)) as z:
 assert z.testzip() is None
 entries={n.split('/',1)[1]:z.read(n) for n in z.namelist() if not n.endswith('/')}
old=entries.copy();dlls=list((src/'SP/build').rglob('renderer_sp_rend2_x64.dll'));assert len(dlls)==1;dll=dlls[0].read_bytes()
for marker in (b'IFLC14_VOLUME',b'IFLC14_BACKEND',b'IFLC14_SCENE',b'r_iflc13Electric',b'dw_fl13_audit',b'dw_fl12_mode',b'r_iflc12Legacy'):assert marker not in dll,marker
assert b'dw_fl_self_pick' in dll and b'ownBodySurfaces' in dll
entries['renderer_sp_rend2_x64.dll']=dll
for name in ('BUILD_STATUS.json','README_RU.txt'):
 if name in entries:entries['docs/base-v13/'+name]=entries.pop(name)
entries.pop('SHA256SUMS.txt',None)
readme='''DarkWolf IFLC V1.4 — Native Containment / Own Self-Shadow — Win64 TEST
База принятой линии: IFLC V1.2 #41772470237; исправление прожектора из V1.3
сохранено. Новые правки проверяются отдельно; production-тег не заменяется.

Установка: закрыть игру, сохранить renderer_sp_rend2_x64.dll и свои .iflc.
На существующей V1.3 заменить только renderer_sp_rend2_x64.dll рядом с EXE.
Сохранить прежний EXE/BAT, fs_homepath, MapLighting и StaticPromote.
Шейдер встроен: r_externalGLSL 0. Бюджеты и графические профили не повышены.

УТЕЧКИ
Новые пути архитектурного ограничения работают независимо от включения IFLC.
Режим r_dlightWorldContainment 2 распространяет захват на стационарные authored
и локальные физические источники, кроме уже распознанных прожекторов.
Закрытые brush-двери/платформы включены в архитектурный depth; движение меняет
ключ кэша. В синтетическом FireVol исправлены предварительное отсечение граней
и ближняя плоскость, добавлена независимая проверка полностью закрытого объёма.
Direct/RGB/радиус и художественная сила обычной тени не изменяются.
Это не доказательство отсутствия любой утечки: границы игровой приёмки
и реальные изображения см. в отдельном отчёте данного Run.

СОБСТВЕННАЯ ТЕНЬ ОГНЕННОГО СВЕТИЛЬНИКА
/r_dwFireLightControl 1
Навести прицел на пламя:
/dw_fl_select
/dw_fl_set selfshadow 0
/dw_fl_info
/dw_fl_save
0 = не отбрасывать тень собственного распознанного корпуса от своего света.
1 = вернуть исходное участие собственного корпуса в тени.
auto = вернуть прежнюю автоматическую политику IFLC V1.2.
Не путать с enabled: новый Direct включать ради selfshadow НЕ требуется.
Само пламя, свет, окружающая архитектура и тени от других источников остаются.

Если тело не распознано, команда явно отказывает, не удаляя случайную стену.
Не меняя выбранного огня, навести прицел на ЕГО металлическое/деревянное тело,
а не на стену, и выполнить /dw_fl_self_pick. При необходимости привязать ещё
одну отдельную часть этой же конструкции, затем /dw_fl_set selfshadow 0
и /dw_fl_save. Допускаются только небольшие подтверждённые мировые поверхности.
При неоднозначности/несовместимой геометрии исходные тени сохраняются.
Модели движущихся объектов и произвольные большие элементы карты не удаляются.

ПРОФИЛИ
Прежние файлы DW_IFLC 1 читаются. При сохранении явной selfshadow-настройки
используется DW_IFLC 2. Старый рендерер V1.2/V1.3 формат2 не понимает:
перед первым сохранением сделать резервную копию firelights/<map>.iflc.
Для отката вернуть старую DLL и резервные файлы профилей; не удалять Main.
Сброс /dw_fl_reset удаляет все индивидуальные настройки выбранного источника.
Для сброса только новой политики использовать selfshadow auto.

Это тестовый кандидат, не автоматическая замена production-базы.
Успех компиляции не равен визуальному PASS. Windows GPU/FPS пользователя
отдельно не измерены. Новые диагностические команды в DLL не включены.
'''
entries['README_RU.txt']=readme.replace('\n','\r\n').encode('utf-8-sig')
manifest={'status':'TEST_CANDIDATE','build_run':os.environ.get('GITHUB_RUN_ID'),'commit':os.environ.get('GITHUB_SHA'),'base_renderer_run':41793236028,'accepted_production_run':41772470237,'renderer_sha256':sha(dll),'new_production_cvars':[],'new_commands':['dw_fl_set selfshadow 0|1|auto','dw_fl_self_pick'],'profile_formats_read':[1,2],'profile_v2_rollback_requires_backup':True,'diagnostic_hooks_in_shipped_dll':False,'windows_gpu_fps':'NOT_TESTED','visual_review':'Separate real-game artifacts/report required'}
entries['BUILD_STATUS.json']=(json.dumps(manifest,indent=2)+'\n').encode();entries['IFLC14_SOURCE_PROOF.json']=(ev/'IFLC14_SOURCE_PROOF.json').read_bytes()
for name in entries:
 if name in old and name not in ('renderer_sp_rend2_x64.dll','README_RU.txt','BUILD_STATUS.json','SHA256SUMS.txt'):assert entries[name]==old[name]
for name,data in entries.items():
 if name.lower().endswith(('.exe','.dll')):
  assert data[:2]==b'MZ';off=struct.unpack_from('<I',data,0x3c)[0];assert data[off:off+4]==b'PE\0\0' and struct.unpack_from('<H',data,off+4)[0]==0x8664
entries['SHA256SUMS.txt']=''.join(sha(b)+'  '+n+'\n' for n,b in sorted(entries.items())).encode()
name='DarkWolf_IFLC_V1.4_FROM_V13_Win64_TEST';target=out/(name+'.zip')
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
 for n,b in sorted(entries.items()):z.writestr(name+'/'+n,b)
with zipfile.ZipFile(target) as z:assert z.testzip() is None and len(z.namelist())==len(entries)
with tarfile.open(out/'IFLC_V14_EXACT_SOURCE.tar.gz','w:gz') as t:
 t.add(src/'SP/code',arcname='SP/code');t.add(src/'SP/Makefile',arcname='SP/Makefile')
(out/'SHA256SUMS.txt').write_text(''.join(sha(p.read_bytes())+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file() and p.name!='SHA256SUMS.txt'))
print(json.dumps({'package':str(target),'bytes':target.stat().st_size,'sha256':sha(target.read_bytes()),'files':len(entries),'renderer_sha256':sha(dll)},indent=2),flush=True)
