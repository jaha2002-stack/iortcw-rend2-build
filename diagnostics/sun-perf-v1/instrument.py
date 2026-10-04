#!/usr/bin/env python3
"""Diagnostic-only counters and explicitly serialized pass-cost probes; no quality edits."""
from pathlib import Path
import ast, sys
root=Path(sys.argv[1]); rd=root/'SP/code/rend2'
def replace(path,old,new):
 s=path.read_text(); assert s.count(old)==1,(path,old[:70],s.count(old));path.write_text(s.replace(old,new,1))
replace(rd/'tr_init.c','cvar_t  *r_forceSun;', 'cvar_t *r_sunPerfLab;\ncvar_t  *r_forceSun;')
replace(rd/'tr_init.c','\tr_forceSun = ri.Cvar_Get( "r_forceSun", "0", CVAR_ARCHIVE );','\tr_sunPerfLab = ri.Cvar_Get("r_sunPerfLab", "0", 0);\n\tr_forceSun = ri.Cvar_Get( "r_forceSun", "0", CVAR_ARCHIVE );')
with (rd/'tr_local.h').open('a') as f:f.write('\nextern cvar_t *r_sunPerfLab; // isolated Performance TestLab\n')
p=rd/'tr_scene.c'
replace(p,'\tqboolean\t\t\tvolumetricSunCsmRequest = qfalse;', '\tint sunPerfStart, sunPerfSurfs;\n\tqboolean\t\t\tvolumetricSunCsmRequest = qfalse;')
replace(p,'\t// playing with even more shadows\n','\tsunPerfStart = ri.Milliseconds();\n\tsunPerfSurfs = tr.refdef.numDrawSurfs;\n\t// playing with even more shadows\n')
replace(p,'\t// playing with cube maps\n','''\tif (r_sunPerfLab->integer)
        ri.Printf(PRINT_ALL, "SUNPERF_FRONT frame=%d force=%d flags=%d csm_cpu_ms=%d csm_surfs=%d request=%d origin=%.2f,%.2f,%.2f\\n",
            tr.frameCount, r_forceSun->integer, fd->rdflags, ri.Milliseconds()-sunPerfStart,
            tr.refdef.numDrawSurfs-sunPerfSurfs, volumetricSunCsmRequest,
            fd->vieworg[0], fd->vieworg[1], fd->vieworg[2]);
\t// playing with cube maps
''')
p=rd/'tr_backend.c'
s=p.read_text(); anchor='static void RB_VolumetricSunPerfTrace(void)'
helper='''// DARKWOLF_SUN_PERF_TESTLAB_V1: mode 2 serializes GPU for pass isolation.
// These wall-clock probes are NOT GPU timer queries and NOT acceptance FPS.
static int sunPerfMs[9], sunPerfCalls[9], sunPerfLastSwap;
static int SunPerfBegin(void) {
    if (r_sunPerfLab->integer != 2) return 0;
    qglFinish();
    return ri.Milliseconds();
}
static void SunPerfEnd(int stage, int start) {
    if (!r_sunPerfLab->integer) return;
    sunPerfCalls[stage]++;
    if (r_sunPerfLab->integer == 2) {
        qglFinish();
        sunPerfMs[stage] += ri.Milliseconds()-start;
    }
}
static void SunPerfFrame(void) {
    int now=ri.Milliseconds(), i;
    if (r_sunPerfLab->integer) {
        ri.Printf(PRINT_ALL,"SUNPERF_FRAME frame=%d force=%d mode=%d wall_ms=%d size=%dx%d sun=%d local=%d shadowmap=%d shadowfilter=%d msaa=%d\\n",
            tr.frameCount,r_forceSun->integer,r_sunPerfLab->integer,
            sunPerfLastSwap ? now-sunPerfLastSwap : 0,glConfig.vidWidth,glConfig.vidHeight,
            r_volumetricSun->integer,r_volumetricLocal->integer,r_shadowMapSize->integer,
            r_shadowFilter->integer,r_ext_framebuffer_multisample->integer);
        for(i=0;i<9;i++)
            ri.Printf(PRINT_ALL,"SUNPERF_STAGE frame=%d stage=%d calls=%d serialized_wall_ms=%d\\n",tr.frameCount,i,sunPerfCalls[i],sunPerfMs[i]);
    }
    memset(sunPerfMs,0,sizeof(sunPerfMs)); memset(sunPerfCalls,0,sizeof(sunPerfCalls));
    sunPerfLastSwap=now;
}

'''
assert s.count(anchor)==1;s=s.replace(anchor,helper+anchor);p.write_text(s)
for name,idx in [('Sun',5),('Local',6),('Fire',7)]:
 old=f'\t\t\tRB_Volumetric{name}(srcFbo, srcBox);' if name!='Fire' else '\t\tRB_VolumetricFire(srcFbo, srcBox);'
 indent='\t\t\t' if name!='Fire' else '\t\t'
 replace(p,old,indent+'{ int probe=SunPerfBegin(); RB_Volumetric'+name+'(srcFbo, srcBox); SunPerfEnd('+str(idx)+',probe); }')
replace(p,'\t\t\tdata = RB_DrawSurfs( data );','''            { const drawSurfsCommand_t *probeCmd=(const drawSurfsCommand_t *)data;
              int stage=4, c, probe;
              for(c=0;c<4;c++) if(tr.sunShadowFbo[c] && probeCmd->viewParms.targetFbo==tr.sunShadowFbo[c]) stage=c;
              probe=SunPerfBegin(); data=RB_DrawSurfs(data); SunPerfEnd(stage,probe); }
''')
replace(p,'\t\t\tdata = RB_SwapBuffers( data );','\t\t\tdata = RB_SwapBuffers( data );\n\t\t\tSunPerfFrame();')
# Stage 8 includes sun/local/fire subpasses: inclusive, never sum with 5-7.
replace(p,'\t\t\tdata = RB_PostProcess(data);','\t\t\t{ int probe=SunPerfBegin(); data = RB_PostProcess(data); SunPerfEnd(8,probe); }')
# Reuse only the three existing gameplay-entry patches, avoiding lamp diagnostics.
names={'cg_info':root/'SP/code/cgame/cg_info.c','cg_servercmds':root/'SP/code/cgame/cg_servercmds.c'}
tree=ast.parse(Path('testlab/scripts/apply_testlab_instrumentation.py').read_text())
for node in tree.body:
 if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and getattr(node.value.func,'id','')=='one':
  args=node.value.args
  if ast.literal_eval(args[-1]) in ('briefing bypass','automatic gameplay start','scripted camera suppression'):
   replace(names[args[0].id],ast.literal_eval(args[1]),ast.literal_eval(args[2]))
print('SUNPERF_DIAGNOSTIC_PATCH_OK')
