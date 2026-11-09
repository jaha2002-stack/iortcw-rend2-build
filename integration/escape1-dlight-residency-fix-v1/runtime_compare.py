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

def views(retail):
    data=base.load_bsp(retail,MAP); world=World(data); out=[]
    for radius in (128,192,256):
        for step in range(12):
            a=step*2*math.pi/12
            eye=[GUARD[0]+radius*math.cos(a),GUARD[1]+radius*math.sin(a),GUARD[2]+48]
            if world.solid(eye): continue
            hit=world.trace(eye,GUARD)
            if hit and hit.get('fraction',1.0)<0.85: continue
            if all(math.dist(eye,x)>140 for x in out): out.append(eye)
            if len(out)>=4:return out
    return base.choose_eyes(world,GUARD,4)

def run_case(retail,out,enabled):
    out.mkdir(parents=True,exist_ok=True)
    vv=views(retail)
    runtime,main,home=base.assemble_runtime(retail,out,MAP)
    setup=[
      'set r_mode -1','set r_customwidth 640','set r_customheight 360','set r_fullscreen 0',
      'set r_renderer rend2','set cl_renderer rend2',
      'set r_hdr 0','set r_postProcess 0','set r_bloom 0','set r_ssgi 0',
      'set r_forceSun 0','set r_sunShadows 0','set r_volumetricLocal 0','set r_volumetricFire 0','set r_volumetricSun 0',
      'set r_dlightMode 2','set r_dlightShadowMaxLights 3','set r_staticPromote 1',
      'set r_staticPromoteAutoMapLights 1','set r_staticPromoteMaxLights 32','set r_staticPromoteUnifiedResidency 1',
      'set r_dwElectricPhysicalOwner 1',f'set r_dwEscape1StableDlightResidency {1 if enabled else 0}',
      'set r_dwEscape1StableDlightResidencyDiag 1',
      'set r_dwEscape1DlightResidencyAudit 1','set r_dwEscape1DlightResidencyAuditIntervalMs 50',
      'set r_externalGLSL 0','set s_initsound 0','set r_swapInterval 0','set fixedtime 50','set con_notifytime -1'
    ]
    (main/'SETUP.cfg').write_text('\n'.join(setup)+'\n')
    cmd=['set cg_draw2D 0','set cg_drawGun 0','god','notarget','give all','wait 12']
    for i,eye in enumerate(vv):
        ang=base.angles(eye,GUARD)
        cmd += ['proofView '+' '.join(f'{x:.6f}' for x in eye+ang),'wait 12',
                f'echo EDRF_VIEW enabled={1 if enabled else 0} index={i}','wait 3']
    eye=vv[0];ang=base.angles(eye,GUARD)
    cmd += ['proofView '+' '.join(f'{x:.6f}' for x in eye+ang),'wait 10','echo EDRF_PRESSURE_BEGIN']
    for i in range(3):
        cmd += ['+attack','wait 1','-attack','wait 5',f'echo EDRF_SHOT index={i}']
    cmd += ['wait 10',f'echo EDRF_DONE enabled={1 if enabled else 0}','quit']
    (main/'TEST.cfg').write_text('\n'.join(cmd)+'\n')
    exe=next(p for p in runtime.iterdir() if p.name.startswith('iowolfsp') and p.is_file());exe.chmod(0o755)
    args=['xvfb-run','-a','-s','-screen 0 800x600x24',str(exe),'+safe',
      '+set','fs_basepath',str(runtime),'+set','fs_homepath',str(home),
      '+set','com_introplayed','1','+set','com_recommendedSet','1','+set','logfile','2',
      '+set','dw_proofAutomation','1','+set','r_renderer','rend2','+set','cl_renderer','rend2',
      '+exec','SETUP.cfg','+vid_restart','+set','dw_proofScenario','TEST.cfg','+spdevmap',MAP]
    env={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ('TOKEN','SECRET','PASSWORD','CREDENTIAL'))}
    env.update(LIBGL_ALWAYS_SOFTWARE='1',SDL_AUDIODRIVER='dummy',LP_NUM_THREADS='2')
    with (out/'stdout.log').open('w') as log:
        p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        try:rc=p.wait(timeout=300)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL);p.wait();rc=124
    text=''
    for i,p in enumerate(sorted(home.rglob('*console*.log'))):
        shutil.copy2(p,out/f'console-{i}.log');text+=p.read_text(errors='replace')+'\n'
    lines=[x for x in text.splitlines() if x.startswith(('EDRA_','EDRF_'))]
    (out/'TRACE.log').write_text('\n'.join(lines)+'\n')
    assert rc==0 and f'EDRF_DONE enabled={1 if enabled else 0}' in text,(rc,enabled)
    sums=[];guards=[]
    for l in lines:
        d=kv(l)
        if l.startswith('EDRA_SUMMARY '):sums.append(d)
        elif l.startswith('EDRA_GUARD '):guards.append(d)
    def rng(k):
        vals=[]
        for d in sums:
            try:vals.append(int(float(d[k])))
            except:pass
        return {'min':min(vals),'max':max(vals),'values':sorted(set(vals))} if vals else None
    g={}
    for d in guards:
        try:f=str(int(d['fixture']));r=int(d['resident']);e=int(d['budgetEvicted'])
        except:continue
        x=g.setdefault(f,{'resident':[],'evicted':[],'tier':[],'route':[]})
        x['resident'].append(r);x['evicted'].append(e);x['tier'].append(d.get('tier'));x['route'].append(d.get('route'))
    for x in g.values():
        x['changes']=sum(1 for i in range(1,len(x['resident'])) if x['resident'][i]!=x['resident'][i-1])
        x['everEvicted']=1 if any(x['evicted']) else 0
    return {'enabled':enabled,'sceneNative':rng('sceneNative'),'headroom':rng('headroom'),'staticBudget':rng('staticBudget'),
            'budgetEvictions':rng('budgetEvictions'),'submittedPromoted':rng('submittedPromoted'),
            'accepted':rng('accepted'),'resident':rng('resident'),'guard':g}

def main(retail,out):
    out.mkdir(parents=True,exist_ok=True)
    off=run_case(retail,out/'off',False)
    on=run_case(retail,out/'on',True)
    report={'map':MAP,'off':off,'on':on}
    faults=[]
    for k in ('sceneNative','headroom','staticBudget','budgetEvictions','submittedPromoted','accepted','resident'):
        if off[k]!=on[k]: faults.append('budget/count range changed: '+k)
    for f in ('741','742','743','744'):
        if on['guard'].get(f,{}).get('changes',999)>off['guard'].get(f,{}).get('changes',999):
            faults.append('stable guard fixture worsened '+f)
    c0=off['guard'].get('740',{}).get('changes',999)
    c1=on['guard'].get('740',{}).get('changes',999)
    if c1>=c0: faults.append(f'fixture740 churn not reduced: {c0}->{c1}')
    if c1>2: faults.append(f'fixture740 still unstable: {c1}')
    report['fixture740_changes_off']=c0
    report['fixture740_changes_on']=c1
    report['faults']=faults
    (out/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
    print('EDRF_COMPARE_RESULT',json.dumps(report,sort_keys=True))
    assert not faults,faults

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('retail',type=Path);ap.add_argument('out',type=Path)
    a=ap.parse_args();main(a.retail.resolve(),a.out.resolve())
