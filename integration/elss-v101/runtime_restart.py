#!/usr/bin/env python3
"""Two-process proof for the ELSS V1.0.1 restart persistence fix.

Session 1:
- activate the known Boss1 projector used by ELSS V1 proof
- bind its housing, set selfshadow OFF, save, capture OFF, quit

Session 2:
- start a completely new game process with the same fs_homepath
- let ELSS load the saved profile while the test lamp is still absent
- activate the lamp later
- do NOT call dw_el_reload / dw_el_select / dw_el_set
- prove the saved manual fixture is rebuilt automatically and capture it
"""
from pathlib import Path
import sys,math,struct,re,json,zipfile,tempfile,shutil,subprocess,os,signal,hashlib
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'testlab/scripts'))
from rc4_assault_camera import World
from PIL import Image
import numpy as np

MAP='boss1';EMITTER=7234;BODY=7232

def geometry(retail):
    data=None
    for p in sorted(retail.iterdir()):
        if p.suffix.lower()!='.pk3':continue
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                if n.lower()=='maps/boss1.bsp':data=z.read(n);break
        if data is not None:break
    assert data is not None
    return data

def parsed(data):
    def lump(i):o,n=struct.unpack_from('<ii',data,8+8*i);return data[o:o+n]
    verts=list(struct.iter_unpack('<10f4B',lump(10)));surfs=list(struct.iter_unpack('<12i12f2i',lump(13)))
    return verts,surfs

def center(verts,surfs,index):
    s=surfs[index];v=verts[s[3]:s[3]+s[4]];assert v
    return [sum(x[k] for x in v)/len(v) for k in range(3)]

def angles(eye,target):
    d=[target[k]-eye[k] for k in range(3)]
    return [-math.degrees(math.atan2(d[2],math.hypot(d[0],d[1]))),math.degrees(math.atan2(d[1],d[0]))%360,0]

def camera_for(world,anchor):
    candidates=[]
    for distance in (160,224,112,288):
        for step in range(16):
            theta=step*math.pi/8
            for dz in (-40,-64,-16,16):
                eye=[anchor[0]+distance*math.cos(theta),anchor[1]+distance*math.sin(theta),anchor[2]+dz]
                if world.solid(eye):continue
                if any(world.solid([eye[k]+o[k] for k in range(3)]) for o in ((8,0,0),(-8,0,0),(0,8,0),(0,-8,0),(0,0,-16))):continue
                hit=world.trace(eye,anchor)
                if hit and hit.get('fraction',0)<.98:continue
                candidates.append((distance+abs(dz)*.01+step*.001,eye))
    assert candidates
    return min(candidates,key=lambda x:x[0])[1]

def make_runtime(retail,out):
    runtime=Path(tempfile.mkdtemp(prefix='elss-v101-restart-',dir=out.parent)).resolve()
    main=runtime/'main';main.mkdir();home=runtime/'home';home.mkdir()
    build=Path('source/SP/build/release-linux-x86_64')
    for p in build.iterdir():
        if p.is_file():shutil.copy2(p,runtime/p.name)
    for p in (build/'main').glob('*.so'):shutil.copy2(p,main/p.name)
    for p in retail.iterdir():
        if p.suffix.lower()=='.pk3':(main/p.name.lower()).symlink_to(p.resolve())
    setup=['set r_mode -1','set r_customwidth 960','set r_customheight 540','set r_fullscreen 0','set r_renderer rend2','set cl_renderer rend2',
           'set r_hdr 1','set r_postProcess 1','set r_bloom 1','set r_bloomMode 2','set r_ssgi 1','set r_forceSun 1','set r_sunShadows 1',
           'set r_dlightMode 2','set r_dlightShadowMaxLights 3','set r_dlightWorldContainment 2','set r_volumetricSun 1','set r_volumetricLocal 1',
           'set r_volumetricFire 1','set r_ext_framebuffer_multisample 4','set r_cameraExposure 1','set r_autoExposure 0','set r_forceAutoExposure 0',
           'set r_dwFireLightControl 0','set r_dwElectricLightControl 1','set r_externalGLSL 0','set s_initsound 0','set r_swapInterval 0',
           'set fixedtime 100','set con_notifytime -1']
    (main/'SETUP.cfg').write_text('\n'.join(setup)+'\n')
    return runtime,main,home

def run_session(runtime,main,home,commands,label,out):
    (main/'TEST.cfg').write_text('\n'.join(commands)+'\n')
    exe=next(p for p in runtime.iterdir() if p.name.startswith('iowolfsp') and p.is_file());exe.chmod(0o755)
    args=['xvfb-run','-a','-s','-screen 0 1280x720x24',str(exe),'+safe','+set','fs_basepath',str(runtime),'+set','fs_homepath',str(home),
          '+set','com_introplayed','1','+set','com_recommendedSet','1','+set','logfile','2','+set','dw_proofAutomation','1',
          '+set','r_renderer','rend2','+set','cl_renderer','rend2','+exec','SETUP.cfg','+vid_restart','+set','dw_proofScenario','TEST.cfg','+spdevmap',MAP]
    env={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ('TOKEN','SECRET','PASSWORD','CREDENTIAL'))}
    env.update(LIBGL_ALWAYS_SOFTWARE='1',LP_NUM_THREADS='2',SDL_AUDIODRIVER='dummy')
    with (out/(label+'_stdout.log')).open('w') as log:
        p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        try:rc=p.wait(timeout=1800)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait();rc=124
    logs=[]
    for src in sorted(home.rglob('*console*.log')):
        # logfile names can be reused; copy current content after each process
        dst=out/(label+'_'+src.name)
        shutil.copy2(src,dst);logs.append(dst.read_text(errors='replace'))
    return rc,'\n'.join(logs)

def capture(retail,out):
    out.mkdir(parents=True,exist_ok=True)
    data=geometry(retail);verts,surfs=parsed(data);world=World(data)
    emitter=center(verts,surfs,EMITTER);body=center(verts,surfs,BODY);eye=camera_for(world,emitter);scene=[(emitter[k]+body[k])*.5 for k in range(3)]
    def pv(target):return 'proofView '+' '.join(f'{x:.6f}' for x in eye+angles(eye,target))
    (out/'TARGET.json').write_text(json.dumps({'emitter':emitter,'body':body,'eye':eye,'bsp_sha256':hashlib.sha256(data).hexdigest()},indent=2)+'\n')
    runtime,main,home=make_runtime(retail,out)

    first=[
      'set cg_draw2D 0','set cg_drawGun 0','set cg_bobup 0','set cg_bobpitch 0','set cg_bobroll 0','set r_forceSunPause 1','god','notarget','wait 20',
      f'dw_el_test_enable {EMITTER} 1','wait 28',pv(emitter),'wait 16','dw_el_select',pv(body),'wait 12','dw_el_self_pick',
      'dw_el_set selfshadow 0','dw_el_save',pv(scene),'wait 28','set dw_proofFreeze 1','wait 12',
      'echo ELSS101_FIRST_OFF','dw_el_info','dw_el_test_audit','set dw_proofShot 1','wait 4','screenshot elss101_first_off','set dw_proofShot 0','wait 2',
      'echo ELSS101_FIRST_DONE','quit'
    ]
    rc1,text1=run_session(runtime,main,home,first,'session1',out)
    profile=list(home.rglob('electricshadows/boss1.elss'))
    assert len(profile)==1,profile
    shutil.copy2(profile[0],out/'boss1_saved.elss')

    # New process. Deliberately wait with the lamp absent so an old V1 build
    # would poison its fixture cache before the owner appears.
    second=[
      'set cg_draw2D 0','set cg_drawGun 0','set cg_bobup 0','set cg_bobpitch 0','set cg_bobroll 0','set r_forceSunPause 1','god','notarget',
      'wait 60',f'dw_el_test_enable {EMITTER} 1','wait 48',pv(scene),'wait 20','set dw_proofFreeze 1','wait 12',
      'echo ELSS101_RESTART_LOADED','dw_el_test_audit','set dw_proofShot 2','wait 4','screenshot elss101_restart_loaded','set dw_proofShot 0','wait 2',
      'echo ELSS101_RESTART_DONE','quit'
    ]
    # remove prior logfile so session2 evidence is not contaminated
    for p in home.rglob('*console*.log'):p.unlink()
    rc2,text2=run_session(runtime,main,home,second,'session2',out)

    imgs={}
    for name in ('elss101_first_off','elss101_restart_loaded'):
        found=list(home.rglob(name+'.tga'))
        # session1 screenshot may remain in home; both are expected
        if not found:
            # look in all runtime paths explicitly
            found=list(runtime.rglob(name+'.tga'))
        assert len(found)==1,(name,found)
        im=Image.open(found[0]).convert('RGB');im.save(out/(name+'.png'));imgs[name]=np.asarray(im).astype(np.int16)
    d=np.abs(imgs['elss101_first_off']-imgs['elss101_restart_loaded'])
    comp={'pixels':int(np.any(d>0,axis=2).sum()),'above2':int(np.any(d>2,axis=2).sum()),'mae':float(d.mean()),'max':int(d.max())}

    faults=[]
    if rc1!=0:faults.append('session1 exit '+str(rc1))
    if rc2!=0:faults.append('session2 exit '+str(rc2))
    if 'ELSS: saved and verified 1 lamp profiles' not in text1:faults.append('profile not saved')
    if 'ELSS: loaded 1 lamp profiles' not in text2:faults.append('profile not auto-loaded after restart')
    enable=re.search(r'ELSS_TEST_ENABLE emitter='+str(EMITTER)+r'[^\n]*entity=(\d+)',text1)
    if not enable:faults.append('fixture entity not found in session1')
    else:
        key='fixture:'+enable.group(1)
        lines=[l for l in text2.splitlines() if l.startswith('ELSS_TEST_LIGHT ') and ('key='+key+' ') in l]
        if not lines:faults.append('restarted target light not audited: '+key)
        elif not any(re.search(r'fixture=-\d+',l) for l in lines):faults.append('saved OFF profile did not rebuild manual fixture after restart')
    if comp['pixels']!=0:faults.append('restart image differs from saved OFF state')
    if 'ELSS101_RESTART_DONE' not in text2:faults.append('restart scenario incomplete')

    report={'session1_exit':rc1,'session2_exit':rc2,'restart_vs_saved_off':comp,'faults':faults,
            'profile_text':(out/'boss1_saved.elss').read_text(errors='replace'),
            'session2_elss_lines':[l for l in text2.splitlines() if l.startswith(('ELSS:','ELSS_TEST_','ELSS101_'))]}
    (out/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'session1_exit':rc1,'session2_exit':rc2,'restart_vs_saved_off':comp,'faults':faults},indent=2))
    assert not faults,faults

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('retail',type=Path);p.add_argument('out',type=Path);a=p.parse_args();capture(a.retail.resolve(),a.out.resolve())
