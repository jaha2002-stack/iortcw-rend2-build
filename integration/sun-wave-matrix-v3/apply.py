#!/usr/bin/env python3
"""Two-file Sun CSM/ray root-cause matrix. Strict accepted Wave V2 source lineage."""
import argparse,hashlib,json
from pathlib import Path
MARK='DARKWOLF_SUN_WAVE_CAUSE_MATRIX_V3_20261027'
EXPECTED={'tr_backend.c':'0cfcad4ad18882691f16749697d09a48e832b9344de4e58a11e36c3b7efb405e',
 'glsl/volumetricsun_fp.glsl':'8e22ade3bba934b471b270fd5db3e6066e500acb47bc1ea03588abe1bcd780ab'}
def sha(s): return hashlib.sha256(s.encode()).hexdigest()
def one(s,old,new,tag):
    n=s.count(old)
    if n!=1: raise AssertionError((tag,'UNIQUE_ANCHOR_FAIL',n))
    return s.replace(old,new,1)
def apply(root):
    dest=root/'SP/code/rend2'
    before={f:(dest/f).read_text() for f in EXPECTED}
    for f,v in before.items():
        assert sha(v)==EXPECTED[f],('WRONG_EXACT_40487188767_SOURCE',f,sha(v))
        assert MARK not in v,('DUPLICATE_PATCH',f)
    b=before['tr_backend.c'];s=before['glsl/volumetricsun_fp.glsl']
    assert 'DARKWOLF_PORTAL_SKY_SINGLE_SAMPLE_UNIVERSAL_V1' in b
    assert 'DARKWOLF_VOLUMETRIC_WAVE_CLEAN_V2_20261027' in b
    assert 'DARKWOLF_VOLUMETRIC_EDGE_RAY_CSM_AA_V1' in s
    b=one(b,'static void RB_VolumetricSun(FBO_t *srcFbo, ivec4_t srcBox)',
        '// '+MARK+': diagnostic Sun-only cvars; both default to accepted Wave V2.\n'
        'static cvar_t *s_dwSunWaveMode;\n'
        'static cvar_t *s_dwSunReconMode;\n'
        'static void RB_VolumetricSun(FBO_t *srcFbo, ivec4_t srcBox)', 'SUN_CVAR_DECL')
    b=one(b,'\t\treturn; // DARKWOLF_SUN_VOLUMETRIC_PERF_ISOLATION_V0_3: true live raymarch bypass\n\n\tsunDirLenSq =',
        '\t\treturn; // DARKWOLF_SUN_VOLUMETRIC_PERF_ISOLATION_V0_3: true live raymarch bypass\n'
        '\tif (!s_dwSunWaveMode) s_dwSunWaveMode = ri.Cvar_Get("r_dwSunWaveMode", "0", CVAR_ARCHIVE);\n'
        '\tif (!s_dwSunReconMode) s_dwSunReconMode = ri.Cvar_Get("r_dwSunReconMode", "0", CVAR_ARCHIVE);\n\n\tsunDirLenSq =','SUN_CVAR_INIT')
    b=one(b,'\t\tCom_Clamp(0.0f, 4.0f, r_volumetricSunKnee->value),\n\t\t0.0f, 0.0f);',
        '\t\tCom_Clamp(0.0f, 4.0f, r_volumetricSunKnee->value),\n'
        '\t\t(float)Com_Clamp(0, 4, s_dwSunWaveMode->integer), 0.0f); // '+MARK, 'SUN_RESERVED_SHADER_UNIFORM')
    b=one(b,'\t\tVectorSet4(aaParams, 0.0f, 4.0f, 1.0f, 0.0f);',
        '\t\tVectorSet4(aaParams, 0.0f, s_dwSunReconMode->integer == 1 ? 2.0f : 4.0f, 1.0f, 0.0f); // '+MARK,'SUN_RECON_ONLY')
    s=one(s,
        'float dwCascadeWeight(vec4 p)\n{\n    // Fades only across the nearest 6% of the orthographic clip volume;\n    // interior pixels continue to use EXACT original single-cascade PCF.\n    float x = clamp(dwCascadeInterior(p) / 0.06, 0.0, 1.0);\n    return x * x * (3.0 - 2.0 * x);\n}',
        '// '+MARK+': mode 0 reproduces the accepted 6% CSM transition exactly.\n'
        'float dwCascadeWeight(vec4 p, int waveMode)\n'
        '{\n    if (waveMode == 2) return 1.0; // hard cascade selection control\n'
        '    float width = (waveMode == 1 || waveMode == 4) ? 0.015 : 0.06;\n'
        '    float x = clamp(dwCascadeInterior(p) / width, 0.0, 1.0);\n'
        '    return x * x * (3.0 - 2.0 * x);\n}', 'SUN_CSM_WEIGHT')
    s=one(s,'float sunVisibility(vec3 worldPos, int pcfMode)',
        'float sunVisibility(vec3 worldPos, int pcfMode, int waveMode)', 'SUN_VIS_SIGNATURE')
    assert s.count('dwCascadeWeight(p)')==5,('CASCADE_CALLS_CHANGED',s.count('dwCascadeWeight(p)'))
    s=s.replace('dwCascadeWeight(p)','dwCascadeWeight(p, waveMode)')
    s=one(s,'    float kneeStrength = clamp(u_BaseColor.y, 0.0, 4.0);',
        '    float kneeStrength = clamp(u_BaseColor.y, 0.0, 4.0);\n'
        '    int waveMode = int(clamp(u_BaseColor.z, 0.0, 4.0) + 0.5); // '+MARK,'SUN_WAVE_UNIFORM')
    s=one(s,'        float visibility = sunVisibility(worldPos, pcfMode);\n'
        '        integrated += visibility * transmittance * density * worldStep;',
        '        // '+MARK+': stratified dual-sample visibility tests step aliasing.\n'
        '        float visibility;\n'
        '        if (waveMode >= 3)\n        {\n'
        '            vec3 subStep = var_ViewDir * (0.25 * stepDepth);\n'
        '            float va = sunVisibility(worldPos - subStep, pcfMode, waveMode);\n'
        '            float vb = sunVisibility(worldPos + subStep, pcfMode, waveMode);\n'
        '            visibility = 0.5 * (va + vb);\n'
        '        }\n        else\n        {\n'
        '            visibility = sunVisibility(worldPos, pcfMode, waveMode);\n'
        '        }\n'
        '        integrated += visibility * transmittance * density * worldStep;', 'SUN_STRATIFIED_VISIBILITY')
    after={'tr_backend.c':b,'glsl/volumetricsun_fp.glsl':s}
    for f,v in after.items(): (dest/f).write_text(v)
    return {'marker':MARK,'exact_base_run':40487188767,'fixture_only':False,
       'modified_files':['SP/code/rend2/'+f for f in EXPECTED],
       'sha256_before':{f:sha(v) for f,v in before.items()},
       'sha256_after':{f:sha(v) for f,v in after.items()},
       'frozen':['Sky Single-Sample','Fire E','Local Volumetric','CSM producers','SSGI','Tesla'],
       'gpu_quality':'NOT_YET_VERIFIED'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path)
    p.add_argument('--proof',type=Path)
    a=p.parse_args();result=apply(a.source)
    if a.proof:
        a.proof.parent.mkdir(parents=True,exist_ok=True)
        a.proof.write_text(json.dumps(result,indent=2)+'\n')
    print('DW_SUN_WAVE_MATRIX_V3_SOURCE_PASS')
