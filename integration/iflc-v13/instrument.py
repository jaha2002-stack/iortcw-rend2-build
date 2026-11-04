#!/usr/bin/env python3
"""Isolated native causal harness. Never include these hooks in a user DLL."""
from pathlib import Path
import sys,hashlib,json,difflib
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'testlab/scripts'))
import rc4_requested_views as camera
src=Path(sys.argv[1]);ev=Path(sys.argv[2]);code=src/'SP/code';ev.mkdir(parents=True,exist_ok=True)
before={p.relative_to(src).as_posix():p.read_bytes() for p in code.rglob('*') if p.is_file()}
camera.instrument(src)
def edit(rel,old,new,count=1):
 p=code/rel;t=p.read_text();assert t.count(old)==count,(rel,old[:120],t.count(old));p.write_text(t.replace(old,new))
edit('rend2/tr_electric_fixture.inc','static efFixture_t s_efFixtures[EF_MAX_FIXTURES];','static efFixture_t s_efFixtures[EF_MAX_FIXTURES];\nstatic unsigned int s_efTestPoint, s_efTestWorld;')
edit('rend2/tr_electric_fixture.inc','    entity=(ds->sort>>QSORT_REFENTITYNUM_SHIFT)&REFENTITYNUM_MASK;', '''    if ((backEnd.viewParms.flags & VPF_DLIGHT_WORLD_OCCLUSION) ? !(ri.Cvar_VariableIntegerValue("r_iflc13Electric") & 1) : !(ri.Cvar_VariableIntegerValue("r_iflc13Electric") & 2)) goto original;
    entity=(ds->sort>>QSORT_REFENTITYNUM_SHIFT)&REFENTITYNUM_MASK;''')
edit('rend2/tr_electric_fixture.inc','            RB_SurfaceElectricTrim((srfBspSurface_t *)ds->surface,body->omit,body->triangleCount);','''            if(backEnd.viewParms.flags & VPF_DLIGHT_WORLD_OCCLUSION) s_efTestWorld+=body->removed; else s_efTestPoint+=body->removed;
            RB_SurfaceElectricTrim((srfBspSurface_t *)ds->surface,body->omit,body->triangleCount);''')
with (code/'rend2/tr_electric_fixture.inc').open('a') as f:f.write(r'''
void R_IFLC13_ElectricAudit(void) {
 int i,j;EF_Build();
 ri.Printf(PRINT_ALL,"IFLC13_ELECTRIC counts=%d overflow=%d mode=%d pointTrim=%u worldTrim=%u\n",s_efCount,s_efOverflow,ri.Cvar_VariableIntegerValue("r_iflc13Electric"),s_efTestPoint,s_efTestWorld);
 for(i=0;i<s_efCount;++i){const efFixture_t *f=&s_efFixtures[i];ri.Printf(PRINT_ALL,"IFLC13_FIXTURE aperture=%d origin=%.3f,%.3f,%.3f normal=%.4f,%.4f,%.4f radius=%.3f key=%u bodies=",f->apertureSurface,f->origin[0],f->origin[1],f->origin[2],f->normal[0],f->normal[1],f->normal[2],f->radius,f->key);for(j=0;j<f->bodyCount;++j)ri.Printf(PRINT_ALL,"%d:%d/%d,",f->body[j].surfaceIndex,f->body[j].removed,f->body[j].triangleCount);ri.Printf(PRINT_ALL,"\n");}
}
void R_IFLC13_ElectricCountersClear(void){s_efTestPoint=s_efTestWorld=0;}
''')
edit('rend2/tr_world.c','\t\tif (tr.viewParms.flags & VPF_DLIGHT_WORLD_OCCLUSION) return qfalse;','\t\tif (tr.viewParms.flags & VPF_DLIGHT_WORLD_OCCLUSION) return qfalse;\n\t\tif ((tr.viewParms.flags & VPF_FIREVOL_SYNTHETIC_SHADOW) && (ri.Cvar_VariableIntegerValue("r_iflc13SynthCapture") & 1)) return qfalse;')
edit('rend2/tr_main.c','zNear = (dest->flags & VPF_DLIGHT_WORLD_OCCLUSION) ? 0.25f : r_znear->value;', 'zNear = ((dest->flags & VPF_DLIGHT_WORLD_OCCLUSION) || ((dest->flags & VPF_FIREVOL_SYNTHETIC_SHADOW) && (ri.Cvar_VariableIntegerValue("r_iflc13SynthCapture") & 2))) ? 0.25f : r_znear->value;')
edit('rend2/tr_backend.c','\tGLSL_SetUniformVec4(&tr.volumetricLocalShader, UNIFORM_DLIGHTSHADOWPARAMS, shadowParams);', '''    if(mode>=5 && mode<=8 && useShadow && ri.Cvar_VariableIntegerValue("r_iflc13FireHardShadow")) shadowParams[3]=1.0f;
    if(mode>=5 && mode<=8 && ri.Cvar_VariableIntegerValue("dw_proofShot")>0) {
      static int lastShot=-1;static unsigned int seen=0;int shot=ri.Cvar_VariableIntegerValue("dw_proofShot");
      unsigned int bit=1u<<(((int)source[0]^(int)source[1]^(int)source[2])&31);
      if(shot!=lastShot){lastShot=shot;seen=0;}
      if(!(seen&bit)){seen|=bit;ri.Printf(PRINT_ALL,"IFLC13_VOLUME shot=%d mode=%d shadow=%d origin=%.3f,%.3f,%.3f captureRadius=%.3f plumeRadius=%.3f shadowStrength=%.4f weight=%.4f gain=%.4f\\n",shot,mode,useShadow,source[0],source[1],source[2],source[3],volumeInfo[3],shadowParams[3],sourceWeight,fireVolumeGain);}
    }
\tGLSL_SetUniformVec4(&tr.volumetricLocalShader, UNIFORM_DLIGHTSHADOWPARAMS, shadowParams);''')
with (code/'rend2/tr_local.h').open('a') as f:f.write('\nvoid R_IFLC13_Test_f(void);\nvoid R_IFLC13_ElectricAudit(void);\nvoid R_IFLC13_ElectricCountersClear(void);\nfloat R_IFLC13_DirectGain(const dlight_t *dl);\n')
for token in ('Add','Remove'):
 old=f'ri.Cmd_{token}Command( "dw_fl_select"'+(', R_IFLC_Select_f );' if token=='Add' else ' );')
 new=old
 for cmd in ('dw_fl13_mode','dw_fl13_audit','dw_fl13_target','dw_fl13_electric','dw_fl13_survey'):
  new+=f'\n\tri.Cmd_{token}Command("{cmd}"'+(', R_IFLC13_Test_f);' if token=='Add' else ');')
 edit('rend2/tr_init.c',old,new)
for k in range(3):
 edit('rend2/tr_shade.c',f'\t\tvector[{k}] = dl->color[{k}] * r_dlightIntensity->value;',f'\t\tvector[{k}] = dl->color[{k}] * r_dlightIntensity->value * R_IFLC13_DirectGain(dl);')
edit('rend2/tr_shade.c','\t\tVectorScale(dl->color, r_dlightIntensity->value, vector);','\t\tVectorScale(dl->color, r_dlightIntensity->value * R_IFLC13_DirectGain(dl), vector);')
edit('cgame/cg_view.c','"r_ssgi","r_volumetricSun"','"r_iflc13Electric","r_iflc13DirectMask","r_iflc13FireHardShadow","r_iflc13SynthCapture","r_dwFireLightControl","r_dlightShadowMaxLights","r_dlightWorldContainment","r_bloom","r_hdr","r_postProcess","r_volumetricFireV07Mode","r_volumetricFireSourceMode","r_ssgi","r_volumetricSun"')
with (code/'rend2/tr_iflc.inc').open('a') as f:f.write(r'''
/* Native-only diagnostics. Fixed source IDs belong only in the test scenario. */
float R_IFLC13_DirectGain(const dlight_t *dl) {
 int mask=ri.Cvar_VariableIntegerValue("r_iflc13DirectMask");
 return (mask&2)||((mask&1)&&(dl->iflcOptIn||dl->fireVolumetricSource)) ? 0.0f : 1.0f;
}
void R_IFLC13_Test_f(void) {
 int i,j;const char *cmd=ri.Cmd_Argv(0);
 R_IssuePendingRenderCommands();
 if(!tr.world)return;
 if(!strcmp(cmd,"dw_fl13_mode")) {
  const char *cvars[]={"r_iflc13Electric","r_iflc13DirectMask","r_iflc13FireHardShadow","r_iflc13SynthCapture"};
  for(i=0;i<4;++i)ri.Cvar_Set(cvars[i],ri.Cmd_Argc()>i+1?ri.Cmd_Argv(i+1):"0");
  R_IFLC13_ElectricCountersClear();
  for(i=0;i<DLIGHT_WORLD_CACHE_MAX;++i)tr.dlightWorldCache[i].valid=qfalse;
  for(i=0;i<FIREVOL_SYNTH_SHADOW_CACHE_MAX;++i)tr.fireVolumetricSyntheticShadowCache[i].valid=qfalse;
  return;
 }
 if(!strcmp(cmd,"dw_fl13_survey")) {
  for(i=0;i<tr.world->numWorldSurfaces;++i){const msurface_t *s=&tr.world->surfaces[i];const srfBspSurface_t *b;vec3_t lo,hi;
   if(!s->shader||!s->shader->ssgiEmitter||!s->data||(*s->data!=SF_FACE&&*s->data!=SF_TRIANGLES))continue;
   b=(const srfBspSurface_t*)s->data;if(!b->verts||b->numVerts<3)continue;ClearBounds(lo,hi);for(j=0;j<b->numVerts;++j)AddPointToBounds(b->verts[j].xyz,lo,hi);
   ri.Printf(PRINT_ALL,"IFLC13_EMITTER id=%d shader=%s verts=%d tris=%d lo=%.3f,%.3f,%.3f hi=%.3f,%.3f,%.3f\n",i,s->shader->name,b->numVerts,b->numIndexes/3,lo[0],lo[1],lo[2],hi[0],hi[1],hi[2]);
  }
  R_IFLC13_ElectricAudit();return;
 }
 if(!strcmp(cmd,"dw_fl13_target")) {
  int target=atoi(ri.Cmd_Argv(1));if(!R_IFLC_EnsureCatalog())return;
  for(i=0;i<s_iflcSurfaceCount;++i)if(s_iflcSurfaces[i].surfaceIndex==target){s_iflcSelected=s_iflcSurfaces[i].owner;ri.Printf(PRINT_ALL,"IFLC13_TARGET surface=%d owner=%d key=%s\n",target,s_iflcSelected,s_iflcOwners[s_iflcSelected].key);R_IFLC_Info_f();return;}
  ri.Printf(PRINT_WARNING,"IFLC13_TARGET_MISSING %d\n",target);return;
 }
 if(!strcmp(cmd,"dw_fl13_electric")) {
  int id=atoi(ri.Cmd_Argv(1)),best=-1;float dist=96*96;vec3_t o;const srfBspSurface_t *b;const msurface_t *s;
  if(id<0||id>=tr.world->numWorldSurfaces||!R_StaticPromoteBuildPersistentRegistry())return;s=&tr.world->surfaces[id];
  if(!s->data||(*s->data!=SF_FACE&&*s->data!=SF_TRIANGLES))return;b=(const srfBspSurface_t*)s->data;VectorClear(o);
  for(i=0;i<b->numVerts;++i)VectorAdd(o,b->verts[i].xyz,o);VectorScale(o,1.0f/b->numVerts,o);
  for(i=0;i<s_staticPromotePersistentCount;++i){float d=R_IFLC_DistanceSquared(o,s_staticPromotePersistentLights[i].candidate.origin);if(d<dist){dist=d;best=i;}}
  if(best<0){ri.Printf(PRINT_WARNING,"IFLC13_ELECTRIC_TARGET_MISSING aperture=%d\n",id);return;}
  {staticPromotePersistentLight_t *l=&s_staticPromotePersistentLights[best];int state=ri.Cmd_Argc()>2?atoi(ri.Cmd_Argv(2)):1;
   ri.Printf(PRINT_ALL,"IFLC13_ELECTRIC_TARGET aperture=%d fixture=%d entity=%d origin=%.3f,%.3f,%.3f distance=%.4f state=%d\n",id,best,l->candidate.entityOrdinal,l->candidate.origin[0],l->candidate.origin[1],l->candidate.origin[2],sqrtf(dist),state);
   if(!R_StaticPromotePhysicalOverrideSet(l,state))ri.Printf(PRINT_WARNING,"IFLC13_ELECTRIC_TARGET_SAVE_FAILED\n");}
  return;
 }
 R_IFLC13_ElectricAudit();
 for(i=0;i<tr.refdef.num_dlights&&i<MAX_DLIGHTS;++i){const dlight_t *d=&tr.refdef.dlights[i];int w=tr.refdef.dlightWorldSlot[i],ef=R_ElectricFixtureForLight(d);
  ri.Printf(PRINT_ALL,"IFLC13_LIGHT i=%d class=%d optin=%d fire=%d native=%d fixture=%d origin=%.3f,%.3f,%.3f radius=%.3f rgb=%.5f,%.5f,%.5f directGain=%.1f world=%d point=%d ef=%d efKey=%u cacheKey=%u\n",i,d->shadowSourceClass,d->iflcOptIn,d->fireVolumetricSource,d->nativeAuthoredDlight,d->staticPromoteFixtureId,d->origin[0],d->origin[1],d->origin[2],d->radius,d->color[0],d->color[1],d->color[2],R_IFLC13_DirectGain(d),w,(tr.refdef.dlightShadowMask&(1u<<i))?(int)tr.refdef.dlightShadowSlot[i]:-1,ef,R_ElectricFixtureKey(ef),w>=0&&w<DLIGHT_WORLD_CACHE_MAX?tr.dlightWorldCache[w].electricFixtureKey:0);
 }
 R_IFLC_Info_f();
}
''')
after={p.relative_to(src).as_posix():p.read_bytes() for p in code.rglob('*') if p.is_file()};changed=[k for k in before if before[k]!=after[k]]
assert not any('/glsl/' in k for k in changed)
(ev/'IFLC13_NATIVE_HOOKS.patch').write_text(''.join(''.join(difflib.unified_diff(before[k].decode().splitlines(True),after[k].decode().splitlines(True),fromfile='a/'+k,tofile='b/'+k)) for k in changed))
print('IFLC13_DISPOSABLE_NATIVE_HOOKS',changed,flush=True)
