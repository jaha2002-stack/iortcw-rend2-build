#!/usr/bin/env python3
"""Diagnostic copy only: explicit runtime gates and raw framebuffer readbacks."""
from pathlib import Path
import sys
root=Path(sys.argv[1])/'SP/code'
def edit(path,old,new):
    p=root/path;s=p.read_text();assert s.count(old)==1,(path,old[:100],s.count(old));p.write_text(s.replace(old,new))
for name in ('r_ssgiDebug','r_ssgiTrace'):
    edit(Path('rend2/tr_init.c'),f'{name} = &s_darkwolfProductionDiagOffCvar;',f'{name} = ri.Cvar_Get("{name}", "0", 0);')
# Silence the old hard-enabled diagnostic text without touching production logic.
edit(Path('rend2/tr_scene.c'),'// DARKWOLF_TESTLAB_V0_1: enable existing read-only production residency telemetry.','// DARKWOLF_TESTLAB_V0_1: enable existing read-only production residency telemetry.\n\treturn;')
helper=r'''
/* QUALITY_DUMP: test-only float framebuffers, not retail texture assets. */
static int s_qualityDumpId, s_qualityDumpActive, s_qualityDumpLocal;
static void RB_QualityDump(FBO_t *fbo, GLenum format, const char *label)
{
 FBO_t *oldFbo=glState.currentFBO;
 int components=(format==GL_DEPTH_COMPONENT)?1:4;
 int bytes; int *header; char name[128];
 if(!s_qualityDumpActive || !fbo) return;
 bytes=12+fbo->width*fbo->height*components*sizeof(float);
 header=ri.Hunk_AllocateTempMemory(bytes);
 header[0]=fbo->width;header[1]=fbo->height;header[2]=components;
 FBO_Bind(fbo);
 qglReadPixels(0,0,fbo->width,fbo->height,format,GL_FLOAT,header+3);
 Com_sprintf(name,sizeof(name),"quality/%04d-%s.dwfp",s_qualityDumpId,label);
 ri.FS_WriteFile(name,header,bytes);
 ri.Hunk_FreeTempMemory(header);
 FBO_Bind(oldFbo);
}
'''
edit(Path('rend2/tr_backend.c'),'static void RB_VolumetricSun(FBO_t *srcFbo, ivec4_t srcBox)',helper+'\nstatic void RB_VolumetricSun(FBO_t *srcFbo, ivec4_t srcBox)')
anchor='\tRB_USLRDRootCauseBeginFrameSample(srcFbo, dstBox);'
edit(Path('rend2/tr_backend.c'),anchor,r'''
 {
  static cvar_t *dump; int id;
  if(!dump) dump=ri.Cvar_Get("r_qualityDump", "0", 0);
  id=dump->integer;s_qualityDumpActive=0;
  if(id>0 && id!=s_qualityDumpId && srcFbo && !(backEnd.refdef.rdflags & RDF_NOWORLDMODEL))
  {
   char data[512],name[128];
   s_qualityDumpId=id;s_qualityDumpActive=1;s_qualityDumpLocal=0;
   Com_sprintf(data,sizeof(data),"zfar %.9g\nznear %.9g\nwidth %d\nheight %d\norigin %.9g %.9g %.9g\nssgi %d\nhdrDepth %d\n",
    backEnd.viewParms.zFar,r_znear->value,srcFbo->width,srcFbo->height,
    backEnd.refdef.vieworg[0],backEnd.refdef.vieworg[1],backEnd.refdef.vieworg[2],r_ssgi->integer,tr.hdrDepthImage?1:0);
   Com_sprintf(name,sizeof(name),"quality/%04d-view.txt",id);ri.FS_WriteFile(name,data,strlen(data));
   RB_QualityDump(srcFbo,GL_RGBA,"scene");RB_QualityDump(srcFbo,GL_DEPTH_COMPONENT,"depth");
   RB_QualityDump(tr.hdrDepthFbo,GL_RGBA,"hdrdepth");RB_QualityDump(tr.ssgiEntityDepthFbo,GL_DEPTH_COMPONENT,"entity");
  }
 }
'''+anchor)
for kind in ('Sun','Local'):
    anchor=f'FBO_Blit(srcFbo, srcBox, NULL, tr.quarterFbo[0], NULL, &tr.volumetric{kind}Shader, params, 0);'
    if kind=='Sun':extra='\n\tRB_QualityDump(tr.quarterFbo[0],GL_RGBA,"sun");'
    else:extra='\n\tif(s_qualityDumpActive) { char label[64]; Com_sprintf(label,sizeof(label),"local-%02d-mode%d",s_qualityDumpLocal++,mode); RB_QualityDump(tr.quarterFbo[0],GL_RGBA,label); }'
    edit(Path('rend2/tr_backend.c'),anchor,anchor+extra)
anchor='FBO_Blit(srcFbo, giSrcBox, giTexScale, tr.quarterFbo[0], giBox, &tr.ssgiShader, giParams, 0);'
edit(Path('rend2/tr_backend.c'),anchor,anchor+'\n\t\t\t\tRB_QualityDump(tr.quarterFbo[0],GL_RGBA,"ssgi");')
anchor='\t\tRB_VolumetricFire(srcFbo, srcBox);'
edit(Path('rend2/tr_backend.c'),anchor,anchor+'\n\t\ts_qualityDumpActive=0;')
print('QUALITY_FLOAT_CAPTURE_INSTRUMENTED diagnostic-only')
