#!/usr/bin/env python3
"""V7: fix false fail-open and exclude source-local lamp hull; no map whitelist."""
import argparse, hashlib, json
from pathlib import Path
BASE='aeeee7cfa6bb2067ba65348d008d09364b7d31359ef3d06ba48d3546c9806772'
SRC='SP/code/rend2/tr_backend.c'
MARK='DW_LAMP_V7_SOURCE_LOCAL_HOUSING_FIX'

def once(s,old,new):
    assert s.count(old)==1,(old[:55],s.count(old))
    return s.replace(old,new,1)

def main(root,check,proof):
    p=Path(root)/SRC; original=p.read_text()
    assert hashlib.sha256(original.encode()).hexdigest()==BASE
    assert MARK not in original
    s=original
    s=once(s,'''       s->shader->ssgiEmitter ||
       R_DarkWolfClassifyShadowMaterial(s->shader) !=
           DWSHADOW_MATERIAL_OPAQUE_SOLID''','''       s->shader->isSky ||
       (s->shader->surfaceFlags & (SURF_SKY|SURF_NODRAW|SURF_NODLIGHT))''')
    s=once(s,'''        if(!DW_LampIsBspSheet(s) || !DW_LampIsPotentialMetal(s->shader) ||
           !(b->type & CULLINFO_BOX))continue;''','''        /* No fake metal-only requirement for the compact fixture underside. */
        if(!DW_LampIsBspSheet(s) || s->shader->ssgiEmitter ||
           !(b->type & CULLINFO_BOX))continue;
        if(strstr(s->shader->name,"ember") || strstr(s->shader->name,"flame") ||
           strstr(s->shader->name,"torch") || strstr(s->shader->name,"glow"))continue;''')
    s=once(s,'''    /* A fixture missing its identifiable underside should not remove all
     * radial shadows: that is not the tested source-centered type. */
    if(dst->dishCount<1)
    {
        dst->recognized=qfalse;
        dst->radialCount=0;
    }
}''','''    /* '''+MARK+''': previously the whole rule failed open when a
     * metal dish was absent despite 16 matching radial sides. Confirmed
     * fixture symmetry is now enough. Include its compact near-source metal
     * housing, but never a wide room wall, floor, or long support pole. */
    for(i=0;i<tr.world->numWorldSurfaces;i++)
    {
        const msurface_t *s=&tr.world->surfaces[i];
        const cullinfo_t *b=&s->cullinfo;
        float x0,x1,y0,y1,z0,z1,dist2=0.0f;
        int k,existing=0;
        if(!DW_LampIsBspSheet(s) || s->shader->ssgiEmitter ||
           !DW_LampIsPotentialMetal(s->shader) ||
           !(b->type&CULLINFO_BOX))continue;
        x0=b->bounds[0][0]-org[0];x1=b->bounds[1][0]-org[0];
        y0=b->bounds[0][1]-org[1];y1=b->bounds[1][1]-org[1];
        z0=b->bounds[0][2]-org[2];z1=b->bounds[1][2]-org[2];
        if(x0<-48 || x1>48 || y0<-48 || y1>48 || z0<-80 || z1>80 ||
           x1-x0>96 || y1-y0>96 || z1-z0>100)continue;
        for(k=0;k<3;k++)
        {
            float a=b->bounds[0][k]-org[k],c=b->bounds[1][k]-org[k];
            float gap=a>0?a:(c<0?c:0.0f);
            dist2+=gap*gap;
        }
        if(dist2>1024.0f)continue;
        for(k=0;k<dst->radialCount;k++)
            if(dst->radial[k]==s->data)existing=1;
        for(k=0;k<dst->dishCount;k++)
            if(dst->dish[k]==s->data)existing=1;
        if(existing)continue;
        if(dst->dishCount==DW_LAMP_DISH_MAX)
        {
            dst->recognized=qfalse;
            dst->radialCount=dst->dishCount=0;
            return;
        }
        dst->dish[dst->dishCount++]=s->data;
    }
}''')
    assert s.count(MARK)==1
    assert 'if(dst->dishCount<1)' not in s
    assert 'DW_Boss1CleanSkipSourceLocalCaster(drawSurf)' in s
    assert 'DW_LampSkipSourceLocalCaster(drawSurf)' in s
    digest=hashlib.sha256(s.encode()).hexdigest()
    if not check:p.write_text(s)
    data={'parent_run':41408153237,'base_sha256':BASE,'new_sha256':digest,
          'changed_files':[SRC],'gpu_visual_pass':False,
          'only_ordinary_point_shadow':True,'source_local':True,
          'boss1_rule_preserved':True,'no_global_material_blacklist':True}
    if proof:
        Path(proof).parent.mkdir(parents=True,exist_ok=True)
        Path(proof).write_text(json.dumps(data,indent=2)+'\n')
    print('DW_LAMP_V7_SOURCE_FIX_PASS',digest)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('root',type=Path)
    ap.add_argument('--check-only',action='store_true');ap.add_argument('--proof',type=Path)
    a=ap.parse_args();main(a.root,a.check_only,a.proof)
