#!/usr/bin/env python3
from pathlib import Path
import hashlib,io,json,os,subprocess,zipfile
ev=Path('evidence');out=Path('dist');out.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
artifact=ev/'v101_win64_artifact.zip'
with artifact.open('wb') as f:
    subprocess.run(['gh','api','repos/jaha2002-stack/iortcw-rend2-build/actions/artifacts/13393829867/zip'],stdout=f,check=True)
with zipfile.ZipFile(artifact) as z:
    inner=[n for n in z.namelist() if n.endswith('DarkWolf_ELSS_V1.0.1_PersistenceFix_From_IFLC_V1.5U_Win64_TEST.zip')]
    assert len(inner)==1,inner
    raw=z.read(inner[0])
assert sha(raw)=='47a5ec0245782abf7a2f0acd209d991bd52bcdca4548499bc91b858780d6cdb6',sha(raw)
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    assert z.testzip() is None
    entries={n.split('/',1)[1]:z.read(n) for n in z.namelist() if not n.endswith('/')}
dlls=list(Path('source/SP/build').rglob('renderer_sp_rend2_x64.dll'));assert len(dlls)==1,dlls
dll=dlls[0].read_bytes()
for m in (b'dw_el_select',b'dw_el_self_pick',b'r_dwElectricLightControl',b'ELSS V1.1:'):
    assert m in dll,m
for m in (b'ELSS_TEST_',b'dw_el_test',b'ELSS11_AUDIT_'):
    assert m not in dll,m
entries['renderer_sp_rend2_x64.dll']=dll
entries['Main/DW_ELSS_V11_ENABLE.cfg']=b'// ELSS V1.1 Component Pick on V1.0.1 Persistence Fix\r\nseta r_dwElectricLightControl "1"\r\n'
readme='''DarkWolf ELSS V1.1 Component Pick - Win64 TEST
Base: ELSS V1.0.1 Persistence Fix / GitHub Run #41982135692
and IFLC V1.5 Universal.

V1.0.1 persistence behavior is preserved:
saved electricshadows/<map>.elss profiles automatically rebind after a full game restart.

V1.1 improves dw_el_self_pick for difficult electric fixtures:
1. Existing V1 connected-body flood is tried first, so already working lamps keep
   the accepted behavior.
2. If that local flood cannot be formed, V1.1 safely falls back to the exact
   compact BSP surface explicitly picked by the user.
3. If the literal first crosshair hit is protected large architecture, V1.1 may
   select a unique compact housing surface only when it is near the same ray,
   within 112 units of the already selected physical lamp owner, and the owner
   itself is visible. Ambiguous candidates are refused.

No wall/floor/ceiling surface is disabled merely because it was the first hit.
Profile format remains DW_ELSS 1. Existing ELSS V1/V1.0.1 profiles are compatible.

Workflow:
  /r_dwElectricLightControl 1
  aim at lamp/light -> /dw_el_select
  aim at the desired solid housing part -> /dw_el_self_pick
  /dw_el_info
  /dw_el_set selfshadow 0
  /dw_el_save

The lamp keeps its DLight, Local Volumetric, shadow slot, and shadows cast by
player/world/other objects. Only selected own-body surfaces are removed from
that lamp's own shadow capture.

Keep the previous DLL for rollback. This remains a TEST candidate until Windows
GPU/FPS acceptance.
'''
entries['README_ELSS_V11.txt']=readme.replace('\n','\r\n').encode('utf-8-sig')
manifest={
 'status':'TEST_CANDIDATE','version':'ELSS_V1.1_COMPONENT_PICK',
 'base_run':41982135692,'base_version':'ELSS_V1.0.1_PersistenceFix',
 'build_run':os.environ.get('GITHUB_RUN_ID'),'commit':os.environ.get('GITHUB_SHA'),
 'renderer_sha256':sha(dll),'profile_format':'DW_ELSS 1',
 'existing_profiles_compatible':True,'persistence_fix_preserved':True,
 'component_policy':'V1 flood first, exact compact picked surface fallback',
 'shadow_slot_preserved':True,'direct_preserved':True,'local_volumetric_preserved':True,
 'other_casters_preserved':True,'iflc_v15u_preserved':True
}
entries['ELSS_V11_BUILD_STATUS.json']=(json.dumps(manifest,indent=2)+'\n').encode()
entries.pop('SHA256SUMS.txt',None)
entries['SHA256SUMS.txt']=''.join(sha(b)+'  '+n+'\n' for n,b in sorted(entries.items())).encode()
name='DarkWolf_ELSS_V1.1_ComponentPick_From_V1.0.1_Win64_TEST';target=out/(name+'.zip')
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
    for n,b in sorted(entries.items()):z.writestr(name+'/'+n,b)
with zipfile.ZipFile(target) as z:assert z.testzip() is None
(out/'SHA256SUMS.txt').write_text(sha(target.read_bytes())+'  '+target.name+'\n'+sha(dll)+'  renderer_sp_rend2_x64.dll\n')
print(json.dumps({'package':str(target),'sha256':sha(target.read_bytes()),'renderer_sha256':sha(dll),'files':len(entries)},indent=2))
