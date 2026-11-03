#!/usr/bin/env python3
"""Apply the global, geometry-qualified IFLC V1.1 policy to verified V1 source."""
from pathlib import Path
import argparse, hashlib, json, shutil
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('evidence',type=Path);a=p.parse_args()
kit=Path(__file__).resolve().parent
root=a.source.resolve();a.evidence.mkdir(parents=True,exist_ok=True)
paths=['tr_iflc.inc','tr_local.h','tr_main.c','tr_world.c']
before={n:(root/'SP/code/rend2'/n).read_text() for n in paths}
text=dict(before)
def sub(n,old,new,count=1):
 assert text[n].count(old)==count,(n,old,text[n].count(old),count)
 text[n]=text[n].replace(old,new)
sub('tr_iflc.inc','static qboolean R_IFLC_LoadProfile(qboolean explicitReload);','static qboolean R_IFLC_LoadProfile(qboolean explicitReload);\nstatic void R_IFLC_ResetFixtures(void);')
sub('tr_iflc.inc','\ts_iflcOwnerCount = s_iflcSurfaceCount = s_iflcBrushCount = 0;','\tR_IFLC_ResetFixtures();\n\ts_iflcOwnerCount = s_iflcSurfaceCount = s_iflcBrushCount = 0;')
sub('tr_iflc.inc','\ts_iflcOwnerCount = s_iflcSurfaceCount = 0;','\tR_IFLC_ResetFixtures();\n\ts_iflcOwnerCount = s_iflcSurfaceCount = 0;')
sub('tr_iflc.inc','static qboolean R_IFLC_LineVisible(', '#include "tr_iflc_fixture.inc"\n\nstatic qboolean R_IFLC_LineVisible(')
sub('tr_iflc.inc','\towner = &s_iflcOwners[s_iflcSelected]; p = R_IFLC_ProfileForOwner(s_iflcSelected, qfalse);', '\towner = &s_iflcOwners[s_iflcSelected]; p = R_IFLC_ProfileForOwner(s_iflcSelected, qfalse);\n\tR_IFLC_PrepareFixture(s_iflcSelected);\n\tri.Printf(PRINT_ALL, "IFLC: fixtureSelfCasters=%d policyKey=%08x scope=OWN_OPTIN_DIRECT_SHADOWS_ONLY\\n",\n\t\ts_iflcFixtures[s_iflcSelected].count, s_iflcFixtures[s_iflcSelected].policyKey);')
sub('tr_local.h','\tunsigned int lastUse;\n} dlightWorldCache_t;','\tunsigned int lastUse;\n\tunsigned int iflcFixtureKey;\n} dlightWorldCache_t;')
sub('tr_local.h','\tviewParmFlags_t flags;','\tviewParmFlags_t flags;\n\tint iflcFixture;\n\tunsigned int iflcFixtureKey;')
sub('tr_local.h','void R_IFLC_Info_f(void);','void R_IFLC_Info_f(void);\nint R_IFLC_ShadowFixture(const dlight_t *dl);\nunsigned int R_IFLC_FixturePolicyKey(int fixture);\nqboolean R_IFLC_SuppressSelfCaster(const msurface_t *surface);')
sub('tr_world.c','\t// FIXME: bmodel fog?','\tif (R_IFLC_SuppressSelfCaster(surf)) return; // IFLC V1.1: this emitter/mount only.\n\n\t// FIXME: bmodel fog?')
sub('tr_main.c','const vec3_t captureOrigin, float radius)\n{\n\treturn cache->valid && VectorCompare(cache->origin, captureOrigin)\n\t\t&& cache->radius >= radius;', 'const vec3_t captureOrigin, float radius, unsigned int iflcFixtureKey)\n{\n\treturn cache->valid && VectorCompare(cache->origin, captureOrigin)\n\t\t&& cache->radius >= radius && cache->iflcFixtureKey == iflcFixtureKey;')
sub('tr_main.c','R_DlightWorldCacheMatches(&tr.dlightWorldCache[j], testCaptureOrigin, requiredRadius)', 'R_DlightWorldCacheMatches(&tr.dlightWorldCache[j], testCaptureOrigin, requiredRadius, R_IFLC_FixturePolicyKey(R_IFLC_ShadowFixture(dl)))',2)
sub('tr_main.c','\t\t\tshadowParms.zFar = range;','\t\t\tshadowParms.iflcFixture = R_IFLC_ShadowFixture(dl);\n\t\t\tshadowParms.iflcFixtureKey = R_IFLC_FixturePolicyKey(shadowParms.iflcFixture);\n\t\t\tshadowParms.zFar = range;')
sub('tr_main.c','\t\t\tcache->radius = range;','\t\t\tcache->radius = range;\n\t\t\tcache->iflcFixtureKey = shadowParms.iflcFixtureKey;')
sub('tr_main.c','\t\tshadowParms.flags = VPF_SHADOWMAP | VPF_DEPTHSHADOW | VPF_NOVIEWMODEL;','\t\tshadowParms.flags = VPF_SHADOWMAP | VPF_DEPTHSHADOW | VPF_NOVIEWMODEL;\n\t\tshadowParms.iflcFixture = R_IFLC_ShadowFixture(&tr.refdef.dlights[bestLight]);\n\t\tshadowParms.iflcFixtureKey = R_IFLC_FixturePolicyKey(shadowParms.iflcFixture);')
for n in paths:(root/'SP/code/rend2'/n).write_text(text[n])
shutil.copy2(kit/'tr_iflc_fixture.inc',root/'SP/code/rend2/tr_iflc_fixture.inc')
def h(t):return hashlib.sha256(t.encode()).hexdigest()
import re
def function(src, name):
 start=src.index(name+'('); brace=src.index('{',start); depth=1
 for tok in re.finditer(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|[{}]',src[brace+1:],re.S):
  if tok[0] not in ('{','}'):continue
  depth+=1 if tok[0]=='{' else -1
  if depth==0:return src[start:brace+1+tok.end()]
 raise AssertionError(name)
for name in ('R_RenderFireVolumetricSyntheticShadows',):
 if name+'(' in before['tr_main.c']:
  assert function(before['tr_main.c'],name)==function(text['tr_main.c'],name)
module=(kit/'tr_iflc_fixture.inc').read_text()
assert not any(x in module.lower() for x in ('crypt1','crypt2','2992','291','textures/'))
report={'parent_run':41691075610,'accepted_base_run':41408153237,'changes':{n:{'before':h(before[n]),'after':h(text[n])} for n in paths},'module_sha256':h(module),'map_or_material_hardcoding':False,'new_production_cvars':[],'policy':'compact connected own mount, opt-in direct captures only; retain architecture and shadows from other lights','visual_status':'UNVERIFIED'}
(a.evidence/'IFLC_V11_SOURCE_PROOF.json').write_text(json.dumps(report,indent=2)+'\n')
print('IFLC_V11_GLOBAL_SOURCE_PATCH_APPLIED')
