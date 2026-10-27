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
assert proof['marker']=='DARKWOLF_VOL_OVERLAP_DIAG_V1_20261027'
assert proof['sha256_before']['tr_backend.c']=='0cfcad4ad18882691f16749697d09a48e832b9344de4e58a11e36c3b7efb405e'
assert proof['sha256_before']['glsl/volumetriclocal_fp.glsl']=='ef616bfc50be66a048fe0817971e4308574ff91cab4393185f6153999dd26a67'
assert sorted(proof['modified_files'])==sorted(['SP/code/rend2/tr_backend.c','SP/code/rend2/glsl/volumetriclocal_fp.glsl'])
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
 'candidate':'DARKWOLF_VOL_OVERLAP_DIAG_V1_20261027',
 'accepted_base_run_id':40487188767,
 'accepted_base_zip_sha256':accepted_zip_sha,
 'accepted_renderer_sha256':accepted_renderer_sha,
 'new_renderer_sha256':H(newdll),
 'source':proof,
 'changed_existing_files':[rel,'docs/SHA256SUMS.txt'],
 'unchanged_existing_files_count':len(original)-2,
 'runtime_visual_test':'NOT_TESTED',
 'preserved_sky_single_sample':True,
 'preserved_fire_e_with_separate_local_pcf':True,
 'not_yet_user_accepted':True
}
entries['docs/VOLUMETRIC_OVERLAP_DIAGNOSTIC_V1_MANIFEST.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf8')
profiles=[
 ('1_SUN_QUARTER_CSM2',1,0,2,0,0,1,0),
 ('2_SUN_FULLRES_CSM2',1,1,2,0,0,1,0),
 ('3_SUN_QUARTER_PCF0',1,0,0,0,0,1,0),
 ('4_LOCAL_REFERENCE',0,0,2,5,0,1,0),
 ('5_LOCAL_5X5',0,0,2,5,1,1,0),
 ('6_LOCAL_5X5_9TAP',0,0,2,5,1,2,0),
 ('7_LOCAL_FULLRES_9TAP',0,0,2,5,2,2,0),
 ('8_BOTH_REFERENCE',1,0,2,5,0,1,0),
 ('9_BOTH_LOCAL_CLEAN',1,0,2,5,1,2,0),
 ('0_FIRE_E_CONTROL',1,0,2,5,0,1,1)
]
for name,sun,sunFull,pcf,local,localSpatial,lampPcf,fire in profiles:
 cfg=(f'// DARKWOLF_VOL_OVERLAP_DIAG_V1_20261027 {name}\n'
      f'seta r_volumetricSunMode "{sun}"\n'
      f'seta r_dwVolSunFullresDiag "{sunFull}"\n'
      f'seta r_volumetricSunShadowPcf "{pcf}"\n'
      f'seta r_volumetricLocalMode "{local}"\n'
      f'seta r_dwVolLocalSpatialDiag "{localSpatial}"\n'
      f'seta r_dwVolLocalLampPcfDiag "{lampPcf}"\n'
      f'seta r_volumetricFire "{fire}"\n'
      'seta r_volumetricFireSamples "40"\n'
      'seta r_volumetricFireUpscale "2"\n'
      'seta r_volumetricLocalShadowPcf "2"\n'
      'seta r_volumetricLocalSamples "24"\n'
      'seta r_volumetricSunSamples "32"\n'
      'seta r_volumetricLocalJitter "0.08"\n'
      'seta r_volumetricSunJitter "0.08"\n'
      'seta cg_drawFPS "1"\n')
 entries['Main/DW_VOL_DIAG_'+name+'.cfg']=cfg.encode('ascii')
readme="""DARKWOLF SUN / LOCAL / FIRE VOLUMETRIC DIAGNOSTIC V1 - NOT PRODUCTION
Exact base: #40487188767 Wave Clean V2, itself from accepted Sky #40480112714.
The accepted Fire E GPU result is preserved; no Sun shader or CSM producer change.
This renderer contains optional full-resolution modes with higher GPU cost.
Use the same save, camera angle, resolution, exposure, HDR, MSAA and lighting source.
Use a real learned lamp/spotlight for Local tests; otherwise Local can be invisible.
Master r_volumetricSun and r_volumetricLocal are latched; ensure both are 1 and vid_restart once.
Select a numbered CFG with RUN_VOL_DIAG.cmd or exec DW_VOL_DIAG_<name>.cfg.

SUN GROUP:
1: Sun only / quarter / CSM volumetric PCF2.
2: Sun only / full-resolution raymarch / same CSM PCF2.
3: Sun only / quarter / volumetric PCF0 (THIS DOES NOT DISABLE CSM).
If 1 bad, 2 clean: source pixel sampling implicated.
If 1 bad, 2 bad, 3 clean: CSM shadow sampling/PCF implicated.
If 1,2,3 bad: other CSM cascade/ray-integral mechanism remains.

LOCAL GROUP:
4: Local only / quarter / accepted AA / lamp 5-tap PCF.
5: Local only / quarter / depth-aware 5x5 / lamp 5-tap PCF.
6: Local only / quarter / depth-aware 5x5 / lamp 9-tap PCF.
7: Local only / direct full-resolution / lamp 9-tap PCF (EXPENSIVE).
4 bad / 5 clean: upscale/reconstruction implicated.
5 bad / 6 clean: lamp cubemap PCF implicated.
6 bad / 7 clean: low-resolution Local producer implicated.

COMPOSITE GROUP:
8: Sun+Local / baseline local.
9: Sun+Local / clean local 5x5 + 9-tap.
Compare 1 vs 4 vs 8, then 1 vs 6 vs 9.
If separate sources clean but combination banded, analyze HDR additive energy and tone mapping.
Local and Sun do not directly multiply their shadow masks; they sum before tone mapping.

FIRE E CONTROL:
0: User-preferred Fire E: 40 steps, upscale 2 (5x5), PCF2 (fire-only 9 taps).
This is a GPU regression control, NOT a new Fire optimization.
Shadowed lamps/fire must have a resident point-shadow slot for PCF testing.

Capture stable-position PNGs and moving camera video for wave/shimmer.
For FPS record 10s same camera and compare relative frame times.
No commercial game pak files are bundled. CI success is not GPU runtime acceptance.
"""
entries['README_VOL_OVERLAP_DIAGNOSTIC_RU.txt']=readme.encode('utf8')
cmd='@echo off\nsetlocal EnableExtensions DisableDelayedExpansion\ncd /d "%~dp0"\n'
cmd+='if not exist "ioWolfSP.x64.exe" exit /b 1\n'
cmd+='set /p CHOICE=Select 1..9 or 0 (see README_VOL_OVERLAP_DIAGNOSTIC_RU.txt): \n'
cmd+='set "CFG="\n'
for name,*_ in profiles:
 cmd+=f'if "%CHOICE%"=="{name[0]}" set "CFG=DW_VOL_DIAG_{name}.cfg"\n'
cmd+='if "%CFG%"=="" (echo Invalid mode & exit /b 1)\n'
cmd+='set "DW_HOME=%CD%\\DW_September_FourWeek_Home"\n'
cmd+='if not exist "%DW_HOME%\\Main" mkdir "%DW_HOME%\\Main"\n'
cmd+='"%CD%\\ioWolfSP.x64.exe" +set fs_basepath "%CD%" +set fs_homepath "%DW_HOME%" +set cl_renderer rend2 +set r_renderer rend2 +exec %CFG%\n'
cmd+='exit /b %errorlevel%\n'
entries['RUN_VOL_DIAG.cmd']=cmd.encode('ascii')
entries['docs/SHA256SUMS.txt']=(''.join(H(v)+'  '+k+'\n' for k,v in sorted(entries.items()) if k!='docs/SHA256SUMS.txt')).encode('ascii')

name='DarkWolf_Sun_Local_Overlap_Diagnostic_V1_Win64'
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
assert len(entries)==len(original)+13
sha=H(out.read_bytes())
(a.out/(out.name+'.sha256')).write_text(sha+'  '+out.name+'\n')
(a.out/'VOLUMETRIC_OVERLAP_DIAG_V1_VERIFICATION.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('DW_VOL_OVERLAP_DIAG_V1_ARCHIVE_PASS',str(out),'archive_sha256='+sha,'dll_sha256='+H(newdll),'preserved_original_files='+str(len(original)-2))