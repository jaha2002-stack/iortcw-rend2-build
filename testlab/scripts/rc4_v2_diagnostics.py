#!/usr/bin/env python3
"""TEST ONLY: valid BSP cameras, reproducible authored phase and random arcs."""
from pathlib import Path
import sys,ast,json
source=Path(sys.argv[1]).resolve();runtime=Path(sys.argv[2]).resolve();assert source.name=='linux-test'
def one(rel,a,b):
 p=source/'SP/code'/rel;s=p.read_text();assert s.count(a)==1,(rel,a[:60],s.count(a));p.write_text(s.replace(a,b))
one('rend2/tr_scene.c','if (!(fd->rdflags & RDF_NOWORLDMODEL) && step > 0 && step != lastStep)','if (!(fd->rdflags & (RDF_NOWORLDMODEL | RDF_SKYBOXPORTAL)) && step > 0 && step != lastStep)')
one('rend2/tr_scene.c','\t\t\tlastStep = step;',r'''            mnode_t *abLeaf = R_StaticPromotePointInLeafSafe(fd->vieworg);
            lastStep = step;
            ri.Printf(PRINT_ALL,"AB_LEAF step=%d cluster=%d area=%d\n",step,abLeaf?abLeaf->cluster:-1,abLeaf?abLeaf->area:-1);''')
one('rend2/tr_shade.c', '\tif (ri.Cvar_VariableIntegerValue("dw_abReference")) origin[3] = 0.0f;\n\tif (ri.Cvar_VariableIntegerValue("dw_abSourceOff") && backEnd.refdef.dlights[lightIndex].worldOcclusion) origin[3] = -1.0f;', r'''    {
        int family=ri.Cvar_VariableIntegerValue("dw_abFamily");
        const dlight_t *d=&backEnd.refdef.dlights[lightIndex];
        qboolean target=d->worldOcclusion;
        if(family==1) target=d->nativeAuthoredDlight && fabsf(d->origin[0]+1340.0f)<2.0f && fabsf(d->origin[1]-692.0f)<2.0f && fabsf(d->origin[2]+36.0f)<2.0f;
        if(family==2) target=d->worldOcclusion && ((d->nativeAuthoredDlight && fabsf(d->origin[0]-328.0f)<2.0f && fabsf(d->origin[1]-448.0f)<2.0f && fabsf(d->origin[2]+532.0f)<2.0f) || (!d->nativeAuthoredDlight && d->origin[0]>40.0f && d->origin[0]<210.0f && fabsf(d->origin[1]-448.0f)<2.0f && fabsf(d->origin[2]+476.0f)<2.0f));
        if(target && ri.Cvar_VariableIntegerValue("dw_abReference")) origin[3]=0.0f;
        if(target && ri.Cvar_VariableIntegerValue("dw_abSourceOff")) origin[3]=-1.0f;
    }''')
# Existing authored phase, not an invented radius, color, or emitter.
one('cgame/cg_ents.c','\totime = cg.time - cent->dl_time;',r'''    {
        char peak[16];
        trap_Cvar_VariableStringBuffer("dw_abAuthoredPeak",peak,sizeof(peak));
        if (atoi(peak)) {
            int i,best=0;
            for(i=1;cent->dl_stylestring[i];++i)
                if(cent->dl_stylestring[i]>cent->dl_stylestring[best]) best=i;
            cent->dl_oldframe=cent->dl_frame=best;
            cent->dl_backlerp=0.0f;cent->dl_time=cg.time;
        }
    }
    otime = cg.time - cent->dl_time;''')
one('cgame/cg_view.c','\t\tCG_AddPacketEntities();',r'''        {
            char frozen[16];
            trap_Cvar_VariableStringBuffer("dw_abFreeze",frozen,sizeof(frozen));
            if(atoi(frozen)) srand((unsigned int)cg.time);
        }
        CG_AddPacketEntities();''')
one('game/g_cmds.c','if(target->use) { target->use(target,ent,ent);count++; }',r'''if(target->use && !target->r.linked) { target->use(target,ent,ent);count++; }
        G_Printf("AB_MAP_ENABLE target=%s entity=%d linked=%d time=%d\n",name,target->s.number,target->r.linked,level.time);''')
changes={(-980,602,-90,25,180,0):(-1010,692,-90,22,180,0),(-1060,602,-90,35,180,0):(-1100,692,-90,40,180,0),(-1460,520,-90,0,20,0):(-1340,760,-50,7,306,0),(400,400,-600,-14,170,0):(120,560,-510,3,300,0),(328,448,-330,70,180,0):(448,448,-250,65,180,0),(100,580,-330,45,315,0):(576,448,-250,55,180,0),(480,600,-330,35,225,0):(448,320,-250,40,90,0)}
t=runtime.read_text();offsets=[0]
for line in t.splitlines(keepends=True):offsets.append(offsets[-1]+len(line))
edits=[];found=set()
for node in ast.walk(ast.parse(t)):
 if not isinstance(node,(ast.Tuple,ast.List)):continue
 try:value=ast.literal_eval(node)
 except (ValueError,TypeError,SyntaxError):continue
 if not isinstance(value,(list,tuple)) or len(value)!=6 or not all(isinstance(v,(int,float)) for v in value):continue
 key=tuple(value)
 if key in changes:
  v=list(changes[key]) if isinstance(node,ast.List) else changes[key]
  edits.append((offsets[node.lineno-1]+node.col_offset,offsets[node.end_lineno-1]+node.end_col_offset,repr(v)));found.add(key)
assert found==set(changes)
for a,b,v in sorted(edits,reverse=True):t=t[:a]+v+t[b:]
assert "cmd=['set cg_draw2D 0'" in t
t=t.replace("cmd=['set cg_draw2D 0'","cmd=['set con_notifytime -1','set dw_abAuthoredPeak 1','set cg_draw2D 0'")
a="'dw_testView '+' '.join(map(str,v)),'wait 24'";b="'dw_testView '+' '.join(map(str,v)),'dw_abUse t1055','dw_abUse t1012','dw_abUse t1008','wait 24'";assert t.count(a)==1;t=t.replace(a,b)
assert "for tag,v in views:\n cmd+=" in t
t=t.replace("for tag,v in views:\n cmd+=", "for tag,v in views:\n cmd+=['set dw_abFamily '+('1' if tag.startswith('fire') else '2')]\n cmd+=")
t=t.replace('reference bypasses only the new geometric mask; separate source-off attribution; manual exposure during A/B','reference bypasses only target-family geometry; target-family source-off; authored peak phase and fixed random arcs; manual A/B exposure')
ast.parse(t);runtime.write_text(t)
Path('evidence/view-corrections.json').write_text(json.dumps({'scope':'DIAGNOSTIC ONLY','phase':'maximum character already authored in each light style; no new energy values','random_arcs':'fixed cgame random seed while frozen','skybox_excluded':True,'main_leaf_logged':True,'camera_changes':[{'before':a,'after':b} for a,b in changes.items()]},indent=2))
print('VALID_BSP_PHASE_AND_ARC_REPRODUCIBILITY_INSTRUMENTED')
