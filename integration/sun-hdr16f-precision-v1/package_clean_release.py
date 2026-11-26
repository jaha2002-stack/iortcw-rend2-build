#!/usr/bin/env python3
"""Artifact-pinned Clean Production packager for user-approved DarkWolf Sun HDR16F V1."""
import hashlib, io, json, sys, zipfile
from pathlib import Path

NAME='DarkWolf_Volumetric_Sun_HDR16F_Precision_V1_Clean_Production_Win64'
OLD='8f1d482011200e8aa5d254450c360b753a2e514b9e9cf3f34c35bbc6e3fe18b5'
NEW='d7423e8648e2de556f79c7cddecf1a8df16b9f60a46c503d1440089876116b45'
EXPECTED_DIFF={'renderer_sp_rend2_x64.dll','docs/SHA256SUMS.txt','docs/DW_ALARM_CLEAN_V1_MANIFEST.json'}

def sha(b):return hashlib.sha256(b).hexdigest()
def read_artifact(path):
    with zipfile.ZipFile(path) as outer:
        assert outer.testzip() is None
        inner=[n for n in outer.namelist() if n.startswith('dist/') and n.endswith('.zip')]
        assert len(inner)==1,inner
        innerbytes=outer.read(inner[0])
    with zipfile.ZipFile(io.BytesIO(innerbytes)) as z:
        assert z.testzip() is None
        names=[s for s in z.namelist() if not s.endswith('/')]
        assert len({s.split('/',1)[0] for s in names})==1
        files={s.split('/',1)[1]:z.read(s) for s in names}
        assert len(files)==len(names)
        return files,sha(innerbytes)

def profile(label,msaa,shadow,fire,cas):
    return f'''// Optional {label}: all DarkWolf effects ON; baseline startup remains unchanged.
// /exec DW_HDR16F_V1_{label}.cfg ; then /vid_restart
exec DW_SEPTEMBER_FOURWEEK_VISUAL_BASE.cfg
exec DW_SUN3_FIRE_E_PRODUCTION.cfg
seta r_externalGLSL "0"
seta r_hdr "1"
seta r_postProcess "1"
seta r_bloom "1"
seta r_bloomMode "2"
seta r_ssgi "1"
seta r_forceSun "1"
seta r_sunShadows "1"
seta r_dlightMode "2"
seta r_dlightShadowMaxLights "3"
seta r_staticPromote "1"
seta r_staticPromoteMaxLights "32"
seta r_volumetricSun "1"
seta r_volumetricSunMode "1"
seta r_volumetricSunSamples "32"
seta r_volumetricLocal "1"
seta r_volumetricFire "1"
seta r_softParticles "1"
seta r_dwTextureFidelity "1"
seta r_dwMaterialFidelity "1"
seta r_dwCas "1"
seta r_dwA2C "1"
seta r_dwLut "1"
seta r_dwLutStrength "0.00"
seta r_picmip "0"
seta r_ext_framebuffer_multisample "{msaa}"
seta r_shadowMapSize "{shadow}"
seta r_dlightShadowMapSize "{shadow}"
seta r_volumetricFireSamples "{fire}"
seta r_dwCasStrength "{cas}"
'''.encode()

def build(base_zip,hdr_zip,outdir):
    base,basehash=read_artifact(base_zip)
    new,newhash=read_artifact(hdr_zip)
    assert set(base)==set(new) and len(base)==49
    changed={s for s in base if base[s]!=new[s]}
    assert changed==EXPECTED_DIFF,changed
    assert sha(base['renderer_sp_rend2_x64.dll'])==OLD
    assert sha(new['renderer_sp_rend2_x64.dll'])==NEW
    assert b'_dwSunHalfRGBA16F' in new['renderer_sp_rend2_x64.dll']
    source=base['Main/DW_SEPTEMBER_FOURWEEK_VISUAL_BASE.cfg'].decode()
    for c in ['seta r_forceSun "1"','seta r_dlightMode "2"','seta r_staticPromoteMaxLights "32"','seta r_dlightShadowMaxLights "3"']:
        assert c in source
    files=dict(base)
    files['renderer_sp_rend2_x64.dll']=new['renderer_sp_rend2_x64.dll']
    presets=[('PERFORMANCE',2,1024,32,'0.40'),('BALANCED',4,2048,40,'0.50'),('QUALITY',4,2048,40,'0.55'),('HIGH',4,4096,40,'0.55'),('ULTRA',8,4096,48,'0.55')]
    for vals in presets:
        key=f'Main/DW_HDR16F_V1_{vals[0]}.cfg'
        files[key]=profile(*vals)
        assert all(t not in files[key].lower() for t in [b'diag',b'debug',b'telemetry'])
    files['README_HDR16F_V1_CLEAN_PRODUCTION_RU.txt']='''DarkWolf Volumetric Sun HDR16F Precision V1 - CLEAN PRODUCTION
Base: Actions #40878732886. User-validated HDR16F DLL: #41013202896.
Factory Visual PASS; user reports no sky arcs on other tested maps and >100 FPS.
Very fine residual grain is acceptable. No experimental GLSL/dither or debug code.

1. Back up your RTCW installation. Extract the archive, retaining the Main folder.
2. Add your licensed RTCW pak*.pk3 to Main (not distributed).
3. Remove earlier Sun DITHER/V3 diagnostic PK3s and external glsl overrides.
4. Use the unchanged RUN_DARKWOLF_SEPTEMBER_FOURWEEK.bat.
5. In an existing installation set r_externalGLSL 0, r_hdr 1, r_volumetricSun 1,
   r_volumetricSunSamples 32, then vid_restart.
6. Extra profiles DW_HDR16F_V1_PERFORMANCE/BALANCED/QUALITY/HIGH/ULTRA.cfg
   are optional, ALL EFFECTS ON, and not included in validated default startup.

The ONLY changed executable compared to #40878732886 is renderer_sp_rend2_x64.dll.
CSM/Sun3/32-step raymarch, Local+Fire, SSGI, Bloom V2, Portal Sky and lighting kept.
Original historical BUILD_PROVENANCE and DW_ALARM manifests retained unchanged;
use docs/DW_SUN_HDR16F_V1_RELEASE_MANIFEST.json for CURRENT provenance.
Original user game pak*.pk3 files are not included.
'''.encode()
    files['docs/DW_SUN_HDR16F_V1_ACCEPTANCE_2026-10-30.md']='''# Accepted DarkWolf Sun HDR16F V1 — 2026-10-30
Factory Visual PASS. Other maps tested by user: no sky arcs. FPS reported >100.
Residual very fine grain accepted. GPU results user-reported, not benchmarked in CI.
Base run #40878732886; accepted DLL run #41013202896. No external dithering.
Optional performance presets remain unbenchmarked and are not the accepted default.
'''.encode()
    manifest={
        'release':NAME,'release_status':'CLEAN_PRODUCTION_USER_ACCEPTED',
        'base_run':40878732886,'base_artifact_id':12899612623,
        'hdr16f_run':41013202896,'hdr16f_artifact_id':12958870751,
        'base_inner_sha256':basehash,'hdr16f_inner_sha256':newhash,
        'base_renderer_sha256':OLD,'release_renderer_sha256':NEW,
        'baseline_file_count':len(base),'accepted_test_diff':sorted(changed),
        'original_runtime_changed_only':['renderer_sp_rend2_x64.dll'],
        'preserved_original_files_except_renderer_and_checksums':len(base)-2,
        'sun_fp16_buffer':'GL_RGBA16F; half resolution; Sun-only',
        'user_visual_acceptance':'Factory Visual PASS; other tested maps no arcs',
        'user_reported_fps':'>100 on tested maps',
        'minor_grain':'remains; accepted',
        'new_debug_cvars':False,'new_telemetry':False,'new_external_glsl':False,
        'new_dither':False,'sun_samples':32,'sun_visibility':'unchanged',
        'optional_profiles':[f'Main/DW_HDR16F_V1_{v[0]}.cfg' for v in presets],
        'optional_profiles_gpu_benchmarked':False,
        'historical_manifests_preserved':True
    }
    files['docs/DW_SUN_HDR16F_V1_RELEASE_MANIFEST.json']=(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n').encode()
    files['docs/SHA256SUMS.txt']=''.join(f'{sha(files[n])}  {n}\n' for n in sorted(files) if n!='docs/SHA256SUMS.txt').encode()
    assert len(files)==57 and set(base).issubset(files)
    assert all(files[n]==base[n] for n in base if n not in {'renderer_sp_rend2_x64.dll','docs/SHA256SUMS.txt'})
    assert all(files[n]==base[n] for n in base if n.endswith(('.exe','.dll')) and n!='renderer_sp_rend2_x64.dll')
    assert not any(n.startswith('glsl/') or 'DITHER' in n for n in files)
    outdir.mkdir(parents=True,exist_ok=True)
    out=outdir/(NAME+'.zip')
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name in sorted(files):
            info=zipfile.ZipInfo(NAME+'/'+name,(2026,10,30,12,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
            z.writestr(info,files[name],compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        assert len(z.namelist())==57
        for line in z.read(NAME+'/docs/SHA256SUMS.txt').decode().splitlines():
            h,n=line.split('  ',1);assert sha(z.read(NAME+'/'+n))==h,n
        assert sha(z.read(NAME+'/renderer_sp_rend2_x64.dll'))==NEW
    final=sha(out.read_bytes())
    (outdir/(NAME+'.zip.sha256')).write_text(final+'  '+out.name+'\n')
    (outdir/'DW_SUN_HDR16F_CLEAN_PRODUCTION_AUDIT.json').write_text(json.dumps({**manifest,'final_release_zip_sha256':final,'total_files':len(files),'verified':True},indent=2)+'\n')
    print('DW_SUN_HDR16F_CLEAN_PRODUCTION_PACKAGING_PASS '+final)

if __name__=='__main__':
    assert len(sys.argv)==4, 'usage: script base-artifact.zip hdr16f-artifact.zip output-dir'
    build(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]))
