#!/usr/bin/env python3
"""Byte-pinned public native renderer artifact package. Licensed maps are excluded."""
import hashlib,io,json,sys,zipfile
from pathlib import Path
ROOT='DarkWolf_Hybrid_Relight_V2_Native_Rend2_Win64'
OLD='DarkWolf_Volumetric_Sun_HDR16F_Precision_V1_Clean_Production_Win64'
A='6385f719eb29bfa2c4edd172cadc9b95b6c5f3d107d7e0e088ed25769a8df57f'
I='e61a38fec90fbdece43364232c0064e40825eb86db7c035df9a46cddcf2cc869'
D='d7423e8648e2de556f79c7cddecf1a8df16b9f60a46c503d1440089876116b45'
TIERS=('PERFORMANCE','BALANCED','QUALITY','HIGH','ULTRA')
def sha(x):return hashlib.sha256(x).hexdigest()
def need(v,e):
    if not v:raise AssertionError(e)
def make(source,dll,out):
    need(not out.exists(),'release exists')
    data=source.read_bytes()
    need(sha(data)==A,'Not exact accepted Actions 41019985033')
    with zipfile.ZipFile(io.BytesIO(data)) as outer:
        need(outer.testzip() is None,'Bad outer zip')
        body=outer.read('dist/'+OLD+'.zip')
    need(sha(body)==I,'Not exact approved nested production')
    with zipfile.ZipFile(io.BytesIO(body)) as z:
        need(z.testzip() is None,'Bad production archive')
        files={p[len(OLD)+1:]:z.read(p) for p in z.namelist() if not p.endswith('/')}
    need(len(files)==57 and sha(files['renderer_sp_rend2_x64.dll'])==D,'Not exact approved 57-file clean production')
    original=dict(files)
    blob=dll.read_bytes()
    need(len(blob)>1000000 and sha(blob)!=D,'Native renderer missing or unchanged')
    for marker in [b'r_dwHybridRelight',b'r_dwHybridRelightStrength',b'DW_HYBRID_V2:',b'_dwSunHalfRGBA16F']:
        need(marker in blob,'Missing accepted/native compiled marker '+str(marker))
    files['renderer_sp_rend2_x64.dll']=blob
    for tier in TIERS:
        files['Main/DW_HYBRID_NATIVE_V2_'+tier+'.cfg']=(f'''// Opt-in Native V2; old maplighting disabled
exec DW_HDR16F_V1_{tier}.cfg
seta r_hdr "1"
seta r_forceSun "1"
seta r_dlightMode "2"
seta r_staticPromote "1"
seta r_staticPromoteMaxLights "32"
seta r_dlightShadowMaxLights "3"
seta r_mapLightingOverride "0"
seta r_mapLightingProfileEnable "0"
seta r_mapLightingAutoload "0"
seta r_mapLightingLearn "0"
seta r_dwHybridRelight "1"
seta r_dwHybridRelightStrength "1.0"
''').encode()
    files['Main/DW_HYBRID_NATIVE_V2_OFF.cfg']=b'seta r_dwHybridRelight "0"\n'
    files['README_DW_HYBRID_NATIVE_V2.txt']=(b'''DarkWolf Hybrid Relight V2 Native Rend2, development-candidate Win64.
Base #41019985033. One renderer_sp_rend2_x64.dll is rebuilt;
every other original accepted file is byte-preserved.

Default r_dwHybridRelight 0; no lighting assets are modified automatically.
An additional PRIVATE PK3 with maps/<map>/dwrl_XXXX.hdr and
maps/<map>/dwrl_v2.manifest is needed for any real visual change.
These licensed-game-derived assets are NOT uploaded to public GitHub.
Use only NEW zz_dw_hybrid_native_v2_*.pk3 packs, not the old
zz_dw_hybrid_v2_*.pk3 with lm_XXXX.hdr: old packs bypass the cvar.

With licensed game pak*.pk3 and new optional private map packs in Main:
  /exec DW_HYBRID_NATIVE_V2_QUALITY.cfg
  /vid_restart
  /spdevmap norway
Check console: DW_HYBRID_V2: map=norway active=1
To disable:
  /exec DW_HYBRID_NATIVE_V2_OFF.cfg
  /vid_restart
  /spdevmap norway
Strength [0,1]: /seta r_dwHybridRelightStrength 0.50
Changes are evaluated at map LOAD, not per-frame.
Only one surface per tested map is supported initially.
This is bounded source-guided stock lightmap adjustment, NOT exact
historical RTCW direct/indirect light decomposition.
User GPU visual validation is still required.
''')
    need(sum(files[k]!=v for k,v in original.items())==1,'Accepted source release modified unexpectedly')
    need(all(files[k]==v for k,v in original.items() if k.endswith(('.exe','.dll')) and k!='renderer_sp_rend2_x64.dll'),
         'Other accepted binaries modified')
    metadata={'source_run':41019985033,'source_branch_commit':'c653433e1b0a29b2f43f29a240b96a8192acb617',
              'base_renderer_sha256':D,'native_renderer_sha256':sha(blob),
              'original_files_preserved':56,'only_replaced_binary':'renderer_sp_rend2_x64.dll',
              'opt_in':True,'native_default_off':True,
              'private_map_assets_in_public_archive':False,'user_runtime_validation':'PENDING'}
    files['docs/DW_HYBRID_NATIVE_RELEASE_PROOF.json']=(json.dumps(metadata,indent=2)+'\n').encode()
    files['docs/DW_HYBRID_NATIVE_SHA256SUMS.txt']=''.join(f'{sha(files[k])}  {k}\n' for k in sorted(files) if k!='docs/DW_HYBRID_NATIVE_SHA256SUMS.txt').encode()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for k,v in sorted(files.items()):
            info=zipfile.ZipInfo(ROOT+'/'+k,(2026,10,30,12,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,v)
    with zipfile.ZipFile(out) as z:
        need(z.testzip() is None and len(z.namelist())==len(files),'Broken release zip')
    (out.parent/(out.name+'.sha256')).write_text(sha(out.read_bytes())+'  '+out.name+'\n')
    (out.parent/'NATIVE_RELEASE_PROOF.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print('DW_HYBRID_NATIVE_PRODUCTION_PACKAGE_PASS',sha(out.read_bytes()))
if __name__=='__main__':
    need(len(sys.argv)==4,'usage: pack accepted_actions_zip renderer_dll output.zip')
    make(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]))
