#!/usr/bin/env python3
"""Bounded CSM cache invalidation for exact RC4 Bloom v2, no other renderer edits."""
from pathlib import Path
import argparse
import hashlib

MARK = 'DARKWOLF_RC4_FORCE_SUN_CSM_REPRIME_V1'
RENDER_REL = 'SP/code/rend2/tr_scene.c'

def once(text: str, old: str, new: str, context: str) -> str:
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f'{context}: expected one anchor, found {n}')
    return text.replace(old, new, 1)

GUARD = r'''// DARKWOLF_RC4_FORCE_SUN_CSM_REPRIME_V1
// The world-level fourth cascade is camera-independent but still needs a
// deterministic re-prime when the visible-sun source or view generation changes.
// Ordinary camera movement keeps the historical staggered 1/2/4 cadence.
#define FORCE_SUN_CSM_CUT_DISTANCE_SQ (192.0f * 192.0f)
#define FORCE_SUN_CSM_CUT_FORWARD_DOT 0.8660254f

typedef struct {
	const world_t *world;
	int time;
	vec3_t vieworg;
	vec3_t forward;
	float fovX, fovY;
	float cascadeNear, cascadeFar, cascadeBias;
	int shadowFilter;
} forceSunVisibleCsmState_t;

static forceSunVisibleCsmState_t s_forceSunVisibleCsmState;

static qboolean R_ForceSunVisibleNeedsReprime(const refdef_t *fd)
{
	vec3_t delta;
	if (!s_forceSunVisibleCsmActive ||
		s_forceSunVisibleCsmState.world != tr.world ||
		tr.refdef.areamaskModified ||
		!tr.volumetricSunCsmValid[3])
		return qtrue;
	if (r_shadowCascadeZFar->integer != 0 &&
		(!tr.volumetricSunCsmValid[0] || !tr.volumetricSunCsmValid[1] || !tr.volumetricSunCsmValid[2]))
		return qtrue;
	if (fd->time < s_forceSunVisibleCsmState.time ||
		fd->time - s_forceSunVisibleCsmState.time > 1000)
		return qtrue;
	if (s_forceSunVisibleCsmState.fovX != fd->fov_x ||
		s_forceSunVisibleCsmState.fovY != fd->fov_y ||
		s_forceSunVisibleCsmState.cascadeNear != r_shadowCascadeZNear->value ||
		s_forceSunVisibleCsmState.cascadeFar != r_shadowCascadeZFar->value ||
		s_forceSunVisibleCsmState.cascadeBias != r_shadowCascadeZBias->value ||
		s_forceSunVisibleCsmState.shadowFilter != r_shadowFilter->integer)
		return qtrue;
	VectorSubtract(fd->vieworg, s_forceSunVisibleCsmState.vieworg, delta);
	if (DotProduct(delta, delta) > FORCE_SUN_CSM_CUT_DISTANCE_SQ ||
		DotProduct(fd->viewaxis[0], s_forceSunVisibleCsmState.forward) < FORCE_SUN_CSM_CUT_FORWARD_DOT)
		return qtrue;
	return qfalse;
}

static void R_ForceSunVisibleRemember(const refdef_t *fd)
{
	s_forceSunVisibleCsmState.world = tr.world;
	s_forceSunVisibleCsmState.time = fd->time;
	VectorCopy(fd->vieworg, s_forceSunVisibleCsmState.vieworg);
	VectorCopy(fd->viewaxis[0], s_forceSunVisibleCsmState.forward);
	s_forceSunVisibleCsmState.fovX = fd->fov_x;
	s_forceSunVisibleCsmState.fovY = fd->fov_y;
	s_forceSunVisibleCsmState.cascadeNear = r_shadowCascadeZNear->value;
	s_forceSunVisibleCsmState.cascadeFar = r_shadowCascadeZFar->value;
	s_forceSunVisibleCsmState.cascadeBias = r_shadowCascadeZBias->value;
	s_forceSunVisibleCsmState.shadowFilter = r_shadowFilter->integer;
}

'''

def apply(source: Path) -> None:
    p = source / RENDER_REL
    code = p.read_text(encoding='utf-8')
    if MARK in code:
        raise RuntimeError('already patched; refuse to apply twice')
    if 'DARKWOLF_FORCE_SUN_CSM_SMART_PRODUCTION_V444' not in code:
        raise RuntimeError('missing historically accepted forceSun optimization')
    code = once(code,
                'static int s_forceSunVisibleCsmActive = 0;\n\nstatic qboolean R_ForceSunVisibleShouldUpdateCascade',
                'static int s_forceSunVisibleCsmActive = 0;\n\n' + GUARD + 'static qboolean R_ForceSunVisibleShouldUpdateCascade',
                'inject scoped cache helper')
    code = once(code,
                '\tRE_BeginScene(fd);\n\ttr.volumetricSunPerfCsmRenderedThisFrame = 0;',
                '''\tRE_BeginScene(fd);
\t// DARKWOLF_RC4_FORCE_SUN_CSM_REPRIME_V1: source mode exit invalidates reuse.
\tif (!(fd->rdflags & (RDF_NOWORLDMODEL | RDF_SKYBOXPORTAL)) &&
\t\t(r_forceSun->integer != 1 || !r_sunlightMode->integer || !glRefConfig.framebufferObject))
\t\ts_forceSunVisibleCsmActive = 0;
\ttr.volumetricSunPerfCsmRenderedThisFrame = 0;''',
                'invalidate on mode exit')
    code = once(code,
                '''\t\t\tif (!s_forceSunVisibleCsmActive)
\t\t\t{
\t\t\t\tfor (cascade = 0; cascade < 4; ++cascade)
\t\t\t\t\ttr.volumetricSunCsmValid[cascade] = qfalse;
\t\t\t\ts_forceSunVisibleCsmActive = 1;
\t\t\t}

\t\t\tsunChanged''',
                '''\t\t\tif (R_ForceSunVisibleNeedsReprime(fd))
\t\t\t{
\t\t\t\tfor (cascade = 0; cascade < 4; ++cascade)
\t\t\t\t\ttr.volumetricSunCsmValid[cascade] = qfalse;
\t\t\t}
\t\t\ts_forceSunVisibleCsmActive = 1;
\t\t\tR_ForceSunVisibleRemember(fd);

\t\t\tsunChanged''',
                're-prime cache before consumer')
    p.write_text(code, encoding='utf-8', newline='\n')
    print('RC4_FORCE_SUN_REPRIME_APPLIED', p, hashlib.sha256(code.encode()).hexdigest())

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('source', type=Path)
    args = ap.parse_args()
    apply(args.source)
