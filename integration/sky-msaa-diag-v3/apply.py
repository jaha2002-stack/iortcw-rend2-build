#!/usr/bin/env python3
"""Minimal, repeat-safe diagnostic integration; no modification when --check-only."""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('source', type=Path)
p.add_argument('--check-only', action='store_true')
p.add_argument('--manifest', type=Path)
a = p.parse_args()
root = a.source.resolve()
backend = root/'SP/code/rend2/tr_backend.c'
sky = root/'SP/code/rend2/tr_sky.c'
hdr = root/'SP/code/rend2/tr_sky_diag.h'
local_header = Path(__file__).resolve().with_name('sky_diag_runtime.h')
assert backend.is_file() and sky.is_file() and local_header.is_file()
assert not hdr.exists(), 'DIAGNOSTIC_ALREADY_PRESENT: rerun refused'
b = backend.read_text(encoding='utf-8', errors='surrogateescape')
s = sky.read_text(encoding='utf-8', errors='surrogateescape')
assert 'DARKWOLF_SKY_MSAA_ROOT_CAUSE_MATRIX_V1' not in b+s
assert b.count('void RB_BeginDrawingView (void) {') == 1
assert b.count('const void\t*RB_SwapBuffers( const void *data ) {') == 1
assert b.count('const void *RB_PostProcess(const void *data)') == 1
assert s.count('void RB_StageIteratorSky( void ) {') == 1
assert s.count('DrawSkyBox( tess.shader );') == 1
assert s.count('R_BuildCloudData( &tess );\n\n\tRB_StageIteratorGeneric();') == 1
assert b.count('RB_USLRDRootCauseBeginFrameSample(srcFbo, dstBox);') == 1
assert b.count('if ( clearBits ) {\n\t\tqglClear( clearBits );\n\t}') == 1
assert 'FBO_FastBlit(tr.renderFbo, NULL, tr.msaaResolveFbo, NULL, GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT, GL_NEAREST);' in b
assert 'DARKWOLF_HDR_MSAA_SELECTIVE_SAMPLE_SHADING_PRODUCTION_INTEGRATION' in b
assert 'DARKWOLF_VOL_EDGE' in (root/'SP/code/rend2/glsl/volumetricsun_fp.glsl').read_text() or 'DARKWOLF' in (root/'SP/code/rend2/glsl/volumetricsun_fp.glsl').read_text(), 'volumetric source lineage missing'

def replace_one(content, old, new):
    count = content.count(old)
    assert count == 1, f'Expected unique source anchor, got {count}: {old[:70]!r}'
    return content.replace(old, new, 1)

b = replace_one(b, '#include "tr_dsa.h"\n', '#include "tr_dsa.h"\n#include "tr_sky_diag.h" /* SKY_DIAG_V3: header-only backend diagnostics */\n')
b = replace_one(b, 'if ( clearBits ) {\n\t\tqglClear( clearBits );\n\t}',
                'if ( clearBits ) {\n\t\tqglClear( clearBits );\n\t}\n\tDW_SkyDiagBeginView(); /* SKY_DIAG_V3: reference/control after normal clear */')
b = replace_one(b, '\tGLimp_LogComment( "***************** RB_SwapBuffers *****************\\n\\n\\n" );',
                '\tDW_SkyDiagOnSwap(); /* SKY_DIAG_V3: capture final screen and progress mode */\n\tGLimp_LogComment( "***************** RB_SwapBuffers *****************\\n\\n\\n" );')
b = replace_one(b, '\tRB_USLRDRootCauseBeginFrameSample(srcFbo, dstBox);',
                '\tDW_SkyDiagAfterResolve(srcFbo); /* SKY_DIAG_V3: HDR+depth BEFORE any post effects */\n\tRB_USLRDRootCauseBeginFrameSample(srcFbo, dstBox);')
b = replace_one(b, '\t\t// Resolve the MSAA before anything else',
                '\t\tDW_SkyDiagPreResolve(); /* V3: pre-postprocess snapshot, no sky-stage prerequisite */\n\t\t// Resolve the MSAA before anything else')
s = replace_one(s, '#include "tr_local.h"\n',
                '#include "tr_local.h"\n/* SKY_DIAG_V3: implemented in tr_backend.c, no public renderer ABI change */\nextern int DW_SkyDiagMode(void);\nextern void DW_SkyDiagSkyStage(void);\nextern void DW_SkyDiagSkyProbe(int phase);\nextern void DW_SkyDiagControlUsed(int mode);\n')
s = replace_one(s, 'void RB_StageIteratorSky( void ) {',
                'void RB_StageIteratorSky( void ) {\n\tDW_SkyDiagSkyProbe(0);')
s = replace_one(s, '\tif ( r_fastsky->integer ) {\n\t\treturn;',
                '\tif ( r_fastsky->integer ) {\n\t\tDW_SkyDiagSkyProbe(1);\n\t\treturn;')
s = replace_one(s, '\tif ( skyboxportal && !( backEnd.refdef.rdflags & RDF_SKYBOXPORTAL ) ) {\n\t\treturn;',
                '\tif ( skyboxportal && !( backEnd.refdef.rdflags & RDF_SKYBOXPORTAL ) ) {\n\t\tDW_SkyDiagSkyProbe(2);\n\t\treturn;')
s = replace_one(s, '\t\tDrawSkyBox( tess.shader );', '''\t\t/* SKY_DIAG_V3 modes 2/4: draw all background cube faces, then restore
\t\t * original clipped sky extents for cloud geometry. */
\t\tif (DW_SkyDiagMode() == 2 || DW_SkyDiagMode() == 4) {\n\t\t\tDW_SkyDiagControlUsed(DW_SkyDiagMode());
\t\t\tfloat savedMins[2][6], savedMaxs[2][6];
\t\t\tint face, axis;
\t\t\tmemcpy(savedMins, sky_mins, sizeof(savedMins));
\t\t\tmemcpy(savedMaxs, sky_maxs, sizeof(savedMaxs));
\t\t\tfor (axis = 0; axis < 2; ++axis)
\t\t\t\tfor (face = 0; face < 6; ++face) {
\t\t\t\t\tsky_mins[axis][face] = -1.0f;
\t\t\t\t\tsky_maxs[axis][face] = 1.0f;
\t\t\t\t}
\t\t\tDrawSkyBox( tess.shader );
\t\t\tmemcpy(sky_mins, savedMins, sizeof(savedMins));
\t\t\tmemcpy(sky_maxs, savedMaxs, sizeof(savedMaxs));
\t\t} else {
\t\t\tDrawSkyBox( tess.shader );
\t\t}''')
s = replace_one(s, '\tR_BuildCloudData( &tess );\n\n\tRB_StageIteratorGeneric();',
                '\t/* SKY_DIAG_V3 modes 3/4 isolate cloud geometry and its blend stages. */\n\tif (DW_SkyDiagMode() != 3 && DW_SkyDiagMode() != 4) {\n\t\tR_BuildCloudData( &tess );\n\t\tRB_StageIteratorGeneric();\n\t} else {\n\t\tDW_SkyDiagControlUsed(DW_SkyDiagMode());\n\t}')
s = replace_one(s, '\tbackEnd.skyRenderedThisView = qtrue;',
                '\tbackEnd.skyRenderedThisView = qtrue;\n\tDW_SkyDiagSkyProbe(3);\n\tDW_SkyDiagSkyStage(); /* SKY_DIAG_V3: optional early sky-only MSAA resolve capture */')
header = local_header.read_text(encoding='utf-8')
assert 'DARKWOLF_SKY_MSAA_ROOT_CAUSE_MATRIX_V1' in header
assert s.count('DW_SkyDiagSkyStage();') == 1
assert s.count('DW_SkyDiagSkyProbe(0);') == 1
assert b.count('DW_SkyDiagPreResolve();') == 1
assert b.count('DW_SkyDiagAfterResolve(srcFbo)') == 1
assert b.count('DW_SkyDiagOnSwap()') == 1
assert b.count('DW_SkyDiagBeginView()') == 1
sha = lambda text: hashlib.sha256(text.encode('utf-8', errors='surrogateescape')).hexdigest()
manifest = {'status':'STATIC_SOURCE_TRANSFORM_VALIDATED' if a.check_only else 'APPLIED',
    'base': 'runtime-accepted GitHub Actions #40294211216',
    'source_paths':['SP/code/rend2/tr_backend.c','SP/code/rend2/tr_sky.c','SP/code/rend2/tr_sky_diag.h'],
    'backend_source_before_sha256':hashlib.sha256(backend.read_bytes()).hexdigest(),
    'sky_source_before_sha256':hashlib.sha256(sky.read_bytes()).hexdigest(),
    'backend_source_after_sha256':sha(b),'sky_source_after_sha256':sha(s),
    'new_header_sha256':sha(header),'modes':['REFERENCE','PINK_COLOR_CLEAR','FULL_SKYBOX','CLOUD_SKIP','FULL_SKYBOX_CLOUD_SKIP'],
    'screenshots_are_runtime_proof':False}
if not a.check_only:
    backend.write_text(b, encoding='utf-8', errors='surrogateescape')
    sky.write_text(s, encoding='utf-8', errors='surrogateescape')
    hdr.write_text(header, encoding='utf-8')
if a.manifest:
    a.manifest.parent.mkdir(parents=True, exist_ok=True)
    a.manifest.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print('DARKWOLF_SKY_MSAA_DIAG_SOURCE_CHECK_PASS' if a.check_only else 'DARKWOLF_SKY_MSAA_DIAG_SOURCE_APPLIED')
