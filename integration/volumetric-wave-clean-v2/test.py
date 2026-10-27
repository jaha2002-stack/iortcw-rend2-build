#!/usr/bin/env python3
"""Volumetric Wave Clean V2 real-source and GLSL130 checks; GPU acceptance remains pending."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path

MARK='DARKWOLF_VOLUMETRIC_WAVE_CLEAN_V2_20261027'
FILES=('tr_backend.c','tr_init.c','glsl/volumetricsun_fp.glsl','glsl/volumetriclocal_fp.glsl','glsl/volumetriclocal_upscale_fp.glsl')
p=argparse.ArgumentParser()
p.add_argument('source',type=Path)
p.add_argument('--out',type=Path,required=True)
p.add_argument('--require-glslang',action='store_true')
a=p.parse_args()
root=a.source/'SP/code/rend2'
data={k:(root/k).read_text() for k in FILES}
for k,v in data.items(): assert MARK in v,('MISSING_V2_MARKER',k)
backend=data['tr_backend.c']
sun=data['glsl/volumetricsun_fp.glsl']
fire=data['glsl/volumetriclocal_fp.glsl']
up=data['glsl/volumetriclocal_upscale_fp.glsl']
init=data['tr_init.c']
assert 'DARKWOLF_PORTAL_SKY_SINGLE_SAMPLE_UNIVERSAL_V1' in backend
assert 'FBO_FastBlit(tr.msaaResolveFbo, NULL, tr.renderFbo' in backend
assert 'DARKWOLF_VOLUMETRIC_EDGE_RAY_CSM_AA_V1' in sun
assert 'DARKWOLF_VOLUMETRIC_EDGE_RAY_CSM_AA_V1' in up
assert '#define VOLUMETRIC_MAX_SAMPLES 64' in sun
assert '#define LOCALVOL_MAX_SAMPLES 64' in fire
assert 'Com_Clamp(4, 64, r_volumetricSunSamples->integer)' in backend
assert 'Com_Clamp(8, 64, s_rVolumetricFireSamples->integer)' in backend
assert 'int pcfMode = int(clamp(u_EnableTextures.y, 0.0, 2.0)' in fire
assert '(float)Com_Clamp(0, 2, r_volumetricLocalShadowPcf->integer)' in backend
assert 'r_volumetricLocalShadowPcf, 0, 2, qtrue' in init
assert 'r_volumetricSunSamples, 4, 64, qtrue' in init
assert 'bool shadowedFire = pcfMode >= 2 && u_EnableTextures.w >= 5.0' in fire
assert fire.count('filtered += compareDlightShadow(')>=12
assert 'reconstructionMode >= 2' in backend
assert '0.28+0.22*lumaEdge' in up and 'max(blend,0.32)' in up
assert 'if(max(max(rel.x,rel.y),max(rel.z,rel.w))<0.06)' in up
a.out.mkdir(parents=True,exist_ok=True)
validator=shutil.which('glslangValidator')
if a.require_glslang: assert validator, 'GLSLANG_COMPILER_MISSING'
tested=[]
if validator:
    header='#version 130\n#define varying in\nout vec4 out_Color;\n#define gl_FragColor out_Color\n#define texture2D texture\n#define shadow2D texture\n#define M_PI 3.14159265358979323846\n'
    shaders=[('volumetricsun_fp.glsl','SUN_CASCADE','#define USE_SHADOW_CASCADE\n#define r_shadowMapSize 2048.0\n'),
      ('volumetricsun_fp.glsl','SUN_SINGLE','#define r_shadowMapSize 2048.0\n'),
      ('volumetriclocal_fp.glsl','FIRE_LOCAL',''),
      ('volumetriclocal_upscale_fp.glsl','DEPTH_UPSCALE','')]
    for fname,tag,defs in shaders:
        filename=a.out/(tag+'.frag')
        filename.write_text(header+defs+(root/'glsl'/fname).read_text())
        r=subprocess.run([validator,'-S','frag',str(filename)],capture_output=True,text=True)
        (a.out/(tag+'.log')).write_text(r.stdout+'\n'+r.stderr)
        assert r.returncode==0,('GLSL130_'+tag,r.stdout,r.stderr)
        print('PASS_GLSLANG_130',tag)
        tested.append(tag)
else: print('LOCAL_GLSLANG_NOT_INSTALLED; CI MUST REQUIRE GLSL COMPILATION')
result={'status':'STATIC_TESTS_PASSED','marker':MARK,'compiled_glsl':tested,
 'source_sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in data.items()},
 'runtime_visual':'NOT_TESTED'}
(a.out/'QUALITY_TEST_SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n')
print('DW_VOLWAVE_V2_STATIC_TESTS_PASS')
