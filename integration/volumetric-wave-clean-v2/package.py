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
accepted_zip_sha='05e6d68fe1b59924f074b18a2e60e54fee79bd4d39fb151a4978f5f6a406c8eb'
accepted_renderer_sha='0809d44cce520d36514e6dd60c82cc3504b520217a5c867dfbee2efa8471eef8'
base=a.base_zip.read_bytes()
assert H(base)==accepted_zip_sha,('WRONG_BASE_ARCHIVE',H(base))
newdll=a.renderer.read_bytes()
assert newdll[:2]==b'MZ' and len(newdll)>2000000
assert H(newdll)!=accepted_renderer_sha
proof=json.loads(a.proof.read_text())
assert proof['marker']=='DARKWOLF_VOLUMETRIC_WAVE_CLEAN_V2_20261027'
assert proof['before_sha256']['tr_backend.c']=='505ef716a0e316a99f00f0ce8d2e4e81ecef650424bfd22a537227ffbfbb37ba'
assert sorted(proof['modified_files'])==sorted(['SP/code/rend2/'+p for p in ('tr_backend.c','tr_init.c','glsl/volumetricsun_fp.glsl','glsl/volumetriclocal_fp.glsl','glsl/volumetriclocal_upscale_fp.glsl')])
with zipfile.ZipFile(io.BytesIO(base)) as z:
 original={i.filename:z.read(i) for i in z.infolist() if not i.is_dir()}
 assert len(original)==30
assert len({x.split('/')[0] for x in original})==1
root=next(iter(original)).split('/')[0]
assert all(p.startswith(root+'/') and '..' not in Path(p).parts for p in original)
assert root=='DarkWolf_Sky_Portal_Universal_Single_Sample_V1_Win64'
rel='renderer_sp_rend2_x64.dll';full=root+'/'+rel
assert H(original[full])==accepted_renderer_sha
for f in ('ioWolfSP.x64.exe','renderer_sp_opengl1_x64.dll','Main/cgame_sp_x64.dll','Main/qagame_sp_x64.dll','Main/ui_sp_x64.dll','SDL264.dll','OpenAL64.dll'):
 assert root+'/'+f in original
assert not any(re.search(r'(^|/)pak[0-9]*\.pk3$',n,re.I) for n in original)
entries={name.split('/',1)[1]:b for name,b in original.items()}
entries[rel]=newdll
manifest={
 'status':'CI_COMPILE_CANDIDATE__GPU_RUNTIME_PENDING',
 'candidate':'DARKWOLF_VOLUMETRIC_WAVE_CLEAN_V2_20261027',
 'accepted_base_run_id':40480112714,
 'accepted_base_zip_sha256':accepted_zip_sha,
 'accepted_renderer_sha256':accepted_renderer_sha,
 'new_renderer_sha256':H(newdll),
 'source':proof,
 'changed_existing_files':[rel,'docs/SHA256SUMS.txt'],
 'unchanged_existing_files_count':len(original)-2,
 'runtime_visual_test':'NOT_TESTED',
 'preserved_sky_single_sample':'DARKWOLF_PORTAL_SKY_SINGLE_SAMPLE_UNIVERSAL_V1',
 'not_yet_user_accepted':True
}
entries['docs/VOLUMETRIC_WAVE_CLEAN_V2_MANIFEST.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf8')
modes={
 'DW_VOLWAVE_B_LOW_COST.cfg':(32,24,1,1),
 'DW_VOLWAVE_C_MORE_STEPS.cfg':(48,40,1,1),
 'DW_VOLWAVE_D_DEPTH_5X5.cfg':(48,40,1,2),
 'DW_VOLWAVE_E_FIRE_9TAP.cfg':(48,40,2,2),
 'DW_VOLWAVE_F_PERF_CONTROL.cfg':(24,24,1,1)
}
for fname,(sun,fire,pcf,upscale) in modes.items():
 cfg='// DarkWolf Volumetric Wave V2 controlled test\n'
 cfg+='seta r_volumetricSunSamples "%d"\n' % sun
 cfg+='seta r_volumetricFireSamples "%d"\n' % fire
 cfg+='seta r_volumetricLocalShadowPcf "%d"\n' % pcf
 cfg+='seta r_volumetricFireUpscale "%d"\n' % upscale
 cfg+='seta r_volumetricSunJitter "0.08"\n'
 cfg+='seta r_volumetricLocalJitter "0.08"\n'
 cfg+='seta cg_drawFPS "1"\n'
 entries['Main/'+fname]=cfg.encode('ascii')
entries['README_VOLUMETRIC_WAVE_CLEAN_V2_RU.txt']=(
 'DarkWolf ioRTCW Rend2 Single Player - Volumetric Wave Clean V2\n'
 'Exact base: 40480112714, Universal Portal Sky Single-Sample V1 preserved.\n'
 'The original accepted archive is REFERENCE A. Keep it in a separate folder.\n'
 'B new shader/noise/AA at reference ray sample counts: exec DW_VOLWAVE_B_LOW_COST.cfg\n'
 'C more ray samples: exec DW_VOLWAVE_C_MORE_STEPS.cfg\n'
 'D depth-aware Fire 5x5: exec DW_VOLWAVE_D_DEPTH_5X5.cfg\n'
 'E fire-only 9-tap shadow PCF: exec DW_VOLWAVE_E_FIRE_9TAP.cfg\n'
 'F perf control: exec DW_VOLWAVE_F_PERF_CONTROL.cfg\n'
 'Use the SAME saves, camera angles, HDR, MSAA, exposure and resolution for all modes.\n'
 'Sun: test screenshots 1/2, look for repeated wavy rays/CSM edge patterns.\n'
 'Fire: test screenshots 3/4 and player-shadow interference in 5/6/7.\n'
 'Record screenshot and FPS for each mode; capture moving-wave video if possible.\n'
 'If C helps: ray-step aliasing. If D helps: upscale. If E helps: point-shadow PCF.\n'
 'E requires an eligible shadowed fire source and a resident point-shadow slot.\n'
 'Quality C/D/E has higher GPU cost. Revert to accepted #404801 if regression appears.\n'
 'This candidate has CI tests only; runtime GPU quality is NOT YET CONFIRMED.\n'
 'Copy original commercial RTCW assets locally; never distribute commercial pak*.pk3.\n'
).encode('utf8')
# The accepted Sky ZIP carries a historical renderer SHA in SHA256SUMS.
# Refresh checksum manifest so the new release does not falsely validate the old DLL.
entries['docs/SHA256SUMS.txt']=(''.join(H(v)+'  '+k+'\n' for k,v in sorted(entries.items()) if k!='docs/SHA256SUMS.txt')).encode('ascii')

name='DarkWolf_Sky_Portal_Volumetric_Wave_Clean_V2_Win64'
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
assert len(entries)==37
sha=H(out.read_bytes())
(a.out/(out.name+'.sha256')).write_text(sha+'  '+out.name+'\n')
(a.out/'VOLUMETRIC_WAVE_CLEAN_V2_VERIFICATION.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('DW_VOLWAVE_CLEAN_40480112714_ARCHIVE_PASS',str(out),'archive_sha256='+sha,'dll_sha256='+H(newdll),'preserved_original_files='+str(len(original)-2))