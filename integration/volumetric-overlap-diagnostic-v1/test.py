#!/usr/bin/env python3
"""Checks for exact-source Sun/Local overlap diagnostic after the two-file patch."""
import argparse, hashlib, json, shutil, subprocess
from pathlib import Path
MARK='DARKWOLF_VOL_OVERLAP_DIAG_V1_20261027'
p=argparse.ArgumentParser()
p.add_argument('source',type=Path)
p.add_argument('--out',type=Path,required=True)
p.add_argument('--require-glslang',action='store_true')
a=p.parse_args()
root=a.source/'SP/code/rend2'
b=(root/'tr_backend.c').read_text()
l=(root/'glsl/volumetriclocal_fp.glsl').read_text()
assert MARK in b and MARK in l
assert 'DARKWOLF_PORTAL_SKY_SINGLE_SAMPLE_UNIVERSAL_V1' in b
assert 'DARKWOLF_VOLUMETRIC_WAVE_CLEAN_V2_20261027' in b and 'DARKWOLF_VOLUMETRIC_WAVE_CLEAN_V2_20261027' in l
for t in ('s_dwVolSunFullresDiag','s_dwVolLocalSpatialDiag','s_dwVolLocalLampPcfDiag'):
    assert b.count(t)>=2,t
assert 'if (mode <= 4 && s_dwVolLocalSpatialDiag' in b
assert 'mode == 3 && s_dwVolLocalLampPcfDiag' in b
assert 'r_dwVolSunFullresDiag", "0"' in b
assert 'r_dwVolLocalSpatialDiag", "0"' in b
assert 'r_dwVolLocalLampPcfDiag", "1"' in b
assert 'mode <= 4 && s_dwVolLocalSpatialDiag && s_dwVolLocalSpatialDiag->integer == 1' in b
assert 'tr.volumetricFullresFbo, srcBox, &tr.volumetricSunShader' in b
assert 'tr.volumetricFullresFbo, srcBox, &tr.volumetricLocalShader' in b
assert 'u_EnableTextures.w >= 2.5 && u_EnableTextures.w <= 3.5' in l
assert 'u_EnableTextures.w >= 5.0 && u_EnableTextures.w <= 7.5' in l
assert 'filtered += compareDlightShadow(' in l
assert b.index('RB_VolumetricSun(srcFbo, srcBox);') < b.index('RB_VolumetricLocal(srcFbo, srcBox);') < b.index('RB_VolumetricFire(srcFbo, srcBox);')
assert b.count('GLS_SRCBLEND_ONE | GLS_DSTBLEND_ONE')>=6
a.out.mkdir(parents=True,exist_ok=True)
validator=shutil.which('glslangValidator')
if a.require_glslang: assert validator,'REQUIRE_GLSLANG'
shaders=[]
if validator:
    header='#version 130\n#define varying in\nout vec4 out_Color;\n#define gl_FragColor out_Color\n#define texture2D texture\n#define shadow2D texture\n#define M_PI 3.14159265358979323846\n'
    for filename in ('volumetriclocal_fp.glsl','volumetricsun_fp.glsl','volumetriclocal_upscale_fp.glsl'):
        shader=root/'glsl'/filename
        variants=[('SUN_CASCADE','#define USE_SHADOW_CASCADE\n#define r_shadowMapSize 2048.0\n'),('SUN_SINGLE','#define r_shadowMapSize 2048.0\n')] if filename=='volumetricsun_fp.glsl' else [(filename[:-5].upper(),'')]
        for tag,defines in variants:
            tmp=a.out/(tag+'.frag')
            tmp.write_text(header+defines+shader.read_text())
            proc=subprocess.run([validator,'-S','frag',str(tmp)],text=True,capture_output=True)
            (a.out/(tag+'.log')).write_text(proc.stdout+'\n'+proc.stderr)
            assert proc.returncode==0,('GLSL130_COMPILE_FAIL',tag,proc.stdout,proc.stderr)
            shaders.append(tag)
            print('PASS_GLSLANG_130',tag)
else: print('NOTE: glslang not installed locally; CI requires compiler test')
result={'status':'STATIC_TESTS_PASSED','marker':MARK,'glsl_pass':shaders,'gpu_runtime':'PENDING',
        'sun_spatial_resolution_test':'QUARTER_VS_FULL',
        'local_tests':'BASE_VS_5X5_9TAP_VS_FULL','composite':'ADD_HDR_BEFORE_TONEMAP'}
(a.out/'QA_SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n')
print('DW_VOL_OVERLAP_DIAG_V1_STATIC_PASS')
