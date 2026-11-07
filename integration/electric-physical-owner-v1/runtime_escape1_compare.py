#!/usr/bin/env python3
from pathlib import Path
import argparse,json,math,os,re,shutil,signal,subprocess,sys
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integration/electric-owner-audit-v1'))
sys.path.insert(0,str(ROOT/'testlab/scripts'))
import runtime_lab as base
from rc4_assault_camera import World

MAP='escape1'

def kv(line): return dict(re.findall(r'(\w+)=([^\s]+)',line))

def best_summary(lines):
    rows=[]
    for l in lines:
        if l.startswith('EPOA_SUMMARY '):
            d=kv(l)
            rows.append({k:int(float(v)) for k,v in d.items() if re.fullmatch(r'-?\d+(?:\.\d+)?',v)})
    keys=['sceneDlights','promotedDirect','syntheticDirect','shadowGroups','shadowRenderedGroups',
          'shadowSlotsUsed','shadowGroupedExtraDirect','localVolGroups','localVolActiveGroups',
          'localVolGroupedExtraDirect','nearSyntheticPairs']
    return {k:max((r.get(k,0) for r in rows),default=0) for k in keys}

def registry(lines):
    out={}
    for l in lines:
        if not l.startswith('EPOA_REG map='): continue
        d=kv(l)
        try:
            out[int(d['fixture'])]={
              'synthetic':int(d['synthetic']),
              'origin':[float(x) for x in d['origin'].split(',')],
              'rawIntensity':float(d['rawIntensity']),
              'rawColor':[float(x) for x in d['rawColor'].split(',')],
              'resident':int(d.get('resident','0')),
              'actualDlight':int(d.get('actualDlight','-1'))
            }
        except Exception: pass
    return out

def members(lines):
    out=[]
    for l in lines:
        if not l.startswith('EPOA_MEMBER '): continue
        d=kv(l)
        try:
            out.append({
              'dlight':int(d['dlight']),'fixture':int(d['fixture']),'synthetic':int(d['synthetic']),
              'origin':[float(x) for x in d['origin'].split(',')],
              'directRadius':float(d['directRadius']),
              'shadowGroup':int(d['shadowGroup']),'localVolGroup':int(d['localVolGroup']),
              'shadowSlot':int(d['shadowSlot'])
            })
        except Exception: pass
    return out

def owner_members(lines):
    out=[]
    for l in lines:
        if not l.startswith('EPO_V1_MEMBER '): continue
        d=kv(l)
        try: out.append({'fixture':int(d['fixture']),'synthetic':int(d['synthetic']),'owner':int(d['owner'])})
        except Exception: pass
    return out

def run_case(retail,out,owner_on,target,eye,synthetics=None,label='case',capture=True,verbose=False):
    out.mkdir(parents=True,exist_ok=True)
    runtime,main,home=base.assemble_runtime(retail,out,MAP)
    if synthetics:
        hmain=home/'main'; hmain.mkdir(parents=True,exist_ok=True)
        text='# TestLab-only Escape1 EPO companions\n# map id x y z intensity r g b\n'
        for row in synthetics:
            text += '%s %d %.3f %.3f %.3f %.3f %.4f %.4f %.4f\n' % tuple(row)
        (hmain/'static_promote_synthetic_lights.txt').write_text(text)
    setup=[
      'set r_mode -1','set r_customwidth 960','set r_customheight 540','set r_fullscreen 0',
      'set r_renderer rend2','set cl_renderer rend2','set r_hdr 1','set r_postProcess 1',
      'set r_bloom 1','set r_bloomMode 2','set r_ssgi 1','set r_forceSun 1','set r_sunShadows 1',
      'set r_dlightMode 2','set r_dlightShadowMaxLights 3','set r_dlightWorldContainment 2',
      'set r_staticPromote 1','set r_staticPromoteAutoMapLights 1','set r_staticPromoteMaxLights 32',
      'set r_staticPromoteUnifiedResidency 1','set r_volumetricLocal 1','set r_volumetricLocalMode 5',
      'set r_volumetricFire 1','set r_volumetricSun 1',
      f'set r_dwElectricPhysicalOwner {1 if owner_on else 0}',
      f'set r_dwElectricPhysicalOwnerDiag {2 if verbose else 0}',
      'set r_dwElectricOwnerAudit 3','set r_dwElectricOwnerAuditIntervalMs 10000',
      'set r_dwElectricOwnerAuditFocus -1','set r_dwElectricOwnerAuditNearRadius 96',
      'set r_externalGLSL 0','set s_initsound 0','set r_swapInterval 0','set fixedtime 100',
      'set con_notifytime -1','set r_autoExposure 0','set r_forceAutoExposure 0'
    ]
    (main/'SETUP.cfg').write_text('\n'.join(setup)+'\n')
    ang=base.angles(eye,target)
    shot=f'epo_v1_escape1_{label}'
    cmd=['set cg_draw2D 0','set cg_drawGun 0','god','notarget','wait 18',
         'proofView '+' '.join(f'{x:.6f}' for x in eye+ang),'wait 42',
         f'echo EPO_V1_ESCAPE1_CASE label={label} owner={1 if owner_on else 0}','wait 5']
    if capture: cmd += [f'screenshot {shot}','wait 3']
    cmd += ['set r_dwElectricOwnerAudit 0','set r_dwElectricPhysicalOwnerDiag 0',
            f'echo EPO_V1_ESCAPE1_DONE label={label}','quit']
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
        try: rc=p.wait(timeout=600)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL); p.wait(); rc=124
    text=''
    for i,p in enumerate(sorted(home.rglob('*console*.log'))):
        shutil.copy2(p,out/f'console-{i}.log'); text+=p.read_text(errors='replace')+'\n'
    lines=[x for x in text.splitlines() if x.startswith(('EPOA_','EPO_V1_'))]
    (out/'EPO.log').write_text('\n'.join(lines)+'\n')
    img=None
    if capture:
        found=list(home.rglob(shot+'.tga'))
        if len(found)==1:
            im=Image.open(found[0]).convert('RGB'); im.save(out/(shot+'.png')); img=np.asarray(im).astype(np.int16)
    assert rc==0 and f'EPO_V1_ESCAPE1_DONE label={label}' in text,(rc,label)
    return {'summary':best_summary(lines),'registry':registry(lines),'members':members(lines),
            'owner_members':owner_members(lines),'image':img,'lines':lines}

def image_diff(a,b):
    assert a is not None and b is not None
    d=np.abs(a-b)
    return {'pixels':int(np.any(d>0,axis=2).sum()),'above2':int(np.any(d>2,axis=2).sum()),
            'mae':float(d.mean()),'max':int(d.max())}

def main(retail,out):
    out.mkdir(parents=True,exist_ok=True)
    data,target=base.target_for(retail,MAP)
    world=World(data)
    eye=base.choose_eyes(world,target,1)[0]

    discovery=run_case(retail,out/'00_discovery_off',False,target,eye,None,'discovery_off',False,False)
    regs=discovery['registry']
    delivered=[]
    for m in discovery['members']:
        r=regs.get(m['fixture'])
        if m['synthetic'] or not r: continue
        delivered.append((math.dist(m['origin'],target),m,r))
    assert delivered,'Escape1 discovery has no delivered real promoted light'
    delivered.sort(key=lambda x:x[0])
    _,target_member,target_reg=delivered[0]

    o=target_member['origin']; inten=target_reg['rawIntensity']; col=target_reg['rawColor']
    syn=[
      [MAP,9301,o[0]+8.0,o[1],o[2],inten,col[0],col[1],col[2]],
      [MAP,9302,o[0]+32.0,o[1],o[2],inten,col[0],col[1],col[2]],
    ]

    native_off=run_case(retail,out/'10_native_off',False,target,eye,None,'native_off',True,False)
    native_on=run_case(retail,out/'11_native_on',True,target,eye,None,'native_on',True,True)
    ctrl_off=run_case(retail,out/'20_controlled_off',False,target,eye,syn,'controlled_off',True,False)
    ctrl_on=run_case(retail,out/'21_controlled_on',True,target,eye,syn,'controlled_on',True,True)

    direct_keys=('sceneDlights','promotedDirect','syntheticDirect')
    topology_keys=('sceneDlights','promotedDirect','syntheticDirect','shadowGroups','shadowRenderedGroups',
                   'shadowSlotsUsed','shadowGroupedExtraDirect','localVolGroups','localVolActiveGroups',
                   'localVolGroupedExtraDirect')
    native_direct_same=all(native_off['summary'][k]==native_on['summary'][k] for k in direct_keys)
    native_topology_same=all(native_off['summary'][k]==native_on['summary'][k] for k in topology_keys)
    controlled_direct_same=all(ctrl_off['summary'][k]==ctrl_on['summary'][k] for k in direct_keys)

    member_by_fixture={x['fixture']:x for x in ctrl_on['members']}
    synthetic_group_map={
      f:{'shadowGroup':member_by_fixture[f]['shadowGroup'],'localVolGroup':member_by_fixture[f]['localVolGroup']}
      for f in (1009301,1009302) if f in member_by_fixture
    }
    groups_linked=all(
      f in member_by_fixture and
      member_by_fixture[f]['shadowGroup']==target_member['fixture'] and
      member_by_fixture[f]['localVolGroup']==target_member['fixture']
      for f in (1009301,1009302)
    )

    report={
      'map':MAP,'target':target,'eye':eye,'target_fixture':target_member,'synthetics':syn,
      'native_off':native_off['summary'],'native_on':native_on['summary'],
      'controlled_off':ctrl_off['summary'],'controlled_on':ctrl_on['summary'],
      'native_direct_same':native_direct_same,'native_topology_same':native_topology_same,
      'controlled_direct_same':controlled_direct_same,
      'native_pixel_diff':image_diff(native_off['image'],native_on['image']),
      'controlled_pixel_diff':image_diff(ctrl_off['image'],ctrl_on['image']),
      'synthetic_group_map':synthetic_group_map,'synthetic_groups_linked':groups_linked,
      'shadow_groups_saved':ctrl_off['summary']['shadowGroups']-ctrl_on['summary']['shadowGroups'],
      'shadow_slots_saved':ctrl_off['summary']['shadowSlotsUsed']-ctrl_on['summary']['shadowSlotsUsed'],
      'localvol_groups_saved':ctrl_off['summary']['localVolGroups']-ctrl_on['summary']['localVolGroups'],
      'localvol_active_saved':ctrl_off['summary']['localVolActiveGroups']-ctrl_on['summary']['localVolActiveGroups'],
    }
    faults=[]
    if not native_direct_same: faults.append('native Direct counts changed')
    if not native_topology_same: faults.append('native topology changed without synthetic companions')
    # Mesa separate-process temporal noise is tolerated only at the same conservative envelope used by Factory lab.
    if report['native_pixel_diff']['mae']>0.10 or report['native_pixel_diff']['above2']>5200 or report['native_pixel_diff']['max']>32:
        faults.append('native visual drift exceeds Mesa stochastic envelope')
    if not controlled_direct_same: faults.append('controlled Direct counts changed')
    if report['shadow_groups_saved']<1: faults.append('no Escape1 shadow-owner reduction')
    if report['localvol_groups_saved']<1: faults.append('no Escape1 LocalVol-owner reduction')
    if ctrl_on['summary']['shadowSlotsUsed']>ctrl_off['summary']['shadowSlotsUsed']: faults.append('Escape1 shadow slots increased')
    if ctrl_on['summary']['localVolActiveGroups']>ctrl_off['summary']['localVolActiveGroups']: faults.append('Escape1 active LocalVol increased')
    if not groups_linked: faults.append('Escape1 synthetic companions not linked to physical owner groups')
    report['faults']=faults
    (out/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
    print('EPO_V1_ESCAPE1_RUNTIME_RESULT',json.dumps(report,sort_keys=True))
    assert not faults,faults

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('retail',type=Path); ap.add_argument('out',type=Path)
    a=ap.parse_args(); main(a.retail.resolve(),a.out.resolve())
