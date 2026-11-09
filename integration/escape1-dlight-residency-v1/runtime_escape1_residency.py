#!/usr/bin/env python3
from pathlib import Path
import argparse,json,math,os,re,shutil,signal,subprocess,sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integration/electric-owner-audit-v1'))
sys.path.insert(0,str(ROOT/'testlab/scripts'))
import runtime_lab as base
from rc4_assault_camera import World

MAP='escape1'
GUARD=[-700.0,650.0,-300.0]

def kv(line): return dict(re.findall(r'(\w+)=([^\s]+)',line))

def choose_views(retail):
    data=base.load_bsp(retail,MAP)
    world=World(data)
    candidates=[]
    for radius in (96,128,160,208,256,320):
        for step in range(16):
            a=step*2*math.pi/16
            eye=[GUARD[0]+radius*math.cos(a),GUARD[1]+radius*math.sin(a),GUARD[2]+40]
            if world.solid(eye): continue
            hit=world.trace(eye,GUARD)
            if hit and hit.get('fraction',1.0)<0.90: continue
            candidates.append(eye)
    chosen=[]
    for eye in candidates:
        if all(math.dist(eye,x)>100 for x in chosen):
            chosen.append(eye)
        if len(chosen)>=8: break
    if len(chosen)<4:
        chosen=base.choose_eyes(world,GUARD,6)
    return chosen

def run(retail,out):
    out.mkdir(parents=True,exist_ok=True)
    views=choose_views(retail)
    runtime,main,home=base.assemble_runtime(retail,out,MAP)
    setup=[
      'set r_mode -1','set r_customwidth 960','set r_customheight 540','set r_fullscreen 0',
      'set r_renderer rend2','set cl_renderer rend2','set r_hdr 1','set r_postProcess 1',
      'set r_bloom 1','set r_bloomMode 2','set r_ssgi 1','set r_forceSun 1','set r_sunShadows 1',
      'set r_dlightMode 2','set r_dlightShadowMaxLights 3','set r_dlightWorldContainment 2',
      'set r_staticPromote 1','set r_staticPromoteAutoMapLights 1','set r_staticPromoteMaxLights 32',
      'set r_staticPromoteUnifiedResidency 1','set r_volumetricLocal 1','set r_volumetricLocalMode 5',
      'set r_volumetricFire 1','set r_volumetricSun 1','set r_dwElectricPhysicalOwner 1',
      'set r_dwEscape1DlightResidencyAudit 1','set r_dwEscape1DlightResidencyAuditIntervalMs 100',
      'set r_externalGLSL 0','set s_initsound 0','set r_swapInterval 0','set fixedtime 50',
      'set con_notifytime -1'
    ]
    (main/'SETUP.cfg').write_text('\n'.join(setup)+'\n')
    cmd=['set cg_draw2D 0','set cg_drawGun 0','god','notarget','give all','wait 30']
    for i,eye in enumerate(views):
        ang=base.angles(eye,GUARD)
        cmd += [
          'proofView '+' '.join(f'{x:.6f}' for x in eye+ang),
          'wait 40',
          f'echo EDRA_LAB_VIEW phase=move index={i}',
          'wait 10'
        ]
    # Controlled transient-native pressure: muzzle flashes should consume transient native DLight capacity
    # without changing any StaticPromote profile.
    eye=views[0]; ang=base.angles(eye,GUARD)
    cmd += ['proofView '+' '.join(f'{x:.6f}' for x in eye+ang),'wait 30',
            'echo EDRA_LAB_PHASE native_pressure_begin']
    for i in range(6):
        cmd += ['+attack','wait 3','-attack','wait 10',f'echo EDRA_LAB_SHOT index={i}']
    cmd += ['wait 40','echo EDRA_LAB_DONE','quit']
    (main/'TEST.cfg').write_text('\n'.join(cmd)+'\n')

    exe=next(p for p in runtime.iterdir() if p.name.startswith('iowolfsp') and p.is_file()); exe.chmod(0o755)
    args=['xvfb-run','-a','-s','-screen 0 1280x720x24',str(exe),'+safe',
      '+set','fs_basepath',str(runtime),'+set','fs_homepath',str(home),
      '+set','com_introplayed','1','+set','com_recommendedSet','1','+set','logfile','2',
      '+set','dw_proofAutomation','1','+set','r_renderer','rend2','+set','cl_renderer','rend2',
      '+exec','SETUP.cfg','+vid_restart','+set','dw_proofScenario','TEST.cfg','+spdevmap',MAP]
    env={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ('TOKEN','SECRET','PASSWORD','CREDENTIAL'))}
    env.update(LIBGL_ALWAYS_SOFTWARE='1',SDL_AUDIODRIVER='dummy',LP_NUM_THREADS='2')
    with (out/'stdout.log').open('w') as log:
        p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        try: rc=p.wait(timeout=900)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL); p.wait(); rc=124

    text=''
    for i,p in enumerate(sorted(home.rglob('*console*.log'))):
        shutil.copy2(p,out/f'console-{i}.log'); text += p.read_text(errors='replace')+'\n'
    lines=[x for x in text.splitlines() if x.startswith('EDRA_')]
    (out/'EDRA.log').write_text('\n'.join(lines)+'\n')
    assert rc==0 and 'EDRA_LAB_DONE' in text,(rc,'missing done')
    assert any(x.startswith('EDRA_SUMMARY ') for x in lines),'no EDRA summary'

    summaries=[]; guard=[]; natives=[]; evicts=[]
    for l in lines:
        d=kv(l); d['_line']=l
        if l.startswith('EDRA_SUMMARY '): summaries.append(d)
        elif l.startswith('EDRA_GUARD '): guard.append(d)
        elif l.startswith('EDRA_NATIVE_CHANGE '): natives.append(d)
        elif l.startswith('EDRA_EVICT '): evicts.append(d)

    def nums(key,rows):
        out=[]
        for d in rows:
            try: out.append(int(float(d[key])))
            except Exception: pass
        return out
    metrics={}
    for k in ('sceneNative','globalUsedBeforePromote','headroom','staticBudget','submittedPromoted','accepted','resident','budgetEvictions','gained','lost'):
        v=nums(k,summaries)
        metrics[k]={'min':min(v),'max':max(v)} if v else None

    byfixture={}
    for d in guard:
        try:
            f=int(d['fixture']); state=int(d['resident'])
        except Exception: continue
        row=byfixture.setdefault(str(f),{'samples':0,'resident_states':[],'budgetEvicted_states':[],'tiers':[],'routes':[]})
        row['samples']+=1
        row['resident_states'].append(state)
        try: row['budgetEvicted_states'].append(int(d['budgetEvicted']))
        except Exception: pass
        row['tiers'].append(d.get('tier'))
        row['routes'].append(d.get('route'))
    for row in byfixture.values():
        row['resident_changes']=sum(1 for i in range(1,len(row['resident_states'])) if row['resident_states'][i]!=row['resident_states'][i-1])
        row['ever_evicted']=1 if any(row['budgetEvicted_states']) else 0
        row['resident_min']=min(row['resident_states']) if row['resident_states'] else None
        row['resident_max']=max(row['resident_states']) if row['resident_states'] else None

    report={
      'map':MAP,'guard_center':GUARD,'views':views,'summary_metrics':metrics,
      'native_change_events':len(natives),'eviction_events_logged':len(evicts),
      'guard_fixtures':byfixture,
      'max_scene_dlights':32,
      'read_only':True
    }
    (out/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
    print('EDRA_ESCAPE1_RESULT',json.dumps(report,sort_keys=True))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('retail',type=Path);ap.add_argument('out',type=Path)
    a=ap.parse_args();run(a.retail.resolve(),a.out.resolve())
