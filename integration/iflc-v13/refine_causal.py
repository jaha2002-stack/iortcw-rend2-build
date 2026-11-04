#!/usr/bin/env python3
"""Second isolated causal revision: head connectivity, stable caches, world gate."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=ROOT/'tr_electric_fixture.inc';s=p.read_text()
helper=r'''
/* Only components of the SAME proven model mesh, contained in the head box,
 * may join its housing. Require actual triangle contact/intersection, not just
 * proximity of bounds. This admits a swivel yoke and the head axle but never
 * the long stand, feet, an adjacent wall, or a different BSP mesh. */
static qboolean EF_SegmentTriangle(const vec3_t a, const vec3_t b,
                                  const vec3_t p, const vec3_t q, const vec3_t r)
{
    vec3_t d,u,v,h,t,c; float det,x,y,z;
    VectorSubtract(b,a,d);VectorSubtract(q,p,u);VectorSubtract(r,p,v);
    CrossProduct(d,v,h);det=DotProduct(u,h);
    if(fabsf(det)<0.000001f)return qfalse;
    VectorSubtract(a,p,t);x=DotProduct(t,h)/det;
    if(x < -0.001f || x > 1.001f)return qfalse;
    CrossProduct(t,u,c);y=DotProduct(d,c)/det;
    if(y < -0.001f || x+y > 1.001f)return qfalse;
    z=DotProduct(v,c)/det;
    return z >= -0.001f && z <= 1.001f;
}
static qboolean EF_ComponentsContact(const srfBspSurface_t *b, int a, int c)
{
    int i,j;
    for(i=0;i<3;++i) {
        const float *p=b->verts[b->indexes[a*3+i]].xyz;
        const float *q=b->verts[b->indexes[a*3+(i+1)%3]].xyz;
        if(EF_SegmentTriangle(p,q,b->verts[b->indexes[c*3]].xyz,
             b->verts[b->indexes[c*3+1]].xyz,b->verts[b->indexes[c*3+2]].xyz))return qtrue;
        for(j=0;j<3;++j)
            if(EF_Dist2(p,b->verts[b->indexes[c*3+j]].xyz)<0.015625f)return qtrue;
    }
    return qfalse;
}
static void EF_JoinHeadComponents(const efFixture_t *f, efBody_t *out)
{
    const srfBspSurface_t *b=out->mesh;
    unsigned char visited[EF_MAX_TRIS];
    int i,j,k,n=out->triangleCount;
    qboolean changed;
    vec3_t lo,hi;
    float margin=MIN(4.0f, f->radius*.3f);
    ClearBounds(lo,hi);
    for(i=0;i<n;++i)if(out->omit[i])for(j=0;j<3;++j)
        AddPointToBounds(b->verts[b->indexes[i*3+j]].xyz,lo,hi);
    do {
    changed=qfalse;memcpy(visited,out->omit,sizeof(visited));
    for(i=0;i<n;++i)if(!visited[i]) {
        int head=0,tail=0,queue[EF_MAX_TRIS];qboolean inside=qtrue,touches=qfalse;
        queue[tail++]=i;visited[i]=1;
        while(head<tail) {
            int current=queue[head++];
            for(j=0;j<n;++j)if(!visited[j]&&EF_TrianglesAdjacent(b,current,j)) {
                visited[j]=1;queue[tail++]=j;
            }
        }
        if(tail<8||tail>64||out->removed+tail>128)continue;
        for(j=0;j<tail&&inside;++j)for(k=0;k<3;++k) {
            const float *p=b->verts[b->indexes[queue[j]*3+k]].xyz;
            int axis;for(axis=0;axis<3;++axis)
                if(p[axis]<lo[axis]-margin||p[axis]>hi[axis]+margin)inside=qfalse;
        }
        if(!inside)continue;
        for(j=0;j<tail&&!touches;++j)for(k=0;k<n;++k)if(out->omit[k]&&
             (EF_ComponentsContact(b,queue[j],k)||EF_ComponentsContact(b,k,queue[j]))) {
            touches=qtrue;break;
        }
        if(touches){changed=qtrue;for(j=0;j<tail;++j){out->omit[queue[j]]=1;++out->removed;}}
    }
    } while(changed);
}

'''
anchor='static unsigned int EF_Hash('
assert s.count(anchor)==1
s=s.replace(anchor,helper+anchor)
s=s.replace('body.surfaceIndex=j; temp.body[temp.bodyCount++]=body;','EF_JoinHeadComponents(&temp,&body);\n            body.surfaceIndex=j; temp.body[temp.bodyCount++]=body;')
p.write_text(s)

p=ROOT/'instrument.py';s=p.read_text()
marker="with (code/'rend2/tr_local.h').open('a') as f:"
assert s.count(marker)==1
extra=r'''
edit('rend2/tr_backend.c','static void RB_LocalVolumetricRenderEx(',r"""
/* Test-only reuse of an already existing, uniquely associated world capture. */
static int RB_IFLC13_FireWorldOwner(const dlight_t *lamp, const vec3_t plume)
{
 int i,match=-1;
 for(i=0;i<backEnd.refdef.num_dlights&&i<MAX_DLIGHTS;++i){
  const dlight_t *d=&backEnd.refdef.dlights[i];vec3_t delta;float distance;
  int slot=(int)backEnd.refdef.dlightWorldSlot[i];
  if(!d->worldOcclusion||slot<0||slot>=DLIGHT_WORLD_CACHE_MAX||!tr.dlightWorldCubemaps[slot])continue;
  if(!(d->iflcOptIn||d->fireVolumetricSource))continue;
  VectorSubtract(lamp->origin,d->origin,delta);distance=DotProduct(delta,delta);
  if(distance>.0001f){
   if(!d->iflcOptIn||!plume)continue;
   VectorSubtract(plume,d->origin,delta);if(DotProduct(delta,delta)>16*16)continue;
  }
  if(match>=0)return -1;match=i;
 }
 return match;
}
static void RB_LocalVolumetricRenderEx(""")
edit('rend2/tr_backend.c','\tif (!srcFbo || !tr.quarterFbo[0] || !tr.renderDepthImage || !tr.volumetricLocalShader.program)',
     '\tif (mode>=5 && mode<=8 && ri.Cvar_VariableIntegerValue("r_iflc13VolumeOnlyTarget") && !R_IFLC13_VolumeTarget(lamp,fireVolumeOrigin)) return;\n\tif (!srcFbo || !tr.quarterFbo[0] || !tr.renderDepthImage || !tr.volumetricLocalShader.program)')
edit('rend2/tr_backend.c','\tGLSL_BindProgram(&tr.volumetricLocalShader);',r"""
 if(mode>=5&&mode<=7&&lamp&&ri.Cvar_VariableIntegerValue("r_iflc13FireWorld")) {
  int wi=RB_IFLC13_FireWorldOwner(lamp,fireVolumeOrigin?fireVolumeOrigin:lamp->origin);
  if(wi>=0){int slot=(int)backEnd.refdef.dlightWorldSlot[wi];
   VectorCopy4(backEnd.refdef.dlightWorldOrigin[wi],alarmWorldCapture);
   if(alarmWorldCapture[3]<-.5f)alarmWorldCapture[3]=-alarmWorldCapture[3]-2.0f;
   if(alarmWorldCapture[3]>0)alarmWorldCube=tr.dlightWorldCubemaps[slot];
   else VectorSet4(alarmWorldCapture,0,0,0,0);
  }
 }
\tGLSL_BindProgram(&tr.volumetricLocalShader);""".replace('\\t','\t'))
edit('rend2/glsl/volumetriclocal_fp.glsl','if (mode == 3 && u_DlightWorldOrigin.w > 0.0)',
     'if ((mode == 3 || (mode >= 5 && mode <= 7)) && u_DlightWorldOrigin.w > 0.0)')
with (code/'rend2/tr_electric_fixture.inc').open('a') as f:f.write(r"""
static int s_efShadeTarget=-1;static vec3_t s_efShadeOrigin;
void R_IFLC13_SetShade(int surface,const vec3_t origin){s_efShadeTarget=surface;VectorCopy(origin,s_efShadeOrigin);}
static qboolean RB_IFLC13_SkipShade(const drawSurf_t *ds){
 if(!ri.Cvar_VariableIntegerValue("r_iflc13Shade")||!tr.world||s_efShadeTarget<0||s_efShadeTarget>=tr.world->numWorldSurfaces)return qfalse;
 if((backEnd.viewParms.flags&(VPF_SHADOWMAP|VPF_DEPTHSHADOW))!=(VPF_SHADOWMAP|VPF_DEPTHSHADOW)||
    (backEnd.viewParms.flags&(VPF_ORTHOGRAPHIC|VPF_FIREVOL_SYNTHETIC_SHADOW)))return qfalse;
 if(((ds->sort>>QSORT_REFENTITYNUM_SHIFT)&REFENTITYNUM_MASK)!=REFENTITYNUM_WORLD)return qfalse;
 return ds->surface==tr.world->surfaces[s_efShadeTarget].data&&EF_Dist2(backEnd.viewParms.or.origin,s_efShadeOrigin)<.001f;
}
""")
edit('rend2/tr_electric_fixture.inc','static void RB_ElectricFixtureSurface(const drawSurf_t *ds)',
     'static qboolean RB_IFLC13_SkipShade(const drawSurf_t *ds);\nstatic void RB_ElectricFixtureSurface(const drawSurf_t *ds)')
edit('rend2/tr_electric_fixture.inc','    int i,entity,fixture=backEnd.viewParms.electricFixture;',
     '    int i,entity,fixture=backEnd.viewParms.electricFixture;\n    if(RB_IFLC13_SkipShade(ds))return;')
'''
s=s.replace(marker,extra+'\n'+marker)
s=s.replace('float R_IFLC13_DirectGain(const dlight_t *dl);\\n', 'float R_IFLC13_DirectGain(const dlight_t *dl);\\nqboolean R_IFLC13_VolumeTarget(const dlight_t *dl,const vec3_t origin);\\nvoid R_IFLC13_SetShade(int surface,const vec3_t origin);\\n')
s=s.replace('"r_iflc13Electric","r_iflc13DirectMask","r_iflc13FireHardShadow","r_iflc13SynthCapture"', '"r_iflc13Electric","r_iflc13DirectMask","r_iflc13FireHardShadow","r_iflc13SynthCapture","r_iflc13FireWorld","r_iflc13VolumeOnlyTarget"')
s=s.replace('for(i=0;i<4;++i)ri.Cvar_Set', 'for(i=0;i<6;++i)ri.Cvar_Set')
s=s.replace('  for(i=0;i<DLIGHT_WORLD_CACHE_MAX;++i)tr.dlightWorldCache[i].valid=qfalse;\n  for(i=0;i<FIREVOL_SYNTH_SHADOW_CACHE_MAX;++i)tr.fireVolumetricSyntheticShadowCache[i].valid=qfalse;',
'''  /* Recapture only when actual capture policy changes, not on RGB controls. */
  {static int oldCapture=-1;int capture=ri.Cvar_VariableIntegerValue("r_iflc13SynthCapture");
   if(capture!=oldCapture){for(i=0;i<FIREVOL_SYNTH_SHADOW_CACHE_MAX;++i)tr.fireVolumetricSyntheticShadowCache[i].valid=qfalse;oldCapture=capture;}}
  for(i=0;i<DLIGHT_WORLD_CACHE_MAX;++i)tr.dlightWorldCache[i].valid=qfalse;''')
s=s.replace(' return (mask&2)||', ' if((mask&4)&&!dl->iflcOptIn)return 0.0f;\n return (mask&2)||')
s=s.replace('void R_IFLC13_Test_f(void) {',r'''qboolean R_IFLC13_VolumeTarget(const dlight_t *dl,const vec3_t origin) {
 if(!s_iflcReady||s_iflcSelected<0||s_iflcSelected>=s_iflcOwnerCount||!dl)return qfalse;
 return R_IFLC_DistanceSquared(origin?origin:dl->origin,s_iflcOwners[s_iflcSelected].origin)<16.0f*16.0f;
}
void R_IFLC13_Test_f(void) {''')
s=s.replace('   if(!R_StaticPromotePhysicalOverrideSet(l,state))', '   R_IFLC13_SetShade(ri.Cmd_Argc()>3?atoi(ri.Cmd_Argv(3)):-1,l->candidate.origin);\n   if(!R_StaticPromotePhysicalOverrideSet(l,state))')
s=s.replace("assert not any('/glsl/' in k for k in changed)", "assert [k for k in changed if '/glsl/' in k]==['SP/code/rend2/glsl/volumetriclocal_fp.glsl']")
s=s.replace('shadowStrength=%.4f weight=%.4f gain=%.4f', 'shadowStrength=%.4f weight=%.4f gain=%.4f worldGate=%.6f')
s=s.replace('sourceWeight,fireVolumeGain);', 'sourceWeight,fireVolumeGain,alarmWorldCapture[3]);')
p.write_text(s)

p=ROOT/'runtime.py';s=p.read_text()
start=s.index(" if mapname=='escape1':\n");end=s.index(' views=[]',start)
s=s[:start]+" if mapname=='escape1':ids=[13323,13325,13288]\n"+s[end:]
s=s.replace("anchor[2]-(22 if kind=='electric' else 35)","anchor[2]+(28 if mapname=='escape1' else -22 if kind=='electric' else -35)")
s=s.replace("'set r_iflc13SynthCapture 0'", "'set r_iflc13SynthCapture 0','set r_iflc13FireWorld 0','set r_iflc13VolumeOnlyTarget 0','set r_iflc13Shade 0'")
s=s.replace("f'dw_fl13_electric {v[\"surface\"]} 1'", "f'dw_fl13_electric {v[\"surface\"]} 1 {v[\"surface\"]-1 if mapname==\"escape1\" else -1}'")
s=s.replace(" for label,e,d,h,c,f,l,s,g,b in matrix:"," if kind=='fire':\n   matrix=[('baseline',3,0,0,0,1,1,1,1,1),('no_fire_volume',3,0,0,0,0,1,1,1,1),('world_gate',3,0,0,0,1,1,1,1,1),('world_gate_repeat',3,0,0,0,1,1,1,1,1),('isolated_baseline',3,4,0,0,1,1,1,1,1),('isolated_gate',3,4,0,0,1,1,1,1,1),('isolated_no_volume',3,4,0,0,0,1,1,1,1),('isolated_no_both',3,2,0,0,0,1,1,1,1),('restored',3,0,0,0,1,1,1,1,1)]\n  if mapname=='escape1':matrix += [('no_shade',3,0,0,0,1,1,1,1,1),('shade_restored',3,0,0,0,1,1,1,1,1)]\n  for label,e,d,h,c,f,l,s,g,b in matrix:")
s=s.replace("f'dw_fl13_mode {e} {d} {h} {c}'", "f'dw_fl13_mode {e} {d} {h} {c} {int(\"gate\" in label)} {int(label.startswith(\"isolated\"))}',f'set r_iflc13Shade {int(label==\"no_shade\")}'")
s=s.replace("'wait 12',f'echo IFLC13_STATE", "'wait 36',f'echo IFLC13_STATE")
s=s.replace("'capture':c,'fireVol':f", "'capture':c,'worldGate':int('gate' in label),'onlyTarget':int(label.startswith('isolated')),'fireVol':f")
s=s.replace("'r_iflc13SynthCapture':s['capture'],'r_dlightShadowMaxLights':3", "'r_iflc13SynthCapture':s['capture'],'r_iflc13FireWorld':s['worldGate'],'r_iflc13VolumeOnlyTarget':s['onlyTarget'],'r_dlightShadowMaxLights':3")
p.write_text(s)
print('IFLC13_CAUSAL_REFINEMENT_APPLIED')
