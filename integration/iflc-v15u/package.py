#!/usr/bin/env python3
from pathlib import Path
import hashlib,io,json,os,struct,subprocess,tarfile,zipfile
src=Path('source');ev=Path('evidence');out=Path('dist');out.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
base_artifact=ev/'v15_runtime_artifact.zip'
with base_artifact.open('wb') as f:
    subprocess.run(['gh','api','repos/jaha2002-stack/iortcw-rend2-build/actions/artifacts/13321246159/zip'],stdout=f,check=True)
with zipfile.ZipFile(base_artifact) as z:
    candidates=[n for n in z.namelist() if n.endswith('_Win64_TEST.zip')]
    assert len(candidates)==1,candidates;raw=z.read(candidates[0])
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    assert z.testzip() is None
    entries={n.split('/',1)[1]:z.read(n) for n in z.namelist() if not n.endswith('/')}
old=entries.copy()
assert sha(entries['renderer_sp_rend2_x64.dll'])=='d5da9a77d23fc000bd68adaac08427b491248b548821d95de30726a317cc79a8'
dlls=list((src/'SP/build').rglob('renderer_sp_rend2_x64.dll'));assert len(dlls)==1
dll=dlls[0].read_bytes()
for marker in (b'IFLC15_STATE',b'IFLC14_VOLUME',b'dw_proofShot',b'IFLC15U_TEST_FORCED'):
    assert marker not in dll,marker
for marker in (b'dw_fl_self_pick',b'IFLC V1.5 Universal',b'ownBodySurfaces'):
    assert marker in dll,marker
entries['renderer_sp_rend2_x64.dll']=dll
for name in ('BUILD_STATUS.json','README_RU.txt'):
    if name in entries:entries['docs/base-v15/'+name]=entries.pop(name)
entries.pop('SHA256SUMS.txt',None)
readme='''DarkWolf IFLC V1.5 Universal Manual Self-Shadow — Win64 TEST
Основа: успешная V1.5 Run #41827953550, которая в свою очередь основана на V1.4.

Эта версия меняет только ручной self_pick:
AUTO по-прежнему требует надёжную flame geometry.
MANUAL после /dw_fl_select использует уже выбранный стабильный owner/DLight
как anchor и не требует compact flame bounds.

Универсальный ручной путь одинаков для:
- NATIVE_FIRE
- PROMOTED_FIRE
- VOLUME_ONLY

Безопасность сохранена: неоднозначный owner запрещён; flame shader не может
стать корпусом; стены/пол/потолок и крупные архитектурные плоскости защищены;
группа растёт только по mesh contact, ограничена по размеру и дистанции.

Проверка:
1. /r_dwFireLightControl 1
2. прицел на огонь: /dw_fl_select
3. прицел на нужную часть корпуса: /dw_fl_self_pick
4. при необходимости повторить пункт 3 для другой несвязанной части
5. /dw_fl_info
   ожидается manualSeeds>=1 и ownBodySurfaces>=1
6. /dw_fl_set selfshadow 0
7. /dw_fl_save

selfshadow auto = прежняя автоматическая политика.
selfshadow 1 = исходная собственная тень.
Direct, FireVol, видимый корпус и тени от других источников не отключаются.

Перед тестом сохранить старую renderer_sp_rend2_x64.dll и папку firelights.
Для установки достаточно заменить только renderer_sp_rend2_x64.dll.
'''
entries['README_RU.txt']=readme.replace('\n','\r\n').encode('utf-8-sig')
manifest={
 'status':'TEST_CANDIDATE','version':'IFLC_V1.5_UNIVERSAL_MANUAL_SELFSHADOW',
 'build_run':os.environ.get('GITHUB_RUN_ID'),'commit':os.environ.get('GITHUB_SHA'),
 'base_run':41827953550,'accepted_production_run':41772470237,
 'renderer_sha256':sha(dll),
 'changed_source':['SP/code/rend2/tr_iflc.inc','SP/code/rend2/tr_iflc_self.inc'],
 'manual_requires_flame_bounds':False,'auto_requires_flame_bounds':True,
 'owner_kinds':['NATIVE_FIRE','PROMOTED_FIRE','VOLUME_ONLY'],
 'v14_native_containment_preserved':True,'v13_electric_fixture_preserved':True,
 'glsl_unchanged':True,'windows_gpu_fps':'NOT_TESTED'
}
entries['BUILD_STATUS.json']=(json.dumps(manifest,indent=2)+'\n').encode()
entries['IFLC15U_SOURCE_PROOF.json']=(ev/'IFLC15U_SOURCE_PROOF.json').read_bytes()
for name in old:
    if name in entries and name not in ('renderer_sp_rend2_x64.dll','README_RU.txt','BUILD_STATUS.json','SHA256SUMS.txt'):
        assert entries[name]==old[name],name
for name,data in entries.items():
    if name.lower().endswith(('.exe','.dll')):
        assert data[:2]==b'MZ';off=struct.unpack_from('<I',data,0x3c)[0]
        assert data[off:off+4]==b'PE\0\0' and struct.unpack_from('<H',data,off+4)[0]==0x8664
entries['SHA256SUMS.txt']=''.join(sha(b)+'  '+n+'\n' for n,b in sorted(entries.items())).encode()
name='DarkWolf_IFLC_V1.5_Universal_ManualSelfShadow_Win64_TEST'
target=out/(name+'.zip')
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
    for n,b in sorted(entries.items()):z.writestr(name+'/'+n,b)
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None and len(z.namelist())==len(entries)
with tarfile.open(out/'IFLC_V15U_EXACT_SOURCE.tar.gz','w:gz') as t:
    t.add(src/'SP/code',arcname='SP/code');t.add(src/'SP/Makefile',arcname='SP/Makefile')
(out/'SHA256SUMS.txt').write_text(''.join(sha(p.read_bytes())+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file() and p.name!='SHA256SUMS.txt'))
print(json.dumps({'package':str(target),'bytes':target.stat().st_size,'sha256':sha(target.read_bytes()),'files':len(entries),'renderer_sha256':sha(dll)},indent=2))
