#!/usr/bin/env python3
"""Disposable native TestLab only. Never package these hooks in Win64."""
from pathlib import Path
import sys,hashlib,json,difflib
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'testlab/scripts'))
import rc4_requested_views as camera
src=Path(sys.argv[1]);ev=Path(sys.argv[2]);code=src/'SP/code'
before={p.relative_to(src).as_posix():p.read_bytes() for p in code.rglob('*') if p.is_file()}
camera.instrument(src)
def edit(rel,old,new,count=1):
 p=code/rel;t=p.read_text();assert t.count(old)==count,(rel,old,t.count(old));p.write_text(t.replace(old,new))
edit('rend2/tr_iflc_fixture.inc','#define IFLC_FIXTURE_CAP 48','#define IFLC_FIXTURE_CAP 48\nstatic unsigned int s_iflc12CasterHits[16384];')
edit('rend2/tr_iflc_fixture.inc','    if (result->built && !slender) return;','    if (result->built && !slender) return;\n    if (slender && ri.Cvar_VariableIntegerValue("r_iflc12Legacy")) return;')
edit('rend2/tr_iflc_fixture.inc','        if (index == f->surfaces[mid]) return qtrue;','        if (index == f->surfaces[mid]) { if (index < 16384) ++s_iflc12CasterHits[index]; return qtrue; }')
edit('rend2/tr_local.h','\tint iflcFixture;','\tint iflcFixture;\n\tint iflc12Castle;')
with (code/'rend2/tr_local.h').open('a') as f:f.write('\nvoid R_IFLC12_Test_f(void);\nqboolean R_IFLC12_CastleLight(const dlight_t *dl);\nqboolean R_IFLC12_SkipCaster(const msurface_t *s);\n')
edit('rend2/tr_init.c','ri.Cmd_AddCommand( "dw_fl_select", R_IFLC_Select_f );','ri.Cmd_AddCommand( "dw_fl_select", R_IFLC_Select_f );\n\tri.Cmd_AddCommand("dw_fl12_mode", R_IFLC12_Test_f);\n\tri.Cmd_AddCommand("dw_fl12_audit", R_IFLC12_Test_f);')
edit('rend2/tr_init.c','ri.Cmd_RemoveCommand( "dw_fl_select" );','ri.Cmd_RemoveCommand( "dw_fl_select" );\n\tri.Cmd_RemoveCommand("dw_fl12_mode");\n\tri.Cmd_RemoveCommand("dw_fl12_audit");')
edit('rend2/tr_main.c','\t\t\tshadowParms.iflcFixture = R_IFLC_ShadowFixture(dl);','\t\t\tshadowParms.iflc12Castle = R_IFLC12_CastleLight(dl);\n\t\t\tshadowParms.iflcFixture = R_IFLC_ShadowFixture(dl);')
edit('rend2/tr_main.c','\t\tshadowParms.iflcFixture = R_IFLC_ShadowFixture(&tr.refdef.dlights[bestLight]);','\t\tshadowParms.iflc12Castle = R_IFLC12_CastleLight(&tr.refdef.dlights[bestLight]);\n\t\tshadowParms.iflcFixture = R_IFLC_ShadowFixture(&tr.refdef.dlights[bestLight]);')
edit('rend2/tr_world.c','\tif (R_IFLC_SuppressSelfCaster(surf)) return;','\tif (R_IFLC12_SkipCaster(surf)) return;\n\tif (R_IFLC_SuppressSelfCaster(surf)) return;')
edit('rend2/tr_shade.c','\t\tvector[0] = dl->color[0] * r_dlightIntensity->value;','\t\tvector[0] = dl->color[0] * r_dlightIntensity->value * ((R_IFLC12_CastleLight(dl) && (ri.Cvar_VariableIntegerValue("r_iflc12CastleMask") & 8)) ? 0.0f : 1.0f);')
for k in (1,2):
 edit('rend2/tr_shade.c',f'\t\tvector[{k}] = dl->color[{k}] * r_dlightIntensity->value;',f'\t\tvector[{k}] = dl->color[{k}] * r_dlightIntensity->value * ((R_IFLC12_CastleLight(dl) && (ri.Cvar_VariableIntegerValue("r_iflc12CastleMask") & 8)) ? 0.0f : 1.0f);')
edit('rend2/tr_shade.c','\t\tVectorScale(dl->color, r_dlightIntensity->value, vector);','\t\tVectorScale(dl->color, r_dlightIntensity->value * ((R_IFLC12_CastleLight(dl) && (ri.Cvar_VariableIntegerValue("r_iflc12CastleMask") & 8)) ? 0.0f : 1.0f), vector);')
edit('cgame/cg_view.c','"r_ssgi","r_volumetricSun"','"r_iflc12Legacy","r_iflc12CastleMask","r_dwFireLightControl","r_dlightShadowMaxLights","r_dlightWorldContainment","r_hdr","r_postProcess","r_volumetricFireV07Mode","r_volumetricFireSourceMode","r_ssgi","r_volumetricSun"')
with (code/'rend2/tr_iflc.inc').open('a') as f:f.write(r'''
/* Test-only known target IDs are prohibited from the production classifier. */
qboolean R_IFLC12_CastleLight(const dlight_t *dl) {
 return tr.world && !Q_stricmp(tr.world->baseName,"castle") && dl && dl->nativeAuthoredDlight && dl->fireVolumetricNativeOrdinal==349 &&
 fabsf(dl->origin[0]+126)<.01f && fabsf(dl->origin[1]-62)<.01f && fabsf(dl->origin[2]+144)<.01f;
}
qboolean R_IFLC12_SkipCaster(const msurface_t *s) {
 int mask,index;
 if (!tr.world || !tr.viewParms.iflc12Castle || tr.currentEntityNum!=REFENTITYNUM_WORLD ||
  (tr.viewParms.flags & (VPF_SHADOWMAP|VPF_DEPTHSHADOW))!=(VPF_SHADOWMAP|VPF_DEPTHSHADOW) ||
  (tr.viewParms.flags & (VPF_FIREVOL_SYNTHETIC_SHADOW|VPF_ORTHOGRAPHIC)))return qfalse;
 index=(int)(s-tr.world->surfaces);mask=ri.Cvar_VariableIntegerValue("r_iflc12CastleMask");
 if (((mask&1)&&index>=3672&&index<=3675)||((mask&2)&&index>=3681&&index<=3704)||((mask&4)&&index>=3676&&index<=3680)) {
  if(index>=0&&index<16384)++s_iflc12CasterHits[index];return qtrue;
 }
 return qfalse;
}
void R_IFLC12_Test_f(void) {
 int i,j;
 R_IssuePendingRenderCommands();
 if(!strcmp(ri.Cmd_Argv(0),"dw_fl12_mode")) {
  ri.Cvar_Set("r_iflc12Legacy",ri.Cmd_Argc()>1?ri.Cmd_Argv(1):"0");
  ri.Cvar_Set("r_iflc12CastleMask",ri.Cmd_Argc()>2?ri.Cmd_Argv(2):"0");
  R_IFLC_ResetFixtures();memset(s_iflc12CasterHits,0,sizeof(s_iflc12CasterHits));
  for(i=0;i<DLIGHT_WORLD_CACHE_MAX;++i)tr.dlightWorldCache[i].valid=qfalse;
  return;
 }
 if(!R_IFLC_EnsureCatalog())return;
 if(ri.Cmd_Argc()>1&&!strcmp(ri.Cmd_Argv(1),"catalog")) {
  for(i=0;i<s_iflcOwnerCount;++i) {
   R_IFLC_PrepareFixture(i);
   ri.Printf(PRINT_ALL,"IFLC12_OWNER map=%s key=%s route=%s origin=%.3f,%.3f,%.3f selfCasters=%d ids=",s_iflcMap,s_iflcOwners[i].key,R_IFLC_Route(&s_iflcOwners[i]),s_iflcOwners[i].origin[0],s_iflcOwners[i].origin[1],s_iflcOwners[i].origin[2],s_iflcFixtures[i].count);
   for(j=0;j<s_iflcFixtures[i].count;++j)ri.Printf(PRINT_ALL,"%d,",s_iflcFixtures[i].surfaces[j]);ri.Printf(PRINT_ALL,"\n");
  }
 }
 if(s_iflcSelected>=0&&s_iflcSelected<s_iflcOwnerCount) {
  const iflcFixture_t *f=&s_iflcFixtures[s_iflcSelected];
  ri.Printf(PRINT_ALL,"IFLC12_SELECTED key=%s selfCasters=%d submittedExclusions=",s_iflcOwners[s_iflcSelected].key,f->count);
  for(j=0;j<f->count;++j)ri.Printf(PRINT_ALL,"%d:%u,",f->surfaces[j],f->surfaces[j]<16384?s_iflc12CasterHits[f->surfaces[j]]:0);ri.Printf(PRINT_ALL,"\n");
 }
 for(i=0;i<tr.refdef.num_dlights&&i<MAX_DLIGHTS;++i) {
  const dlight_t *dl=&tr.refdef.dlights[i];int w=tr.refdef.dlightWorldSlot[i],fixture=R_IFLC_ShadowFixture(dl);
  if(!dl->iflcOptIn&&!R_IFLC12_CastleLight(dl))continue;
  ri.Printf(PRINT_ALL,"IFLC12_LIGHT index=%d native=%d optin=%d origin=%.3f,%.3f,%.3f radius=%.3f rgb=%.6f,%.6f,%.6f policy=%u cachePolicy=%u worldSlot=%d worldOrigin=%.3f,%.3f,%.3f pointSlot=%d captureOrigin=%.3f,%.3f,%.3f captureRadius=%.3f\n",i,dl->fireVolumetricNativeOrdinal,dl->iflcOptIn,dl->origin[0],dl->origin[1],dl->origin[2],dl->radius,dl->color[0],dl->color[1],dl->color[2],R_IFLC_FixturePolicyKey(fixture),w>=0&&w<DLIGHT_WORLD_CACHE_MAX?tr.dlightWorldCache[w].iflcFixtureKey:0,w,tr.refdef.dlightWorldOrigin[i][0],tr.refdef.dlightWorldOrigin[i][1],tr.refdef.dlightWorldOrigin[i][2],(tr.refdef.dlightShadowMask&(1u<<i))?(int)tr.refdef.dlightShadowSlot[i]:-1,tr.refdef.dlightShadowCaptureOrigin[i][0],tr.refdef.dlightShadowCaptureOrigin[i][1],tr.refdef.dlightShadowCaptureOrigin[i][2],tr.refdef.dlightShadowCaptureRadius[i]);
 }
 if(!Q_stricmp(s_iflcMap,"castle")) {
  ri.Printf(PRINT_ALL,"IFLC12_CASTLE_MASK value=%d hits=",ri.Cvar_VariableIntegerValue("r_iflc12CastleMask"));
  for(i=3672;i<=3704;++i)if(s_iflc12CasterHits[i])ri.Printf(PRINT_ALL,"%d:%u,",i,s_iflc12CasterHits[i]);ri.Printf(PRINT_ALL,"\n");
 }
}
''')
after={p.relative_to(src).as_posix():p.read_bytes() for p in code.rglob('*') if p.is_file()}
changed=[k for k in before if before[k]!=after[k]]
assert not any('/glsl/' in k for k in changed)
(ev/'IFLC12_NATIVE_HOOKS.patch').write_text(''.join(''.join(difflib.unified_diff(before[k].decode().splitlines(True),after[k].decode().splitlines(True),fromfile='a/'+k,tofile='b/'+k)) for k in changed))
(ev/'IFLC12_NATIVE_HOOKS.json').write_text(json.dumps({'test_only':True,'changed':changed,'production_packaged_before_hooks':True,'glsl_unchanged':True},indent=2)+'\n')
print('DISPOSABLE_NATIVE_TEST_HOOKS_ONLY')
