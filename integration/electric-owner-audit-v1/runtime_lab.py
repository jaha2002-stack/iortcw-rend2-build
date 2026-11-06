#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json,math,os,re,shutil,signal,struct,subprocess,tempfile,zipfile
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'testlab/scripts'))
from rc4_assault_camera import World

SURFACE_TARGETS={
    'escape1':13323,
    'boss1':7234,
    'crypt1':11827,
}
FIXED_TARGETS={
    'church':[-241.0,-178.0,144.0],
    'factory':[-448.0,-1055.0,-178.0],
}

def load_bsp(retail,mapname):
    wanted=f'maps/{mapname}.bsp'
    for p in sorted(retail.iterdir()):
        if p.suffix.lower()!='.pk3': continue
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                if n.lower()==wanted:
                    return z.read(n)
    raise RuntimeError('map missing '+mapname)

def surface_center(data,index):
    def lump(i):
        o,n=struct.unpack_from('<ii',data,8+8*i)
        return data[o:o+n]
    verts=list(struct.iter_unpack('<10f4B',lump(10)))
    surfs=list(struct.iter_unpack('<12i12f2i',lump(13)))
    s=surfs[index]
    vv=verts[s[3]:s[3]+s[4]]
    if not vv: raise RuntimeError('surface has no verts')
    return [sum(v[k] for v in vv)/len(vv) for k in range(3)]

def target_for(retail,mapname):
    data=load_bsp(retail,mapname)
    if mapname in SURFACE_TARGETS:
        target=surface_center(data,SURFACE_TARGETS[mapname])
    else:
        target=list(FIXED_TARGETS[mapname])
    return data,target

def angles(eye,target):
    d=[target[k]-eye[k] for k in range(3)]
    return [-math.degrees(math.atan2(d[2],math.hypot(d[0],d[1]))),
            math.degrees(math.atan2(d[1],d[0]))%360,0.0]

def choose_eyes(world,target,count=4):
    cand=[]
    for dist in (96,144,192,256,320,400):
        for step in range(24):
            a=step*2*math.pi/24
            for dz in (-64,-40,-16,16,40,64):
                eye=[target[0]+dist*math.cos(a),target[1]+dist*math.sin(a),target[2]+dz]
                if world.solid(eye): continue
                if any(world.solid([eye[k]+o[k] for k in range(3)]) for o in ((8,0,0),(-8,0,0),(0,8,0),(0,-8,0),(0,0,-16))):
                    continue
                hit=world.trace(eye,target)
                frac=hit.get('fraction',1.0) if hit else 1.0
                if frac<0.96: continue
                cand.append((dist+abs(dz)*0.1+step*0.001,eye))
    if not cand:
        raise RuntimeError('no valid camera '+str(target))
    cand.sort(key=lambda x:x[0])
    chosen=[]
    for _,eye in cand:
        if all(math.dist(eye,x)>90 for x in chosen):
            chosen.append(eye)
        if len(chosen)>=count: break
    if not chosen: chosen=[cand[0][1]]
    return chosen

def assemble_runtime(retail,out,mapname):
    runtime=Path(tempfile.mkdtemp(prefix='epoa-'+mapname+'-',dir=out.parent)).resolve()
    main=runtime/'main'; home=runtime/'home'
    main.mkdir(); home.mkdir()
    build=Path('source/SP/build/release-linux-x86_64')
    for p in build.iterdir():
        if p.is_file(): shutil.copy2(p,runtime/p.name)
    for p in (build/'main').glob('*.so'): shutil.copy2(p,main/p.name)
    for p in retail.iterdir():
        if p.suffix.lower()=='.pk3':
            (main/p.name.lower()).symlink_to(p.resolve())
    return runtime,main,home

def run_once(retail,out,mapname,variant,synthetic_rows=None):
    out.mkdir(parents=True,exist_ok=True)
    data,target=target_for(retail,mapname)
    world=World(data)
    eyes=choose_eyes(world,target,4)
    runtime,main,home=assemble_runtime(retail,out,mapname)

    if synthetic_rows:
        text='# TestLab-only synthetic companions. Never packaged.\n# map id x y z intensity r g b\n'
        for row in synthetic_rows:
            text += '%s %d %.3f %.3f %.3f %.3f %.4f %.4f %.4f\n' % tuple(row)
        (home/'main').mkdir(parents=True,exist_ok=True)
        (home/'main'/'static_promote_synthetic_lights.txt').write_text(text)

    setup=[
      'set r_mode -1','set r_customwidth 960','set r_customheight 540','set r_fullscreen 0',
      'set r_renderer rend2','set cl_renderer rend2','set r_hdr 1','set r_postProcess 1',
      'set r_bloom 1','set r_bloomMode 2','set r_ssgi 1','set r_forceSun 1','set r_sunShadows 1',
      'set r_dlightMode 2','set r_dlightShadowMaxLights 3','set r_dlightWorldContainment 2',
      'set r_staticPromote 1','set r_staticPromoteAutoMapLights 1','set r_staticPromoteMaxLights 32',
      'set r_staticPromoteUnifiedResidency 1','set r_volumetricLocal 1','set r_volumetricLocalMode 5',
      'set r_volumetricFire 1','set r_volumetricSun 1',
      'set r_dwElectricOwnerAudit 3','set r_dwElectricOwnerAuditIntervalMs 500',
      'set r_dwElectricOwnerAuditFocus -1','set r_dwElectricOwnerAuditNearRadius 96',
      'set r_staticPromoteUnifiedDiag 1','set r_externalGLSL 0','set s_initsound 0',
      'set r_swapInterval 0','set fixedtime 100','set con_notifytime -1'
    ]
    (main/'SETUP.cfg').write_text('\n'.join(setup)+'\n')

    cmd=['set cg_draw2D 0','set cg_drawGun 0','god','notarget','wait 30']
    for idx,eye in enumerate(eyes):
        ang=angles(eye,target)
        cmd += [
          'set dw_proofFreeze 0',
          'proofView '+' '.join(f'{x:.6f}' for x in eye+ang),
          'wait 45',
          f'echo EPOA_LAB_VIEW map={mapname} variant={variant} index={idx}',
          'wait 10'
        ]
    cmd += [f'echo EPOA_LAB_DONE map={mapname} variant={variant}','quit']
    (main/'TEST.cfg').write_text('\n'.join(cmd)+'\n')

    exe=next(p for p in runtime.iterdir() if p.name.startswith('iowolfsp') and p.is_file())
    exe.chmod(0o755)
    args=['xvfb-run','-a','-s','-screen 0 1280x720x24',str(exe),'+safe',
          '+set','fs_basepath',str(runtime),'+set','fs_homepath',str(home),
          '+set','com_introplayed','1','+set','com_recommendedSet','1','+set','logfile','2',
          '+set','dw_proofAutomation','1','+set','r_renderer','rend2','+set','cl_renderer','rend2',
          '+exec','SETUP.cfg','+vid_restart','+set','dw_proofScenario','TEST.cfg','+spdevmap',mapname]
    env={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ('TOKEN','SECRET','PASSWORD','CREDENTIAL'))}
    env.update(LIBGL_ALWAYS_SOFTWARE='1',LP_NUM_THREADS='2',SDL_AUDIODRIVER='dummy')
    with (out/'stdout.log').open('w') as log:
        p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        try: rc=p.wait(timeout=900)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL); p.wait(); rc=124

    texts=[]
    for i,p in enumerate(sorted(home.rglob('*console*.log'))):
        shutil.copy2(p,out/f'console-{i}.log')
        texts.append(p.read_text(errors='replace'))
    text='\n'.join(texts)
    epoa=[l for l in text.splitlines() if l.startswith('EPOA_')]
    (out/'EPOA.log').write_text('\n'.join(epoa)+'\n')
    assert rc==0 and f'EPOA_LAB_DONE map={mapname} variant={variant}' in text,(rc,mapname,variant)
    assert any(l.startswith('EPOA_SUMMARY ') for l in epoa),(mapname,variant,'no summary')
    return parse(epoa,mapname,variant,target,eyes,data)

def kv(line):
    return dict(re.findall(r'(\w+)=([^\s]+)',line))

def parse_num(v):
    try:
        if any(x in v for x in '.eE'): return float(v)
        return int(v)
    except Exception:
        return v

def parse(lines,mapname,variant,target,eyes,data):
    summaries=[]; groups=[]; members=[]; near=[]; regs=[]
    for line in lines:
        d={k:parse_num(v) for k,v in kv(line).items()}
        d['_line']=line
        if line.startswith('EPOA_SUMMARY '): summaries.append(d)
        elif line.startswith('EPOA_GROUP '): groups.append(d)
        elif line.startswith('EPOA_MEMBER '): members.append(d)
        elif line.startswith('EPOA_NEAR '): near.append(d)
        elif line.startswith('EPOA_REG map='): regs.append(d)
    unique={}
    for d in near:
        key=(d.get('fixtureA'),d.get('fixtureB'))
        unique[key]=d
    suspicious=[d for d in unique.values() if d.get('currentShadowSame')==0 or d.get('currentLocalVolSame')==0]
    maxv={}
    for key in ('sceneDlights','promotedDirect','syntheticDirect','shadowGroups','shadowRenderedGroups','shadowSlotsUsed',
                'shadowGroupedExtraDirect','localVolGroups','localVolActiveGroups','localVolGroupedExtraDirect','nearSyntheticPairs'):
        vals=[d.get(key) for d in summaries if isinstance(d.get(key),(int,float))]
        maxv[key]=max(vals) if vals else None
    return {
      'map':mapname,'variant':variant,'bsp_sha256':hashlib.sha256(data).hexdigest(),
      'target':target,'eyes':eyes,'summary_max':maxv,
      'summary_samples':len(summaries),'group_samples':len(groups),'member_samples':len(members),
      'unique_near_pairs':list(unique.values()),'suspicious_near_pairs':suspicious,
      'registry_sample':regs[:200],
      'delivered_members':list({int(m.get('fixture')):m for m in members if isinstance(m.get('fixture'),int)}.values()),
    }

def choose_physical(native,mapname,target):
    registry={int(r.get('fixture')):r for r in native.get('registry_sample',[]) if isinstance(r.get('fixture'),int)}
    candidates=[]
    for m in native.get('delivered_members',[]):
        try:
            fixture=int(m.get('fixture'))
            if fixture>=1000000: continue
            o=[float(x) for x in str(m['origin']).split(',')]
            r=registry.get(fixture)
            if not r: continue
            if int(r.get('synthetic',0))!=0: continue
            combined=dict(r)
            combined['deliveredDlight']=m.get('dlight')
            combined['deliveredOrigin']=m.get('origin')
            combined['deliveredRadius']=m.get('directRadius')
            combined['deliveredColor']=m.get('directColor')
            candidates.append((math.dist(o,target),combined,o))
        except Exception:
            continue
    if not candidates: return None
    candidates.sort(key=lambda x:x[0])
    return candidates[0]

def lab(retail,out,mapname):
    out.mkdir(parents=True,exist_ok=True)
    native=run_once(retail,out/'native',mapname,'native')
    chosen=choose_physical(native,mapname,native['target'])
    controlled=None
    if chosen:
        dist,r,o=chosen
        intensity=float(r.get('rawIntensity',60.0))
        color=[float(x) for x in str(r.get('rawColor','1,0.9,0.8')).split(',')]
        rows=[
          [mapname,9001,o[0]+8.0,o[1],o[2],intensity,color[0],color[1],color[2]],
          [mapname,9002,o[0]+32.0,o[1],o[2],intensity,color[0],color[1],color[2]],
        ]
        controlled=run_once(retail,out/'controlled',mapname,'controlled',rows)
    report={'map':mapname,'native':native,'selected_fixture':chosen[1] if chosen else None,
            'selected_fixture_distance_to_target':chosen[0] if chosen else None,'controlled':controlled}
    if controlled:
        a=native['summary_max'];b=controlled['summary_max']
        report['delta']={k:(b.get(k)-a.get(k) if isinstance(a.get(k),(int,float)) and isinstance(b.get(k),(int,float)) else None)
                         for k in b}
    (out/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'map':mapname,'native':native['summary_max'],'selected':report['selected_fixture'],
                      'controlled':controlled['summary_max'] if controlled else None,'delta':report.get('delta'),
                      'controlled_suspicious':len(controlled['suspicious_near_pairs']) if controlled else None},indent=2))
    return report

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('retail',type=Path)
    ap.add_argument('out',type=Path)
    ap.add_argument('map',choices=['escape1','boss1','crypt1','church','factory'])
    a=ap.parse_args()
    lab(a.retail.resolve(),a.out.resolve(),a.map)
