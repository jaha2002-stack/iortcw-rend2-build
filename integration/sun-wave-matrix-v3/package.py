#!/usr/bin/env python3
"""Package exact user-accepted DarkWolf SP archive, replacing only rend2 DLL."""
import argparse,hashlib,io,json,re,zipfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--base-zip',type=Path,required=True)
p.add_argument('--renderer',type=Path,required=True)
p.add_argument('--proof',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
H=lambda d:hashlib.sha256(d).hexdigest()
accepted_zip_sha='2e882812df4aaa2bbca9cc25e91591a681b3ce2afe0edc0b69f691fcf5029f70'
accepted_renderer_sha='655ab7e38bbdb2eaacb35466e7f791e6813f826e40c104bedff08bd829fb7357'
base=a.base_zip.read_bytes()
assert H(base)==accepted_zip_sha,('WRONG_BASE_ARCHIVE',H(base))
newdll=a.renderer.read_bytes()
assert newdll[:2]==b'MZ' and len(newdll)>2000000
assert H(newdll)!=accepted_renderer_sha
proof=json.loads(a.proof.read_text())
assert proof['marker']=='DARKWOLF_SUN_WAVE_CAUSE_MATRIX_V3_20261027'
assert proof['fixture_only'] is False
assert proof['sha256_before']['tr_backend.c']=='0cfcad4ad18882691f16749697d09a48e832b9344de4e58a11e36c3b7efb405e'
assert proof['sha256_before']['glsl/volumetricsun_fp.glsl']=='8e22ade3bba934b471b270fd5db3e6066e500acb47bc1ea03588abe1bcd780ab'
assert sorted(proof['modified_files'])==sorted(['SP/code/rend2/tr_backend.c','SP/code/rend2/glsl/volumetricsun_fp.glsl'])
with zipfile.ZipFile(io.BytesIO(base)) as z:
 original={i.filename:z.read(i) for i in z.infolist() if not i.is_dir()}
 assert len(original)==37
assert len({x.split('/')[0] for x in original})==1
root=next(iter(original)).split('/')[0]
assert all(p.startswith(root+'/') and '..' not in Path(p).parts for p in original)
assert root=='DarkWolf_Sky_Portal_Volumetric_Wave_Clean_V2_Win64'
rel='renderer_sp_rend2_x64.dll';full=root+'/'+rel
assert H(original[full])==accepted_renderer_sha
for f in ('ioWolfSP.x64.exe','renderer_sp_opengl1_x64.dll','Main/cgame_sp_x64.dll','Main/qagame_sp_x64.dll','Main/ui_sp_x64.dll','SDL264.dll','OpenAL64.dll'):
 assert root+'/'+f in original
assert not any(re.search(r'(^|/)pak[0-9]*\.pk3$',n,re.I) for n in original)
entries={name.split('/',1)[1]:b for name,b in original.items()}
entries[rel]=newdll
manifest={
 'status':'CI_DIAGNOSTIC_CANDIDATE__GPU_RUNTIME_PENDING',
 'candidate':'DARKWOLF_SUN_WAVE_CAUSE_MATRIX_V3_20261027',
 'accepted_base_run_id':40487188767,
 'accepted_base_zip_sha256':accepted_zip_sha,
 'accepted_renderer_sha256':accepted_renderer_sha,
 'new_renderer_sha256':H(newdll),
 'source':proof,
 'changed_existing_files':[rel,'docs/SHA256SUMS.txt'],
 'unchanged_existing_files_count':len(original)-2,
 'runtime_visual_test':'NOT_TESTED',
 'preserved_sky_single_sample':True,
 'preserved_fire_e':True,
 'preserved_local_volumetric':True,
 'not_yet_user_accepted':True
}
entries['docs/DW_SUN_WAVE_V3_MANIFEST.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf8')
modes=[
 ('0_REFERENCE',0,0,0.08),
 ('1_CSM_NARROW',1,0,0.08),
 ('2_CSM_HARD',2,0,0.08),
 ('3_DUAL_VIS',3,0,0.08),
 ('4_DUAL_NARROW',4,0,0.08),
 ('5_SUN_5X5',0,1,0.08),
 ('6_ZERO_JITTER',0,0,0.0)
]
for name,mode,recon,jitter in modes:
 cfg=(f'// Sun-only root cause matrix V3 {name}\n'
      'seta r_volumetricSun "1"\n'
      'seta r_volumetricSunMode "1"\n'
      'seta r_volumetricSunSamples "32"\n'
      'seta r_volumetricSunShadowPcf "2"\n'
      f'seta r_volumetricSunJitter "{jitter:.2f}"\n'
      f'seta r_dwSunWaveMode "{mode}"\n'
      f'seta r_dwSunReconMode "{recon}"\n'
      'seta r_volumetricFireSamples "40"\n'
      'seta r_volumetricFireUpscale "2"\n'
      'seta r_volumetricLocalShadowPcf "2"\n'
      'seta cg_drawFPS "1"\n')
 entries['Main/DW_SUN_V3_'+name+'.cfg']=cfg.encode('ascii')
readme="""DARKWOLF ioRTCW Rend2 SP - SUN WAVE ROOT CAUSE MATRIX V3 (DIAGNOSTIC)
EXACT accepted binary base: GitHub Actions #40487188767 Wave Clean V2.
Sky #40480112714 preserved. Fire E config 40/2/2 preserved.
No Local or Fire shader edits; no change to CSM production render paths.

TEST ONE fixed sun save/camera at arch hall and tree-and-cliff map.
Select using RUN_SUN_V3_TEST.cmd or console: exec DW_SUN_V3_0_REFERENCE.cfg etc.
0 reference: 6% CSM fade, 1 shadow visibility per step, accepted quarter AA.
1 narrow 1.5% transition: isolate CSM fade width.
2 hard cascade selection (may create seam): isolate transition fade.
3 2 stratified shadow samples per step: isolate ray sampling aliasing.
4 2 samples + 1.5% transition: combined candidate, potentially more expensive.
5 reference CSM + alternate depth-aware 5x5 Sun upscale.
6 reference policy + zero Sun jitter: isolate jitter/temporal shimmer.
All modes use 32 Sun raymarch steps and PCF2. Other renderer subsystems frozen.

DECISION TABLE:
1 clean = broad CSM transition implicated;
2 clean = CSM blend implicated, inspect hard boundaries;
3 clean = ray sampling integration implicated;
4 best = combined CSM and integration;
5 clean = quarter upscaling implicated;
6 clean = unstable jitter implicated;
all still bad = other shadows/CSM producer geometry or depth alias, no blind tuning.
These are hypotheses until A/B GPU acceptance.
Compare the same save, camera angle, sky, HDR, exposure and MSAA.
Record 5-10s average FPS and still shots (plus motion video for shimmer).
CI build success is NOT runtime acceptance. Never package commercial pak*.pk3.
"""
entries['README_DW_SUN_WAVE_MATRIX_V3_RU.txt']=readme.encode('utf8')
cmd=['@echo off','setlocal EnableExtensions DisableDelayedExpansion','cd /d "%~dp0"',
     'if not exist "ioWolfSP.x64.exe" (echo Missing SP EXE & exit /b 1)',
     'set /p MODE=Select Sun wave mode 0..6: ','set "CFG="']
for name,*_ in modes:
 cmd.append(f'if "%MODE%"=="{name[0]}" set "CFG=DW_SUN_V3_{name}.cfg"')
cmd+=['if "%CFG%"=="" (echo Invalid mode & exit /b 1)',
      '"%CD%\\ioWolfSP.x64.exe" +set fs_basepath "%CD%" +set cl_renderer rend2 +set r_renderer rend2 +exec %CFG%',
      'exit /b %errorlevel%']
entries['RUN_SUN_V3_TEST.cmd']=('\r\n'.join(cmd)+'\r\n').encode('ascii')
entries['docs/SHA256SUMS.txt']=(''.join(H(v)+'  '+k+'\n' for k,v in sorted(entries.items()) if k!='docs/SHA256SUMS.txt')).encode('ascii')

name='DarkWolf_Sun_Wave_CSM_Ray_Matrix_V3_Win64'
a.out.mkdir(parents=True,exist_ok=True)
out=a.out/(name+'.zip')
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
 for relname,b in sorted(entries.items()):
  inf=zipfile.ZipInfo(name+'/'+relname,date_time=(2026,10,27,0,0,0));inf.compress_type=zipfile.ZIP_DEFLATED;z.writestr(inf,b)
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 final={n.split('/',1)[1]:z.read(n) for n in z.namelist()}
 assert H(final[rel])==H(newdll)
 for n,b in original.items():
  relative=n.split('/',1)[1]
  if relative not in (rel,'docs/SHA256SUMS.txt'): assert final[relative]==b
assert len(entries)==len(original)+10
sha=H(out.read_bytes())
(a.out/(out.name+'.sha256')).write_text(sha+'  '+out.name+'\n')
(a.out/'SUN_WAVE_V3_VERIFICATION.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('DW_SUN_WAVE_V3_PACKAGE_PASS',str(out),'archive_sha256='+sha,'dll_sha256='+H(newdll),'preserved_original_files='+str(len(original)-2))