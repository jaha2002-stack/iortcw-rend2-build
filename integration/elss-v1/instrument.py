#!/usr/bin/env python3
"""Disposable ELSS V1 proof hooks. Never packaged into the user DLL."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'testlab/scripts'))
import rc4_requested_views as camera
src=Path(sys.argv[1]).resolve();ev=Path(sys.argv[2]).resolve();ev.mkdir(parents=True,exist_ok=True)
camera.instrument(src)
code=src/'SP/code/rend2'

p=code/'tr_local.h';s=p.read_text()
anchor='void R_ELSS_List_f(void);\n'
assert s.count(anchor)==1
s=s.replace(anchor,anchor+'void R_ELSS_Test_f(void);\n')
p.write_text(s)

p=code/'tr_init.c';s=p.read_text()
a='\tri.Cmd_AddCommand( "dw_el_list", R_ELSS_List_f );\n';assert s.count(a)==1
s=s.replace(a,a+'\tri.Cmd_AddCommand( "dw_el_test_enable", R_ELSS_Test_f );\n\tri.Cmd_AddCommand( "dw_el_test_audit", R_ELSS_Test_f );\n')
a='\tri.Cmd_RemoveCommand( "dw_el_list" );\n';assert s.count(a)==1
s=s.replace(a,a+'\tri.Cmd_RemoveCommand( "dw_el_test_enable" );\n\tri.Cmd_RemoveCommand( "dw_el_test_audit" );\n')
p.write_text(s)

p=code/'tr_elss.inc';s=p.read_text()
s += r'''
/* ELSS TEST ONLY: deterministic physical-light activation from an emitter BSP
 * ordinal. Production code contains no map or surface ordinals. */
void R_ELSS_Test_f(void)
{
    const char *cmd=ri.Cmd_Argv(0);int i;
    R_IssuePendingRenderCommands();
    if(!tr.world)return;
    if(!strcmp(cmd,"dw_el_test_enable")) {
        int id=atoi(ri.Cmd_Argv(1)),state=ri.Cmd_Argc()>2?atoi(ri.Cmd_Argv(2)):1,best=-1;
        float best2=128.0f*128.0f;vec3_t center;const msurface_t *surface;const srfBspSurface_t *b;
        if(id<0||id>=tr.world->numWorldSurfaces||!R_StaticPromoteBuildPersistentRegistry())return;
        surface=&tr.world->surfaces[id];
        if(!surface->data||(*surface->data!=SF_FACE&&*surface->data!=SF_TRIANGLES))return;
        b=(const srfBspSurface_t*)surface->data;if(!b->verts||b->numVerts<3)return;VectorClear(center);
        for(i=0;i<b->numVerts;++i)VectorAdd(center,b->verts[i].xyz,center);
        VectorScale(center,1.0f/b->numVerts,center);
        for(i=0;i<s_staticPromotePersistentCount;++i){
            float d=R_IFLC_DistanceSquared(center,s_staticPromotePersistentLights[i].candidate.origin);
            if(d<best2){best2=d;best=i;}
        }
        if(best<0){ri.Printf(PRINT_WARNING,"ELSS_TEST_ENABLE_MISSING emitter=%d\n",id);return;}
        {staticPromotePersistentLight_t *l=&s_staticPromotePersistentLights[best];
         qboolean ok=R_StaticPromotePhysicalOverrideSet(l,state);
         ri.Printf(PRINT_ALL,"ELSS_TEST_ENABLE emitter=%d fixture=%d entity=%d origin=%.3f,%.3f,%.3f distance=%.4f state=%d ok=%d\n",
          id,best,l->candidate.entityOrdinal,l->candidate.origin[0],l->candidate.origin[1],l->candidate.origin[2],sqrtf(best2),state,ok);
        }
        return;
    }
    ri.Printf(PRINT_ALL,"ELSS_TEST_AUDIT map=%s selected=%d lights=%d master=%d\n",
      tr.world?tr.world->baseName:"",s_elssSelected,tr.refdef.num_dlights,r_dwElectricLightControl?r_dwElectricLightControl->integer:0);
    for(i=0;i<tr.refdef.num_dlights&&i<MAX_DLIGHTS;++i){
        const dlight_t *d=&tr.refdef.dlights[i];char key[ELSS_KEY_MAX];int fixture=R_ElectricFixtureForLight(d);
        if(!R_ELSS_KeyForLight(d,key,sizeof(key)))continue;
        ri.Printf(PRINT_ALL,"ELSS_TEST_LIGHT i=%d key=%s origin=%.3f,%.3f,%.3f radius=%.3f pointSlot=%d worldSlot=%d fixture=%d policyKey=%u native=%d promoted=%d localVol=%d\n",
          i,key,d->origin[0],d->origin[1],d->origin[2],d->radius,
          (tr.refdef.dlightShadowMask&(1u<<i))?(int)tr.refdef.dlightShadowSlot[i]:-1,
          (int)tr.refdef.dlightWorldSlot[i],fixture,R_ElectricFixtureKey(fixture),
          d->nativeAuthoredDlight,d->staticPromoteFixtureId,d->localVolumetricLamp);
    }
    R_ELSS_Info_f();
}
'''
p.write_text(s)
print('ELSS_V1_DISPOSABLE_PROOF_HOOKS_APPLIED')
