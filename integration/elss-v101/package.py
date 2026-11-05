#!/usr/bin/env python3
from pathlib import Path
import hashlib,io,json,os,subprocess,zipfile
ev=Path('evidence');out=Path('dist');out.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
artifact=ev/'v15u_win64_artifact.zip'
with artifact.open('wb') as f:subprocess.run(['gh','api','repos/jaha2002-stack/iortcw-rend2-build/actions/artifacts/13354723866/zip'],stdout=f,check=True)
with zipfile.ZipFile(artifact) as z:
    inner=[n for n in z.namelist() if n.endswith('_Win64_TEST.zip')];assert len(inner)==1
    raw=z.read(inner[0])
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    assert z.testzip() is None
    entries={n.split('/',1)[1]:z.read(n) for n in z.namelist() if not n.endswith('/')}
dlls=list(Path('source/SP/build').rglob('renderer_sp_rend2_x64.dll'));assert len(dlls)==1,dlls
dll=dlls[0].read_bytes()
for m in (b'dw_el_select',b'dw_el_self_pick',b'r_dwElectricLightControl',b'ELSS: selfshadow='):
    assert m in dll,m
for m in (b'ELSS_TEST_',b'dw_el_test'):
    assert m not in dll,m
entries['renderer_sp_rend2_x64.dll']=dll
entries['Main/DW_ELSS_V101_ENABLE.cfg']=b'// ELSS V1.0.1 Persistence Fix\r\nseta r_dwElectricLightControl "1"\r\n'
readme='''DarkWolf ELSS V1.0.1 Persistence Fix - Win64 TEST
Base: IFLC V1.5 Universal Run #41895006605 + ELSS V1.

Fix:
Saved electric-lamp selfshadow OFF profiles are now rebound automatically after
a full game restart / fresh map load. ELSS V1 loaded the file correctly, but
could mark the own-body fixture cache as already built before the physical
electric DLight owner had been rediscovered. That left an empty cached fixture
for the rest of the session.

V1.0.1 changes only startup/rebind order and cache readiness:
- rediscover current electric DLight owners first;
- then rebuild saved OFF fixtures;
- if an owner is not present yet, leave the fixture unbuilt so a later frame can retry.

Profile format remains DW_ELSS 1. Existing electricshadows/<map>.elss files are
compatible and do not need to be recreated.

Commands and semantics are unchanged:
  /r_dwElectricLightControl 1
  /dw_el_select
  /dw_el_self_pick
  /dw_el_set selfshadow 0
  /dw_el_save

This maintenance build does NOT include the paused V1.1 triangle-component work.
'''
entries['README_ELSS_V101.txt']=readme.replace('\n','\r\n').encode('utf-8-sig')
manifest={
 'status':'TEST_CANDIDATE','version':'ELSS_V1.0.1_PERSISTENCE_FIX',
 'base_iflc_run':41895006605,'build_run':os.environ.get('GITHUB_RUN_ID'),'commit':os.environ.get('GITHUB_SHA'),
 'renderer_sha256':sha(dll),'profile_format':'DW_ELSS 1','existing_profiles_compatible':True,
 'paused_v11_component_pick_included':False
}
entries['ELSS_V101_BUILD_STATUS.json']=(json.dumps(manifest,indent=2)+'\n').encode()
entries.pop('SHA256SUMS.txt',None)
entries['SHA256SUMS.txt']=''.join(sha(b)+'  '+n+'\n' for n,b in sorted(entries.items())).encode()
name='DarkWolf_ELSS_V1.0.1_PersistenceFix_From_IFLC_V1.5U_Win64_TEST';target=out/(name+'.zip')
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
    for n,b in sorted(entries.items()):z.writestr(name+'/'+n,b)
with zipfile.ZipFile(target) as z:assert z.testzip() is None
(out/'SHA256SUMS.txt').write_text(sha(target.read_bytes())+'  '+target.name+'\n'+sha(dll)+'  renderer_sp_rend2_x64.dll\n')
print(json.dumps({'package':str(target),'sha256':sha(target.read_bytes()),'renderer_sha256':sha(dll),'files':len(entries)},indent=2))
