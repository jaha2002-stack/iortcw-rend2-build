#!/usr/bin/env python3
"""Promote only the visually exercised architectural FireVol gate.
The unresolved synthetic-capture experiment is NOT included in this candidate.
"""
from pathlib import Path
import sys,hashlib,json,difflib
src=Path(sys.argv[1]);ev=Path(sys.argv[2]);ev.mkdir(parents=True,exist_ok=True)
r=src/'SP/code/rend2'
before={p.relative_to(src).as_posix():p.read_bytes() for p in (src/'SP/code').rglob('*') if p.is_file()}
assert hashlib.sha256((r/'tr_electric_fixture.inc').read_bytes()).hexdigest()=='439ece2b50a3569ea8a8835d39b69f1a1a856f54a07ec228af4f4e290bf2a81f'
def edit(name,old,new,n=1):
 p=r/name;s=p.read_text();assert s.count(old)==n,(name,old[:80],s.count(old));p.write_text(s.replace(old,new))
helper=r'''
/* A group capture is shared: every member must identify the same housing.
 * Preserve the original cast geometry on ANY ambiguity. Allocation and capture
 * positions are unchanged. This does not remove other lights' shadows. */
static int R_ElectricFixtureForCapture(int index)
{
    int i, fixture, group;
    if (index < 0 || index >= tr.refdef.num_dlights || index >= MAX_DLIGHTS) return 0;
    fixture = R_ElectricFixtureForLight(&tr.refdef.dlights[index]);
    if (!fixture || !R_DarkWolfStaticPromoteShadowGroupEligible(&tr.refdef.dlights[index])) return fixture;
    group = R_DarkWolfStaticPromoteShadowGroupCanonicalId(index);
    if (group < 0) return 0;
    for (i = 0; i < tr.refdef.num_dlights && i < MAX_DLIGHTS; ++i)
        if (R_DarkWolfStaticPromoteShadowGroupEligible(&tr.refdef.dlights[i]) &&
            R_DarkWolfStaticPromoteShadowGroupCanonicalId(i) == group &&
            R_ElectricFixtureForLight(&tr.refdef.dlights[i]) != fixture) return 0;
    return fixture;
}

'''
edit('tr_main.c','void R_RenderDlightCubemaps(const refdef_t *fd)',helper+'void R_RenderDlightCubemaps(const refdef_t *fd)')
edit('tr_main.c','shadowParms.electricFixture = R_ElectricFixtureForLight(&tr.refdef.dlights[bestLight]);','shadowParms.electricFixture = R_ElectricFixtureForCapture(bestLight);')
helper=r'''
/* Reuse an existing current-frame architectural capture for a uniquely
 * associated physical fire. No new DLight, cubemap, shadow slot or budget.
 * Cached FireVol captures can be displaced from the latched plume, therefore
 * the opt-in physical owner may also be identified at that plume (<=16u).
 * Multiple eligible owners fail closed to legacy FireVol; never pick nearest.
 * The following matching rule was exercised in causal Run 41789875771. */
static int RB_FireWorldOwner(const dlight_t *lamp, const vec3_t plume)
{
    int i, match = -1;
    if (!lamp) return -1;
    for (i = 0; i < backEnd.refdef.num_dlights && i < MAX_DLIGHTS; ++i)
    {
        const dlight_t *d = &backEnd.refdef.dlights[i];
        vec3_t delta;
        int slot = (int)backEnd.refdef.dlightWorldSlot[i];
        if (!d->worldOcclusion || slot < 0 || slot >= DLIGHT_WORLD_CACHE_MAX ||
            !tr.dlightWorldCubemaps[slot] || !(d->iflcOptIn || d->fireVolumetricSource)) continue;
        VectorSubtract(lamp->origin, d->origin, delta);
        if (DotProduct(delta, delta) > .0001f)
        {
            if (!d->iflcOptIn || !plume) continue;
            VectorSubtract(plume, d->origin, delta);
            if (DotProduct(delta, delta) > 16.0f * 16.0f) continue;
        }
        if (match >= 0) return -1;
        match = i;
    }
    return match;
}

'''
edit('tr_backend.c','static void RB_LocalVolumetricRenderEx(',helper+'static void RB_LocalVolumetricRenderEx(')
edit('tr_backend.c','\tGLSL_BindProgram(&tr.volumetricLocalShader);',r'''
    /* Architectural blockage is independent of artistic shadow strength.
     * Keep the ordinary/synthetic shadow filter and all fire energy unchanged. */
    if (mode >= 5 && mode <= 7 && lamp)
    {
        int worldIndex = RB_FireWorldOwner(lamp, fireVolumeOrigin ? fireVolumeOrigin : lamp->origin);
        if (worldIndex >= 0)
        {
            int slot = (int)backEnd.refdef.dlightWorldSlot[worldIndex];
            VectorCopy4(backEnd.refdef.dlightWorldOrigin[worldIndex], alarmWorldCapture);
            /* Decode accepted signed world-PCF mode marker, not a new range. */
            if (alarmWorldCapture[3] < -0.5f) alarmWorldCapture[3] = -alarmWorldCapture[3] - 2.0f;
            if (alarmWorldCapture[3] > 0.0f) alarmWorldCube = tr.dlightWorldCubemaps[slot];
            else VectorSet4(alarmWorldCapture, 0, 0, 0, 0);
        }
    }
\tGLSL_BindProgram(&tr.volumetricLocalShader);'''.replace('\\t','\t'))
edit('glsl/volumetriclocal_fp.glsl','if (mode == 3 && u_DlightWorldOrigin.w > 0.0)','if ((mode == 3 || (mode >= 5 && mode <= 7)) && u_DlightWorldOrigin.w > 0.0)')
edit('glsl/volumetriclocal_fp.glsl','// It is NEVER entered by Fire Volumetric (modes 5..9).','// Shaped fire 5..7 also uses this gate when a unique architectural owner exists.')
edit('glsl/volumetriclocal_fp.glsl','// Alarm only. Original Fire/torch/candle volumetric raymarch is untouched.','// Alarm and uniquely associated shaped fire: block architecture independently.')
after={p.relative_to(src).as_posix():p.read_bytes() for p in (src/'SP/code').rglob('*') if p.is_file()}
changed=[p for p in before if before[p]!=after[p]]
assert set(changed)=={'SP/code/rend2/tr_main.c','SP/code/rend2/tr_backend.c','SP/code/rend2/glsl/volumetriclocal_fp.glsl'}
for p in ('tr_iflc.inc','tr_iflc_fixture.inc','tr_scene.c','tr_world.c','tr_shade.c'):
 assert before['SP/code/rend2/'+p]==after['SP/code/rend2/'+p]
assert all(before[p]==after[p] for p in before if '/glsl/' in p and not p.endswith('/volumetriclocal_fp.glsl'))
(ev/'IFLC13_RELEASE_FIRE.patch').write_text(''.join(''.join(difflib.unified_diff(before[p].decode().splitlines(True),after[p].decode().splitlines(True),fromfile='a/'+p,tofile='b/'+p)) for p in sorted(changed)))
sha=lambda b:hashlib.sha256(b).hexdigest()
(ev/'IFLC13_RELEASE_SOURCE_SHA256.json').write_text(json.dumps({p:sha(v) for p,v in after.items()},indent=2)+'\n')
(ev/'IFLC13_RELEASE_PROOF.json').write_text(json.dumps({'base_run':41772470237,'causal_run':41789875771,'iflc_sources_unchanged':True,'direct_light_code_unchanged':True,'source_positions_budgets_cfg_unchanged':True,'synthetic_capture_experiment_included':False,'only_glsl_change':'add existing architectural visibility gate to shaped fire 5..7','new_production_cvars':[],'new_fire_changes':{p:{'before':sha(before[p]),'after':sha(after[p])} for p in changed}},indent=2)+'\n')
print('IFLC13_RELEASE_PATCH_APPLIED_NO_DIAGNOSTIC_HOOKS')
