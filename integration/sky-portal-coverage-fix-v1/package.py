#!/usr/bin/env python3
"""Seal a candidate release with *only* the Win64 rend2 DLL replaced."""
import argparse,hashlib,io,json,re,zipfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--base-zip',type=Path,required=True)
p.add_argument('--renderer',type=Path,required=True)
p.add_argument('--proof',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
H=lambda d:hashlib.sha256(d).hexdigest()
base=a.base_zip.read_bytes()
accepted_zip_sha='cabbf853370ba544cc13eca4467dba3be855cf9525b36bd610620e1777a2ead5'
accepted_renderer_sha='11a67525c3f930165391912aced7358d8f827a1669700230c6b4672a253cf2f0'
assert H(base)==accepted_zip_sha,('BASE_ARCHIVE_SHA_MISMATCH',H(base))
renderer=a.renderer.read_bytes(); assert renderer[:2]==b'MZ' and len(renderer)>1000000
assert H(renderer)!=accepted_renderer_sha,'NO_CHANGE_TO_RENDERER'
proof=json.loads(a.proof.read_text()); assert proof['status']=='APPLIED'
assert proof['files_changed']==['SP/code/rend2/tr_sky.c']
with zipfile.ZipFile(io.BytesIO(base)) as z:
    original={i.filename:z.read(i) for i in z.infolist() if not i.is_dir()}
    assert len(original)==28,('ORIGINAL_INNER_COUNT_CHANGED',len(original))
root=next(iter(set(n.split('/')[0] for n in original)))
assert all(n.startswith(root+'/') and '..' not in Path(n).parts for n in original)
rpath=root+'/renderer_sp_rend2_x64.dll'
assert H(original[rpath])==accepted_renderer_sha
for x in ('ioWolfSP.x64.exe','renderer_sp_opengl1_x64.dll','Main/cgame_sp_x64.dll','Main/qagame_sp_x64.dll','Main/ui_sp_x64.dll','SDL264.dll','OpenAL64.dll'):
    assert root+'/'+x in original
assert not any(re.search(r'(^|/)pak[0-9]*\.pk3$',n,re.I) for n in original)
newroot='DarkWolf_Sky_Portal_MSAA_Coverage_Candidate_V1_Win64'
rep={n.split('/',1)[1]:bytes(v) for n,v in original.items()}
rep['renderer_sp_rend2_x64.dll']=renderer
for old,oldbytes in original.items():
    rel=old.split('/',1)[1]
    if rel!='renderer_sp_rend2_x64.dll': assert rep[rel]==oldbytes
manifest={
 'status':'WIN64_CI_BUILT_SOURCE_VALIDATED_GPU_ACCEPTANCE_PENDING',
 'candidate':'DARKWOLF_SKY_PORTAL_CLOUD_COVERAGE_CANDIDATE_V1',
 'accepted_base':{'run_id':40294211216,'zip_sha256':accepted_zip_sha,'renderer_sha256':accepted_renderer_sha},
 'updated':{'renderer_sha256':H(renderer),'source_patch':proof},
 'changed_existing_files':['renderer_sp_rend2_x64.dll'],
 'unchanged_existing_files_count':len(original)-1,
 'compiled_gpu_verified':False,'user_visual_acceptance':'PENDING',
 'known_scope':'cloud-only sky portal on trainyard/factory with HDR MSAA, original sky materials retained',
 'notes':'Existing docs/SHA256SUMS.txt belongs to the immutable accepted base. See this manifest for new renderer checksum.'
}
rep['docs/SKY_PORTAL_MSAA_COVERAGE_CANDIDATE_MANIFEST.json']=json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8')
rep['README_SKY_PORTAL_MSAA_CANDIDATE_RU.txt']=(
'DarkWolf / Sky Portal MSAA Coverage Candidate V1\n'
'Base: user-accepted Actions #40294211216 (all game binaries except renderer byte identical).\n'
'Only modified existing file: renderer_sp_rend2_x64.dll.\n'
'For Trainyard / Factory portal-sky cloud shader, use five complete sky cube faces\n'
'in the HDR+MSAA framebuffer; original materials, colors, alpha and fog remain.\n'
'This is a single candidate GPU TEST, not yet a game-proven production fix.\n'
'Install in an independent folder; add your legally owned Main/pak*.pk3 assets.\n'
'Use the existing RUN_DARKWOLF_SEPTEMBER_FOURWEEK.bat launcher.\n'
'Save screenshots at the same camera coordinates as the accepted build.\n').encode('utf-8')
a.out.mkdir(parents=True,exist_ok=True)
output=a.out/(newroot+'.zip')
with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
    for n,d in sorted(rep.items()):
        info=zipfile.ZipInfo(newroot+'/'+n,date_time=(2026,10,27,0,0,0))
        info.compress_type=zipfile.ZIP_DEFLATED
        z.writestr(info,d)
with zipfile.ZipFile(output) as z:
    assert z.testzip() is None
    entries={n.split('/',1)[1]:z.read(n) for n in z.namelist()}
    assert H(entries['renderer_sp_rend2_x64.dll'])==H(renderer)
    for old,oldbytes in original.items():
        rel=old.split('/',1)[1]
        if rel!='renderer_sp_rend2_x64.dll':assert entries[rel]==oldbytes
assert len(original)==28 and len(entries)==30
(a.out/(output.name+'.sha256')).write_text(H(output.read_bytes())+'  '+output.name+'\n')
(a.out/'SKY_PORTAL_MSAA_COVERAGE_CANDIDATE_VERIFICATION.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('DW_SKY_PORTAL_COVERAGE_CANDIDATE_CLEAN_ARCHIVE_PASS',output,H(output.read_bytes()),'DLL',H(renderer),'UNTOUCHED',len(original)-1)