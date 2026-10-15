#!/usr/bin/env python3
"""TEST COPY ONLY: sample actual Tesla-on phase and restore frozen trail state."""
from pathlib import Path
import ast,json,sys
root=Path(sys.argv[1]).resolve();runtime=Path(sys.argv[2]).resolve();assert root.name=='linux-test'
src=root/'SP/code'
def one(rel,a,b):
 p=src/rel;s=p.read_text();assert s.count(a)==1,(rel,a[:60],s.count(a));p.write_text(s.replace(a,b))
one('client/cl_cgame.c','\tif (Cvar_VariableIntegerValue("dw_abFreeze")) return;',r'''    if (Cvar_VariableIntegerValue("dw_abFreeze")) {
        int family=Cvar_VariableIntegerValue("dw_abFamily");
        int randomValue=MAX(1,Cvar_VariableIntegerValue("dw_abTeslaRandom"));
        // Keep advancing normal client time until the ORIGINAL map predicate is ON.
        // Neither force an extra light nor change any emitter's temporal formula.
        if (family!=2 || (cl.serverTime/50) % (randomValue+(cl.serverTime%randomValue))==0)
            return;
    }''')
one('cgame/cg_local.h','void CG_ClearTrails( void );','void CG_ClearTrails( void );\nvoid CG_ABTrailSnapshot( void );')
p=src/'cgame/cg_trails.c';t=p.read_text();assert 'CG_ABTrailSnapshot' not in t
t+=r'''
// Diagnostic frozen-state replay: repeated rendering must not create another
// 1-ms lightning trail at the SAME time. Restore the real pre-frame trail pool.
// All pointers refer to the original pool and remain valid after memcpy back.
void CG_ABTrailSnapshot(void) {
    static trailJunc_t saved[MAX_TRAILJUNCS];
    static trailJunc_t *savedFree,*savedActive,*savedHead;
    static qboolean savedInit;
    static int savedCount,savedTime=-1;
    char frozen[16];
    trap_Cvar_VariableStringBuffer("dw_abFreeze",frozen,sizeof(frozen));
    if (!atoi(frozen) || savedTime!=cg.time) {
        memcpy(saved,trailJuncs,sizeof(saved));
        savedFree=freeTrails;savedActive=activeTrails;savedHead=headTrails;
        savedInit=initTrails;savedCount=numTrailsInuse;savedTime=cg.time;
    } else {
        memcpy(trailJuncs,saved,sizeof(saved));
        freeTrails=savedFree;activeTrails=savedActive;headTrails=savedHead;
        initTrails=savedInit;numTrailsInuse=savedCount;
    }
}
''';p.write_text(t)
one('cgame/cg_view.c','        CG_AddPacketEntities();','        CG_ABTrailSnapshot();\n        CG_AddPacketEntities();')
p=src/'cgame/cg_ents.c';t=p.read_text();start=t.index('static void CG_Efx(');end=t.index('} else if ( cent->currentState.eType == ET_SPOTLIGHT_EF )',start);f=t[start:end]
a='\t\t\tb = ( dli >> 16 ) & 255;';assert f.count(a)==1
f=f.replace(a,a+r'''
            {
                static int lastStep[MAX_GENTITIES];
                char stepString[16];int step,number=cent->currentState.number;
                trap_Cvar_VariableStringBuffer("dw_abStep",stepString,sizeof(stepString));
                step=atoi(stepString);
                if (step>0 && number>=0 && number<MAX_GENTITIES && lastStep[number]!=step) {
                    lastStep[number]=step;
                    CG_Printf("AB_TESLA step=%d entity=%d time=%d randomness=%d attachedOn=%d baseRadius=%d origin=%.3f,%.3f,%.3f\n",step,number,cg.time,randomness,(cg.time/50)%(randomness+(cg.time%randomness))==0,cent->currentState.time,cent->currentState.origin[0],cent->currentState.origin[1],cent->currentState.origin[2]);
                }
            }
''');p.write_text(t[:start]+f+t[end:])
# These centers belong to actual upward-facing rendered floor/step surfaces,
# not collision-only roof tops. Eye = mesh floor + 64, player origin = eye - 40.
changes={(448,448,-250,65,180,0):(-160,512,-376,50,90,0),(576,448,-250,55,180,0):(-160.888888888889,724.347222222222,-392,50,0,0),(448,320,-250,40,90,0):(-8,795.71875,-408,40,180,0)}
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
assert "cmd=['set con_notifytime -1'" in t
t=t.replace("cmd=['set con_notifytime -1'","cmd=['set dw_abTeslaRandom 5','set con_notifytime -1'")
# A 100-ms grid can permanently miss a modulo phase. The 50-ms approach
# visits every quotient residue (period <=9 frames for the authored random=5).
t=t.replace("'set dw_abFreeze 1','wait 4'","'set com_fixedtime 50','set dw_abFreeze 1','wait 16'")
t=t.replace("'set dw_abFreeze 0','set dw_abStep 0'","'set com_fixedtime 100','set dw_abFreeze 0','set dw_abStep 0'")
t=t.replace('authored peak phase and fixed random arcs','authored peak phase, actual Tesla-on predicate, and replayed pre-frame trail state')
ast.parse(t);runtime.write_text(t)
Path('evidence/v3-diagnostic-corrections.json').write_text(json.dumps({'scope':'TEST COPY ONLY','tesla_phase':'Wait for original predicate (time/50) % (5+time%5)==0 on a 50-ms approach grid; actual metadata random=5. No added light or forced radius.','trails':'Restore entire actual pre-frame pool plus list roots/count for same-time replay; no cumulative fresh bolt trails.','floor_probe_run':38730165594,'floor_surface_ids':[5682,8586,8588],'new_cameras':list(changes.values())},indent=2))
print('ACTUAL_TESLA_PHASE_FLOOR_AND_TRAIL_REPLAY_INSTRUMENTED')
