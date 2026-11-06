#!/usr/bin/env python3
from pathlib import Path
import sys
src=Path(sys.argv[1]).resolve();root=src/'SP/code/rend2'

p=root/'tr_local.h';s=p.read_text()
anchor='unsigned int R_ElectricFixtureKey(int fixture);\n'
assert s.count(anchor)==1
s=s.replace(anchor,anchor+'void R_ELSS_V11_AutoEnable_f(void);\nvoid R_ELSS_V11_AutoAudit_f(void);\n');p.write_text(s)

p=root/'tr_init.c';s=p.read_text()
a='\tri.Cmd_AddCommand( "dw_el_list", R_ELSS_List_f );\n';assert s.count(a)==1
s=s.replace(a,a+'\tri.Cmd_AddCommand( "dw_el_v11_auto_enable", R_ELSS_V11_AutoEnable_f );\n\tri.Cmd_AddCommand( "dw_el_v11_auto_audit", R_ELSS_V11_AutoAudit_f );\n')
a='\tri.Cmd_RemoveCommand( "dw_el_list" );\n';assert s.count(a)==1
s=s.replace(a,a+'\tri.Cmd_RemoveCommand( "dw_el_v11_auto_enable" );\n\tri.Cmd_RemoveCommand( "dw_el_v11_auto_audit" );\n');p.write_text(s)

# StaticPromote internals live in the tr_scene translation unit with tr_elss.inc.
p=root/'tr_elss.inc';s=p.read_text()
s+=r'''
/* TEST ONLY: activate one promoted fixture so backend AUTO geometry can be audited. */
void R_ELSS_V11_AutoEnable_f(void)
{
    int requested=atoi(ri.Cmd_Argv(1)),state=ri.Cmd_Argc()>2?atoi(ri.Cmd_Argv(2)):1,i,found=0;
    R_IssuePendingRenderCommands();
    if(!tr.world||!R_StaticPromoteBuildPersistentRegistry())return;
    for(i=0;i<s_staticPromotePersistentCount;++i) {
        staticPromotePersistentLight_t *l=&s_staticPromotePersistentLights[i];
        if(l->candidate.entityOrdinal!=requested)continue;
        ++found;
        ri.Printf(PRINT_ALL,"ELSS11_AUTO_ENABLE fixture=%d idx=%d origin=%.3f,%.3f,%.3f state=%d ok=%d\n",
            requested,i,l->candidate.origin[0],l->candidate.origin[1],l->candidate.origin[2],state,R_StaticPromotePhysicalOverrideSet(l,state));
    }
    if(!found)ri.Printf(PRINT_WARNING,"ELSS11_AUTO_ENABLE_MISSING fixture=%d\n",requested);
}
'''
p.write_text(s)

p=root/'tr_electric_fixture.inc';s=p.read_text()
s+=r'''
/* TEST ONLY: report existing V1.3 AUTO geometry after the lamp is active. */
void R_ELSS_V11_AutoAudit_f(void)
{
    int requested=atoi(ri.Cmd_Argv(1)),i,j,found=0;
    R_IssuePendingRenderCommands();if(!tr.world)return;EF_Build();
    for(i=0;i<tr.refdef.num_dlights;++i) {
        const dlight_t *d=&tr.refdef.dlights[i];int af;
        if(d->staticPromoteFixtureId!=requested)continue;
        af=R_ElectricFixtureForLightAuto(d);
        ri.Printf(PRINT_ALL,"ELSS11_AUTO_LIGHT i=%d fixture=%d origin=%.3f,%.3f,%.3f radius=%.3f autoFixture=%d shadow=%d slot=%d\n",
          i,requested,d->origin[0],d->origin[1],d->origin[2],d->radius,af,
          (tr.refdef.dlightShadowMask&(1u<<i))?1:0,
          (tr.refdef.dlightShadowMask&(1u<<i))?(int)tr.refdef.dlightShadowSlot[i]:-1);
        if(af>0&&af<=s_efCount) {
          const efFixture_t *f=&s_efFixtures[af-1];
          ri.Printf(PRINT_ALL,"ELSS11_AUTO_FIXTURE id=%d apertureSurface=%d bodyCount=%d origin=%.3f,%.3f,%.3f radius=%.3f key=%u\n",
            af,f->apertureSurface,f->bodyCount,f->origin[0],f->origin[1],f->origin[2],f->radius,f->key);
          for(j=0;j<f->bodyCount;++j) {
            const efBody_t *b=&f->body[j];int t,removed=0;vec3_t lo,hi;ClearBounds(lo,hi);
            for(t=0;t<b->mesh->numVerts;++t)AddPointToBounds(b->mesh->verts[t].xyz,lo,hi);
            for(t=0;t<b->triangleCount;++t)if(b->omit[t])++removed;
            ri.Printf(PRINT_ALL,"ELSS11_AUTO_BODY n=%d surface=%d tris=%d removed=%d bounds=(%.2f %.2f %.2f)-(%.2f %.2f %.2f) ext=(%.2f %.2f %.2f)\n",
              j,b->surfaceIndex,b->triangleCount,removed,lo[0],lo[1],lo[2],hi[0],hi[1],hi[2],
              hi[0]-lo[0],hi[1]-lo[1],hi[2]-lo[2]);
          }
        }
        ++found;
    }
    if(!found)ri.Printf(PRINT_WARNING,"ELSS11_AUTO_NO_LIGHT fixture=%d\n",requested);
}
'''
p.write_text(s)
print('ELSS_V11_AUTO_AUDIT_INSTRUMENTED')
