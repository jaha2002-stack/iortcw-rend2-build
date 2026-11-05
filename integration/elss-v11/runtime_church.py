#!/usr/bin/env python3
"""Church fixture:107 proof for ELSS V1.1 Component Pick + V1.0.1 persistence."""
from pathlib import Path
import argparse,zipfile,struct,math,tempfile,shutil,subprocess,os,signal,re,json,hashlib
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
import sys;sys.path.insert(0,str(ROOT/'testlab/scripts'))
from rc4_assault_camera import World

MAP='church';FIXTURE=107;BODY_SURFACE=11459;PROTECTED_SURFACE=10810
ANCHOR=(-241.0,-178.0,144.0)

def load_bsp(retail):
    for p in sorted(retail.iterdir()):
        if p.suffix.lower()!='.pk3':continue
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                if n.lower()=='maps/church.bsp':return z.read(n)
    raise RuntimeError('church.bsp missing')
def lump(data,i):
    o,n=struct.unpack_from('<ii',data,8+8*i);return data[o:o+n]
def parsed(data):
    verts=list(struct.iter_unpack('<10f4B',lump(data,10)));surfs=list(struct.iter_unpack('<12i12f2i',lump(data,13)))
    return verts,surfs
def center(verts,surfs,index):
    s=surfs[index];v=verts[s[3]:s[3]+s[4]];assert v
    return [sum(float(x[k]) for x in v)/len(v) for k in range(3)]
def angles(eye,target):
    d=[target[k]-eye[k] for k in range(3)]
    return [-math.degrees(math.atan2(d[2],math.hypot(d[0],d[1]))),math.degrees(math.atan2(d[1],d[0]))%360,0]
def line_dist(p,a,b):
    ab=[b[k]-a[k] for k in range(3)];ap=[p[k]-a[k] for k in range(3)];den=sum(x*x for x in ab)
    t=max(0,min(1,sum(ap[k]*ab[k] for k in range(3))/den))
    q=[a[k]+t*ab[k] for k in range(3)]
    return math.dist(p,q)
def choose_eye(world,body,floor):
    cand=[]
    for dist in (112,144,176,208,240):
      for step in range(32):
        a=step*2*math.pi/32
        for dz in (16,32,48,64,-8):
          eye=[ANCHOR[0]+dist*math.cos(a),ANCHOR[1]+dist*math.sin(a),ANCHOR[2]+dz]
          if world.solid(eye):continue
          if any(world.solid([eye[k]+o[k] for k in range(3)]) for o in ((8,0,0),(-8,0,0),(0,8,0),(0,-8,0),(0,0,-16))):continue
          hit=world.trace(eye,ANCHOR)
          if hit and hit.get('fraction',0)<.96:continue
          # Prefer a view where the body is close to the user-like ray toward
          # the protected floor point below the light.
          score=line_dist(body,eye,floor)+dist*.002+abs(dz-32)*.01
          cand.append((score,eye))
    assert cand,'no camera'
    return min(cand,key=lambda x:x[0])[1]

def make_runtime(retail,out):
    runtime=Path(tempfile.mkdtemp(prefix='elss11-church-',dir=out.parent)).resolve();main=runtime/'main';main.mkdir();home=runtime/'home';home.mkdir()
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
def run_process(runtime,main,home,commands,label,out):
    (main/'TEST.cfg').write_text('\n'.join(commands)+'\n')
    exe=next(p for p in runtime.iterdir() if p.name.startswith('iowolfsp') and p.is_file());exe.chmod(0o755)
    args=['xvfb-run','-a','-s','-screen 0 1280x720x24',str(exe),'+safe','+set','fs_basepath',str(runtime),'+set','fs_homepath',str(home),
          '+set','com_introplayed','1','+set','com_recommendedSet','1','+set','logfile','2','+set','dw_proofAutomation','1',
          '+set','r_renderer','rend2','+set','cl_renderer','rend2','+exec','SETUP.cfg','+vid_restart','+set','dw_proofScenario','TEST.cfg','+spdevmap',MAP]
    env={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ('TOKEN','SECRET','PASSWORD','CREDENTIAL'))}
    env.update(LIBGL_ALWAYS_SOFTWARE='1',LP_NUM_THREADS='2',SDL_AUDIODRIVER='dummy')
    with (out/(label+'_stdout.log')).open('w') as log:
        p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        try:rc=p.wait(timeout=1500)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait();rc=124
    logs=[]
    for src in sorted(home.rglob('*console*.log')):
        dst=out/(label+'_'+src.name);shutil.copy2(src,dst);logs.append(dst.read_text(errors='replace'))
    return rc,'\n'.join(logs)
def grab(runtime,out,name):
    found=list(runtime.rglob(name+'.tga'));assert len(found)==1,(name,found)
    im=Image.open(found[0]).convert('RGB');im.save(out/(name+'.png'));return np.asarray(im).astype(np.int16)

def main(retail,out):
    out.mkdir(parents=True,exist_ok=True);data=load_bsp(retail);verts,surfs=parsed(data);world=World(data)
    body=center(verts,surfs,BODY_SURFACE);floor=[ANCHOR[0],ANCHOR[1],78.0];eye=choose_eye(world,body,floor)
    scene=[ANCHOR[0],ANCHOR[1],110.0]
    def pv(t):return 'proofView '+' '.join(f'{x:.6f}' for x in eye+angles(eye,t))
    (out/'TARGET.json').write_text(json.dumps({'fixture':FIXTURE,'body_surface':BODY_SURFACE,'body_center':body,'protected_surface':PROTECTED_SURFACE,'floor_target':floor,'anchor':ANCHOR,'eye':eye,'body_to_floor_ray_distance':line_dist(body,eye,floor),'bsp_sha256':hashlib.sha256(data).hexdigest()},indent=2)+'\n')
    runtime,mainp,home=make_runtime(retail,out)

    cmds=['set cg_draw2D 0','set cg_drawGun 0','set cg_bobup 0','set cg_bobpitch 0','set cg_bobroll 0','set r_forceSunPause 1','god','notarget','wait 24',
          f'dw_el_v11_test_fixture {FIXTURE} 1','wait 36',pv(body),'wait 20','dw_el_select','dw_el_info','dw_el_v11_test_audit 107',
          # Direct body pick first: V1 failed on some compact parts because the flood candidate set overflowed.
          pv(body),'wait 12','dw_el_self_pick','dw_el_info',
          'dw_el_set selfshadow 1',pv(scene),'wait 24','set dw_proofFreeze 1','wait 12',
          'echo ELSS11_STATE ON','dw_el_info','dw_el_v11_test_audit 107','set dw_proofShot 1','wait 4','screenshot elss11_church_on','set dw_proofShot 0','wait 2',
          'dw_el_set selfshadow 0','wait 32',
          'echo ELSS11_STATE OFF','dw_el_info','dw_el_v11_test_audit 107','set dw_proofShot 2','wait 4','screenshot elss11_church_off','set dw_proofShot 0','wait 2',
          'dw_el_save','wait 12',
          'echo ELSS11_STATE SAVED','dw_el_info','set dw_proofShot 3','wait 4','screenshot elss11_church_saved','set dw_proofShot 0','wait 2',
          'set dw_proofFreeze 0','echo ELSS11_SESSION1_DONE','quit']
    rc1,t1=run_process(runtime,mainp,home,cmds,'session1',out)
    profile=list(home.rglob('electricshadows/church.elss'));assert len(profile)==1,profile;shutil.copy2(profile[0],out/'church_saved.elss')
    img_on=grab(runtime,out,'elss11_church_on');img_off=grab(runtime,out,'elss11_church_off');img_saved=grab(runtime,out,'elss11_church_saved')

    # Fresh process: preserve V1.0.1 persistence behavior and do not use reload/select/set.
    for p in home.rglob('*console*.log'):p.unlink()
    cmds2=['set cg_draw2D 0','set cg_drawGun 0','set cg_bobup 0','set cg_bobpitch 0','set cg_bobroll 0','set r_forceSunPause 1','god','notarget',
           'wait 70',f'dw_el_v11_test_fixture {FIXTURE} 1','wait 48',pv(scene),'wait 20','set dw_proofFreeze 1','wait 12',
           'echo ELSS11_STATE RESTART','dw_el_v11_test_audit 107','set dw_proofShot 4','wait 4','screenshot elss11_church_restart','set dw_proofShot 0','wait 2',
           'set dw_proofFreeze 0','echo ELSS11_SESSION2_DONE','quit']
    rc2,t2=run_process(runtime,mainp,home,cmds2,'session2',out);img_restart=grab(runtime,out,'elss11_church_restart')

    def comp(a,b):
        d=np.abs(a-b);return {'pixels':int(np.any(d>0,axis=2).sum()),'above2':int(np.any(d>2,axis=2).sum()),'mae':float(d.mean()),'max':int(d.max())}
    comps={'on_off':comp(img_on,img_off),'off_saved':comp(img_off,img_saved),'off_restart':comp(img_off,img_restart)}
    faults=[]
    if rc1!=0:faults.append('session1 exit '+str(rc1))
    if rc2!=0:faults.append('session2 exit '+str(rc2))
    if 'ELSS11_SESSION1_DONE' not in t1:faults.append('session1 incomplete')
    if 'ELSS11_SESSION2_DONE' not in t2:faults.append('session2 incomplete')
    if not re.search(r'ELSS V1\.1: bound body surface \d+ mode=EXACT',t1):
        faults.append('V1.1 exact body fallback not exercised')
    if re.search(r'bound (?:nearby safe )?body surface 10810',t1):faults.append('protected surface 10810 was bound')
    if 'selfshadow=OFF' not in t1:faults.append('OFF not active')
    if comps['on_off']['above2']<20:faults.append('no visible selfshadow response')
    if comps['off_saved']['pixels']!=0:faults.append('OFF->saved differs')
    if comps['off_restart']['pixels']!=0:faults.append('OFF->restart differs')
    if 'ELSS: loaded 1 lamp profiles' not in t2:faults.append('profile not loaded on restart')
    lightlines=[l for l in t2.splitlines() if l.startswith('ELSS11_TEST_LIGHT ') and 'key=fixture:107 ' in l]
    if not lightlines:faults.append('fixture107 not audited after restart')
    elif not any(re.search(r'policyFixture=-\d+',l) for l in lightlines):faults.append('restart did not restore manual OFF policy')
    # The slot must still exist; ELSS removes only own-body casters.
    if lightlines and not any(re.search(r'pointSlot=[0-2]\b',l) for l in lightlines):faults.append('shadow slot not preserved after restart')
    report={'session1_exit':rc1,'session2_exit':rc2,'comparisons':comps,'faults':faults,
            'profile':(out/'church_saved.elss').read_text(errors='replace'),
            'session1_elss':[l for l in t1.splitlines() if l.startswith(('ELSS:','ELSS V1.1:','ELSS11_'))],
            'session2_elss':[l for l in t2.splitlines() if l.startswith(('ELSS:','ELSS V1.1:','ELSS11_'))]}
    (out/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'comparisons':comps,'faults':faults},indent=2))
    assert not faults,faults

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('retail',type=Path);p.add_argument('out',type=Path);a=p.parse_args();main(a.retail.resolve(),a.out.resolve())
