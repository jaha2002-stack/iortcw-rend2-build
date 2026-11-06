#!/usr/bin/env python3
from pathlib import Path
import hashlib,io,json,os,subprocess,zipfile
ev=Path('evidence');out=Path('dist');out.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
artifact=ev/'run421985_clean_artifact.zip'
with artifact.open('wb') as f:
    subprocess.run(['gh','api','repos/jaha2002-stack/iortcw-rend2-build/actions/artifacts/13494035208/zip'],stdout=f,check=True)
with zipfile.ZipFile(artifact) as z:
    inners=[n for n in z.namelist() if n.endswith('.zip') and 'Clean_Production_FireVol_Final' in n]
    assert len(inners)==1,inners
    raw=z.read(inners[0])
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    assert z.testzip() is None
    roots={n.split('/',1)[0] for n in z.namelist() if '/' in n}
    assert len(roots)==1,roots
    oldroot=next(iter(roots))
    base={n.split('/',1)[1]:z.read(n) for n in z.namelist() if not n.endswith('/')}

dlls=list(Path('source/SP/build').rglob('renderer_sp_rend2_x64.dll'));assert len(dlls)==1,dlls
dll=dlls[0].read_bytes()
for m in (b'dw_el_select',b'dw_el_self_pick',b'r_dwElectricLightControl',b'ELSS V1.1:',b'ownBodyTriangles=',b'FIREVOL_CLEAN_PRODUCTION'):
    assert m in dll,m
for m in (b'ELSS11_TEST_',b'dw_el_v11_test_'):
    assert m not in dll,m

entries=base.copy()
base_dll=entries['renderer_sp_rend2_x64.dll']
assert sha(base_dll)=='57da8388945f3f7e9e874d8cd19b886a6e4685ac0457390f8028f176efdfa002'
entries['renderer_sp_rend2_x64.dll']=dll
entries['Main/DW_ELSS_V11_ENABLE.cfg']=b'// ELSS V1.1 Component Pick on Clean Production Run #42198541106\r\nseta r_dwElectricLightControl "1"\r\n'
readme='''DarkWolf ELSS V1.1 Component Pick - Win64 TEST
Base: GitHub Run #42198541106 Clean Production FireVol Final.

V1.1 extends the accepted ELSS V1.0.1 persistence build. Existing saved
DW_ELSS 1 profiles are read unchanged. New saves use DW_ELSS 2 because a manual
seed may now contain both BSP surface and triangle index.

What changed:
- If a lamp housing is a normal safe BSP surface, V1 behavior is preserved.
- If the aimed BSP surface is large/shared/architectural, V1.1 locates the
  exact triangle under the crosshair and grows only its edge-connected component.
- The component is accepted only if it stays compact and close to the selected
  physical electric light. If it grows into a wall/floor/ceiling it is rejected.
- Only those own-body triangles are omitted from THIS lamp's shadow capture.
  The DLight, shadow slot, Local Volumetric, player/world/object shadows remain.

Workflow:
1. /r_dwElectricLightControl 1
2. aim at lamp -> /dw_el_select
3. aim at exact housing part -> /dw_el_self_pick
4. /dw_el_info
5. /dw_el_set selfshadow 0
6. /dw_el_save

V1.1 info reports ownBodyTriangles=N for component picks.
Profiles: electricshadows/<map>.elss

Compatibility:
V1.1 reads DW_ELSS 1 and DW_ELSS 2, but writes DW_ELSS 2.
Back up the electricshadows folder before the first V1.1 save if you may roll
back to V1.0.1, because V1.0.1 does not read DW_ELSS 2.

Inherited Clean Production FireVol, Crypt1 Slot6 reanchor, IFLC V1.5 Universal,
and ELSS V1.0.1 restart persistence are preserved.
'''
entries['README_ELSS_V11_COMPONENT_PICK.txt']=readme.replace('\n','\r\n').encode('utf-8-sig')
manifest={
 'status':'TEST_CANDIDATE',
 'version':'ELSS_V1.1_COMPONENT_PICK',
 'base_run':42198541106,
 'base_commit':'5ba3e923803674c9acee71600412720a0eeaf81e',
 'build_run':os.environ.get('GITHUB_RUN_ID'),
 'commit':os.environ.get('GITHUB_SHA'),
 'renderer_sha256':sha(dll),
 'base_renderer_sha256':sha(base_dll),
 'profile_read':['DW_ELSS 1','DW_ELSS 2'],
 'profile_write':'DW_ELSS 2',
 'inherits_elss_v101_persistence':True,
 'firevol_clean_production_preserved':True,
 'crypt1_slot6_reanchor_preserved':True,
 'shadow_slot_preserved':True,
 'direct_preserved':True,
 'local_volumetric_preserved':True,
 'other_casters_preserved':True,
 'windows_gpu_fps':'NOT_TESTED'
}
entries['ELSS_V11_BUILD_STATUS.json']=(json.dumps(manifest,indent=2)+'\n').encode()
entries.pop('SHA256SUMS.txt',None)
entries['SHA256SUMS.txt']=''.join(sha(b)+'  '+n+'\n' for n,b in sorted(entries.items())).encode()
name='DarkWolf_ELSS_V1.1_ComponentPick_From_42198541106_Win64_TEST'
target=out/(name+'.zip')
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for n,b in sorted(entries.items()):z.writestr(name+'/'+n,b)
with zipfile.ZipFile(target) as z:assert z.testzip() is None
# Every inherited payload except renderer and package metadata remains byte-identical.
for n,b in base.items():
    if n in ('renderer_sp_rend2_x64.dll','SHA256SUMS.txt'):continue
    assert entries[n]==b,n
(out/'SHA256SUMS.txt').write_text(sha(target.read_bytes())+'  '+target.name+'\n'+sha(dll)+'  renderer_sp_rend2_x64.dll\n')
print(json.dumps({'package':str(target),'sha256':sha(target.read_bytes()),'renderer_sha256':sha(dll),'base_files':len(base),'files':len(entries)},indent=2))
