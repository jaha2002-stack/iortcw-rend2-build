#!/usr/bin/env python3
"""Disposable Church fixture:107 hooks for ELSS V1.1 proof. Never packaged."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'testlab/scripts'))
import rc4_requested_views as camera
src=Path(sys.argv[1]).resolve();camera.instrument(src);root=src/'SP/code/rend2'

p=root/'tr_local.h';s=p.read_text()
anchor='void R_ELSS_List_f(void);\n';assert s.count(anchor)==1
s=s.replace(anchor,anchor+'void R_ELSS_V11_TestFixture_f(void);\n')
p.write_text(s)

p=root/'tr_init.c';s=p.read_text()
a='\tri.Cmd_AddCommand( "dw_el_list", R_ELSS_List_f );\n';assert s.count(a)==1
s=s.replace(a,a+'\tri.Cmd_AddCommand( "dw_el_v11_test_fixture", R_ELSS_V11_TestFixture_f );\n\tri.Cmd_AddCommand( "dw_el_v11_test_audit", R_ELSS_V11_TestFixture_f );\n')
a='\tri.Cmd_RemoveCommand( "dw_el_list" );\n';assert s.count(a)==1
s=s.replace(a,a+'\tri.Cmd_RemoveCommand( "dw_el_v11_test_fixture" );\n\tri.Cmd_RemoveCommand( "dw_el_v11_test_audit" );\n')
p.write_text(s)

p=root/'tr_elss.inc';s=p.read_text()
s+=r'''
/* TEST ONLY. Production V1.1 contains no fixture ordinals or map names. */
void R_ELSS_V11_TestFixture_f(void)
{
    const char *cmd=ri.Cmd_Argv(0);int requested=atoi(ri.Cmd_Argv(1)),i;
    R_IssuePendingRenderCommands();
    if(!tr.world||!R_StaticPromoteBuildPersistentRegistry())return;
    if(!strcmp(cmd,"dw_el_v11_test_fixture")){
        int state=ri.Cmd_Argc()>2?atoi(ri.Cmd_Argv(2)):1,found=0;
        for(i=0;i<s_staticPromotePersistentCount;++i){
            staticPromotePersistentLight_t *l=&s_staticPromotePersistentLights[i];
            if(l->candidate.entityOrdinal!=requested)continue;
            ++found;
            ri.Printf(PRINT_ALL,"ELSS11_TEST_FIXTURE entity=%d idx=%d origin=%.3f,%.3f,%.3f state=%d ok=%d\n",
              requested,i,l->candidate.origin[0],l->candidate.origin[1],l->candidate.origin[2],state,R_StaticPromotePhysicalOverrideSet(l,state));
        }
        if(!found)ri.Printf(PRINT_WARNING,"ELSS11_TEST_FIXTURE_MISSING entity=%d\n",requested);
        return;
    }
    ri.Printf(PRINT_ALL,"ELSS11_TEST_AUDIT entity=%d lights=%d master=%d\n",requested,tr.refdef.num_dlights,r_dwElectricLightControl?r_dwElectricLightControl->integer:0);
    for(i=0;i<tr.refdef.num_dlights&&i<MAX_DLIGHTS;++i){
        const dlight_t *d=&tr.refdef.dlights[i];char key[96];int fixture;
        if(d->staticPromoteFixtureId!=requested)continue;
        if(!R_ELSS_KeyForLight(d,key,sizeof(key)))continue;
        fixture=R_ElectricFixtureForLight(d);
        ri.Printf(PRINT_ALL,"ELSS11_TEST_LIGHT i=%d key=%s origin=%.3f,%.3f,%.3f radius=%.3f pointSlot=%d policyFixture=%d policyKey=%u\n",
          i,key,d->origin[0],d->origin[1],d->origin[2],d->radius,
          (tr.refdef.dlightShadowMask&(1u<<i))?(int)tr.refdef.dlightShadowSlot[i]:-1,
          fixture,R_ElectricFixtureKey(fixture));
    }
    if(s_elssSelected>=0)R_ELSS_Info_f();
}
'''
p.write_text(s)
print('ELSS_V11_CHURCH_TEST_HOOKS_APPLIED')
