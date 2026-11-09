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
    data=base.load_bsp(retail,MAP); world=World(data)
    cand=[]
    for radius in (128,192,256):
        for step in range(12):
            a=step*2*math.pi/12
            eye=[GUARD[0]+radius*math.cos(a),GUARD[1]+radius*math.sin(a),GUARD[2]+48]
            if world.solid(eye): continue
            hit=world.trace(eye,GUARD)
            if hit and hit.get('fraction',1.0)<0.85: continue
            cand.append(eye)
    chosen=[]
    for eye in cand:
        if all(math.dist(eye,x)>140 for x in chosen): chosen.append(eye)
        if len(chosen)>=4: break
    if len(chosen)<3: chosen=base.choose_eyes(world,GUARD,4)
    return chosen[:4]

def run(retail,out):
    out.mkdir(parents=True,exist_ok=True)
    views=choose_views(retail)
    runtime,main,home=base.assemble_runtime(retail,out,MAP)
    setup=[
      'set r_mode -1','set r_customwidth 640','set r_customheight 360','set r_fullscreen 0',
      'set r_renderer rend2','set cl_renderer rend2',
      'set r_hdr 0','set r_postProcess 0','set r_bloom 0','set r_ssgi 0',
      'set r_forceSun 0','set r_sunShadows 0','set r_volumetricLocal 0','set r_volumetricFire 0','set r_volumetricSun 0',
      'set r_dlightMode 2','set r_dlightShadowMaxLights 3','set r_dlightWorldContainment 2',
      'set r_staticPromote 1','set r_staticPromoteAutoMapLights 1','set r_staticPromoteMaxLights 32',
      'set r_staticPromoteUnifiedResidency 1','set r_dwElectricPhysicalOwner 1',
      'set r_dwEscape1DlightResidencyAudit 1','set r_dwEscape1DlightResidencyAuditIntervalMs 50',
      'set r_externalGLSL 0','set s_initsound 0','set r_swapInterval 0','set fixedtime 50','set con_notifytime -1'
    ]
    (main/'SETUP.cfg').write_text('\n'.join(setup)+'\n')
    cmd=['set cg_draw2D 0','set cg_drawGun 0','god','notarget','give all','wait 12']
    for i,eye in enumerate(views):
        ang=base.angles(eye,GUARD)
        cmd += ['proofView '+' '.join(f'{x:.6f}' for x in eye+ang),'wait 12',f'echo EDRA_FAST_VIEW index={i}','wait 3']
    eye=views[0]; ang=base.angles(eye,GUARD)
    cmd += ['proofView '+' '.join(f'{x:.6f}' for x in eye+ang),'wait 10','echo EDRA_FAST_PRESSURE_BEGIN']
    for i in range(3):
        cmd += ['+attack','wait 1','-attack','wait 5',f'echo EDRA_FAST_SHOT index={i}']
    cmd += ['wait 10','echo EDRA_FAST_DONE','quit']
    (main/'TEST.cfg').write_text('\n'.join(cmd)+'\n')
    exe=next(p for p in runtime.iterdir() if p.name.startswith('iowolfsp') and p.is_file()); exe.chmod(0o755)
    args=['xvfb-run','-a','-s','-screen 0 800x600x24',str(exe),'+safe',
      '+set','fs_basepath',str(runtime),'+set','fs_homepath',str(home),
      '+set','com_introplayed','1','+set','com_recommendedSet','1','+set','logfile','2',
      '+set','dw_proofAutomation','1','+set','r_renderer','rend2','+set','cl_renderer','rend2',
      '+exec','SETUP.cfg','+vid_restart','+set','dw_proofScenario','TEST.cfg','+spdevmap',MAP]
    env={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ('TOKEN','SECRET','PASSWORD','CREDENTIAL'))}
    env.update(LIBGL_ALWAYS_SOFTWARE='1',SDL_AUDIODRIVER='dummy',LP_NUM_THREADS='2')
    with (out/'stdout.log').open('w') as log:
        p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        try: rc=p.wait(timeout=300)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL); p.wait(); rc=124
    text=''
    for i,p in enumerate(sorted(home.rglob('*console*.log'))):
        shutil.copy2(p,out/f'console-{i}.log'); text += p.read_text(errors='replace')+'\n'
    lines=[x for x in text.splitlines() if x.startswith('EDRA_')]
    (out/'EDRA.log').write_text('\n'.join(lines)+'\n')
    assert rc==0 and 'EDRA_FAST_DONE' in text,(rc,'missing done')
    assert any(x.startswith('EDRA_SUMMARY ') for x in lines),'no EDRA summary'

    summaries=[]; guards=[]; native_changes=[]; evicts=[]
    for l in lines:
        d=kv(l); d['_line']=l
        if l.startswith('EDRA_SUMMARY '): summaries.append(d)
        elif l.startswith('EDRA_GUARD '): guards.append(d)
        elif l.startswith('EDRA_NATIVE_CHANGE '): native_changes.append(d)
        elif l.startswith('EDRA_EVICT '): evicts.append(d)

    def range_for(k):
        vals=[]
        for d in summaries:
            try: vals.append(int(float(d[k])))
            except Exception: pass
        return {'min':min(vals),'max':max(vals),'values':sorted(set(vals))} if vals else None

    byfixture={}
    for d in guards:
        try: f=str(int(d['fixture'])); resident=int(d['resident']); ev=int(d['budgetEvicted'])
        except Exception: continue
        x=byfixture.setdefault(f,{'resident':[],'evicted':[],'tiers':[],'routes':[],'priority':None})
        x['resident'].append(resident); x['evicted'].append(ev); x['tiers'].append(d.get('tier')); x['routes'].append(d.get('route'))
        try: x['priority']=int(d['priority'])
        except Exception: pass
    for x in byfixture.values():
        x['changes']=sum(1 for i in range(1,len(x['resident'])) if x['resident'][i]!=x['resident'][i-1])
        x['everResident']=1 if any(x['resident']) else 0
        x['everEvicted']=1 if any(x['evicted']) else 0

    report={
      'map':MAP,'guard':GUARD,'views':views,
      'sceneNative':range_for('sceneNative'),'headroom':range_for('headroom'),
      'staticBudget':range_for('staticBudget'),'budgetEvictions':range_for('budgetEvictions'),
      'submittedPromoted':range_for('submittedPromoted'),'accepted':range_for('accepted'),
      'resident':range_for('resident'),'gained':range_for('gained'),'lost':range_for('lost'),
      'native_change_events':len(native_changes),'eviction_lines':len(evicts),
      'guardFixtures':byfixture,'readOnly':True
    }
    (out/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
    print('EDRA_FAST_RESULT',json.dumps(report,sort_keys=True))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('retail',type=Path);ap.add_argument('out',type=Path)
    a=ap.parse_args();run(a.retail.resolve(),a.out.resolve())
