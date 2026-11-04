#!/usr/bin/env python3
from pathlib import Path
import hashlib,io,json,os,struct,subprocess,tarfile,zipfile
src=Path('source');ev=Path('evidence');out=Path('dist');out.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
a=ev/'v14_runtime_artifact.zip'
with a.open('wb') as f:subprocess.run(['gh','api','repos/jaha2002-stack/iortcw-rend2-build/actions/artifacts/13310079645/zip'],stdout=f,check=True)
with zipfile.ZipFile(a) as z:
 candidates=[n for n in z.namelist() if n.endswith('_Win64_TEST.zip')];assert len(candidates)==1,candidates;raw=z.read(candidates[0])
with zipfile.ZipFile(io.BytesIO(raw)) as z:
 assert z.testzip() is None
 entries={n.split('/',1)[1]:z.read(n) for n in z.namelist() if not n.endswith('/')}
old=entries.copy();assert sha(entries['renderer_sp_rend2_x64.dll'])=='9051d549812a29413d0930847066ba8cab0797bfb984ef1488e486aaee740b66'
dlls=list((src/'SP/build').rglob('renderer_sp_rend2_x64.dll'));assert len(dlls)==1;dll=dlls[0].read_bytes()
for marker in (b'IFLC15_STATE',b'IFLC14_VOLUME',b'IFLC14_BACKEND',b'dw_proofShot',b'r_iflc14TargetMask'):assert marker not in dll,marker
for marker in (b'dw_fl_self_pick',b'bound exact body surface',b'ownBodySurfaces'):assert marker in dll,marker
entries['renderer_sp_rend2_x64.dll']=dll
for name in ('BUILD_STATUS.json','README_RU.txt'):
 if name in entries:entries['docs/base-v14/'+name]=entries.pop(name)
entries.pop('SHA256SUMS.txt',None)
readme='''DarkWolf IFLC V1.5 — Exact Body Self-Shadow — Win64 TEST
Основа: V1.4 Run #41808242270. Нативные containment-исправления V1.4 и
прожектор V1.3 сохранены; V1.5 изменяет только ручную привязку собственного
корпуса огненного источника. GLSL, PCF4x4, бюджеты и профили качества не менялись.

Установка для проверки: закрыть игру, сохранить старую renderer_sp_rend2_x64.dll
и папку firelights, затем заменить только renderer_sp_rend2_x64.dll рядом с EXE.
Сохранить прежний fs_homepath и запускать игру обычным способом.

НОВАЯ РУЧНАЯ ПРИВЯЗКА КОНКРЕТНОЙ ЧАСТИ КОРПУСА
1. /r_dwFireLightControl 1
2. Навести прицел на пламя: /dw_fl_select
3. Не меняя выбранный огонь, навести прицел на конкретную металлическую/деревянную
   часть его корпуса или чаши: /dw_fl_self_pick
4. Проверить: /dw_fl_info
   Ожидается manualSeeds>=1 и ownBodySurfaces>=1.
5. /dw_fl_set selfshadow 0
6. /dw_fl_save

V1.5 использует выбранную поверхность как seed и строит только ограниченную
связанную группу вокруг неё. Flood-fill проходит лишь через реальный контакт
геометрии, ограничен локальным размером/дистанцией и останавливается на больших
архитектурных плоскостях. Стена, пол, потолок, пламя и удалённая геометрия
защищены. Если безопасную группу построить нельзя, команда отказывает без
изменений. Повторный dw_fl_self_pick позволяет добавить ещё одну отдельную часть
того же корпуса. AUTO-политика V1.4 не изменена.

selfshadow 0 = собственный выбранный корпус не затеняет свой источник.
selfshadow 1 = исходное участие корпуса в тени.
selfshadow auto = прежняя автоматическая политика V1.2/V1.4.
Direct, FireVol, видимая геометрия и тени других объектов не отключаются.

Профиль DW_IFLC 2 совместим с V1.4. Для отката на V1.2/V1.3 восстановить
резервную копию .iflc старого формата. Это TEST candidate: Windows GPU/FPS
пользователя ещё не являются частью автоматической проверки.
'''
entries['README_RU.txt']=readme.replace('\n','\r\n').encode('utf-8-sig')
manifest={'status':'TEST_CANDIDATE','version':'IFLC_V1.5','build_run':os.environ.get('GITHUB_RUN_ID'),'commit':os.environ.get('GITHUB_SHA'),'base_run':41808242270,'accepted_production_run':41772470237,'renderer_sha256':sha(dll),'changed_source':['SP/code/rend2/tr_iflc.inc','SP/code/rend2/tr_iflc_self.inc'],'v14_native_containment_preserved':True,'electric_fixture_preserved':True,'glsl_unchanged':True,'new_commands':[],'behavior_change':'dw_fl_self_pick exact safe local part binding','windows_gpu_fps':'NOT_TESTED'}
entries['BUILD_STATUS.json']=(json.dumps(manifest,indent=2)+'\n').encode();entries['IFLC15_SOURCE_PROOF.json']=(ev/'IFLC15_SOURCE_PROOF.json').read_bytes()
for name in entries:
 if name in old and name not in ('renderer_sp_rend2_x64.dll','README_RU.txt','BUILD_STATUS.json','SHA256SUMS.txt'):assert entries[name]==old[name]
for name,data in entries.items():
 if name.lower().endswith(('.exe','.dll')):
  assert data[:2]==b'MZ';off=struct.unpack_from('<I',data,0x3c)[0];assert data[off:off+4]==b'PE\0\0' and struct.unpack_from('<H',data,off+4)[0]==0x8664
entries['SHA256SUMS.txt']=''.join(sha(b)+'  '+n+'\n' for n,b in sorted(entries.items())).encode()
name='DarkWolf_IFLC_V1.5_ExactBody_From_V14_Win64_TEST';target=out/(name+'.zip')
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
 for n,b in sorted(entries.items()):z.writestr(name+'/'+n,b)
with zipfile.ZipFile(target) as z:assert z.testzip() is None and len(z.namelist())==len(entries)
with tarfile.open(out/'IFLC_V15_EXACT_SOURCE.tar.gz','w:gz') as t:
 t.add(src/'SP/code',arcname='SP/code');t.add(src/'SP/Makefile',arcname='SP/Makefile')
(out/'SHA256SUMS.txt').write_text(''.join(sha(p.read_bytes())+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file() and p.name!='SHA256SUMS.txt'))
print(json.dumps({'package':str(target),'bytes':target.stat().st_size,'sha256':sha(target.read_bytes()),'files':len(entries),'renderer_sha256':sha(dll)},indent=2),flush=True)
