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
accepted_zip_sha='cabbf853370ba544cc13eca4467dba3be855cf9525b36bd610620e1777a2ead5'
accepted_renderer_sha='11a67525c3f930165391912aced7358d8f827a1669700230c6b4672a253cf2f0'
base=a.base_zip.read_bytes()
assert H(base)==accepted_zip_sha,('WRONG_BASE_ARCHIVE',H(base))
newdll=a.renderer.read_bytes()
assert newdll[:2]==b'MZ' and len(newdll)>2000000
assert H(newdll)!=accepted_renderer_sha
proof=json.loads(a.proof.read_text())
assert proof['status']=='APPLIED'
assert proof['files_changed']==['SP/code/rend2/tr_backend.c']
assert proof['candidate']=='DARKWOLF_PORTAL_SKY_SINGLE_SAMPLE_UNIVERSAL_V1'
assert 'any_map_with_eligible_portal_sky' in proof['conditions']
with zipfile.ZipFile(io.BytesIO(base)) as z:
 original={i.filename:z.read(i) for i in z.infolist() if not i.is_dir()}
 assert len(original)==28
assert len({x.split('/')[0] for x in original})==1
root=next(iter(original)).split('/')[0]
assert all(p.startswith(root+'/') and '..' not in Path(p).parts for p in original)
rel='renderer_sp_rend2_x64.dll';full=root+'/'+rel
assert H(original[full])==accepted_renderer_sha
for f in ('ioWolfSP.x64.exe','renderer_sp_opengl1_x64.dll','Main/cgame_sp_x64.dll','Main/qagame_sp_x64.dll','Main/ui_sp_x64.dll','SDL264.dll','OpenAL64.dll'):
 assert root+'/'+f in original
assert not any(re.search(r'(^|/)pak[0-9]*\.pk3$',n,re.I) for n in original)
entries={name.split('/',1)[1]:b for name,b in original.items()}
entries[rel]=newdll
manifest={
 'status':'WIN64_COMPILE_AND_SOURCE_GATES_PASSED__OTHER_MAPS_GPU_REGRESSION_PENDING',
 'candidate':'DARKWOLF_PORTAL_SKY_SINGLE_SAMPLE_UNIVERSAL_V1',
 'accepted_base_run_id':40294211216,
 'accepted_base_zip_sha256':accepted_zip_sha,
 'accepted_renderer_sha256':accepted_renderer_sha,
 'new_renderer_sha256':H(newdll),
 'source':proof,
 'changed_existing_files':[rel],
 'unchanged_existing_files_count':len(original)-1,
 'requested_visual_test':'Confirm universal portal-sky on non-Trainyard/Factory maps; accepted Trainyard/Factory success was reported with prior restricted candidate',
 'not_yet_user_accepted':True,
}
entries['docs/SKY_PORTAL_UNIVERSAL_SINGLE_SAMPLE_MANIFEST.json']=json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf8')
entries['README_SKY_PORTAL_UNIVERSAL_SINGLE_SAMPLE_RU.txt']=(
 'DarkWolf Universal Portal Sky Single-Sample Composite V1\n'
 'Based exactly on accepted Actions #40294211216.\n'
 'The portal-only, map-independent pipeline is the exact visual fix confirmed\n'
 'on Trainyard/Factory in GitHub Actions #40477324252, with the name filter removed.\n'
 'On ANY map: when the renderer uses an eligible portal sky with HDR, MSAA\n'
 'and framebuffer blit, sky is rendered single-sample and copied into all MSAA\n'
 'samples before the regular world passes. Main 8x MSAA world is unchanged.\n'
 'Maps without eligible portal sky continue through the accepted original path.\n'
 'No map names hardcoded; no user commands needed; no graphics settings disabled.\n'
 'CSM, SSGI, volumetrics, smoke, Tesla, postprocess, original FBO/depth are kept.\n'
 'Only original renderer_sp_rend2_x64.dll is replaced. All other accepted\n'
 'existing game files are byte-identical to Actions #40294211216.\n'
 'Test on several other portal-sky maps for edge effects and MSAA regressions.\n'
 'Use separate folder with original Main/pak*.pk3 and the existing RUN BAT.\n'
 'Console marker: DW_PORTAL_SKY_SINGLE_SAMPLE_ACTIVE map=...\n'
).encode('utf8')
name='DarkWolf_Sky_Portal_Universal_Single_Sample_V1_Win64'
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
  if relative!=rel: assert final[relative]==b
assert len(entries)==30
sha=H(out.read_bytes())
(a.out/(out.name+'.sha256')).write_text(sha+'  '+out.name+'\n')
(a.out/'SKY_SINGLE_SAMPLE_FIX_VERIFICATION.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('DW_SKY_PORTAL_UNIVERSAL_CLEAN_ARCHIVE_PASS',str(out),'archive_sha256='+sha,'dll_sha256='+H(newdll),'preserved_original_files='+str(len(original)-1))