#!/usr/bin/env python3
"""Real-game requested views. Camera/client helpers only; renderer stays intact."""
from pathlib import Path
import argparse, hashlib, json, math, os, shutil, signal, subprocess


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def instrument(root):
    code = root / 'SP/code'
    renderer = {str(p.relative_to(code)): digest(p) for p in (code/'rend2').rglob('*') if p.is_file()}
    def edit(rel, old, new):
        p=code/rel; s=p.read_text()
        if s.count(old)!=1: raise RuntimeError(f'{rel}: expected one anchor, got {s.count(old)}')
        p.write_text(s.replace(old,new))
    edit('client/cl_cgame.c', '\t// allow pause in single player',
         '\tif (Cvar_VariableIntegerValue("dw_proofFreeze")) return;\n\t// allow pause in single player')
    edit('cgame/cg_info.c', '\t\ttrap_UI_Popup( "briefing" );', r'''
        { char enabled[16];
          trap_Cvar_VariableStringBuffer("dw_proofAutomation",enabled,sizeof(enabled));
          if (!atoi(enabled)) trap_UI_Popup("briefing"); }
''')
    edit('cgame/cg_servercmds.c', '\t\tqboolean startBlack = atoi( CG_Argv( 2 ) );', r'''
        char enabled[16]; qboolean startBlack = atoi(CG_Argv(2));
        trap_Cvar_VariableStringBuffer("dw_proofAutomation",enabled,sizeof(enabled));
        if (atoi(enabled)) return;
''')
    anchor='\tif ( !strcmp( cmd, "rockandroll" ) ) {   // map loaded, game is ready to begin.'
    edit('cgame/cg_servercmds.c',anchor,anchor+r'''
        char enabled[16];
        trap_Cvar_VariableStringBuffer("dw_proofAutomation",enabled,sizeof(enabled));
        if (atoi(enabled)) {
            CG_Fade(0,0,0,0,cg.time,0);
            trap_Cvar_Set("g_playerstart","1");
            trap_Cvar_Set("dw_proofStarted","1");
            trap_S_FadeAllSound(1.0f,1000);
            return;
        }
''')
    helper=r'''
/* Isolated camera helper. Arguments specify the eye, not the player's feet. */
static void Cmd_ProofView_f(gentity_t *ent) {
    vec3_t origin, angles; char text[MAX_TOKEN_CHARS]; int i;
    if (!g_cheats.integer || trap_Argc()!=7) return;
    for(i=0;i<3;i++) {
        trap_Argv(i+1,text,sizeof(text)); origin[i]=atof(text);
        trap_Argv(i+4,text,sizeof(text)); angles[i]=atof(text);
    }
    trap_SendServerCommand(ent-g_entities,"stopCam");
    trap_UnlinkEntity(ent);
    ent->client->noclip=qtrue;
    ent->client->ps.pm_type=PM_NOCLIP;
    ent->client->ps.pm_flags &= ~PMF_DUCKED;
    ent->client->ps.viewheight=ent->client->ps.standViewHeight;
    origin[2]-=ent->client->ps.viewheight;
    ent->client->ps.groundEntityNum=ENTITYNUM_NONE;
    VectorClear(ent->client->ps.velocity);
    ent->client->pers.cmd.forwardmove=0;
    ent->client->pers.cmd.rightmove=0;
    ent->client->pers.cmd.upmove=0;
    ent->client->ps.weapon=WP_MP40;
    ent->client->ps.weaponstate=WEAPON_READY;
    ent->client->ps.weaponTime=0;
    VectorCopy(origin,ent->client->ps.origin);
    SetClientViewAngle(ent,angles);
    ent->client->ps.eFlags ^= EF_TELEPORT_BIT;
    BG_PlayerStateToEntityState(&ent->client->ps,&ent->s,qtrue);
    VectorCopy(origin,ent->r.currentOrigin);
    trap_LinkEntity(ent);
}

'''
    edit('game/g_cmds.c','void Cmd_SetViewpos_f( gentity_t *ent ) {',helper+'void Cmd_SetViewpos_f( gentity_t *ent ) {')
    anchor='} else if ( Q_stricmp( cmd, "setviewpos" ) == 0 )  {'
    edit('game/g_cmds.c',anchor,'} else if ( Q_stricmp( cmd, "proofView" ) == 0 ) {\n        Cmd_ProofView_f(ent);\n\t'+anchor)
    edit('cgame/cg_view.c','\tCG_DrawActive( stereoView );',r'''
    CG_DrawActive(stereoView);
    {
        static int rendered, firstTime, lastShot=-1;
        static qboolean queued;
        char enabled[16],started[16],scenario[80],shotText[16]; int shot;
        trap_Cvar_VariableStringBuffer("dw_proofAutomation",enabled,sizeof(enabled));
        trap_Cvar_VariableStringBuffer("dw_proofStarted",started,sizeof(started));
        trap_Cvar_VariableStringBuffer("dw_proofScenario",scenario,sizeof(scenario));
        if(atoi(enabled) && atoi(started) && stereoView!=STEREO_RIGHT) {
            if(!rendered) firstTime=cg.time;
            rendered++;
            if(!queued && rendered>=32 && cg.time-firstTime>=6000 && !cg.fadeRate && cg.viewFade<=0.001f && cgs.scrFadeAlphaCurrent<=0.001f) {
                queued=qtrue;
                CG_Printf("PROOF_READY time=%d\n",cg.time);
                trap_SendConsoleCommand(va("exec %s\n",scenario));
            }
            trap_Cvar_VariableStringBuffer("dw_proofShot",shotText,sizeof(shotText));
            shot=atoi(shotText);
            if(shot>0 && shot!=lastShot) {
                static const char *names[]={"r_ssgi","r_volumetricSun","r_volumetricLocal","r_volumetricFire","r_ext_framebuffer_multisample","r_forceSun","r_ssgiStrength","r_volumetricSunStrength","r_volumetricLocalStrength","cg_drawGun"};
                int i; lastShot=shot;
                CG_Printf("PROOF_VIEW shot=%d time=%d eye=%.6f,%.6f,%.6f forward=%.6f,%.6f,%.6f weapon=%d\n",shot,cg.time,cg.refdef.vieworg[0],cg.refdef.vieworg[1],cg.refdef.vieworg[2],cg.refdef.viewaxis[0][0],cg.refdef.viewaxis[0][1],cg.refdef.viewaxis[0][2],cg.predictedPlayerState.weapon);
                for(i=0;i<sizeof(names)/sizeof(names[0]);i++) {
                    char value[32]; trap_Cvar_VariableStringBuffer(names[i],value,sizeof(value));
                    CG_Printf("PROOF_CVAR shot=%d name=%s value=%s\n",shot,names[i],value);
                }
            }
        }
    }
''')
    assert renderer == {str(p.relative_to(code)): digest(p) for p in (code/'rend2').rglob('*') if p.is_file()}
    print('PROOF_CAMERA_HELPERS_READY renderer_bytes_unchanged=true',flush=True)


def views(map_name):
    if map_name=='factory':
        target=[-448.,-1055.,-178.]
        result=[]
        # Approximate visual convention: 40 engine units per metre, not a map guarantee.
        for metre in (1,2,3):
            distance=40.0*metre; pitch=-28.0; angle=math.radians(-pitch)
            eye=[target[0]+math.cos(angle)*distance,target[1],target[2]-math.sin(angle)*distance]
            result.append({'name':f'factory_lamp_{metre}m','eye':eye,'angles':[pitch,180.,0.],
                           'target':target,'distance_units':distance,'metres_approx':metre})
        return result
    return [
        {'name':'assault_mp40_sun_front','eye':[4536.,7006.,1336.],'angles':[8.,115.,0.]},
        {'name':'assault_mp40_sun_side','eye':[4536.,7006.,1336.],'angles':[8.,205.,0.]},
        {'name':'assault_mp40_toward_sun','eye':[4536.,7006.,1336.],'angles':[-8.,295.,0.]}
    ]


def capture(source, retail, release, output, variant, map_name):
    import numpy as np
    from PIL import Image
    output.mkdir(parents=True,exist_ok=True)
    rt=Path(f'proof-runtime-{variant}-{map_name}').resolve(); main=rt/'main';main.mkdir(parents=True,exist_ok=True)
    build=source/'SP/build/release-linux-x86_64'
    for p in build.iterdir():
        if p.is_file():shutil.copy2(p,rt/p.name)
    for p in (build/'main').glob('*.so'):shutil.copy2(p,main/p.name)
    for p in retail.iterdir():
        if p.is_file() and p.suffix.lower()=='.pk3':(main/p.name.lower()).symlink_to(p.resolve())
    for name in ('PRODUCTION_HIGH_QUALITY.cfg','UNIFIED_PRODUCTION.cfg','darkwolf_ignition_rc_v0_6.pk3'):
        p=next(release.rglob(name));shutil.copy2(p,main/name)
    vv=views(map_name)
    cmds=['set con_notifytime -1','set cg_draw2D 0','set cg_drawGun 1','set cg_bobup 0','set cg_bobpitch 0','set cg_bobroll 0',
          'set r_autoExposure 0','set r_forceAutoExposure 0','set r_forceSunPause 1','give all','wait 5','weapon 3','wait 35']
    shots=[];index=0
    for view in vv:
        cmds+=['set dw_proofFreeze 0','proofView '+' '.join(f'{x:.6f}' for x in view['eye']+view['angles']),
               'wait 30','set dw_proofFreeze 1','wait 3']
        for mode in ('on','off','on_repeat'):
            index+=1;name=f"{view['name']}_{variant}_{mode}"
            cmds += ['set r_ssgi '+('0' if map_name=='factory' and mode=='off' else '1'),
                     'set r_volumetricSun '+('0' if map_name=='assault' and mode=='off' else '1'),
                     'set r_volumetricLocal 1','set r_volumetricFire 1',
                     f'set dw_proofShot {index}','wait 5',f'screenshot {name}','wait 3']
            shots.append({'name':name,'view':view['name'],'mode':mode,'index':index})
    cmds+=['echo PROOF_COMPLETE','set dw_proofFreeze 0','quit']
    scenario='REQUESTED_VIEWS.cfg';(main/scenario).write_text('\n'.join(cmds)+'\n');shutil.copy2(main/scenario,output/scenario)
    setup=['exec PRODUCTION_HIGH_QUALITY.cfg','set r_mode -1','set r_customwidth 1600','set r_customheight 900','set r_fullscreen 0',
           'set r_ssgi 1','set r_volumetricSun 1','set r_volumetricLocal 1','set r_volumetricFire 1','set r_shadowBlur 0',
           'set r_autoExposure 0','set r_forceAutoExposure 0','set com_fixedtime 100','set s_initsound 0','set r_swapInterval 0',
           'set cg_draw2D 0','set con_notifytime -1','set developer 0']
    (main/'PROOF_SETUP.cfg').write_text('\n'.join(setup)+'\n');shutil.copy2(main/'PROOF_SETUP.cfg',output/'PROOF_SETUP.cfg')
    home=rt/'home';home.mkdir(exist_ok=True)
    exe=next(p for p in rt.iterdir() if p.name.lower().startswith('iowolfsp'));exe.chmod(0o755)
    command=['xvfb-run','-a',str(exe),'+safe','+set','fs_basepath',str(rt),'+set','fs_homepath',str(home),
             '+set','com_introplayed','1','+set','com_recommendedSet','1','+set','logfile','2',
             '+set','dw_proofAutomation','1','+set','r_renderer','rend2','+set','cl_renderer','rend2',
             '+exec','PROOF_SETUP.cfg','+vid_restart','+set','dw_proofScenario',scenario,'+spdevmap',map_name]
    # Do not propagate workflow credentials to the game subprocess.
    env={k:v for k,v in os.environ.items() if not any(t in k.upper() for t in ('TOKEN','SECRET','PASSWORD','CREDENTIAL'))}
    env.update(LIBGL_ALWAYS_SOFTWARE='1',LP_NUM_THREADS='2')
    with (output/'stdout.log').open('w') as log:
        p=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        try:rc=p.wait(timeout=900)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait();rc=124
    logs=[]
    for i,p in enumerate(home.rglob('*console*.log')):
        shutil.copy2(p,output/f'console-{i}.log');logs.append(p.read_text(errors='replace'))
    images={}
    for s in shots:
        match=list(home.rglob(s['name']+'.tga'))
        if len(match)==1:
            im=Image.open(match[0]).convert('RGB');im.save(output/(s['name']+'.png'));images[s['name']]=np.array(im).astype(int)
    checks=[]
    for v in vv:
        keys=[v['name']+'_'+variant+'_'+k for k in ('on','off','on_repeat')]
        if all(k in images for k in keys):
            on,off,repeat=[images[k] for k in keys];delta=abs(on-off);drift=abs(on-repeat)
            checks.append({'view':v['name'],'effect_changed_pixels':int(np.any(delta>0,axis=2).sum()),
                           'effect_max_delta':int(delta.max()),'repeat_max_delta':int(drift.max()),
                           'repeat_changed_pixels':int(np.any(drift>0,axis=2).sum())})
    text='\n'.join(logs)
    report={'variant':variant,'map':map_name,'exit':rc,'resolution':[1600,900], 'views':vv,'shots':shots,
            'checks':checks,'captured':len(images),'ready':'PROOF_READY' in text,'completed':'PROOF_COMPLETE' in text,
            'renderer_source':'unchanged published candidate' if variant=='candidate' else 'base algorithm with SSGI depth input provisioned',
            'runtime':'Linux Mesa software; not Windows GPU timing','visual_acceptance':'PENDING_REVIEW'}
    (output/'capture.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)
    assert rc==0 and report['ready'] and report['completed'] and len(images)==len(shots),'Capture incomplete'
    assert all(c['effect_changed_pixels']>10 for c in checks),'Requested effect produced no measured image contribution'
    assert all('weapon=3' in line for line in text.splitlines() if 'PROOF_VIEW' in line),'MP40 not selected'


if __name__=='__main__':
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('instrument');p.add_argument('source',type=Path)
    p=sub.add_parser('capture');p.add_argument('source',type=Path);p.add_argument('retail',type=Path);p.add_argument('release',type=Path);p.add_argument('output',type=Path);p.add_argument('variant',choices=['base','candidate']);p.add_argument('map_name',choices=['factory','assault'])
    args=ap.parse_args()
    if args.command=='instrument':instrument(args.source)
    else:capture(args.source,args.retail,args.release,args.output,args.variant,args.map_name)
