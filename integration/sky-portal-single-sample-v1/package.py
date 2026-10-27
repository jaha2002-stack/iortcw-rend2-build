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
 'status':'WIN64_COMPILE_AND_SOURCE_GATES_PASSED__GPU_TEST_PENDING',
 'candidate':'DARKWOLF_PORTAL_SKY_SINGLE_SAMPLE_COMPOSITE_V1',
 'accepted_base_run_id':40294211216,
 'accepted_base_zip_sha256':accepted_zip_sha,
 'accepted_renderer_sha256':accepted_renderer_sha,
 'new_renderer_sha256':H(newdll),
 'source':proof,
 'changed_existing_files':[rel],
 'unchanged_existing_files_count':len(original)-1,
 'requested_visual_test':'Trainyard and Factory same viewpoints 8x MSAA, confirm absence of dashes',
 'not_yet_user_accepted':True,
}
entries['docs/SKY_PORTAL_SINGLE_SAMPLE_FIX_MANIFEST.json']=json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf8')
entries['README_SKY_PORTAL_SINGLE_SAMPLE_RU.txt']=(
 'DarkWolf Sky Portal Single-Sample Composite V1 (GPU candidate)\n'
 'Based exactly on accepted Actions #40294211216.\n'
 'Trainyard/Factory portal sky renders in single-sampled HDR, then replicates\n'
 'its color into all MSAA samples of the standard 8x world framebuffer.\n'
 'World MSAA 8x, HDR, fog, CSM, SSGI, Tesla, Volumetric, UI stay enabled.\n'
 'Only existing renderer_sp_rend2_x64.dll is replaced.\n'
 'Use a SEPARATE folder with your original Main/pak*.pk3 resources.\n'
 'Run RUN_DARKWOLF_SEPTEMBER_FOURWEEK.bat; test Trainyard and Factory at MSAA 8x.\n'
 'This is not proven on your graphics card until you test it.\n'
 'Console log marker: DW_PORTAL_SKY_SINGLE_SAMPLE_ACTIVE map=...\n'
).encode('utf8')
name='DarkWolf_Sky_Portal_Single_Sample_Composite_V1_Win64'
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
print('DW_SKY_PORTAL_SINGLE_SAMPLE_CLEAN_ARCHIVE_PASS',str(out),'archive_sha256='+sha,'dll_sha256='+H(newdll),'preserved_original_files='+str(len(original)-1))