#!/usr/bin/env python3
"""Promote the EXACT #40633659668 PCF2x2 DLL to a frozen clean production zip.

No shader or binary recompile: this is ONLY a deterministic release repack.
"""
import argparse,hashlib,io,json,re,struct,zipfile
from pathlib import Path
BASE_RUN=40633659668
BASE_SHA='39edc613d4cbeb2b40bd04e5da7895df84ec998f09ccb9eaff663d283e363466'
RENDERER_SHA='1d27de162dff6328c1504781edd973fa286289101a0557a1012252d618804c47'
ORIGIN_ROOT='DarkWolf_Sun3_FireE_Crypt1_WorldGate_PCF2x2_Clean_Candidate_Win64'
RELEASE_ROOT='DarkWolf_Sun3_FireE_Crypt1_Shadow_Fidelity_Clean_Production_Win64'
RELEASE_MARK='DARKWOLF_CRYPT1_SHADOW_FIDELITY_FREEZE_PRODUCTION_V1_20261028'
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--base-zip',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    original_bytes=a.base_zip.read_bytes()
    assert sha(original_bytes)==BASE_SHA,('INCORRECT_BASIS',sha(original_bytes))
    with zipfile.ZipFile(io.BytesIO(original_bytes)) as z:
        assert z.testzip() is None
        source={info.filename:z.read(info) for info in z.infolist() if not info.is_dir()}
    assert len(source)==37,('BASIS_FILE_COUNT',len(source))
    assert all(k.startswith(ORIGIN_ROOT+'/') and '..' not in Path(k).parts for k in source)
    old={k[len(ORIGIN_ROOT)+1:]:v for k,v in source.items()}
    renderer=old['renderer_sp_rend2_x64.dll']
    assert sha(renderer)==RENDERER_SHA
    pe_offset=struct.unpack_from('<I',renderer,0x3c)[0]
    assert renderer[:2]==b'MZ' and renderer[pe_offset:pe_offset+4]==b'PE\x00\x00'
    assert struct.unpack_from('<H',renderer,pe_offset+4)[0]==0x8664,'RENDERER_NOT_X64'
    for rel in ('ioWolfSP.x64.exe','RUN_DARKWOLF_SEPTEMBER_FOURWEEK.bat',
                'renderer_sp_opengl1_x64.dll','Main/DW_SUN3_FIRE_E_PRODUCTION.cfg',
                'Main/cgame_sp_x64.dll','Main/qagame_sp_x64.dll','Main/ui_sp_x64.dll',
                'docs/CRYPT1_WORLD_GATE_PCF2X2_MANIFEST.json'):
        assert rel in old,('MISSING_OLDER_FILE',rel)
    assert not any(re.search(r'(^|/)pak[0-9]*\.pk3$',k,re.IGNORECASE) for k in old)
    previous_manifest=json.loads(old['docs/CRYPT1_WORLD_GATE_PCF2X2_MANIFEST.json'])
    assert previous_manifest['new_renderer_sha256']==RENDERER_SHA
    assert previous_manifest['source']['marker']=='DARKWOLF_CRYPT1_ARCHITECTURAL_WORLD_VISIBILITY_PCF2X2_V1_20261028'
    assert previous_manifest['no_new_cvars'] and previous_manifest['no_telemetry']
    assert previous_manifest['source']['accepted_binary_base_run']==40628480022
    assert previous_manifest['test_results']['GLSL_versions']==[120,130]

    cfg='''// DarkWolf frozen Crypt1 shadow fidelity production profile.
// Reapply existing Sun3 + Fire E settings and retain the corrected world gate.
// Existing compiled implementation and all shading parameters are unchanged.
exec DW_SUN3_FIRE_E_PRODUCTION.cfg
seta r_dlightWorldContainment "2"
'''
    readme='''DARKWOLF / ioRTCW Rend2 - Crypt1 Shadow Fidelity Clean Production V1
====================================================================
Frozen renderer from successful GitHub Actions #40633659668 (Oct 28, 2026).
Graphics DLL SHA-256: 1d27de162dff6328c1504781edd973fa286289101a0557a1012252d618804c47
This is EXACTLY the previously user-tested PCF2x2 renderer. No rebuild, new
shader, modified game binary, new CVar, diagnostic mode or telemetry.

RETAINED SUCCESS: Crypt1 architectural shadow mask has 2x2 filtered depth
comparisons; the main point-shadow PCF remains unchanged, as do Sun3, Fire E,
Local Volumetric, Sky Single-Sample, StaticPromote, SSGI, CSM and Tesla code.

KNOWN UNRESOLVED ISSUES: At r_dlightWorldContainment 2, the Crypt1 shadows
may look slightly thick/coarse compared with setting 0. On Xlabs, the blue
stationary Tesla illumination is subdued/lost (while physical containment
works). Escape1 stove light still slightly leaks at an exterior wall.
These are documented for the NEXT separate investigation; NOT fixed here.

INSTALL: Extract to its own folder with licensed RTCW Main/pak*.pk3 files.
Run RUN_DARKWOLF_SEPTEMBER_FOURWEEK.bat, not the EXE directly.
To force a consistent baseline after old archived config overrides:
   exec DW_CRYPT1_SHADOW_FIDELITY_PRODUCTION.cfg
That CFG includes the accepted Sun3+Fire E profile and world containment=2.
Do not mix this folder with older test DLLs or shader files.

ROLLBACK: Keep the accepted #40633659668 binary and #40512393634 archive.
Game-play GPU quality on additional maps and FPS are not independently re-tested
by repackaging. Production here means a frozen, reproducible checkpoint.
No commercial RTCW data is distributed in this ZIP.
'''
    manifest={
        'release':RELEASE_MARK,
        'status':'FROZEN_CLEAN_PRODUCTION_CHECKPOINT_WITH_DOCUMENTED_OPEN_ISSUES',
        'promoted_exact_runtime_run':BASE_RUN,
        'promoted_exact_runtime_sha256':BASE_SHA,
        'promoted_renderer_sha256':RENDERER_SHA,
        'renderer_code_changes_from_run_40633659668':0,
        'graphics_shader_changes_from_run_40633659668':0,
        'game_binary_changes':0,
        'added_cvars':[],'telemetry_added':False,
        'preserved_original_file_count':len(old)-1,
        'original_files_changed':['docs/SHA256SUMS.txt'],
        'new_files':['README_CRYPT1_SHADOW_FIDELITY_PRODUCTION.txt',
                     'Main/DW_CRYPT1_SHADOW_FIDELITY_PRODUCTION.cfg',
                     'docs/CRYPT1_SHADOW_FIDELITY_FREEZE_MANIFEST.json'],
        'code_lineage':[40480112714,40512393634,40628480022,40633659668],
        'crypt1_shadow_PC F_2x2'.replace(' ',''):'RETAINED_USER_TESTED',
        'production_world_containment_baseline':2,
        'known_remaining_issues':[
            'Xlabs stationary Tesla loses blue light at r_dlightWorldContainment 2',
            'Escape1 stove still has some external-wall fire light leakage at containment 2',
            'Crypt1 filtered shadows are slightly coarser and thicker at containment 2 than containment 0',
        ],
        'acceptance_limit':'No newly compiled renderer; unchanged tested DLL, known Tesla regression remains',
    }
    entries=dict(old)
    entries['Main/DW_CRYPT1_SHADOW_FIDELITY_PRODUCTION.cfg']=cfg.encode('ascii')
    entries['README_CRYPT1_SHADOW_FIDELITY_PRODUCTION.txt']=readme.encode('ascii')
    entries['docs/CRYPT1_SHADOW_FIDELITY_FREEZE_MANIFEST.json']=(json.dumps(manifest,indent=2,ensure_ascii=True)+'\n').encode('ascii')
    entries['docs/SHA256SUMS.txt']=''.join(
        sha(v)+'  '+k+'\n' for k,v in sorted(entries.items()) if k!='docs/SHA256SUMS.txt').encode('ascii')
    assert len(entries)==len(old)+3
    for path,blob in old.items():
        if path!='docs/SHA256SUMS.txt':assert entries[path]==blob,('ORIGINAL_CHANGED',path)
    assert not any('r_dwVol' in v.decode('utf8','ignore') or 'r_dwSun' in v.decode('utf8','ignore')
                   for k,v in entries.items() if k.endswith('.cfg'))
    a.out.mkdir(parents=True,exist_ok=True)
    out_file=a.out/(RELEASE_ROOT+'.zip')
    with zipfile.ZipFile(out_file,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for rel,blob in sorted(entries.items()):
            info=zipfile.ZipInfo(RELEASE_ROOT+'/'+rel,date_time=(2026,10,28,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o644<<16
            z.writestr(info,blob)
    with zipfile.ZipFile(out_file) as z:
        assert z.testzip() is None
        actual={n.split('/',1)[1]:z.read(n) for n in z.namelist()}
    assert len(actual)==len(entries)
    assert actual['renderer_sp_rend2_x64.dll']==renderer
    for k,v in old.items():
        if k!='docs/SHA256SUMS.txt':assert actual[k]==v,k
    for line in actual['docs/SHA256SUMS.txt'].decode('ascii').splitlines():
        expected,path=line.split('  ',1)
        assert sha(actual[path])==expected,('SHA256SUMS_MISMATCH',path)
    result={
        'release':RELEASE_MARK,
        'source_base':str(a.base_zip),
        'source_base_sha256':BASE_SHA,
        'production_archive_sha256':sha(out_file.read_bytes()),
        'renderer_sha256_unchanged':RENDERER_SHA,
        'byte_identical_original_files':len(old)-1,
        'original_files_total':len(old),
        'new_documentation_and_cfg_files':3,
        'all_embedded_sha256_verified':True,
        'production_glsl_recompiled':False,
        'known_issues_documented':True,
    }
    (a.out/'CRYPT1_SHADOW_FIDELITY_FREEZE_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n')
    (a.out/(out_file.name+'.sha256')).write_text(result['production_archive_sha256']+'  '+out_file.name+'\n')
    print('DW_CRYPT1_SHADOW_FIDELITY_EXACT_BINARY_FREEZE_PASS')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
