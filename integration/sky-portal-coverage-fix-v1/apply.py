#!/usr/bin/env python3
"""Apply restricted portal-sky cloud-coverage repair to exact DarkWolf base.

Only tr_sky.c is modified. The sky shader/material/texture math is preserved;
this changes the portion of the sky dome rasterized for cloud-only portal skies.
Runtime visual validation remains necessary.
"""
import argparse,hashlib,json,difflib
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('source',type=Path)
p.add_argument('--check-only',action='store_true')
p.add_argument('--proof',type=Path)
p.add_argument('--patch',type=Path)
a=p.parse_args()
src=a.source/'SP/code/rend2/tr_sky.c'
assert src.is_file(),src
before=src.read_text(encoding='utf-8',errors='surrogateescape')
marker='DARKWOLF_SKY_PORTAL_CLOUD_COVERAGE_CANDIDATE_V1'
assert marker not in before, 'PATCH_ALREADY_APPLIED'
anchor='''	// generate the vertexes for all the clouds, which will be drawn
	// by the generic shader routine
	R_BuildCloudData( &tess );

	RB_StageIteratorGeneric();'''
assert before.count(anchor)==1,('SOURCE_ANCHOR_MISMATCH',before.count(anchor))
assert before.count('void RB_StageIteratorSky( void ) {')==1
assert before.count('R_BuildCloudData( &tess );')==1
assert before.count('static float\tsky_mins[2][6], sky_maxs[2][6];')==1
assert 'DARKWOLF_HDR_MSAA_SELECTIVE_SAMPLE_SHADING_PRODUCTION_INTEGRATION' in (a.source/'SP/code/rend2/tr_fbo.c').read_text(), 'REQUIRED_ACCEPTED_MSAA_STACK_NOT_PRESENT'
fix='''	// DARKWOLF_SKY_PORTAL_CLOUD_COVERAGE_CANDIDATE_V1
	// The Wolfenstein skybox-portal maps trainyard/factory use cloud-only sky
	// shaders (there is no outerbox).  Their original clip-derived cloud bounds
	// can leave unpainted multisample pixels at the portal sky silhouette.
	// Expand ONLY cloud sky coverage to all five non-bottom cube faces.  Keep
	// all materials, colors, alpha blending and original geometry behind the
	// skyline; main-world rendering, shadows and other maps are unaffected.
	// The original clipped limits are restored immediately for innerbox/users.
	{
		qboolean fullPortalCoverage = qfalse;
		float originalMins[2][6], originalMaxs[2][6];
		int face, axis, stageCount = 0;
		if (tr.world && tess.shader->sky.cloudHeight &&
		    (backEnd.refdef.rdflags & RDF_SKYBOXPORTAL) &&
		    glState.currentFBO == tr.renderFbo && tr.msaaResolveFbo &&
		    r_hdr && r_hdr->integer &&
		    r_ext_framebuffer_multisample && r_ext_framebuffer_multisample->integer >= 2 &&
		    (Q_stricmp(tr.world->baseName, "trainyard") == 0 ||
		     Q_stricmp(tr.world->baseName, "factory") == 0)) {
			for (stageCount = 0; stageCount < MAX_SHADER_STAGES && tess.xstages[stageCount]; ++stageCount) { }
			// Five 9x9 cloud faces per active stage for SKY_SUBDIVISIONS=8.
			// Fall back to original geometry for a complex shader that could
			// exceed tess vertex capacity, rather than risking overflow.
			if (stageCount > 0 &&
			    stageCount * 5 * (SKY_SUBDIVISIONS + 1) * (SKY_SUBDIVISIONS + 1) < SHADER_MAX_VERTEXES &&
			    5 * SKY_SUBDIVISIONS * SKY_SUBDIVISIONS * 6 < SHADER_MAX_INDEXES)
				fullPortalCoverage = qtrue;
		}
		if (fullPortalCoverage) {
			memcpy(originalMins, sky_mins, sizeof(originalMins));
			memcpy(originalMaxs, sky_maxs, sizeof(originalMaxs));
			for (axis = 0; axis < 2; ++axis) {
				for (face = 0; face < 5; ++face) {
					sky_mins[axis][face] = -1.0f;
					sky_maxs[axis][face] = 1.0f;
				}
			}
		}
		R_BuildCloudData( &tess );
		if (fullPortalCoverage) {
			memcpy(sky_mins, originalMins, sizeof(originalMins));
			memcpy(sky_maxs, originalMaxs, sizeof(originalMaxs));
		}
	}

	RB_StageIteratorGeneric();'''
after=before.replace(anchor,fix,1)
assert after.count(marker)==1
assert after.count('R_BuildCloudData( &tess );')==1
assert after.count('RB_StageIteratorGeneric();')==1
B=lambda b:hashlib.sha256(b).hexdigest()
proof=dict(status='STATIC_CHECK_PASS' if a.check_only else 'APPLIED',
base='2026-10-26 actions 40294211216',candidate='CLOUD_PORTAL_FULL_COVERAGE',
original_sha256=B(before.encode('utf-8',errors='surrogateescape')),
patched_sha256=B(after.encode('utf-8',errors='surrogateescape')),
files_changed=['SP/code/rend2/tr_sky.c'],other_runtime_files='NO_CHANGE',
triggers=['RDF_SKYBOXPORTAL','HDR MSAA FBO','map:trainyard|factory','sky.cloudHeight'],
excluded=['no regular sky outerbox dependency','no postprocess modification','no MSAA disable','no material change'],
validation='CI build is NOT GPU visual acceptance')
if a.patch:
 a.patch.parent.mkdir(parents=True,exist_ok=True)
 a.patch.write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/SP/code/rend2/tr_sky.c',tofile='b/SP/code/rend2/tr_sky.c')))
if a.proof:
 a.proof.parent.mkdir(parents=True,exist_ok=True); a.proof.write_text(json.dumps(proof,indent=2)+'\n')
if not a.check_only:src.write_text(after,encoding='utf-8',errors='surrogateescape')
print('DW_PORTAL_SKY_CLOUD_COVERAGE_PATCH_PRECHECK_PASS' if a.check_only else 'DW_PORTAL_SKY_CLOUD_COVERAGE_PATCH_APPLIED',proof['patched_sha256'])