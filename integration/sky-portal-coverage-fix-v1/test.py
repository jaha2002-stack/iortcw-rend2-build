#!/usr/bin/env python3
"""Static safety tests for sky-portal cloud-only coverage candidate."""
from pathlib import Path
import re,sys
src=Path(__file__).with_name('apply.py').read_text()
assert 'DARKWOLF_SKY_PORTAL_CLOUD_COVERAGE_CANDIDATE_V1' in src
assert "stageCount * 5 * (SKY_SUBDIVISIONS + 1) * (SKY_SUBDIVISIONS + 1) < SHADER_MAX_VERTEXES" in src
assert 'Q_stricmp(tr.world->baseName, "trainyard")' in src and 'Q_stricmp(tr.world->baseName, "factory")' in src
assert 'memcpy(sky_mins, originalMins, sizeof(originalMins))' in src
assert 'memcpy(sky_maxs, originalMaxs, sizeof(originalMaxs))' in src
assert 'glState.currentFBO == tr.renderFbo && tr.msaaResolveFbo' in src
assert 'r_ext_framebuffer_multisample->integer >= 2' in src
assert 'RDF_SKYBOXPORTAL' in src
assert 'R_BuildCloudData( &tess );' in src
assert 'RB_StageIteratorGeneric();' in src
assert 'GL_MULTISAMPLE' not in src, 'Must not toggle multisample state'
assert 'qglDisable(' not in src, 'Must not globally disable any renderer feature'
assert 'MAX_SHADER_STAGES' in src
# Runtime shader capacity C source: 5 faces * 9*9 verts, first-stage 5*8*8*6 indices
assert (5*9*9*9) < 4000
assert (5*8*8*6) < 6*4000
assert (5*9*9*10) >=4000  # excludes stage>9 rather than crashing
print('DW_PORTAL_SKY_CLOUD_COVERAGE_SOURCE_UNIT_TESTS_PASS')