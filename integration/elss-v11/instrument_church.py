#!/usr/bin/env python3
"""Disposable Church proof hooks for ELSS V1.1. Never packaged in user DLL."""
from pathlib import Path
import sys
src=Path(sys.argv[1]).resolve(); root=src/'SP/code/rend2'
p=root/'tr_local.h';s=p.read_text()
anchor='void R_ELSS_List_f(void);\n';assert s.count(anchor)==1
s=s.replace(anchor,anchor+'void R_ELSS_V11_Test_f(void);\n');p.write_text(s)

p=root/'tr_init.c';s=p.read_text()
a='\tri.Cmd_AddCommand( "dw_el_list", R_ELSS_List_f );\n';assert s.count(a)==1
s=s.replace(a,a+'\tri.Cmd_AddCommand( "dw_el_v11_test_fixture", R_ELSS_V11_Test_f );\n\tri.Cmd_AddCommand( "dw_el_v11_test_select", R_ELSS_V11_Test_f );\n\tri.Cmd_AddCommand( "dw_el_v11_test_bind", R_ELSS_V11_Test_f );\n\tri.Cmd_AddCommand( "dw_el_v11_test_audit", R_ELSS_V11_Test_f );\n')
a='\tri.Cmd_RemoveCommand( "dw_el_list" );\n';assert s.count(a)==1
s=s.replace(a,a+'\tri.Cmd_RemoveCommand( "dw_el_v11_test_fixture" );\n\tri.Cmd_RemoveCommand( "dw_el_v11_test_select" );\n\tri.Cmd_RemoveCommand( "dw_el_v11_test_bind" );\n\tri.Cmd_RemoveCommand( "dw_el_v11_test_audit" );\n');p.write_text(s)

p=root/'tr_elss.inc';s=p.read_text()
s+=r'''
/* TEST ONLY: deterministic Church reproduction without shipping map ids. */
void R_ELSS_V11_Test_f(void)
{
    const char *cmd=ri.Cmd_Argv(0);int i;
    R_IssuePendingRenderCommands();if(!R_ELSS_EnsureMap()||!tr.world)return;
    if(!strcmp(cmd,"dw_el_v11_test_fixture")){
        int entity=atoi(ri.Cmd_Argv(1)),state=ri.Cmd_Argc()>2?atoi(ri.Cmd_Argv(2)):1,found=0;
        if(!R_StaticPromoteBuildPersistentRegistry())return;
        for(i=0;i<s_staticPromotePersistentCount;++i){
            staticPromotePersistentLight_t *l=&s_staticPromotePersistentLights[i];
            if(l->candidate.entityOrdinal!=entity)continue;
            ++found;
            ri.Printf(PRINT_ALL,"ELSS11_TEST_FIXTURE entity=%d idx=%d origin=%.3f,%.3f,%.3f state=%d ok=%d\n",
              entity,i,l->candidate.origin[0],l->candidate.origin[1],l->candidate.origin[2],state,R_StaticPromotePhysicalOverrideSet(l,state));
        }
        if(!found)ri.Printf(PRINT_WARNING,"ELSS11_TEST_FIXTURE_MISSING entity=%d\n",entity);
        return;
    }
    if(!strcmp(cmd,"dw_el_v11_test_select")){
        char key[96];int entity=atoi(ri.Cmd_Argv(1));Com_sprintf(key,sizeof(key),"fixture:%d",entity);
        for(i=0;i<s_elssOwnerCount;++i)if(!strcmp(s_elssOwners[i].key,key)){s_elssSelected=i;s_elssPickCount=1;s_elssPicks[0]=i;s_elssPickCursor=0;ri.Printf(PRINT_ALL,"ELSS11_TEST_SELECTED %s\n",key);R_ELSS_Info_f();return;}
        ri.Printf(PRINT_WARNING,"ELSS11_TEST_SELECT_MISSING %s owners=%d\n",key,s_elssOwnerCount);return;
    }
    if(!strcmp(cmd,"dw_el_v11_test_bind")){
        int surface=atoi(ri.Cmd_Argv(1)),tri=atoi(ri.Cmd_Argv(2)),p;elssProfile_t candidate;elssFixture_t test;elssOwner_t *o;
        if(!R_ELSS_Selected())return;o=&s_elssOwners[s_elssSelected];p=R_ELSS_FindProfile(o->key);
        if(p>=0)candidate=s_elssProfiles[p];else{memset(&candidate,0,sizeof(candidate));candidate.used=qtrue;Q_strncpyz(candidate.key,o->key,sizeof(candidate.key));for(i=0;i<ELSS_MAX_SEEDS;++i)candidate.seedTris[i]=-1;}
        if(candidate.seedCount>=ELSS_MAX_SEEDS)return;candidate.seeds[candidate.seedCount]=surface;candidate.seedTris[candidate.seedCount]=tri;++candidate.seedCount;
        if(!R_ELSS_BuildManual(&candidate,o,&test)){ri.Printf(PRINT_WARNING,"ELSS11_TEST_BIND_REFUSED surface=%d tri=%d\n",surface,tri);return;}
        p=R_ELSS_ProfileSlot(o->key,qtrue);if(p<0)return;s_elssProfiles[p]=candidate;s_elssDirty=qtrue;R_ELSS_ResetFixtures();
        ri.Printf(PRINT_ALL,"ELSS11_TEST_BOUND surface=%d tri=%d bodies=%d triangles=%d seeds=%d\n",surface,tri,test.count,test.removed,candidate.seedCount);return;
    }
    ri.Printf(PRINT_ALL,"ELSS11_TEST_AUDIT map=%s selected=%d owners=%d\n",s_elssMap,s_elssSelected,s_elssOwnerCount);
    for(i=0;i<s_elssOwnerCount;++i)ri.Printf(PRINT_ALL,"ELSS11_TEST_OWNER i=%d key=%s origin=%.3f,%.3f,%.3f shadowSlot=%d runtime=%d\n",i,s_elssOwners[i].key,s_elssOwners[i].origin[0],s_elssOwners[i].origin[1],s_elssOwners[i].origin[2],s_elssOwners[i].shadowSlot,s_elssOwners[i].runtimeCount);
    if(s_elssSelected>=0)R_ELSS_Info_f();
}
'''
p.write_text(s)
print('ELSS_V11_CHURCH_TEST_HOOKS_APPLIED')
