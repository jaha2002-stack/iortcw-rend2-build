#!/usr/bin/env python3
"""Triangle-qualified electric policy; no IFLC/GLSL/origin/budget changes."""
from pathlib import Path
import argparse,hashlib,json,shutil,difflib
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('evidence',type=Path);a=p.parse_args();a.evidence.mkdir(parents=True,exist_ok=True)
root=a.source/'SP/code/rend2';kit=Path(__file__).resolve().parent
names=['tr_local.h','tr_main.c','tr_backend.c','tr_surface.c','tr_bsp.c']
before={n:(root/n).read_text() for n in names};text=dict(before)
def sub(n,old,new,count=1):
 assert text[n].count(old)==count,(n,old[:100],text[n].count(old),count)
 text[n]=text[n].replace(old,new)
sub('tr_local.h','\tunsigned int iflcFixtureKey;','\tunsigned int iflcFixtureKey;\n\tunsigned int electricFixtureKey;',2)
sub('tr_local.h','\tint iflcFixture;','\tint iflcFixture;\n\tint electricFixture;')
sub('tr_local.h','void R_IFLC_ResetWorld(void);','void R_IFLC_ResetWorld(void);\nvoid R_ElectricFixtureReset(void);\nint R_ElectricFixtureForLight(const dlight_t *dl);\nunsigned int R_ElectricFixtureKey(int fixture);\nvoid RB_SurfaceElectricTrim(srfBspSurface_t *srf, const unsigned char *omit, int triangleCount);')
sub('tr_bsp.c','\tR_IFLC_ResetWorld();','\tR_IFLC_ResetWorld();\n\tR_ElectricFixtureReset();')
sub('tr_backend.c','static qboolean DW_Boss1CleanSkipSourceLocalCaster(', '#include "tr_electric_fixture.inc"\n\nstatic qboolean DW_Boss1CleanSkipSourceLocalCaster(')
sub('tr_backend.c','rb_surfaceTable[ *drawSurf->surface ]( drawSurf->surface );','RB_ElectricFixtureSurface(drawSurf);',2)
sub('tr_main.c','const vec3_t captureOrigin, float radius, unsigned int iflcFixtureKey)','const vec3_t captureOrigin, float radius, unsigned int iflcFixtureKey, unsigned int electricFixtureKey)')
sub('tr_main.c','&& cache->radius >= radius && cache->iflcFixtureKey == iflcFixtureKey;','&& cache->radius >= radius && cache->iflcFixtureKey == iflcFixtureKey\n\t\t&& cache->electricFixtureKey == electricFixtureKey;')
sub('tr_main.c','R_IFLC_FixturePolicyKey(R_IFLC_ShadowFixture(dl))))','R_IFLC_FixturePolicyKey(R_IFLC_ShadowFixture(dl)), R_ElectricFixtureKey(R_ElectricFixtureForLight(dl))))',2)
sub('tr_main.c','\t\t\tshadowParms.iflcFixtureKey = R_IFLC_FixturePolicyKey(shadowParms.iflcFixture);','\t\t\tshadowParms.iflcFixtureKey = R_IFLC_FixturePolicyKey(shadowParms.iflcFixture);\n\t\t\tshadowParms.electricFixture = R_ElectricFixtureForLight(dl);\n\t\t\tshadowParms.electricFixtureKey = R_ElectricFixtureKey(shadowParms.electricFixture);')
sub('tr_main.c','\t\t\tcache->iflcFixtureKey = shadowParms.iflcFixtureKey;','\t\t\tcache->iflcFixtureKey = shadowParms.iflcFixtureKey;\n\t\t\tcache->electricFixtureKey = shadowParms.electricFixtureKey;')
sub('tr_main.c','\n\t\tshadowParms.iflcFixtureKey = R_IFLC_FixturePolicyKey(shadowParms.iflcFixture);','\n\t\tshadowParms.iflcFixtureKey = R_IFLC_FixturePolicyKey(shadowParms.iflcFixture);\n\t\tshadowParms.electricFixture = R_ElectricFixtureForLight(&tr.refdef.dlights[bestLight]);\n\t\tshadowParms.electricFixtureKey = R_ElectricFixtureKey(shadowParms.electricFixture);')
helper=r'''
/* Copy surviving triangles synchronously; never put stack indices in a VAO. */
void RB_SurfaceElectricTrim(srfBspSurface_t *srf, const unsigned char *omit, int triangleCount)
{
    glIndex_t indexes[512 * 3];
    int i,j,count=0;
    if (!srf || !omit || triangleCount < 1 || triangleCount > 512 || srf->numIndexes != triangleCount*3) {
        if (srf) RB_SurfaceTriangles(srf);
        return;
    }
    for(i=0;i<triangleCount;++i) if(!omit[i])
        for(j=0;j<3;++j) indexes[count++]=srf->indexes[i*3+j];
    if(!count) return;
    RB_SurfaceVertsAndIndexes(srf->numVerts,srf->verts,count,indexes,srf->dlightBits,srf->pshadowBits);
}

'''
sub('tr_surface.c','/*\n==============\nRB_SurfaceBeam',helper+'/*\n==============\nRB_SurfaceBeam')
for n in names:(root/n).write_text(text[n])
shutil.copy2(kit/'tr_electric_fixture.inc',root/'tr_electric_fixture.inc')
patch=''.join(''.join(difflib.unified_diff(before[n].splitlines(True),text[n].splitlines(True),fromfile='a/SP/code/rend2/'+n,tofile='b/SP/code/rend2/'+n)) for n in names)
(a.evidence/'IFLC13_ELECTRIC.patch').write_text(patch)
sha=lambda x:hashlib.sha256(x).hexdigest()
proof={'base_run':41772470237,'new_production_cvars':[],'iflc_module_changed':False,'glsl_changed':False,'origin_budget_changed':False,'changed':{n:{'before':sha(before[n].encode()),'after':sha(text[n].encode())} for n in names},'module_sha256':sha((root/'tr_electric_fixture.inc').read_bytes())}
(a.evidence/'IFLC13_ELECTRIC_PROOF.json').write_text(json.dumps(proof,indent=2)+'\n');print('IFLC13_ELECTRIC_APPLIED',flush=True)
