#!/usr/bin/env python3
"""Real noclip demos and native video capture. Disposable diagnostics only."""
from pathlib import Path
import sys,subprocess,os,json,hashlib,re,shutil,signal
ROOT=Path.cwd();OUT=ROOT/'movie-evidence';OUT.mkdir(exist_ok=True)
TREE='c652eaed9cbcf1df4eb7d7d5187b9bea63dce60b'
ROUTES={
 'tesla':[[0,120,560,-480,3,300],[1.4,160,558,-484,4,325],[3.0,270,550,-496,5,360],[4.8,400,548,-496,5,360],[6.0,496,552,-496,6,420],[7.5,500,704,-496,8,450],[8.5,506,766,-464,10,490],[9.5,462,806,-432,12,515],[10.5,398,832,-400,16,540],[11.5,300,832,-384,20,540],[13.0,150,824,-384,27,540],[14.1,10,798,-368,30,540],[15.3,-160,752,-352,28,610],[16.6,-160,620,-336,24,620],[17.5,-160,528,-336,20,540],[18.6,-292,528,-336,10,540],[20.0,-430,580,-328,7,510],[22.0,-590,690,-324,12,575],[24.0,-620,690,-324,13,590]],
 'furnace':[[0,-960,692,-50,20,180],[3,-1020,692,-55,25,180],[6,-1080,692,-66,35,180],[9,-1110,692,-78,48,180],[12,-1106,620,-78,45,180],[16,-1106,752,-78,45,180]]}
def run(cmd,**kw):return subprocess.run(list(map(str,cmd)),check=True,**kw)
def write_json(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def patch_source(source):
 def one(rel,a,b):
  p=source/'SP/code'/rel;t=p.read_text();assert t.count(a)==1,(rel,a[:80],t.count(a));p.write_text(t.replace(a,b))
 arrays=[]
 for name,rows in ROUTES.items():arrays.append('static const float dwMovie_'+name+'[][6] = {\n'+',\n'.join('{'+','.join(f'{v:.6f}f' for v in r)+'}' for r in rows)+'\n};')
 code='\n'.join(arrays)+r'''
static void DW_MovieNoclipFrame(void) {
    static int previousRoute,startTime,lastPrint=-1;
    int route=trap_Cvar_VariableIntegerValue("dw_movieDrive"),count,i,k;
    const float (*keys)[6];float t,u,anglesU;vec3_t eye,angles;
    gentity_t *ent=&g_entities[0];
    if(!route) {previousRoute=0;return;}
    if(!g_cheats.integer || !ent->inuse || !ent->client) return;
    if(route!=previousRoute) {
        previousRoute=route;startTime=level.time;lastPrint=-1;
        G_Printf("MOVIE_ROUTE_START route=%d time=%d\n",route,startTime);
        trap_SendServerCommand(0,"stopCam");
    }
    keys=route==1?dwMovie_tesla:dwMovie_furnace;
    count=route==1?sizeof(dwMovie_tesla)/sizeof(dwMovie_tesla[0]):sizeof(dwMovie_furnace)/sizeof(dwMovie_furnace[0]);
    t=(level.time-startTime)*0.001f;
    if(t>keys[count-1][0]) t=keys[count-1][0];
    for(i=0;i<count-2 && t>keys[i+1][0];++i) {}
    u=(t-keys[i][0])/(keys[i+1][0]-keys[i][0]);
    if(u<0)u=0;if(u>1)u=1;
    anglesU=u*u*(3-2*u);
    for(k=0;k<3;++k)eye[k]=keys[i][k+1]+u*(keys[i+1][k+1]-keys[i][k+1]);
    angles[0]=keys[i][4]+anglesU*(keys[i+1][4]-keys[i][4]);
    angles[1]=keys[i][5]+anglesU*(keys[i+1][5]-keys[i][5]);angles[2]=0;
    trap_UnlinkEntity(ent);
    ent->client->noclip=qtrue;ent->client->ps.pm_type=PM_NOCLIP;
    ent->flags|=FL_GODMODE|FL_NOTARGET;
    VectorCopy(eye,ent->client->ps.origin);ent->client->ps.origin[2]-=40;
    ent->client->ps.viewheight=40;ent->client->ps.groundEntityNum=ENTITYNUM_NONE;
    VectorClear(ent->client->ps.velocity);
    ent->client->pers.cmd.forwardmove=ent->client->pers.cmd.rightmove=ent->client->pers.cmd.upmove=0;
    SetClientViewAngle(ent,angles);
    BG_PlayerStateToEntityState(&ent->client->ps,&ent->s,qfalse);
    VectorCopy(ent->client->ps.origin,ent->r.currentOrigin);trap_LinkEntity(ent);
    if((int)(t*25.0f)!=lastPrint) {
        lastPrint=(int)(t*25.0f);
        G_Printf("MOVIE_ROUTE route=%d frame=%d time=%d eye=%.3f,%.3f,%.3f solid=%d\n",route,lastPrint,level.time,eye[0],eye[1],eye[2],(trap_PointContents(eye,0)&CONTENTS_SOLID)!=0);
    }
}
'''
 one('game/g_main.c','void G_RunFrame( int levelTime ) {',code+'\nvoid G_RunFrame( int levelTime ) {')
 one('game/g_main.c','\tCheckReloadStatus();','\tDW_MovieNoclipFrame();\n\tCheckReloadStatus();')
 one('client/cl_main.c','\t\t\t\tCL_TakeVideoFrame( );',r'''
                if (Cvar_VariableIntegerValue("dw_movieAudit")) {
                    static int movieIndex;
                    Com_Printf("MOVIE_AVI index=%d time=%d\n",movieIndex++,cl.serverTime);
                }
                CL_TakeVideoFrame( );''')
 one('cgame/cg_view.c','if(atoi(frozen)) srand((unsigned int)cg.time);',r'''if(atoi(frozen)) srand((unsigned int)cg.time);
            trap_Cvar_VariableStringBuffer("dw_movieAudit",frozen,sizeof(frozen));
            if(atoi(frozen)) srand((unsigned int)cg.time);''')
 one('rend2/tr_scene.c','\tR_RenderDlightWorldOcclusion(fd);',r'''
    R_RenderDlightWorldOcclusion(fd);
    if(ri.Cvar_VariableIntegerValue("dw_movieAudit") && !(fd->rdflags&(RDF_NOWORLDMODEL|RDF_SKYBOXPORTAL))) {
        int li,required=0,coils=0;
        unsigned int hash=2166136261u;
        for(li=0;li<tr.refdef.num_dlights;++li) {
            const dlight_t *d=&tr.refdef.dlights[li];
            const byte *b=(const byte *)d->origin;int j;
            for(j=0;j<sizeof(d->origin);++j)hash=(hash^b[j])*16777619u;
            b=(const byte *)&d->radius;for(j=0;j<sizeof(d->radius);++j)hash=(hash^b[j])*16777619u;
            b=(const byte *)d->color;for(j=0;j<sizeof(d->color);++j)hash=(hash^b[j])*16777619u;
            if(d->worldOcclusion)required++;
            if(d->worldOcclusion && !d->nativeAuthoredDlight && d->origin[0]>40 && d->origin[0]<210 && fabsf(d->origin[1]-448)<2 && fabsf(d->origin[2]+476)<2)coils++;
        }
        ri.Printf(PRINT_ALL,"MOVIE_SCENE time=%d camera=%.3f,%.3f,%.3f angles=%.5f,%.5f,%.5f lights=%d required=%d coils=%d hash=%u reference=%d\n",fd->time,fd->vieworg[0],fd->vieworg[1],fd->vieworg[2],fd->viewaxis[0][0],fd->viewaxis[0][1],fd->viewaxis[0][2],tr.refdef.num_dlights,required,coils,hash,ri.Cvar_VariableIntegerValue("dw_abReference"));
    }''')
 run(['git','-C',source,'diff','--check'])
 (OUT/'movie-diagnostic.patch').write_bytes(subprocess.check_output(['git','-C',str(source),'diff']))
 write_json(OUT/'route-keyframes.json',ROUTES)
 print('MOVIE_DIAGNOSTIC_COPY_READY',flush=True)
def launch(runtime,home,args,log,limit=1100):
 exe=next(runtime.glob('iowolfsp.*'),None) or next(runtime.glob('ioWolfSP.*'));assert exe
 command=['xvfb-run','-a','-s','-screen 0 1280x720x24',str(exe),'+set','fs_basepath',str(runtime),'+set','fs_homepath',str(home),'+safe','+set','com_introplayed','1','+set','com_recommendedSet','1','+set','logfile','2','+set','dw_testAutomation','1','+set','r_renderer','rend2','+set','cl_renderer','rend2','+exec','PRODUCTION_HIGH_QUALITY.cfg','+set','r_mode','-1','+set','r_customwidth','960','+set','r_customheight','540','+set','r_fullscreen','0','+set','s_initsound','0','+set','com_fixedtime','40','+set','cg_draw2D','0','+set','cg_drawGun','0','+set','cg_bobup','0','+set','cg_bobpitch','0','+set','cg_bobroll','0','+set','con_notifytime','-1','+set','r_autoExposure','0','+vid_restart']+args
 with log.open('w') as f:
  p=subprocess.Popen(command,stdout=f,stderr=subprocess.STDOUT,env={**os.environ,'LIBGL_ALWAYS_SOFTWARE':'1','LP_NUM_THREADS':'4'},start_new_session=True)
  try:rc=p.wait(timeout=limit)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait();rc=124
 for file in home.rglob('*console*.log'):shutil.copy2(file,log.with_suffix('.console.log'))
 assert rc==0,('GAME_FAILED',rc,str(log))
 text=log.with_suffix('.console.log').read_text(errors='replace')
 assert 'GLimp_Init() - could not load OpenGL subsystem' not in text
 return text
def movies(source,retail):
 runtime=ROOT/'movie-private-runtime';main=runtime/'main';main.mkdir(parents=True,exist_ok=True)
 build=source/'SP/build/release-linux-x86_64'
 for p in build.iterdir():
  if p.is_file():shutil.copy2(p,runtime/p.name)
 for p in (build/'main').glob('*.so'):shutil.copy2(p,main/p.name)
 for p in retail.iterdir():
  if p.suffix.lower()=='.pk3':(main/p.name.lower()).symlink_to(p)
 kit=ROOT/'integration/optimized-v4-4-6'
 for p in ['PRODUCTION_HIGH_QUALITY.cfg','payload/Main/darkwolf_ignition_rc_v0_6.pk3']:shutil.copy2(kit/p,main/Path(p).name)
 provenance={'source_tree':TREE,'baseline_run':38733120730,'capture':'native record/demo/video commands, 25 fps, genuine renderer frames','exposure':'fixed equal exposure in both passes; no image brightness changes','lights':'native lightstyle animation, native Tesla pulses; fixture held ON only during recorded diagnostic session','movies':[]}
 for number,(name,keys) in enumerate(ROUTES.items(),1):
  duration=keys[-1][0];first=keys[0];home=runtime/('record-'+name);home.mkdir(exist_ok=True)
  cmd=['set con_notifytime -1','set dw_movieDrive 0','set dw_movieAudit 0','set dw_abFreeze 0','set dw_abAuthoredPeak 0','set dw_abReference 0','set dw_abSourceOff 0','set dw_abFamily '+str(2 if number==1 else 1),'set dw_abFixtureOn '+str(1 if number==1 else 0),'set com_fixedtime 40','set sv_fps 25','god','notarget','dw_testView '+' '.join(str(v) for v in [first[1],first[2],first[3]-40,first[4],first[5],0]),'dw_abUse t1055','dw_abUse t1012','dw_abUse t1008','wait 80','record '+name,'wait 50','set dw_movieDrive '+str(number),'wait '+str(int(duration*25)+2),'set dw_movieDrive 0','wait 40','stoprecord','quit']
  cfg='MOVIE_RECORD_'+name+'.cfg';(main/cfg).write_text('\n'.join(cmd)+'\n');shutil.copy2(main/cfg,OUT/cfg)
  text=launch(runtime,home,['+set','dw_testlabSmokeCapture','movie-'+name,'+set','dw_testlabScenario',cfg,'+spdevmap','escape1'],OUT/(name+'-record.log'))
  found=list(home.rglob(name+'.dm_*'));assert len(found)==1,('Missing demo',name)
  demos=main/'demos';demos.mkdir(exist_ok=True);shutil.copy2(found[0],demos/found[0].name)
  starts=re.findall(r'MOVIE_ROUTE_START route=\d+ time=(\d+)',text);assert len(starts)==1;start=int(starts[0]);row={'name':name,'duration':duration,'route_start':start,'demo_sha256':hashlib.sha256(found[0].read_bytes()).hexdigest(),'solid_samples':len(re.findall(r'MOVIE_ROUTE [^\n]*solid=1',text)),'passes':[]}
  print('DEMO_RECORDED',name,'start',start,'solid samples',row['solid_samples'],flush=True)
  ledgers=[]
  for state,reference in [('reference',1),('fixed',0)]:
   home=runtime/(name+'-'+state);home.mkdir(exist_ok=True)
   args=['+set','dw_movieAudit','1','+set','dw_movieDrive','0','+set','dw_abFreeze','0','+set','dw_abAuthoredPeak','0','+set','dw_abFamily',str(2 if number==1 else 1),'+set','dw_abReference',str(reference),'+set','dw_abSourceOff','0','+set','dw_testlabSmokeCapture','', '+set','cl_aviFrameRate','25','+set','cl_aviMotionJpeg','1','+set','r_aviMotionJpegQuality','100','+set','nextdemo','quit','+set','activeAction','video capture\n','+demo',name]
   text=launch(runtime,home,args,OUT/(name+'-'+state+'.log'))
   avis=list(home.rglob('capture.avi'));assert len(avis)==1,('Missing AVI',name,state)
   frames=[];scene=None
   for line in text.splitlines():
    if line.startswith('MOVIE_SCENE '):scene=dict(re.findall(r'(\w+)=([^ ]+)',line))
    elif line.startswith('MOVIE_AVI '):
     d=dict(re.findall(r'(\w+)=([^ ]+)',line));d['scene']=scene;frames.append(d)
   probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,r_frame_rate,nb_read_frames','-of','json',str(avis[0])]))['streams'][0]
   assert int(probe['nb_read_frames'])==len(frames),(probe,len(frames))
   indexes=[i for i,f in enumerate(frames) if int(f['time'])>=start];assert indexes
   first_index=indexes[0];count=int(duration*25);assert len(frames)>=first_index+count
   selected=frames[first_index:first_index+count]
   assert all(int(b['time'])-int(a['time'])==40 for a,b in zip(selected,selected[1:])), 'Non-contiguous simulation time'
   output=OUT/(name+'_'+state+'.mp4')
   run(['ffmpeg','-v','error','-y','-i',avis[0],'-vf',f'trim=start_frame={first_index}:end_frame={first_index+count},setpts=PTS-STARTPTS','-an','-c:v','libx264','-preset','fast','-crf','15','-pix_fmt','yuv420p','-movflags','+faststart',output])
   write_json(OUT/(name+'-'+state+'-frames.json'),selected)
   ledgers.append(selected);row['passes'].append({'state':state,'trim_start_frame':first_index,'frames':count,'first_time':selected[0]['time'],'last_time':selected[-1]['time'],'probe':probe,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()})
   run(['ffmpeg','-v','error','-y','-i',output,'-vf','fps=1/2',OUT/(name+'_'+state+'_%02d.png')])
   avis[0].unlink()
   print('NATIVE_VIDEO_ENCODED',name,state,count,flush=True)
  signatures=lambda fs:[(f['time'],None if f['scene'] is None else tuple(f['scene'].get(k) for k in ('time','camera','angles','lights','required','coils','hash'))) for f in fs]
  row['identical_demo_clock_camera_and_lights']=signatures(ledgers[0])==signatures(ledgers[1]);provenance['movies'].append(row)
  write_json(OUT/'movie-provenance.json',provenance)
  assert row['identical_demo_clock_camera_and_lights'],'Replay provenance differs'
  labels=['BEFORE - MASK OFF','AFTER - FIX ON']
  filter="[0:v]pad=iw:ih+36:0:36:black,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='"+labels[0]+"':x=20:y=8:fontsize=22:fontcolor=white[a];[1:v]pad=iw:ih+36:0:36:black,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='"+labels[1]+"':x=20:y=8:fontsize=22:fontcolor=white[b];[a][b]hstack=inputs=2[v]"
  run(['ffmpeg','-v','error','-y','-i',OUT/(name+'_reference.mp4'),'-i',OUT/(name+'_fixed.mp4'),'-filter_complex',filter,'-map','[v]','-an','-c:v','libx264','-crf','16','-preset','fast','-pix_fmt','yuv420p','-movflags','+faststart',OUT/(name+'_comparison.mp4')])
  print('MOVIE_PAIR_COMPLETE',name,flush=True)
 print('ALL_MOVIES_CAPTURED_VISUAL_REVIEW_REQUIRED',flush=True)
if __name__=='__main__':
 if sys.argv[1]=='patch':patch_source(Path(sys.argv[2]).resolve())
 elif sys.argv[1]=='run':movies(Path(sys.argv[2]).resolve(),Path(sys.argv[3]).resolve())
 else:raise SystemExit('Use patch SOURCE or run SOURCE RETAIL_MAIN')
