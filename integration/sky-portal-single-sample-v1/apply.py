#!/usr/bin/env python3
"""Isolate Trainyard/Factory portal-sky rendering to the existing single-sample HDR resolve FBO.

The final portal color is then copied (single -> multisample, all samples filled)
into the accepted 8x MSAA render FBO. The main world continues to use original
8x MSAA/depth/CSM/SSGI/volumetrics. Only tr_backend.c changes.
"""
import argparse, hashlib, difflib, json
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('source', type=Path)
p.add_argument('--check-only', action='store_true')
p.add_argument('--proof', type=Path)
p.add_argument('--patch', type=Path)
a=p.parse_args()
root=a.source.resolve()
backend=root/'SP/code/rend2/tr_backend.c'
fbo=root/'SP/code/rend2/tr_fbo.c'
sky=root/'SP/code/rend2/tr_sky.c'
assert all(x.exists() for x in (backend,fbo,sky)), 'REQUIRED_ACCEPTED_SOURCE_MISSING'
before=backend.read_text(encoding='utf-8',errors='surrogateescape')
assert 'DARKWOLF_PORTAL_SKY_SINGLE_SAMPLE_COMPOSITE_V1' not in before,'ALREADY_APPLIED'
assert 'DARKWOLF_HDR_MSAA_SELECTIVE_SAMPLE_SHADING_PRODUCTION_INTEGRATION' in fbo.read_text(errors='surrogateescape')
assert 'RB_StageIteratorSky' in sky.read_text(errors='surrogateescape')

def replace(s,old,new):
    n=s.count(old)
    assert n==1,('UNIQUE_ANCHOR_REQUIRED',n,old[:100])
    return s.replace(old,new,1)

s=before
# Only redirect portal-sky, not world, shadows, mirrors, cubemaps, or other maps.
s=replace(s,
    'const void\t*RB_DrawSurfs( const void *data ) {\n\tconst drawSurfsCommand_t\t*cmd;\n\tqboolean isShadowView;',
    'const void\t*RB_DrawSurfs( const void *data ) {\n\tconst drawSurfsCommand_t\t*cmd;\n\tqboolean isShadowView;\n\tqboolean dwPortalSkySingleSample = qfalse; // DARKWOLF_PORTAL_SKY_SINGLE_SAMPLE_COMPOSITE_V1')
anchor='\tisShadowView = !!(backEnd.viewParms.flags & VPF_DEPTHSHADOW);'
addition='''\tisShadowView = !!(backEnd.viewParms.flags & VPF_DEPTHSHADOW);

	/* DARKWOLF_PORTAL_SKY_SINGLE_SAMPLE_COMPOSITE_V1
	 * On the reported maps the dark 1px stipple persists with all clouds disabled
	 * and is present in resolved HDR with depth 1.0. Draw the ENTIRE portal-sky
	 * scene into the stock single-sample HDR resolve framebuffer. Its full-size
	 * RGBA16F color texture and depth texture are already allocated and checked
	 * by FBO_Init. Before the main view, expand the final portal color into EVERY
	 * sample of the existing MSAA renderbuffer via legal OpenGL framebuffer blit.
	 * World geometry, depth prepass, sun CSM, SSGI, Tesla, volumetrics and the
	 * existing HDR resolve/postprocess continue completely unchanged.
	 */
	if (skyboxportal &&
	    (backEnd.refdef.rdflags & (RDF_SKYBOXPORTAL | RDF_DRAWSKYBOX)) ==
	        (RDF_SKYBOXPORTAL | RDF_DRAWSKYBOX) &&
	    !(backEnd.refdef.rdflags & RDF_NOWORLDMODEL) &&
	    !isShadowView && !(backEnd.viewParms.flags & VPF_SHADOWMAP) &&
	    !backEnd.viewParms.isPortal && !backEnd.viewParms.targetFbo &&
	    glRefConfig.framebufferObject && glRefConfig.framebufferBlit &&
	    tr.renderFbo && tr.msaaResolveFbo &&
	    tr.renderFbo->width == tr.msaaResolveFbo->width &&
	    tr.renderFbo->height == tr.msaaResolveFbo->height &&
	    r_hdr && r_hdr->integer && r_ext_framebuffer_multisample &&
	    r_ext_framebuffer_multisample->integer >= 2 &&
	    r_portalsky && r_portalsky->integer && tr.world &&
	    (!Q_stricmp(tr.world->baseName, "trainyard") ||
	     !Q_stricmp(tr.world->baseName, "factory")))
	{
		static char s_dwPortalSkyLoggedMap[MAX_QPATH] = "";
		dwPortalSkySingleSample = qtrue;
		backEnd.viewParms.targetFbo = tr.msaaResolveFbo;
		if (Q_stricmp(s_dwPortalSkyLoggedMap, tr.world->baseName))
		{
			Q_strncpyz(s_dwPortalSkyLoggedMap, tr.world->baseName, sizeof(s_dwPortalSkyLoggedMap));
			ri.Printf(PRINT_ALL,
			    "DW_PORTAL_SKY_SINGLE_SAMPLE_ACTIVE map=%s skyFbo=_msaaResolve "
			    "worldFbo=_render fullSize=1 mainWorldMSAA=%d\\n",
			    tr.world->baseName, r_ext_framebuffer_multisample->integer);
		}
	}'''
s=replace(s,anchor,addition)
# The existing portal-sky view normally keeps color in the MSAA buffer. Because
# it is now being drawn to the shared single-sample resolve texture, clear its
# PREVIOUS frame color to the same fog-clear color already selected in this view.
anchor='\tif ( clearBits ) {\n\t\tqglClear( clearBits );\n\t}'
addition='''	/* DARKWOLF_PORTAL_SKY_SINGLE_SAMPLE_COMPOSITE_V1: avoid stale pixels from the
	 * previous HDR resolve while preserving the existing portal fog clear color.
	 * The main world NEVER clears the inherited color, exactly as before. */
	if ((backEnd.refdef.rdflags & RDF_SKYBOXPORTAL) &&
	    backEnd.viewParms.targetFbo == tr.msaaResolveFbo &&
	    tr.msaaResolveFbo && tr.renderFbo)
	{
		qglColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
		clearBits |= GL_COLOR_BUFFER_BIT;
	}
	if ( clearBits ) {
		qglClear( clearBits );
	}'''
s=replace(s,anchor,addition)
# Do not overwrite the single-sample portal depth with unrelated old MSAA depth
# during its depth prepass. The depth is already resident in renderDepthImage.
anchor='\t\t\tif (tr.msaaResolveFbo)\n\t\t\t{\n\t\t\t\t// If we\'re using multisampling, resolve the depth first'
addition='''			if (tr.msaaResolveFbo && !dwPortalSkySingleSample)
			{
				// If we're using multisampling, resolve the depth first.
				// DARKWOLF_PORTAL_SKY_SINGLE_SAMPLE_COMPOSITE_V1: no self-overwrite
				// of portal-depth while already rendering in the resolve FBO.'''
s=replace(s,anchor,addition)
# At the very end of portal view, when all transparent and world surfaces are
# complete, fill every sample in MSAA _render with the SAME portal-sky color.
# The next main-world view clears depth but deliberately preserves this color.
anchor='''	// FIXME? backEnd.viewParms doesn't get properly initialized for 2D drawing.
	// r_cubeMapping 1 generates cubemaps with R_RenderCubemapSide()'''
addition='''	/* DARKWOLF_PORTAL_SKY_SINGLE_SAMPLE_COMPOSITE_V1
	 * GL_ARB_framebuffer_object, BlitFramebuffer section: a read framebuffer
	 * with SAMPLE_BUFFERS=0 copied into a draw framebuffer with SAMPLE_BUFFERS>0
	 * replicates the source color to ALL draw samples. This is not an MSAA
	 * resolve and does NOT disable multisampling for the following world scene.
	 * DO NOT copy portal depth: the main view clears and renders its own depth. */
	if (dwPortalSkySingleSample)
	{
		qglColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
		FBO_FastBlit(tr.msaaResolveFbo, NULL, tr.renderFbo, NULL,
		             GL_COLOR_BUFFER_BIT, GL_NEAREST);
		backEnd.viewParms.targetFbo = NULL;
	}

	// FIXME? backEnd.viewParms doesn't get properly initialized for 2D drawing.
	// r_cubeMapping 1 generates cubemaps with R_RenderCubemapSide()'''
s=replace(s,anchor,addition)

assert s.count('DARKWOLF_PORTAL_SKY_SINGLE_SAMPLE_COMPOSITE_V1')==5
assert s.count('FBO_FastBlit(tr.msaaResolveFbo, NULL, tr.renderFbo, NULL,')==1
assert 'FBO_FastBlit(tr.renderFbo, NULL, tr.msaaResolveFbo, NULL, GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT, GL_NEAREST);' in s, 'DEFAULT_MAIN_RESOLVE_MUST_REMAIN'
assert s.count('RB_RenderDrawSurfList( cmd->drawSurfs, cmd->numDrawSurfs );')==3
B=lambda b:hashlib.sha256(b).hexdigest()
proof={
 'status':'STATIC_CHECK_PASS' if a.check_only else 'APPLIED',
 'candidate':'DARKWOLF_PORTAL_SKY_SINGLE_SAMPLE_COMPOSITE_V1',
 'accepted_base':{'run_id':40294211216,'source_commit':'cc6c1c706b0c6484ec427d2ed6b3bf3408e18546'},
 'source_before_sha256':B(before.encode('utf-8',errors='surrogateescape')),
 'source_after_sha256':B(s.encode('utf-8',errors='surrogateescape')),
 'files_changed':['SP/code/rend2/tr_backend.c'],
 'conditions':['Trainyard|Factory','RDF_SKYBOXPORTAL|RDF_DRAWSKYBOX','HDR','MSAA>=2','main_screen_only','non_shadow'],
 'technical_effect':'render complete portal sky in existing single sample RGBA16F resolve FBO; blit all portal colors into original 8x MSAA render FBO; world scene unchanged',
 'gpu_visual_validation':'PENDING_USER_TEST'
}
if a.patch:
 a.patch.parent.mkdir(parents=True,exist_ok=True)
 a.patch.write_text(''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='a/SP/code/rend2/tr_backend.c',tofile='b/SP/code/rend2/tr_backend.c')))
if a.proof:
 a.proof.parent.mkdir(parents=True,exist_ok=True)
 a.proof.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
if not a.check_only:backend.write_text(s,encoding='utf-8',errors='surrogateescape')
print('DW_PORTAL_SINGLE_SAMPLE_SOURCE_CHECK_PASS' if a.check_only else 'DW_PORTAL_SINGLE_SAMPLE_SOURCE_APPLIED',proof['source_after_sha256'])