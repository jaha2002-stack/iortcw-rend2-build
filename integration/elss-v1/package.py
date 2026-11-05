#!/usr/bin/env python3
from pathlib import Path
import hashlib,io,json,os,struct,subprocess,zipfile
ev=Path('evidence');out=Path('dist');out.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
artifact=ev/'v15u_win64_artifact.zip'
with artifact.open('wb') as f:subprocess.run(['gh','api','repos/jaha2002-stack/iortcw-rend2-build/actions/artifacts/13354723866/zip'],stdout=f,check=True)
assert sha(artifact.read_bytes())=='59aa0e62cbebc354c1faec9cf97e4f238ed8cb73fe75a53ee6c62e4f34510779'
with zipfile.ZipFile(artifact) as z:
    inner=[n for n in z.namelist() if n.endswith('_Win64_TEST.zip')];assert len(inner)==1
    raw=z.read(inner[0])
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    assert z.testzip() is None
    entries={n.split('/',1)[1]:z.read(n) for n in z.namelist() if not n.endswith('/')}
old=entries.copy()
dlls=list(Path('source/SP/build').rglob('renderer_sp_rend2_x64.dll'));assert len(dlls)==1,dlls
dll=dlls[0].read_bytes()
for m in (b'dw_el_select',b'dw_el_self_pick',b'r_dwElectricLightControl',b'ELSS: selfshadow='):
    assert m in dll,m
for m in (b'ELSS_TEST_',b'dw_el_test'):
    assert m not in dll,m
entries['renderer_sp_rend2_x64.dll']=dll
entries['Main/DW_ELSS_V1_ENABLE.cfg']=b'// Electric Lamp Self-Shadow Control V1\r\nseta r_dwElectricLightControl "1"\r\n'
entries['Main/DW_ELSS_V1_DISABLE.cfg']=b'// Disable ELSS overrides; existing V1.3 AUTO policy remains baseline.\r\nseta r_dwElectricLightControl "0"\r\n'
readme='''DarkWolf Electric Lamp Self-Shadow Control V1 — Win64 TEST
Base: IFLC V1.5 Universal Run #41895006605.

Purpose:
Select a physical electric lamp and remove only the shadow cast by selected
parts of its OWN housing from THAT lamp's own shadow capture. Direct light,
Local Volumetric, the shadow slot, player/world/object shadows and shadows from
other lights remain.

Enable:
/exec DW_ELSS_V1_ENABLE.cfg

Workflow:
1. Aim at the lamp/light and run /dw_el_select
2. /dw_el_info
3. Aim at a solid housing part and run /dw_el_self_pick
4. Repeat step 3 for disconnected housing parts when needed (up to 8 seeds)
5. /dw_el_set selfshadow 0
6. /dw_el_save

Modes:
/dw_el_set selfshadow 0    remove selected own-body shadow
/dw_el_set selfshadow 1    restore original own-body shadow
/dw_el_set selfshadow auto return to existing V1.3 automatic electric policy

Other commands:
/dw_el_next /dw_el_info /dw_el_reset /dw_el_reload /dw_el_list

Profiles are stored under fs_homepath/fs_game:
electricshadows/<map>.elss

Safety:
Manual selection accepts bounded opaque BSP housing connected by real mesh
contact and rejects large/coplanar architecture. Production code contains no
map names, fixture ordinals or test coordinates.

This is a TEST candidate. Keep the previous renderer DLL and profiles for rollback.
'''
entries['README_ELSS_V1_RU.txt']=readme.replace('\n','\r\n').encode('utf-8-sig')
manifest={
 'status':'TEST_CANDIDATE','version':'ELSS_V1','base_run':41895006605,
 'build_run':os.environ.get('GITHUB_RUN_ID'),'commit':os.environ.get('GITHUB_SHA'),
 'renderer_sha256':sha(dll),'profile_path':'electricshadows/<map>.elss',
 'shadow_slot_preserved':True,'direct_preserved':True,'local_volumetric_preserved':True,
 'other_casters_preserved':True,'iflc_v15u_preserved':True
}
entries['ELSS_V1_BUILD_STATUS.json']=(json.dumps(manifest,indent=2)+'\n').encode()
entries.pop('SHA256SUMS.txt',None)
entries['SHA256SUMS.txt']=''.join(sha(b)+'  '+n+'\n' for n,b in sorted(entries.items())).encode()
name='DarkWolf_ELSS_V1_From_IFLC_V1.5U_Win64_TEST';target=out/(name+'.zip')
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
    for n,b in sorted(entries.items()):z.writestr(name+'/'+n,b)
with zipfile.ZipFile(target) as z:assert z.testzip() is None
(out/'SHA256SUMS.txt').write_text(sha(target.read_bytes())+'  '+target.name+'\n'+sha(dll)+'  renderer_sp_rend2_x64.dll\n')
print(json.dumps({'package':str(target),'sha256':sha(target.read_bytes()),'renderer_sha256':sha(dll),'files':len(entries)},indent=2))
