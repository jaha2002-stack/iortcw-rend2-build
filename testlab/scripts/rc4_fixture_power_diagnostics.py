#!/usr/bin/env python3
"""TEST COPY ONLY: keep the map's own Tesla fixture ON during controlled A/B.
Use existing entity use callbacks; preserve PVS, radius, RGB and pulse formulas.
"""
from pathlib import Path
import ast,sys
root=Path(sys.argv[1]).resolve();runtime=Path(sys.argv[2]).resolve()
assert root.name=='linux-test', 'Diagnostic copy required'
src=root/'SP/code'
def one(rel,a,b):
 p=src/rel;t=p.read_text();assert t.count(a)==1,(rel,a[:70],t.count(a));p.write_text(t.replace(a,b))
one('game/g_main.c','\tCheckReloadStatus();',r'''	CheckReloadStatus();
    // TEST COPY ONLY: the stock escape1 script can toggle one emitter after
    // the setup command. Maintain the requested ON fixture via its normal
    // use callback, after the game/AI script tick and before snapshot delivery.
    // No broadcast, PVS change, synthetic light, radius or RGB override.
    if (trap_Cvar_VariableIntegerValue("dw_abFixtureOn") &&
        trap_Cvar_VariableIntegerValue("dw_abFamily")==2) {
        static const char *names[]={"t1055","t1012","t1008"};
        static int lastStep=-1;
        int targetIndex,step=trap_Cvar_VariableIntegerValue("dw_abStep");
        for(targetIndex=0;targetIndex<3;++targetIndex) {
            gentity_t *target=NULL;
            while((target=G_Find(target,FOFS(targetname),names[targetIndex]))!=NULL) {
                if(!target->classname || (strcmp(target->classname,"dlight") &&
                    strcmp(target->classname,"shooter_tesla"))) continue;
                if(target->use && !target->r.linked) {
                    target->use(target,&g_entities[0],&g_entities[0]);
                    G_Printf("AB_FIXTURE_REENABLE time=%d entity=%d name=%s linked=%d\n",level.time,target->s.number,names[targetIndex],target->r.linked);
                }
                if(step>0 && step!=lastStep)
                    G_Printf("AB_SERVER_FIXTURE step=%d time=%d entity=%d name=%s linked=%d type=%d light=%d\n",step,level.time,target->s.number,names[targetIndex],target->r.linked,target->s.eType,target->s.dl_intensity);
            }
        }
        lastStep=step;
    }''')
one('cgame/cg_ents.c','\t// NON TAG-CONNECTED ENTITIES',r'''    // Diagnostic snapshot provenance, without adding/culling any entity.
    {
        static int lastStep=-1;
        char value[16];int step;
        trap_Cvar_VariableStringBuffer("dw_abStep",value,sizeof(value));
        step=atoi(value);
        if(step>0 && step!=lastStep) {
            int j;
            lastStep=step;
            for(j=0;j<cg.snap->numEntities;++j) {
                entityState_t *s=&cg.snap->entities[j];
                if(s->eType==ET_TESLA_EF)
                    CG_Printf("AB_CLIENT_FIXTURE step=%d time=%d snapshot=%d entity=%d flags=%d light=%d radius=%d origin=%.3f,%.3f,%.3f\n",step,cg.time,cg.snap->serverTime,s->number,s->eFlags,s->dl_intensity,s->time,s->origin[0],s->origin[1],s->origin[2]);
            }
        }
    }
    // NON TAG-CONNECTED ENTITIES''')
t=runtime.read_text();a="cmd=['set dw_abTeslaRandom 5'";b="cmd=['set dw_abFixtureOn 1','set dw_abTeslaRandom 5'";assert t.count(a)==1;t=t.replace(a,b)
t=t.replace('authored peak phase, actual Tesla-on predicate, and replayed pre-frame trail state','map fixture held ON via native use callbacks; authored peak phase, actual Tesla-on predicate, and replayed pre-frame trail state')
ast.parse(t);runtime.write_text(t)
print('DIAGNOSTIC_FIXTURE_ON_AND_SNAPSHOT_PROVENANCE_APPLIED')
