#!/usr/bin/env python3
"""Disposable Church fixture audit for ELSS V1.1 design."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'testlab/scripts'))
import rc4_requested_views as camera
src=Path(sys.argv[1]).resolve(); root=src/'SP/code/rend2'
camera.instrument(src)

p=root/'tr_local.h';s=p.read_text()
anchor='unsigned int R_ElectricFixtureKey(int fixture);\n'
assert s.count(anchor)==1
s=s.replace(anchor,anchor+'void R_ELSS_V11_AuditElectric_f(void);\n')
p.write_text(s)

p=root/'tr_init.c';s=p.read_text()
a='\tri.Cmd_AddCommand( "dw_el_list", R_ELSS_List_f );\n';assert s.count(a)==1
s=s.replace(a,a+'\tri.Cmd_AddCommand( "dw_el_v11_audit", R_ELSS_V11_AuditElectric_f );\n')
a='\tri.Cmd_RemoveCommand( "dw_el_list" );\n';assert s.count(a)==1
s=s.replace(a,a+'\tri.Cmd_RemoveCommand( "dw_el_v11_audit" );\n')
p.write_text(s)

p=root/'tr_electric_fixture.inc';s=p.read_text()
s += r'''
/* ELSS V1.1 TEST ONLY: report the existing V1.3 AUTO fixture geometry for a
 * promoted/static fixture ordinal. Never packaged into production. */
void R_ELSS_V11_AuditElectric_f(void)
{
    int requested=atoi(ri.Cmd_Argv(1)),i,j,autoFixture=0,light=-1;
    R_IssuePendingRenderCommands();
    EF_Build();
    for(i=0;i<tr.refdef.num_dlights;++i) {
        const dlight_t *d=&tr.refdef.dlights[i];
        if(d->staticPromoteFixtureId!=requested)continue;
        light=i;autoFixture=R_ElectricFixtureForLightAuto(d);
        ri.Printf(PRINT_ALL,"ELSS11_AUDIT_LIGHT i=%d fixtureId=%d origin=%.3f,%.3f,%.3f radius=%.3f autoFixture=%d shadow=%d slot=%d\n",
          i,requested,d->origin[0],d->origin[1],d->origin[2],d->radius,autoFixture,
          (tr.refdef.dlightShadowMask&(1u<<i))?1:0,
          (tr.refdef.dlightShadowMask&(1u<<i))?(int)tr.refdef.dlightShadowSlot[i]:-1);
        break;
    }
    if(light<0){ri.Printf(PRINT_WARNING,"ELSS11_AUDIT_NO_LIGHT fixtureId=%d\n",requested);return;}
    if(autoFixture<=0||autoFixture>s_efCount){ri.Printf(PRINT_WARNING,"ELSS11_AUDIT_NO_AUTO fixtureId=%d auto=%d efCount=%d\n",requested,autoFixture,s_efCount);return;}
    {
      const efFixture_t *f=&s_efFixtures[autoFixture-1];
      ri.Printf(PRINT_ALL,"ELSS11_AUDIT_AUTO id=%d apertureSurface=%d bodyCount=%d origin=%.3f,%.3f,%.3f radius=%.3f key=%u\n",
        autoFixture,f->apertureSurface,f->bodyCount,f->origin[0],f->origin[1],f->origin[2],f->radius,f->key);
      for(i=0;i<f->bodyCount;++i){
        const efBody_t *b=&f->body[i];vec3_t lo,hi;ClearBounds(lo,hi);
        for(j=0;j<b->mesh->numVerts;++j)AddPointToBounds(b->mesh->verts[j].xyz,lo,hi);
        ri.Printf(PRINT_ALL,"ELSS11_AUDIT_BODY n=%d surface=%d tris=%d removed=%d bounds=(%.2f %.2f %.2f)-(%.2f %.2f %.2f) ext=(%.2f %.2f %.2f)\n",
          i,b->surfaceIndex,b->triangleCount,b->removed,
          lo[0],lo[1],lo[2],hi[0],hi[1],hi[2],hi[0]-lo[0],hi[1]-lo[1],hi[2]-lo[2]);
      }
    }
}
'''
p.write_text(s)
print('ELSS_V11_CHURCH_AUTO_AUDIT_HOOK_APPLIED')
