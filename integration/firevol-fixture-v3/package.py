#!/usr/bin/env python3
from pathlib import Path
import hashlib,io,json,os,subprocess,sys,zipfile
src=Path(sys.argv[1]).resolve();ev=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]).resolve()
out.mkdir(parents=True,exist_ok=True);ev.mkdir(parents=True,exist_ok=True)
H=lambda b:hashlib.sha256(b).hexdigest()

# Repackage the already-successful Flash Fix V1 artifact so every non-renderer file stays identical.
outer=ev/'flashfix_v1_artifact.zip'
with outer.open('wb') as f:
    subprocess.run(['gh','api','repos/jaha2002-stack/iortcw-rend2-build/actions/artifacts/13406852042/zip'],stdout=f,check=True)
with zipfile.ZipFile(outer) as z:
    inner=[n for n in z.namelist() if n.endswith('_Win64_TEST.zip')]
    assert len(inner)==1,inner
    raw=z.read(inner[0])
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    assert z.testzip() is None
    files=[n for n in z.namelist() if n and not n.endswith('/')]
    prefix=files[0].split('/',1)[0]+'/'
    entries={n[len(prefix):]:z.read(n) for n in files if n.startswith(prefix)}

dlls=list((src/'SP/build').rglob('renderer_sp_rend2_x64.dll'))
assert len(dlls)==1,dlls
dll=dlls[0].read_bytes()
for marker in (b'r_dwFireVolFixtureV3',b'r_dwFireVolFixtureDiag',b'r_dwFireVolGeometryScale',b'FIREVOL_FIXTURE_V3'):
    assert marker in dll,marker
entries['renderer_sp_rend2_x64.dll']=dll
entries['Main/DW_FIREVOL_FIXTURE_V3_DIAG.cfg']=(
    'seta r_dwFireVolFlashFix "1"\r\n'
    'seta r_dwFireVolWarmupGuard "1"\r\n'
    'seta r_dwFireVolEnergyGuard "1"\r\n'
    'seta r_dwFireVolFLCFade "1"\r\n'
    'seta r_dwFireVolFixtureV3 "1"\r\n'
    'seta r_dwFireVolFixtureDiag "1"\r\n'
    'seta r_dwFireVolGeometryScale "0.55"\r\n'
    'seta r_dwFireVolGeometryMin "96"\r\n').encode()
entries['Main/DW_FIREVOL_FIXTURE_V3_AB_OLD_GEOMETRY.cfg']=(
    'seta r_dwFireVolFixtureV3 "0"\r\n'
    'seta r_dwFireVolFixtureDiag "1"\r\n').encode()
entries['Main/DW_FIREVOL_FIXTURE_V3_AB_ON.cfg']=(
    'seta r_dwFireVolFixtureV3 "1"\r\n'
    'seta r_dwFireVolFixtureDiag "1"\r\n'
    'seta r_dwFireVolGeometryScale "0.55"\r\n'
    'seta r_dwFireVolGeometryMin "96"\r\n').encode()
readme='''DarkWolf FireVol Fixture Owner V3 - Win64 TEST
Base lineage: requested Run #41982135692 -> Flash Fix V1 Run #42011094909.
V2 Physical Owner is NOT carried forward.

Why V2 was withdrawn:
- FireVol surfaceIndex is not one global namespace.
- WORLD uses a world-surface index, BMODEL uses the full BSP surface array,
  MDV uses model-local surface indices, POLY/flare/entity may use drawIndex.
- V2 treated all of them as IFLC world-surface IDs, causing owner misses and possible false merges.

V3:
1) World IFLC owner lookup is accepted only for actual world surfaces.
2) Moving BMODEL physical owner = primitive + entityNum + shader.
   One moving fireplace updates one registry latch instead of leaving old positions behind.
3) MDV/model/entity identities use their own entity domain; cgame POLY fails open.
4) Owner duplicates are removed before stable residency and synthetic shadow-cache publication.
5) FireVol geometry is compacted independently from Direct Light:
   default geometryScale=0.55, geometryMin=96.
   Direct DLight radius, shadow cubemap radius and FLC Direct settings are unchanged.

Test:
/exec DW_FIREVOL_FIXTURE_V3_DIAG.cfg
Chateau: reproduce the secret-fireplace transition several times.
Crypt1: inspect the 8-9 wall torches and verify no torch loses FireVol.
/condump firevol_fixture_v3.txt

Desired Chateau telemetry near the fireplace:
FIREVOL_FIXTURE_V3 selectedPhysical=1 unknownSelected=0 ... selected=1 rendered=1
and FIREVOL_FIXTURE_V3_SLOT should show keyKind=2 (BMODEL) for the moving fireplace.

Crypt1:
separate torches may remain separate WORLD owners; they must not be merged by proximity alone.
'''
entries['README_FIREVOL_FIXTURE_V3.txt']=readme.replace('\n','\r\n').encode('utf-8-sig')
entries['FIREVOL_FIXTURE_V3_BUILD_STATUS.json']=(json.dumps({
 'status':'TEST_CANDIDATE','version':'FIREVOL_FIXTURE_OWNER_V3',
 'requested_base_run':41982135692,'parent_flashfix_run':42011094909,
 'build_run':os.environ.get('GITHUB_RUN_ID'),'commit':os.environ.get('GITHUB_SHA'),
 'renderer_sha256':H(dll),'v2_carried_forward':False,
 'geometryScale':0.55,'geometryMin':96,'renderCap':8},indent=2)+'\n').encode()
entries.pop('SHA256SUMS.txt',None)
entries['SHA256SUMS.txt']=''.join(H(b)+'  '+n+'\n' for n,b in sorted(entries.items())).encode()
name='DarkWolf_FireVol_FixtureOwner_V3_From_41982135692_Win64_TEST'
target=out/(name+'.zip')
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
    for n,b in sorted(entries.items()): z.writestr(name+'/'+n,b)
with zipfile.ZipFile(target) as z: assert z.testzip() is None
(out/'SHA256SUMS.txt').write_text(H(target.read_bytes())+'  '+target.name+'\n'+H(dll)+'  renderer_sp_rend2_x64.dll\n')
print(json.dumps({'package':str(target),'sha256':H(target.read_bytes()),'renderer_sha256':H(dll),'files':len(entries)},indent=2))
