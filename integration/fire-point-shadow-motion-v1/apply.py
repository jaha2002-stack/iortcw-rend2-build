#!/usr/bin/env python3
"""TEST ONLY: exact #41297344177, selective real point-fire motion.

Do not promote to Clean Production without real GPU validation. No global
fire source activation. Source motion requires an explicit map+native ordinal.
"""
from pathlib import Path
import hashlib, json, argparse

FILES = {
    "SP/code/rend2/tr_local.h": "9e2462d329d6b78e5b9674eb77757602b1d4adc6a1d988dbc44fe5ce8fe2993a",
    "SP/code/rend2/tr_scene.c": "6b89b5a8d21e7c0020502dce47f165b275f63e4e0de8ed6d13b6962df71c6d00",
    "SP/code/rend2/tr_main.c": "a304b1e0a30b9d834c9180e15e9275dd40fc08e939f38e675815f4cadca4da59",
    "SP/code/rend2/tr_init.c": "78f724d691ac4f538675e1a95d2921f11a5af60894eb82e2663360bd5abf6f08",
}
MARK = "DARKWOLF_FIRE_POINT_SHADOW_MOTION_V1_TEST_ONLY_20261102"

def sha(data):
    return hashlib.sha256(data.encode()).hexdigest()

def exact_replace(text, before, after, label):
    count = text.count(before)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor; actual={count}")
    return text.replace(before, after, 1)

HELPER = r'''
/* DARKWOLF_FIRE_POINT_SHADOW_MOTION_V1_TEST_ONLY_20261102
 * EXPLICIT SINGLE-TARGET TEST, NOT A RELEASE-WIDE FIRE CLASSIFIER.
 * Uses the original immutable authored center; neither camera position nor
 * dlight index/slot participates in the phase or stable selection.
 * The render-BSP leaf guard is NOT a full collision solver for detail brushes;
 * any source with uncertain world-space clearance must remain disabled.
 * Six world-only faces can be regenerated each moved frame: GPU PERF GATE.
 */
static qboolean R_DWFireMotionSameAirLeaf(const vec3_t a, const vec3_t b)
{
    const mnode_t *first, *second;
    const mnode_t *root = tr.world ? tr.world->nodes : NULL;
    int pass;
    if (!root) return qfalse;
    first = second = NULL;
    for (pass = 0; pass < 2; ++pass)
    {
        const vec_t *point = (pass == 0) ? a : b;
        const mnode_t *node = root;
        int depth = 0;
        while (node && node->contents == CONTENTS_NODE && depth++ < 8192)
        {
            const cplane_t *plane = node->plane;
            float d;
            if (!plane) return qfalse;
            d = DotProduct(point, plane->normal) - plane->dist;
            node = node->children[d > 0.0f ? 0 : 1];
        }
        if (!node || node->contents == CONTENTS_NODE || node->cluster < 0)
            return qfalse;
        if (pass == 0) first = node;
        else second = node;
    }
    return first == second;
}

static void R_DWFireMotionApply(const refdef_t *fd, dlight_t *dl)
{
    float t, phase, amplitude, magnitude;
    vec3_t delta, moved;
    if (!fd || !dl || !r_dwFireShadowMotion || !r_dwFireShadowMotion->integer ||
        !r_dwFireShadowMotionMap || !r_dwFireShadowMotionMap->string[0] ||
        !r_dwFireShadowMotionTargetOrdinal ||
        r_dwFireShadowMotionTargetOrdinal->integer < 0 || !tr.world ||
        Q_stricmp(tr.world->baseName, r_dwFireShadowMotionMap->string) ||
        r_dlightMode->integer < 2 ||
        !dl->nativeAuthoredDlight || !dl->fireVolumetricSource ||
        dl->shadowSourceClass != DWSHADOW_SOURCE_PERSISTENT_FIRE ||
        dl->fireVolumetricNativeOrdinal != r_dwFireShadowMotionTargetOrdinal->integer ||
        dl->staticPromoteFixtureId >= 0 || dl->noDlightShadow ||
        !dl->worldOcclusion || dl->radius <= 0.0f ||
        (r_dlightShadowTestLock && r_dlightShadowTestLock->integer))
        return;
    /* Renderer has no imported CM_BoxTrace; gate on a deliberately selected
       cleared map fixture, prevent BSP decision-node crossings as a backup. */
    amplitude = r_dwFireShadowMotionAmplitude ?
        Com_Clamp(0.0f, 0.75f, r_dwFireShadowMotionAmplitude->value) : 0.0f;
    if (amplitude <= 0.0f) return;
    t = (float)fd->time * 0.001f;
    phase = (float)dl->fireVolumetricNativeOrdinal * 0.271f;
    delta[0] = amplitude * (0.68f * sinf(5.3f * t + phase) +
                           0.17f * sinf(8.1f * t + phase * 0.7f));
    delta[1] = amplitude * (0.46f * sinf(4.7f * t + phase * 0.8f) +
                           0.19f * sinf(7.0f * t - phase));
    delta[2] = amplitude * 0.18f * sinf(4.2f * t + phase + 0.4f);
    magnitude = VectorLength(delta);
    if (magnitude > amplitude && magnitude > 0.000001f)
        VectorScale(delta, amplitude / magnitude, delta);
    VectorAdd(dl->dwFireMotionBaseOrigin, delta, moved);
    if (!R_DWFireMotionSameAirLeaf(dl->dwFireMotionBaseOrigin, moved))
        return;
    /* Keep BOTH ordinary light and its selected main/world depth captures
       at this exact world-space origin. Preserve native radius/color pulse. */
    VectorCopy(moved, dl->origin);
}
'''

def patch(source):
    out = dict(source)
    p = 'SP/code/rend2/tr_local.h'
    s = out[p]
    s = exact_replace(s,
        '\tfloat fireVolumetricSpeakerDistance;\n\t//done\n} dlight_t;',
        '\tfloat fireVolumetricSpeakerDistance;\n'
        '\tvec3_t dwFireMotionBaseOrigin; // '+MARK+': immutable original authored light center\n'
        '\t//done\n} dlight_t;', 'base origin field')
    s = exact_replace(s, 'extern  cvar_t  *r_dlightWorldContainment;',
        'extern  cvar_t  *r_dlightWorldContainment;\n'
        'extern cvar_t *r_dwFireShadowMotion;\n'
        'extern cvar_t *r_dwFireShadowMotionMap;\n'
        'extern cvar_t *r_dwFireShadowMotionTargetOrdinal;\n'
        'extern cvar_t *r_dwFireShadowMotionAmplitude;', 'extern cvars')
    out[p] = s

    p = 'SP/code/rend2/tr_scene.c'
    out[p] = exact_replace(out[p],
        '\tdl = &backEndData->dlights[r_numdlights++];\n\tVectorCopy( org, dl->origin );',
        '\tdl = &backEndData->dlights[r_numdlights++];\n'
        '\tVectorCopy( org, dl->origin );\n'
        '\tVectorCopy( org, dl->dwFireMotionBaseOrigin ); // '+MARK,
        'origin snapshot')

    p = 'SP/code/rend2/tr_init.c'
    s = out[p]
    s = exact_replace(s, 'cvar_t  *r_dlightWorldContainment; // user-adjustable: 0 off, 1 fire, 2 fire+stationary Tesla',
        'cvar_t  *r_dlightWorldContainment; // user-adjustable: 0 off, 1 fire, 2 fire+stationary Tesla\n'
        'cvar_t *r_dwFireShadowMotion;\n'
        'cvar_t *r_dwFireShadowMotionMap;\n'
        'cvar_t *r_dwFireShadowMotionTargetOrdinal;\n'
        'cvar_t *r_dwFireShadowMotionAmplitude; // '+MARK, 'cvar defs')
    s = exact_replace(s, '\tri.Cvar_CheckRange( r_dlightWorldContainment, 0, 2, qtrue );',
        '\tri.Cvar_CheckRange( r_dlightWorldContainment, 0, 2, qtrue );\n'
        '\t// '+MARK+': TEST ONLY, all movement OFF by default.\n'
        '\tr_dwFireShadowMotion = ri.Cvar_Get("r_dwFireShadowMotion", "0", CVAR_ARCHIVE);\n'
        '\tri.Cvar_CheckRange(r_dwFireShadowMotion, 0, 1, qtrue);\n'
        '\tr_dwFireShadowMotionMap = ri.Cvar_Get("r_dwFireShadowMotionMap", "", CVAR_ARCHIVE);\n'
        '\tr_dwFireShadowMotionTargetOrdinal = ri.Cvar_Get("r_dwFireShadowMotionTargetOrdinal", "-1", CVAR_ARCHIVE);\n'
        '\tr_dwFireShadowMotionAmplitude = ri.Cvar_Get("r_dwFireShadowMotionAmplitude", "0", CVAR_ARCHIVE);\n'
        '\tri.Cvar_CheckRange(r_dwFireShadowMotionAmplitude, 0.0f, 0.75f, qfalse);', 'cvar init')
    out[p] = s

    p = 'SP/code/rend2/tr_main.c'
    s = exact_replace(out[p], 'void R_RenderDlightCubemaps(const refdef_t *fd)',
                      HELPER+'\nvoid R_RenderDlightCubemaps(const refdef_t *fd)', 'helper placement')
    s = exact_replace(s,
        '\t\tpendingLightsMask = R_DarkWolfStaticPromoteShadowClearGroup(pendingLightsMask, bestLight);\n'
        '\t\tCom_Memset(&shadowParms, 0, sizeof(shadowParms));',
        '\t\tpendingLightsMask = R_DarkWolfStaticPromoteShadowClearGroup(pendingLightsMask, bestLight);\n'
        '\t\tR_DWFireMotionApply(fd, &tr.refdef.dlights[bestLight]); // '+MARK+'\n'
        '\t\tCom_Memset(&shadowParms, 0, sizeof(shadowParms));', 'real-selected capture')
    out[p] = s
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root',type=Path)
    ap.add_argument('--check-only',action='store_true')
    ap.add_argument('--proof',type=Path)
    args=ap.parse_args()
    src = {}
    for rel, expected in FILES.items():
        s = (args.root/rel).read_text(encoding='utf-8')
        assert sha(s) == expected, ('WRONG_PRODUCTION_SOURCE',rel,sha(s),expected)
        assert MARK not in s, ('ALREADY_PATCHED',rel)
        src[rel]=s
    out=patch(src)
    assert set(out)==set(src)
    assert all(src[k]!=out[k] for k in src)
    assert 'R_RenderDlightWorldOcclusion(fd)' in (args.root/'SP/code/rend2/tr_scene.c').read_text()
    assert out['SP/code/rend2/tr_main.c'].index('R_DWFireMotionApply(fd, &tr.refdef.dlights[bestLight])') < out['SP/code/rend2/tr_main.c'].index('R_AddCapShadowmapCmd(shadowSlot, j)')
    if not args.check_only:
        for rel,content in out.items():
            (args.root/rel).write_text(content,encoding='utf-8')
    evidence={'status':'TEST_ONLY','clean_run':41297344177,'modified_files':sorted(FILES),
              'original_sha256':{k:sha(v) for k,v in src.items()},
              'new_sha256':{k:sha(v) for k,v in out.items()},
              'preserves_shader_files':True,'preserves_game_modules':True,
              'default_motion_on':False,'default_target_ordinal':-1,
              'default_amplitude':0,'max_amplitude_world_units':0.75,
              'world_only_occlusion_cache':'UNCHANGED; moving fire misses may cause six captures each frame',
              'safety_limit':'renderer BSP leaf only; no collision trace, requires verified clear-space target',
              'GPU_FPS_REGRESSION':'UNTESTED',
              'all_fire_sources':'NOT_SUPPORTED; only explicit map+ordinal real point fire'}
    if args.proof:
        args.proof.parent.mkdir(exist_ok=True,parents=True)
        args.proof.write_text(json.dumps(evidence,indent=2)+'\n')
    print('DW_FIRE_POINT_MOTION_EXACT_PRODUCTION_TEST_SOURCE_PASS')

if __name__=='__main__': main()
