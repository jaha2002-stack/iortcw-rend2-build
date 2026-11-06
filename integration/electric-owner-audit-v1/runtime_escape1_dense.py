#!/usr/bin/env python3
from pathlib import Path
import argparse, json, math, os, re, shutil, signal, subprocess, sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import runtime_lab as base
from rc4_assault_camera import World

MAP='escape1'

def parse_kv(line):
    return dict(re.findall(r'(\w+)=([^\s]+)',line))

def run_game(retail,out,target,mode=3,synthetic_rows=None,label='native',wait_frames=18):
    out.mkdir(parents=True,exist_ok=True)
    data=base.load_bsp(retail,MAP); world=World(data)
    eye=base.choose_eyes(world,target,1)[0]
    runtime,main,home=base.assemble_runtime(retail,out,MAP)
    if synthetic_rows:
        hmain=home/'main';hmain.mkdir(parents=True,exist_ok=True)
        text='# EPOA TestLab-only companions\n# map id x y z intensity r g b\n'
        for row in synthetic_rows:
            text += '%s %d %.3f %.3f %.3f %.3f %.4f %.4f %.4f\n' % tuple(row)
        (hmain/'static_promote_synthetic_lights.txt').write_text(text)
    setup=[
      'set r_mode -1','set r_customwidth 800','set r_customheight 600','set r_fullscreen 0',
      'set r_renderer rend2','set cl_renderer rend2','set r_dlightMode 2','set r_dlightShadowMaxLights 3',
      'set r_dlightWorldContainment 2','set r_staticPromote 1','set r_staticPromoteAutoMapLights 1',
      'set r_staticPromoteMaxLights 32','set r_staticPromoteUnifiedResidency 1',
      'set r_volumetricLocal 1','set r_volumetricLocalMode 5','set r_volumetricFire 1','set r_volumetricSun 1',
      f'set r_dwElectricOwnerAudit {mode}','set r_dwElectricOwnerAuditIntervalMs 10000',
      'set r_dwElectricOwnerAuditFocus -1','set r_dwElectricOwnerAuditNearRadius 96',
      'set r_externalGLSL 0','set s_initsound 0','set r_swapInterval 0','set fixedtime 100','set con_notifytime -1'
    ]
    (main/'SETUP.cfg').write_text('\n'.join(setup)+'\n')
    ang=base.angles(eye,target)
    cmd=[
      'set cg_draw2D 0','set cg_drawGun 0','god','notarget','wait 12',
      'proofView '+' '.join(f'{x:.6f}' for x in eye+ang),
      f'wait {wait_frames}',
      f'echo EPOA_ESCAPE1_DENSE_POINT label={label} target={target[0]:.3f},{target[1]:.3f},{target[2]:.3f}',
      'wait 4','set r_dwElectricOwnerAudit 0','wait 2',
      f'echo EPOA_ESCAPE1_DENSE_DONE label={label}','quit'
    ]
    (main/'TEST.cfg').write_text('\n'.join(cmd)+'\n')
    exe=next(p for p in runtime.iterdir() if p.name.startswith('iowolfsp') and p.is_file());exe.chmod(0o755)
    args=['xvfb-run','-a','-s','-screen 0 1024x768x24',str(exe),'+safe',
      '+set','fs_basepath',str(runtime),'+set','fs_homepath',str(home),
      '+set','com_introplayed','1','+set','com_recommendedSet','1','+set','logfile','2',
      '+set','dw_proofAutomation','1','+set','r_renderer','rend2','+set','cl_renderer','rend2',
      '+exec','SETUP.cfg','+vid_restart','+set','dw_proofScenario','TEST.cfg','+spdevmap',MAP]
    env={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ('TOKEN','SECRET','PASSWORD','CREDENTIAL'))}
    env.update(LIBGL_ALWAYS_SOFTWARE='1',SDL_AUDIODRIVER='dummy',LP_NUM_THREADS='2')
    with (out/'stdout.log').open('w') as log:
        p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        try: rc=p.wait(timeout=480)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL);p.wait();rc=124
    text=''
    for p in sorted(home.rglob('*console*.log')):
        text+=p.read_text(errors='replace')+'\n'
    lines=[x for x in text.splitlines() if x.startswith('EPOA_')]
    (out/'EPOA.log').write_text('\n'.join(lines)+'\n')
    assert rc==0 and f'EPOA_ESCAPE1_DENSE_DONE label={label}' in text,(rc,label)
    return lines,eye

def registry(lines):
    out=[]
    for l in lines:
        if not l.startswith('EPOA_REG map='): continue
        d=parse_kv(l)
        if int(d.get('synthetic','0')): continue
        o=[float(x) for x in d['origin'].split(',')]
        out.append({'fixture':int(d['fixture']),'origin':o,'rawIntensity':float(d['rawIntensity']),
                    'rawColor':[float(x) for x in d['rawColor'].split(',')],'line':l})
    return out

def clusters(rows,link=260.0):
    n=len(rows);seen=set();out=[]
    for s in range(n):
        if s in seen:continue
        q=[s];seen.add(s);idx=[]
        while q:
            i=q.pop(0);idx.append(i)
            for j in range(n):
                if j in seen:continue
                if math.dist(rows[i]['origin'],rows[j]['origin'])<=link:
                    seen.add(j);q.append(j)
        members=[rows[i] for i in idx]
        center=[sum(x['origin'][k] for x in members)/len(members) for k in range(3)]
        out.append({'count':len(members),'center':center,'fixtures':[x['fixture'] for x in members],
                    'members':members})
    out.sort(key=lambda x:(-x['count'],x['center'][0],x['center'][1]))
    return out

def summaries(lines):
    out=[]
    for l in lines:
        if l.startswith('EPOA_SUMMARY '):
            d=parse_kv(l); d={k:(float(v) if '.' in v else int(v)) if re.fullmatch(r'-?\d+(?:\.\d+)?',v) else v for k,v in d.items()}
            out.append(d)
    return out

def members(lines):
    out=[]
    for l in lines:
        if not l.startswith('EPOA_MEMBER '):continue
        d=parse_kv(l)
        try:
            out.append({'dlight':int(d['dlight']),'fixture':int(d['fixture']),'synthetic':int(d['synthetic']),
                        'origin':[float(x) for x in d['origin'].split(',')],
                        'directRadius':float(d['directRadius']),'shadowGroup':int(d['shadowGroup']),
                        'localVolGroup':int(d['localVolGroup']),'shadowSlot':int(d['shadowSlot'])})
        except Exception:pass
    return out

def near(lines):
    return [parse_kv(l) for l in lines if l.startswith('EPOA_NEAR ')]

def best_summary(lines):
    ss=summaries(lines)
    keys=['sceneDlights','promotedDirect','syntheticDirect','shadowGroups','shadowRenderedGroups',
          'shadowSlotsUsed','shadowGroupedExtraDirect','localVolGroups','localVolActiveGroups',
          'localVolGroupedExtraDirect','nearSyntheticPairs']
    return {k:max(int(float(x.get(k,0))) for x in ss) if ss else 0 for k in keys}

def choose_delivered(cluster,mem):
    byid={x['fixture']:x for x in cluster['members']}
    cand=[]
    for m in mem:
        if m['synthetic'] or m['fixture'] not in byid:continue
        cand.append((math.dist(m['origin'],cluster['center']),m,byid[m['fixture']]))
    cand.sort(key=lambda x:x[0])
    return cand[0] if cand else None

def main(retail,out):
    out.mkdir(parents=True,exist_ok=True)
    # discovery target is the historical Escape1 ceiling lamp; mode 3 prints full persistent registry once.
    data,t0=base.target_for(retail,MAP)
    discovery,eye0=run_game(retail,out/'00_discovery',t0,mode=3,label='discovery',wait_frames=16)
    regs=registry(discovery)
    cls=clusters(regs,260.0)
    candidates=[c for c in cls if c['count']>=4]
    # User-reported room is expected to be one of the densest 4+ fixture clusters.
    selected=candidates[:4]
    if not selected: selected=cls[:4]
    scan=[]
    for i,c in enumerate(selected):
        lines,eye=run_game(retail,out/f'{i+1:02d}_cluster_native',c['center'],mode=3,label=f'cluster{i}',wait_frames=18)
        scan.append({'cluster':c,'eye':eye,'summary':best_summary(lines),'members':members(lines),'near':near(lines),
                     'log':str((out/f'{i+1:02d}_cluster_native'/'EPOA.log').relative_to(out))})
    # Prefer a cluster with 5-8 fixtures (matches the user-described guard room), otherwise densest.
    guard=next((x for x in scan if 5<=x['cluster']['count']<=8),scan[0])
    chosen=choose_delivered(guard['cluster'],guard['members'])
    controlled=None
    if chosen:
        _,m,r=chosen
        o=m['origin']; inten=r['rawIntensity']; col=r['rawColor']
        syn=[
          [MAP,9101,o[0]+8,o[1],o[2],inten,col[0],col[1],col[2]],
          [MAP,9102,o[0]+32,o[1],o[2],inten,col[0],col[1],col[2]],
        ]
        lines,eye=run_game(retail,out/'90_guard_controlled',guard['cluster']['center'],mode=3,synthetic_rows=syn,label='guard_controlled',wait_frames=18)
        controlled={'summary':best_summary(lines),'members':members(lines),'near':near(lines),'synthetics':syn,'eye':eye}
    report={
      'map':MAP,'registry_non_synthetic':len(regs),'cluster_link_units':260.0,
      'top_clusters':[{'count':c['count'],'center':c['center'],'fixtures':c['fixtures']} for c in cls[:12]],
      'scanned_clusters':[{k:v for k,v in x.items() if k not in ('cluster','members','near')} |
                          {'count':x['cluster']['count'],'center':x['cluster']['center'],
                           'fixtures':x['cluster']['fixtures'],'member_count':len(x['members']),
                           'near_pairs':len(x['near'])} for x in scan],
      'guard_cluster':{'count':guard['cluster']['count'],'center':guard['cluster']['center'],
                       'fixtures':guard['cluster']['fixtures'],'native_summary':guard['summary']},
      'selected_delivered_fixture': chosen[1] if chosen else None,
      'selected_registry_fixture': chosen[2] if chosen else None,
      'controlled':controlled,
    }
    if controlled:
        a=guard['summary'];b=controlled['summary']
        report['delta']={k:b[k]-a[k] for k in a}
    (out/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
    concise={
      'registry_non_synthetic':len(regs),
      'top_clusters':report['top_clusters'][:6],
      'guard_cluster':report['guard_cluster'],
      'selected_fixture':report['selected_delivered_fixture'],
      'controlled_summary':controlled['summary'] if controlled else None,
      'delta':report.get('delta'),
      'controlled_near':controlled['near'] if controlled else None,
    }
    (out/'CONCISE.json').write_text(json.dumps(concise,indent=2)+'\n')
    print('EPOA_ESCAPE1_DENSE_RESULT',json.dumps(concise,sort_keys=True))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('retail',type=Path);ap.add_argument('out',type=Path)
    a=ap.parse_args();main(a.retail.resolve(),a.out.resolve())
