#!/usr/bin/env python3
"""Actual C command allocator/cache producer, mocked geometry/GL execution."""
from pathlib import Path
import re,subprocess,sys,json
base=Path(sys.argv[1]).resolve();fixed=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]).resolve();out.mkdir(parents=True,exist_ok=True)
def function(path,name):
 s=path.read_text();m=re.search(r'(?m)^(?:static\s+)?[^\n;{}]*\b'+re.escape(name)+r'\([^;]*?\)\s*\{',s);assert m,name
 a=m.start();i=s.index('{',a)+1;level=1
 while level:level+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[a:i]
header=r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include "SP/code/rend2/tr_local.h"
trGlobals_t tr; backEndData_t *backEndData; refimport_t ri;
static cvar_t mode; cvar_t *r_dlightMode=&mode;
static __attribute__((noreturn)) void err(int level,const char *fmt,...){abort();}
'''
stubs=r'''
static int requested,dropped,executed,captures,orphanCaps,maxSurfaces,flushes,faceBits[32];
void R_IssuePendingRenderCommands(void) {
 int offset=0,lastDraw=0;
 while(offset<backEndData->commands.used){
  int id=*(int*)(backEndData->commands.cmds+offset);
  if(id==RC_DRAW_SURFS){drawSurfsCommand_t *cmd=(void*)(backEndData->commands.cmds+offset);executed++;lastDraw=1;if(cmd->numDrawSurfs>maxSurfaces)maxSurfaces=cmd->numDrawSurfs;offset+=PAD(sizeof(*cmd),sizeof(void*));}
  else if(id==RC_CAPSHADOWMAP){capShadowmapCommand_t *cmd=(void*)(backEndData->commands.cmds+offset);if(!lastDraw)orphanCaps++;else {captures++;faceBits[cmd->map-DLIGHT_WORLD_MAP_BASE]|=1<<cmd->cubeSide;}lastDraw=0;offset+=PAD(sizeof(*cmd),sizeof(void*));}
  else abort();
 }
 backEndData->commands.used=0;flushes++;
}
void R_RenderView(viewParms_t *p) {int old=backEndData->commands.used;tr.viewParms=*p;tr.refdef.numDrawSurfs+=1200;R_AddDrawSurfCmd(NULL,tr.refdef.numDrawSurfs);requested++;if(backEndData->commands.used==old)dropped++;}
static void R_FireVolProductionSetCubeAxis(viewParms_t*p,int s){}
'''
main=r'''
int main(void) {
 refdef_t fd={0};static dlight_t lights[32];int i,complete=0,valid=0,warm;
 backEndData=calloc(1,sizeof(*backEndData));ri.Error=err;mode.integer=2;
 tr.refdef.dlights=lights;tr.world=(world_t*)1;tr.dlightWorldFbo=(FBO_t*)1;tr.refdef.num_dlights=32;
 for(i=0;i<32;i++){tr.dlightWorldCubemaps[i]=(image_t*)1;lights[i].worldOcclusion=1;lights[i].origin[0]=i*64;lights[i].radius=170;}
 R_RenderDlightWorldOcclusion(&fd);R_IssuePendingRenderCommands();
 for(i=0;i<32;i++){complete+=faceBits[i]==63;valid+=tr.dlightWorldCache[i].valid;}
 warm=requested;R_RenderDlightWorldOcclusion(&fd);warm=requested-warm;
 printf("{\"draw_command_size\":%zu,\"command_capacity\":%d,\"surface_capacity\":%d,\"requested_faces\":%d,\"dropped_draws\":%d,\"delivered_faces\":%d,\"complete_cubes\":%d,\"flagged_valid\":%d,\"orphan_caps\":%d,\"max_surface_prefix\":%d,\"warm_new_faces\":%d}\n",sizeof(drawSurfsCommand_t),MAX_RENDER_COMMANDS,MAX_DRAWSURFS,requested,dropped,captures,complete,valid,orphanCaps,maxSurfaces,warm);
 free(backEndData);return 0;
}
'''
rows={}
for label,src in [('before',base),('fixed',fixed)]:
 text=header+'\n'.join(function(src/'SP/code/rend2/tr_cmds.c',n) for n in ['R_GetCommandBufferReserved','R_GetCommandBuffer','R_AddDrawSurfCmd','R_AddCapShadowmapCmd'])+stubs+'\n'.join(function(src/'SP/code/rend2/tr_main.c',n) for n in ['R_DlightWorldCacheMatches','R_RenderDlightWorldOcclusion'])+main
 f=out/(label+'.c');f.write_text(text);exe=out/label
 cmd=['cc','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-DARCH_STRING="x86_64"','-I'+str(src),'-I'+str(src/'SP/code/SDL2/include'),str(f),'-o',str(exe)]
 subprocess.run(cmd,check=True);run=subprocess.run([str(exe)],capture_output=True,text=True,check=True);(out/(label+'.log')).write_text(run.stdout+run.stderr);rows[label]=json.loads(run.stdout)
a,b=rows['before'],rows['fixed'];assert a['dropped_draws']>0 and a['complete_cubes']<32 and a['flagged_valid']==32,a
assert b['dropped_draws']==0 and b['orphan_caps']==0 and b['complete_cubes']==32 and b['delivered_faces']==192 and b['max_surface_prefix']<=b['surface_capacity'] and b['warm_new_faces']==0,b
report={'status':'PASS','scope':'Actual C allocator and cache with mocked BSP/GL. Legal 32-light cold-cache stress, not GPU timing.','results':rows};(out/'queue-safety.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
