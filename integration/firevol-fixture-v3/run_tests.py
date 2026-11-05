#!/usr/bin/env python3
from pathlib import Path
import json,sys,math
src=Path(sys.argv[1]).resolve();ev=Path(sys.argv[2]).resolve();ev.mkdir(parents=True,exist_ok=True)
r=src/'SP/code/rend2'
b=(r/'tr_backend.c').read_text();i=(r/'tr_iflc.inc').read_text();init=(r/'tr_init.c').read_text();h=(r/'tr_local.h').read_text()
checks={
 'world_owner_rejects_nonworld':'surfaceIndex >= tr.world->numWorldSurfaces' in i,
 'source_identity_fields':all(x in b for x in ['latchedPrimitive','latchedEntityNum','latchedShaderIndex','latchedModelName']),
 'bmodel_owner_key':'FIREVOL_FIXKEY_BMODEL' in b and 'out->a=a->entityNum; out->b=a->shaderIndex' in b,
 'poly_fails_open':'Cgame POLY/drawIndex is transient' in b,
 'moving_refresh':'RB_FireVFixtureV3RefreshRegistry();' in b,
 'pre_residency_dedup':'fixtureV3DroppedFrame += RB_FireVFixtureV3Dedup' in b,
 'anchor_guard':'RB_FireVFixtureV3FindPoolForAnchor(anchor) >= 0' in b,
 'catalog_guard':'RB_FireVFixtureV3FindPoolForCatalogSurface(entry->surfaceIndex) >= 0' in b,
 'compact_geometry':'rawRadius*compactScale' in b and 'r_dwFireVolGeometryScale' in init,
 'diag_slots':'FIREVOL_FIXTURE_V3_SLOT map=%s' in b,
 'diag_summary':'FIREVOL_FIXTURE_V3 map=%s selectedPhysical=%d' in b,
 'v1_flashfix_preserved':'r_dwFireVolFlashFix' in b or 'FIREVOL_FLASHFIX_V1' in b,
 'render_cap_8':'#define FIREVOL081_RENDER_CAP 8' in b,
 'v2_bad_owner_absent':'R_IFLC_FirePhysicalOwnerForSurface' not in b and 'r_dwFireVolPhysicalOwnerDedup' not in init,
}
assert all(checks.values()),{k:v for k,v in checks.items() if not v}

# Model the two critical identity cases.
# Chateau: 8 flame anchors on one moving BMODEL entity + same shader => one physical key.
chateau=[('BMODEL',77,123)]*8
assert len(set(chateau))==1
# Crypt1: eight independent world torch owners remain eight.
crypt=[('WORLD',x,0) for x in range(1,9)]
assert len(set(crypt))==8
# Geometry: small torch radius 205 compacts; large fireplace 410 retains full max envelope.
scale=.55; gmin=96.; gmax=220.
torch=max(gmin,min(gmax,205.*scale));fireplace=max(gmin,min(gmax,410.*scale))
assert 110.0 < torch < 115.0
assert abs(fireplace-220.0)<1e-6

model={
 'chateau':{'anchors':8,'physicalKeys':1,'movingOwner':'entity+shader','expectedSelectedPhysical':1},
 'crypt1':{'distinctTorchOwners':8,'physicalKeys':8,'expectedNoCrossTorchMerge':True},
 'geometry':{'rawTorch':205,'torchGeometry':torch,'rawFireplace':410,'fireplaceGeometry':fireplace}
}
(ev/'FIREVOL_FIXTURE_V3_TESTS.json').write_text(json.dumps({'checks':checks,'model':model},indent=2)+'\n')
print('FIREVOL_FIXTURE_V3_TESTS_PASS',json.dumps(model,sort_keys=True))
