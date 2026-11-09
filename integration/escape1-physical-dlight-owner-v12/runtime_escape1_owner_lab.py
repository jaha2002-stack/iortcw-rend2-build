#!/usr/bin/env python3
from pathlib import Path
import argparse,json,math,os,re,shutil,signal,subprocess,sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integration/electric-owner-audit-v1'))
sys.path.insert(0,str(ROOT/'testlab/scripts'))
import runtime_lab as base
from rc4_assault_camera import World

MAP='escape1'
GUARD_CENTER=[-760.0,690.0,-300.0]
GUARD_IDS={740,741,742,743,744,745}

def kv(line):
    return dict(re.findall(r'(\w+)=([^\s]+)',line))

def choose_views(retail):
    data=base.load_bsp(retail,MAP)
    world=World(data)
    cand=[]
    for radius in (120,160,208,256):
        for step in range(20):
            a=step*2*math.pi/20
            for dz in (24,48,72):
                eye=[GUARD_CENTER[0]+radius*math.cos(a),
                     GUARD_CENTER[1]+radius*math.sin(a),
                     GUARD_CENTER[2]+dz]
                if world.solid(eye):
                    continue
                hit=world.trace(eye,GUARD_CENTER)
                if hit and hit.get('fraction',1.0)<0.86:
                    continue
                cand.append(eye)
    out=[]
    for eye in cand:
        if all(math.dist(eye,x)>110 for x in out):
            out.append(eye)
        if len(out)>=6:
            break
    if len(out)<4:
        out=base.choose_eyes(world,GUARD_CENTER,6)
    return out[:6]

def run(retail,out):
    out.mkdir(parents=True,exist_ok=True)
    vv=choose_views(retail)
    runtime,main,home=base.assemble_runtime(retail,out,MAP)

    setup=[
      'set r_mode -1','set r_customwidth 800','set r_customheight 450','set r_fullscreen 0',
      'set r_renderer rend2','set cl_renderer rend2',
      'set r_hdr 0','set r_postProcess 0','set r_bloom 0','set r_ssgi 0',
      'set r_forceSun 0','set r_sunShadows 0','set r_volumetricLocal 0',
      'set r_volumetricFire 0','set r_volumetricSun 0',
      'set r_dlightMode 2','set r_dlightShadowMaxLights 3',
      'set r_staticPromote 1','set r_staticPromoteAutoMapLights 1',
      'set r_staticPromoteMaxLights 32','set r_staticPromoteUnifiedResidency 1',
      'set r_dwElectricPhysicalOwner 1',
      'set r_dwEscape1PhysicalDlightOwnerResidency 1',
      'set r_dwEscape1ExternalNativeReserve 9',
      'set r_dwEscape1PhysicalDlightOwnerDiag 1',
      'set r_dwEscape1DlightResidencyAudit 1',
      'set r_dwEscape1DlightResidencyAuditIntervalMs 60',
      'set r_externalGLSL 0','set s_initsound 0','set r_swapInterval 0',
      'set fixedtime 50','set con_notifytime -1'
    ]
    (main/'SETUP.cfg').write_text('\n'.join(setup)+'\n')

    cmd=['set cg_draw2D 0','set cg_drawGun 0','god','notarget','give all','wait 16']
    for i,eye in enumerate(vv):
        ang=base.angles(eye,GUARD_CENTER)
        cmd += ['proofView '+' '.join(f'{x:.6f}' for x in eye+ang),
                'wait 18',f'echo EDR12_LAB_VIEW index={i}','wait 5']
    # Native pressure to exercise hard MAX_DLIGHTS headroom.
    eye=vv[0];ang=base.angles(eye,GUARD_CENTER)
    cmd += ['proofView '+' '.join(f'{x:.6f}' for x in eye+ang),
            'wait 12','echo EDR12_NATIVE_PRESSURE_BEGIN']
    for i in range(5):
        cmd += ['+attack','wait 2','-attack','wait 7',f'echo EDR12_SHOT index={i}']
    cmd += ['wait 18','echo EDR12_LAB_DONE','quit']
    (main/'TEST.cfg').write_text('\n'.join(cmd)+'\n')

    exe=next(p for p in runtime.iterdir()
             if p.name.startswith('iowolfsp') and p.is_file())
    exe.chmod(0o755)
    args=['xvfb-run','-a','-s','-screen 0 1024x600x24',str(exe),'+safe',
      '+set','fs_basepath',str(runtime),'+set','fs_homepath',str(home),
      '+set','com_introplayed','1','+set','com_recommendedSet','1',
      '+set','logfile','2','+set','dw_proofAutomation','1',
      '+set','r_renderer','rend2','+set','cl_renderer','rend2',
      '+exec','SETUP.cfg','+vid_restart',
      '+set','dw_proofScenario','TEST.cfg','+spdevmap',MAP]
    env={k:v for k,v in os.environ.items()
         if not any(x in k.upper() for x in ('TOKEN','SECRET','PASSWORD','CREDENTIAL'))}
    env.update(LIBGL_ALWAYS_SOFTWARE='1',SDL_AUDIODRIVER='dummy',LP_NUM_THREADS='2')

    with (out/'stdout.log').open('w') as log:
        p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,
                           env=env,start_new_session=True)
        try:
            rc=p.wait(timeout=500)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL);p.wait();rc=124

    text=''
    for i,p in enumerate(sorted(home.rglob('*console*.log'))):
        shutil.copy2(p,out/f'console-{i}.log')
        text += p.read_text(errors='replace')+'\n'
    lines=[x for x in text.splitlines()
           if x.startswith(('EDR12_','EDRA_'))]
    (out/'TRACE.log').write_text('\n'.join(lines)+'\n')

    assert rc==0 and 'EDR12_LAB_DONE' in text,(rc,'missing done')
    assert any(x.startswith('EDR12_SUMMARY ') for x in lines),'no EDR12 summary'

    summaries=[]
    guards={str(x):[] for x in sorted(GUARD_IDS)}
    for l in lines:
        d=kv(l)
        if l.startswith('EDR12_SUMMARY '):
            summaries.append(d)
        elif l.startswith('EDRA_GUARD '):
            try:
                f=int(d['fixture'])
            except Exception:
                continue
            if f in GUARD_IDS:
                guards[str(f)].append({
                    'resident':int(d.get('resident','0')),
                    'evicted':int(d.get('budgetEvicted','0')),
                    'tier':d.get('tier'),
                    'route':d.get('route'),
                    'selectedSlot':int(d.get('selectedSlot','-1'))
                })

    rows=[]
    for d in summaries:
        try:
            rows.append({k:int(float(v)) for k,v in d.items()
                         if re.fullmatch(r'-?\d+(?:\.\d+)?',v)})
        except Exception:
            pass

    def values(k):
        return sorted(set(r.get(k) for r in rows if k in r))

    faults=[]
    # Route-independent invariant: owner budget remains 23 while external-native <=9.
    for r in rows:
        ext=r.get('externalNative')
        if ext is not None and ext<=9 and r.get('physicalOwnerBudget')!=23:
            faults.append(f'owner budget drift at externalNative={ext}: {r.get("physicalOwnerBudget")}')
        if ext is not None and ext<=9:
            expected=max(0,23-r.get('acceptedNativeRoutes',0))
            if r.get('promotedBudget')!=expected:
                faults.append(
                    f'promoted budget not route-compensated: routes={r.get("acceptedNativeRoutes")} '
                    f'got={r.get("promotedBudget")} expected={expected}')

    guard_report={}
    for f,samples in guards.items():
        if not samples:
            faults.append('no guard telemetry '+f)
            continue
        surface=[s for s in samples if s['tier']=='SURFACE_VISIBLE']
        evicted_surface=sum(1 for s in surface if s['evicted'] or not s['resident'])
        changes=sum(1 for i in range(1,len(samples))
                    if samples[i]['resident']!=samples[i-1]['resident'])
        activations=sum(1 for i in range(1,len(samples))
                        if samples[i-1]['resident']==0 and samples[i]['resident']==1)
        deactivations=sum(1 for i in range(1,len(samples))
                          if samples[i-1]['resident']==1 and samples[i]['resident']==0)
        visible_deactivations=sum(
            1 for i in range(1,len(samples))
            if samples[i-1]['resident']==1 and samples[i]['resident']==0
            and (samples[i-1]['tier']=='SURFACE_VISIBLE'
                 or samples[i]['tier']=='SURFACE_VISIBLE'))
        guard_report[f]={
          'samples':len(samples),'surface_samples':len(surface),
          'surface_evicted_samples':evicted_surface,
          'resident_changes':changes,
          'activations':activations,
          'deactivations':deactivations,
          'visible_deactivations':visible_deactivations,
          'ever_resident':1 if any(s['resident'] for s in samples) else 0
        }
        if surface and evicted_surface:
            faults.append(f'guard {f} evicted while SURFACE_VISIBLE')
        if visible_deactivations:
            faults.append(f'guard {f} deactivated while visible={visible_deactivations}')

    report={
      'map':MAP,
      'views':vv,
      'summary_samples':len(rows),
      'sceneNative_values':values('sceneNative'),
      'acceptedNativeRoutes_values':values('acceptedNativeRoutes'),
      'externalNative_values':values('externalNative'),
      'physicalOwnerBudget_values':values('physicalOwnerBudget'),
      'promotedBudget_values':values('promotedBudget'),
      'selectedPromoted_values':values('selectedPromoted'),
      'guard':guard_report,
      'faults':faults
    }
    (out/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
    print('EDR12_RUNTIME_RESULT',json.dumps(report,sort_keys=True))
    assert not faults,faults

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('retail',type=Path)
    ap.add_argument('out',type=Path)
    a=ap.parse_args()
    run(a.retail.resolve(),a.out.resolve())
