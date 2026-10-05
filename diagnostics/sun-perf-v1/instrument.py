#!/usr/bin/env python3
"""Diagnostic-only counters plus forceSun CSM A/B candidates; no production quality edits."""
from pathlib import Path
import ast, sys
root=Path(sys.argv[1]); rd=root/'SP/code/rend2'
def replace(path,old,new):
 s=path.read_text(); assert s.count(old)==1,(path,old[:90],s.count(old)); path.write_text(s.replace(old,new,1))

replace(rd/'tr_init.c','cvar_t  *r_forceSun;', 'cvar_t *r_sunPerfLab;\ncvar_t *r_sunPerfCandidate;\ncvar_t  *r_forceSun;')
replace(rd/'tr_init.c','\tr_forceSun = ri.Cvar_Get( "r_forceSun", "0", CVAR_ARCHIVE );','\tr_sunPerfLab = ri.Cvar_Get("r_sunPerfLab", "0", 0);\n\tr_sunPerfCandidate = ri.Cvar_Get("r_sunPerfCandidate", "0", 0);\n\tr_forceSun = ri.Cvar_Get( "r_forceSun", "0", CVAR_ARCHIVE );')
with (rd/'tr_local.h').open('a') as out:
 out.write('\nextern cvar_t *r_sunPerfLab; // isolated Performance TestLab\nextern cvar_t *r_sunPerfCandidate; // 0 baseline, 1 portal guard, 2 conservative visible-CSM cache\n')

p=rd/'tr_scene.c'
replace(p,'\tqboolean\t\t\tvolumetricSunCsmRequest = qfalse;', '\tint sunPerfStart, sunPerfSurfs;\n\tqboolean\t\t\tvolumetricSunCsmRequest = qfalse;')
replace(p,'\t// playing with even more shadows\n','\tsunPerfStart = ri.Milliseconds();\n\tsunPerfSurfs = tr.refdef.numDrawSurfs;\n\t// playing with even more shadows\n')
replace(p,
'''\tif(glRefConfig.framebufferObject && r_sunlightMode->integer && !( fd->rdflags & RDF_NOWORLDMODEL ) && (r_forceSun->integer || tr.sunShadows || volumetricSunCsmRequest))
{''',
'''\tif(glRefConfig.framebufferObject && r_sunlightMode->integer && !( fd->rdflags & RDF_NOWORLDMODEL ) &&
\t\t(r_forceSun->integer || tr.sunShadows || volumetricSunCsmRequest) &&
\t\t!(r_sunPerfCandidate && r_sunPerfCandidate->integer >= 1 && (fd->rdflags & RDF_SKYBOXPORTAL)))
{''')

anchor='''static void R_VolumetricSunRestoreCascade(int cascade)
{
\tif (tr.volumetricSunCsmValid[cascade])
\t\tMat4Copy(tr.volumetricSunCsmMvp[cascade], tr.refdef.sunShadowMvp[cascade]);
}
'''
helper=anchor+'''\n// DARKWOLF_SUN_PERF_TESTLAB_V2: diagnostic candidate only. Near cascade stays live every frame;
// middle/far visible cascades reuse the exact full-resolution 2048 shadow maps between refreshes.
// This changes cadence only; map size, filter, PCF, MSAA, volumetric samples and light selection are untouched.
static int s_sunPerfVisibleCacheActive = 0;
static qboolean R_SunPerfVisibleShouldUpdateCascade(int cascade)
{
\tif (!tr.volumetricSunCsmValid[cascade]) return qtrue;
\tif (cascade <= 0) return qtrue;
\tif (cascade == 1) return (tr.frameCount & 1) == 0 ? qtrue : qfalse;
\tif (cascade == 2) return (tr.frameCount & 3) == 0 ? qtrue : qfalse;
\treturn qfalse;
}
'''
replace(p,anchor,helper)

old='''\t\telse
\t\t{

\t\t\tif (r_shadowCascadeZFar->integer != 0)
'''
new='''\t\telse if (r_sunPerfCandidate && r_sunPerfCandidate->integer >= 2 && r_forceSun->integer == 1)
\t\t{
\t\t\tqboolean sunChanged;
\t\t\tqboolean forceAll;
\t\t\tint c;

\t\t\tif (!s_sunPerfVisibleCacheActive)
\t\t\t{
\t\t\t\tfor (c = 0; c < 4; ++c) tr.volumetricSunCsmValid[c] = qfalse;
\t\t\t\ts_sunPerfVisibleCacheActive = 1;
\t\t\t}
\t\t\tsunChanged = R_VolumetricSunDirectionChanged(tr.refdef.sunDir, tr.volumetricSunCsmSunDirection);
\t\t\tforceAll = sunChanged || tr.refdef.areamaskModified;

\t\t\tif (r_shadowCascadeZFar->integer != 0)
\t\t\t{
\t\t\t\tfor (c = 0; c < 3; ++c)
\t\t\t\t{
\t\t\t\t\tif (forceAll || R_SunPerfVisibleShouldUpdateCascade(c))
\t\t\t\t\t{
\t\t\t\t\t\tR_RenderSunShadowMaps(fd, c);
\t\t\t\t\t\tR_VolumetricSunCommitCascade(c);
\t\t\t\t\t}
\t\t\t\t\telse
\t\t\t\t\t{
\t\t\t\t\t\tR_VolumetricSunRestoreCascade(c);
\t\t\t\t\t}
\t\t\t\t}
\t\t\t}
\t\t\telse
\t\t\t{
\t\t\t\tMat4Zero(tr.refdef.sunShadowMvp[0]);
\t\t\t\tMat4Zero(tr.refdef.sunShadowMvp[1]);
\t\t\t\tMat4Zero(tr.refdef.sunShadowMvp[2]);
\t\t\t}

\t\t\tif (forceAll || !tr.volumetricSunCsmValid[3])
\t\t\t{
\t\t\t\tR_RenderSunShadowMaps(fd, 3);
\t\t\t\tR_VolumetricSunCommitCascade(3);
\t\t\t}
\t\t\telse
\t\t\t{
\t\t\t\tR_VolumetricSunRestoreCascade(3);
\t\t\t}
\t\t\tif (sunChanged)
\t\t\t\tVectorCopy(tr.refdef.sunDir, tr.volumetricSunCsmSunDirection);
\t\t}
\t\telse
\t\t{
\t\t\ts_sunPerfVisibleCacheActive = 0;

\t\t\tif (r_shadowCascadeZFar->integer != 0)
'''
replace(p,old,new)

replace(p,'\t// playing with cube maps\n','''\tif (r_sunPerfLab->integer)
        ri.Printf(PRINT_ALL, "SUNPERF_FRONT frame=%d force=%d candidate=%d flags=%d csm_cpu_ms=%d csm_surfs=%d request=%d origin=%.2f,%.2f,%.2f\\n",
            tr.frameCount, r_forceSun->integer, r_sunPerfCandidate->integer, fd->rdflags, ri.Milliseconds()-sunPerfStart,
            tr.refdef.numDrawSurfs-sunPerfSurfs, volumetricSunCsmRequest,
            fd->vieworg[0], fd->vieworg[1], fd->vieworg[2]);
\t// playing with cube maps
''')

p=rd/'tr_backend.c'
s=p.read_text(); anchor='static void RB_VolumetricSunPerfTrace(void)'
helper='''// DARKWOLF_SUN_PERF_TESTLAB_V2: mode 2 serializes GPU for pass isolation.
// Wall-clock values are diagnostic only, not acceptance FPS.
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
        ri.Printf(PRINT_ALL,"SUNPERF_FRAME frame=%d force=%d candidate=%d mode=%d wall_ms=%d size=%dx%d sun=%d local=%d shadowmap=%d shadowfilter=%d msaa=%d\\n",
            tr.frameCount,r_forceSun->integer,r_sunPerfCandidate->integer,r_sunPerfLab->integer,
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
assert s.count(anchor)==1; s=s.replace(anchor,helper+anchor); p.write_text(s)
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
replace(p,'\t\t\tdata = RB_PostProcess(data);','\t\t\t{ int probe=SunPerfBegin(); data = RB_PostProcess(data); SunPerfEnd(8,probe); }')

names={'cg_info':root/'SP/code/cgame/cg_info.c','cg_servercmds':root/'SP/code/cgame/cg_servercmds.c'}
tree=ast.parse(Path('testlab/scripts/apply_testlab_instrumentation.py').read_text())
for node in tree.body:
 if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and getattr(node.value.func,'id','')=='one':
  args=node.value.args
  if ast.literal_eval(args[-1]) in ('briefing bypass','automatic gameplay start','scripted camera suppression'):
   replace(names[args[0].id],ast.literal_eval(args[1]),ast.literal_eval(args[2]))
print('SUNPERF_DIAGNOSTIC_PATCH_V2_OK')
