#!/usr/bin/env python3
"""Sun wave CSM/ray shader source guards and GLSL130 exact-header checks."""
import argparse,json,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('source',type=Path)
p.add_argument('--out',type=Path,required=True)
p.add_argument('--require-glslang',action='store_true')
a=p.parse_args()
root=a.source/'SP/code/rend2'
b=(root/'tr_backend.c').read_text()
s=(root/'glsl/volumetricsun_fp.glsl').read_text()
MARK='DARKWOLF_SUN_WAVE_CAUSE_MATRIX_V3_20261027'
assert MARK in b and MARK in s
assert 'DARKWOLF_PORTAL_SKY_SINGLE_SAMPLE_UNIVERSAL_V1' in b
assert 'DARKWOLF_VOLUMETRIC_WAVE_CLEAN_V2_20261027' in b
assert 'DARKWOLF_VOLUMETRIC_EDGE_RAY_CSM_AA_V1' in s
assert 'float dwCascadeWeight(vec4 p, int waveMode)' in s
assert 'waveMode == 2' in s and 'waveMode == 1 || waveMode == 4' in s
assert s.count('dwCascadeWeight(p, waveMode)')==5
assert 'float va = sunVisibility(worldPos - subStep, pcfMode, waveMode);' in s
assert 'float vb = sunVisibility(worldPos + subStep, pcfMode, waveMode);' in s
assert 'r_dwSunWaveMode", "0"' in b and 'r_dwSunReconMode", "0"' in b
assert 's_dwSunWaveMode->integer' in b and 's_dwSunReconMode->integer' in b
assert 's_dwSunReconMode->integer == 1 ? 2.0f : 4.0f' in b
assert 'FBO_Blit(srcFbo, srcBox, NULL, tr.quarterFbo[0], NULL, &tr.volumetricSunShader, params, 0);' in b
assert 'DARKWOLF_VOL_OVERLAP_DIAG_V1_20261027' not in b
a.out.mkdir(parents=True,exist_ok=True)
validator=shutil.which('glslangValidator')
if a.require_glslang: assert validator,'GLSLANG_MISSING'
validated=[]
if validator:
    header='#version 130\n#define varying in\nout vec4 out_Color;\n#define gl_FragColor out_Color\n#define texture2D texture\n#define shadow2D texture\n#define M_PI 3.14159265358979323846\n'
    for tag,defs in [('CSM','#define USE_SHADOW_CASCADE\n#define r_shadowMapSize 2048.0\n'),
                     ('SINGLE','#define r_shadowMapSize 2048.0\n')]:
        frag=a.out/(tag+'.frag')
        frag.write_text(header+defs+s)
        result=subprocess.run([validator,'-S','frag',str(frag)],capture_output=True,text=True)
        (a.out/(tag+'.log')).write_text(result.stdout+'\n'+result.stderr)
        assert result.returncode==0,('GLSL_130_COMPILE_FAIL',tag,result.stdout,result.stderr)
        print('GLSL130_SUN_'+tag+'_PASS')
        validated.append(tag)
else: print('LOCAL_GLSLANG_UNAVAILABLE_CI_REQUIRED')
(a.out/'QA_SUMMARY.json').write_text(json.dumps({'static':'PASS','glsl_variants':validated,
    'runtime_acceptance':'PENDING','other_systems_frozen':True},indent=2)+'\n')
print('DW_SUN_WAVE_V3_SOURCE_GUARDS_PASS')
