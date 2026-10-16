#!/usr/bin/env python3
from pathlib import Path
import json,math,os,shutil,signal,subprocess,sys,time,zipfile

BLOOM_ART=12004010089
TREE='bb1432b459a4daf72a324f3fb477744bdb51fd4a'
CV=[('r_bloom','1'),('r_bloomMode','2'),('r_bloomThreshold','1.20'),('r_bloomStrength','0.65'),('r_bloomRadius','1.50'),('r_bloomBlurPasses','1'),('r_bloomPyramidRadius','1.35'),('r_bloomPyramidNearWeight','0.35'),('r_bloomPyramidMidWeight','0.55'),('r_bloomPyramidFarWeight','0.90')]
TARGETS={
'crypt1':[
 ('crypt1_spawn_dlight',[-152.,1668.,636.]),
 ('crypt1_spawn_lamp',[-132.,1842.,516.]),
 ('crypt1_spawn_second_dlight',[388.,1668.,420.])],
'escape1':[
 ('escape1_guard_furnace',[-1226.,602.,-64.]),
 ('escape1_guard_lamp',[-1076.,1172.,96.]),
 ('escape1_doctor_tesla_dlight',[328.,448.,-532.])],
'assault':[
 ('assault_spawn_cagelight',[4660.,7136.,1249.]),
 ('assault_burning_truck',[1559.,1068.,94.]),
 ('assault_firetrail',[5816.,2104.,264.])]}
DIAG=[('r_bloomThreshold','0.35'),('r_bloomStrength','2.50'),('r_bloomRadius','3.00'),('r_bloomBlurPasses','3'),('r_bloomPyramidRadius','2.60'),('r_bloomPyramidNearWeight','0.80'),('r_bloomPyramidMidWeight','1.20'),('r_bloomPyramidFarWeight','1.60')]

ESC=[[420.,468.,-250.],[260.,500.,-245.],[80.,520.,-230.],[-120.,540.,-190.],[-360.,560.,-140.],[-620.,580.,-95.],[-840.,595.,-55.],[-1020.,602.,-35.]]
CRYPT=[[-192.,1664.,472.],[-120.,1664.,474.],[-40.,1664.,474.],[40.,1664.,470.],[130.,1665.,462.],[220.,1666.,452.],[310.,1667.,438.],[390.,1668.,425.]]

def sh(cmd,**kw): print('+',' '.join(map(str,cmd)),flush=True);return subprocess.run(cmd,check=True,**kw)

def source():
    root=Path('bloom-proof-source');shutil.rmtree(root,ignore_errors=True);root.mkdir()
    with open('bloom.zip','wb') as f: subprocess.run(['gh','api',f'repos/{os.environ["GITHUB_REPOSITORY"]}/actions/artifacts/{BLOOM_ART}/zip'],stdout=f,check=True)
    sh(['unzip','-q','bloom.zip','-d','bloom'])
    tar=Path('bloom/DarkWolf-v446-RC4-BloomV2-Production-Win64-SP-source.tar.gz');sh(['tar','-xzf',str(tar),'-C',str(root)])
    sh(['git','-C',str(root),'init','-q']);sh(['git','-C',str(root),'add','.'])
    assert subprocess.check_output(['git','-C',str(root),'write-tree'],text=True).strip()==TREE
    return root

def instrument(root):
    sys.path.insert(0,str(Path('testlab/scripts').resolve()))
    import rc4_requested_views as d
    d.instrument(root)
    p=root/'SP/code/cgame/cg_view.c';s=p.read_text()
    old='"r_ssgi","r_volumetricSun","r_volumetricLocal","r_volumetricFire","r_ext_framebuffer_multisample","r_forceSun","r_ssgiStrength","r_volumetricSunStrength","r_volumetricLocalStrength","cg_drawGun"'
    new=old+',"r_bloom","r_bloomMode","r_bloomThreshold","r_bloomStrength","r_bloomRadius","r_bloomBlurPasses","r_bloomPyramidRadius","r_bloomPyramidNearWeight","r_bloomPyramidMidWeight","r_bloomPyramidFarWeight"'
    assert s.count(old)==1;p.write_text(s.replace(old,new))
    p=root/'SP/code/client/cl_main.c';s=p.read_text()
    old='if( !clc.demoplaying )\n\t{\n\t\tCom_Printf( "The video command can only be used when playing back demos\\n" );\n\t\treturn;\n\t}'
    new='if( !clc.demoplaying && !Cvar_VariableIntegerValue("dw_proofAutomation") )\n\t{\n\t\tCom_Printf( "The video command can only be used when playing back demos\\n" );\n\t\treturn;\n\t}'
    assert s.count(old)==1;p.write_text(s.replace(old,new))
    sh(['git','-C',str(root),'diff','--check'])

def build(root,out):
    log=out/'build-bloom-runtime.log'
    with log.open('w') as f:
        r=subprocess.run(['make','-C',str(root/'SP'),'-j2','release','VERSION=1.51d-SP_DarkWolf-v4.4.6-RC4-BloomV2-Proof','BUILD_CLIENT=1','BUILD_SERVER=0','BUILD_GAME_SO=1','BUILD_GAME_QVM=0','BUILD_BASEGAME=1','BUILD_RENDERER_REND2=1','USE_RENDERER_DLOPEN=1'],stdout=f,stderr=subprocess.STDOUT)
    if r.returncode: print(log.read_text(errors='replace')[-10000:]);raise SystemExit(r.returncode)
    return root/'SP/build/release-linux-x86_64'

def retail_bsp(retail,name):
    key=f'maps/{name}.bsp'
    for pk3 in sorted(retail.glob('*.pk3')):
        with zipfile.ZipFile(pk3) as z:
            for n in z.namelist():
                if n.lower()==key:return z.read(n)
    raise RuntimeError(key)

def camera(retail,mapname,target):
    from rc4_assault_camera import World
    w=World(retail_bsp(retail,mapname));best=None
    for r in (128.,176.,224.,288.):
      for dz in (-48.,0.,48.,96.):
       for deg in range(0,360,30):
        a=math.radians(deg);e=[target[0]+math.cos(a)*r,target[1]+math.sin(a)*r,target[2]+dz]
        if w.solid(e):continue
        d=[target[i]-e[i] for i in range(3)];ang=[-math.degrees(math.atan2(d[2],max(1e-6,math.hypot(d[0],d[1])))),math.degrees(math.atan2(d[1],d[0]))%360,0.]
        cand=(r+abs(dz)*.2,e,ang)
        if best is None or cand[0]<best[0]:best=cand
    if best:return best[1],best[2]
    e=[target[0]+192,target[1],target[2]+24];d=[target[i]-e[i] for i in range(3)]
    return e,[-math.degrees(math.atan2(d[2],max(1e-6,math.hypot(d[0],d[1])))),math.degrees(math.atan2(d[1],d[0]))%360,0.]

def runtime(build,retail,release):
    rt=Path('bloom-runtime').resolve();shutil.rmtree(rt,ignore_errors=True);main=rt/'main';main.mkdir(parents=True)
    for p in build.iterdir():
        if p.is_file():shutil.copy2(p,rt/p.name)
    for p in (build/'main').glob('*.so'):shutil.copy2(p,main/p.name)
    for p in retail.glob('*.pk3'):(main/p.name.lower()).symlink_to(p.resolve())
    for n in ('PRODUCTION_HIGH_QUALITY.cfg','UNIFIED_PRODUCTION.cfg','darkwolf_ignition_rc_v0_6.pk3'):
        h=list(release.rglob(n))
        if h:shutil.copy2(h[0],main/n)
    cfg=['exec PRODUCTION_HIGH_QUALITY.cfg','set r_mode -1','set r_customwidth 1280','set r_customheight 720','set r_fullscreen 0','set r_renderer rend2','set cl_renderer rend2','set r_hdr 1','set r_postProcess 1','set r_toneMap 1','set r_ssgi 1','set r_volumetricSun 1','set r_volumetricLocal 1','set r_volumetricFire 1','set r_swapInterval 0','set s_initsound 0','set cg_draw2D 0','set cg_drawGun 1','set con_notifytime -1','set fixedtime 100']+[f'set {k} {v}' for k,v in CV]
    (main/'BLOOM.cfg').write_text('\n'.join(cfg)+'\n');return rt,main

def env():
    e={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ('TOKEN','SECRET','PASSWORD','CREDENTIAL'))};e['LIBGL_ALWAYS_SOFTWARE']='1';e['LP_NUM_THREADS']='2';return e

def game(rt,home,mapname,scenario,out,timeout=180):
    home.mkdir(parents=True,exist_ok=True);exe=next(p for p in rt.iterdir() if p.name.lower().startswith('iowolfsp'));exe.chmod(0o755)
    cmd=['xvfb-run','-a',str(exe),'+safe','+set','fs_basepath',str(rt),'+set','fs_homepath',str(home),'+set','com_introplayed','1','+set','com_recommendedSet','1','+set','logfile','2','+set','dw_proofAutomation','1','+set','r_renderer','rend2','+set','cl_renderer','rend2','+exec','BLOOM.cfg','+vid_restart','+set','dw_proofScenario',scenario,'+spdevmap',mapname]
    with out.open('w') as f:
        p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,env=env(),start_new_session=True)
        try:return p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait();return 124

def logs(home,out,prefix):
    t=[]
    for i,p in enumerate(home.rglob('*console*.log')):shutil.copy2(p,out/f'{prefix}-console-{i}.log');t.append(p.read_text(errors='replace'))
    return '\n'.join(t)

def lerp(points,n=210):
    o=[];m=len(points)-1
    for i in range(n):
        u=i/(n-1)*m;j=min(m-1,int(u));t=u-j;p=[points[j][k]*(1-t)+points[j+1][k]*t for k in range(3)];q=points[min(j+1,m)];d=[q[k]-p[k] for k in range(3)]
        y=math.degrees(math.atan2(d[1],d[0]))%360;pi=-math.degrees(math.atan2(d[2],max(1e-6,math.hypot(d[0],d[1]))));o.append((p,[pi,y,0.]))
    return o

def main():
    _,retail_s,release_s,out_s,variant=sys.argv[1:6]
    out=Path(out_s);out.mkdir(parents=True,exist_ok=True)
    if variant!='candidate':
        (out/'base-skip.json').write_text(json.dumps({'status':'skipped','reason':'A/B proof runs on Bloom candidate only'},indent=2)+'\n')
        return
    retail=Path(retail_s);release=Path(release_s)
    root=source();instrument(root);b=build(root,out);rt,main=runtime(b,retail,release)
    from PIL import Image,ImageDraw,ImageFont

    # Diagnostic preset: deliberately stronger than production to make the difference obvious.
    diag=dict(DIAG)
    report={
      'mode':'Bloom OFF/ON A/B EXAGGERATED diagnostic',
      'source_tree':TREE,
      'build_run':38798189322,
      'production_bloom':dict(CV),
      'diagnostic_bloom_on':{'r_bloom':'1','r_bloomMode':'2',**diag},
      'diagnostic_bloom_off':{'r_bloom':'0','r_bloomMode':'2',**diag},
      'pairs':[]
    }

    pair_images=[]
    pair_no=0
    for mapname,targets in TARGETS.items():
        commands=['set con_notifytime -1','set cg_draw2D 0','set cg_drawGun 1','set cg_bobup 0','set cg_bobpitch 0','set cg_bobroll 0','set r_autoExposure 0','set r_forceAutoExposure 0','set r_forceSunPause 1','god','notarget','give all','wait 20']
        meta=[]
        for local_idx,(name,target) in enumerate(targets,1):
            pair_no+=1
            eye,ang=camera(retail,mapname,target)
            # Apply amplified diagnostic parameters identically to both frames.
            commands += [f'set {k} {v}' for k,v in DIAG]
            anchor_shot=pair_no*2-1
            check_shot=pair_no*2
            commands += ['set r_bloomMode 2','set r_bloom 0','set dw_proofFreeze 0',
                         'proofView '+' '.join(f'{x:.6f}' for x in eye+ang),
                         'wait 24',f'set dw_proofShot {anchor_shot}','wait 2',
                         'set dw_proofFreeze 1','wait 2',
                         f'echo BLOOM_AB_CAPTURE {name} OFF',f'screenshot {name}_OFF','wait 2',
                         'set r_bloom 1','wait 5',
                         f'echo BLOOM_AB_CAPTURE {name} ON',f'screenshot {name}_ON','wait 2',
                         'set dw_proofFreeze 0','wait 1',f'set dw_proofShot {check_shot}','wait 2']
            meta.append((name,target,eye,ang,pair_no))
        commands += ['set dw_proofFreeze 0','echo BLOOM_AB_MAP_COMPLETE','quit']
        scen=f'BLOOM_AB_{mapname.upper()}.cfg'
        (main/scen).write_text('\n'.join(commands)+'\n')
        shutil.copy2(main/scen,out/scen)
        home=rt/f'home-ab-{mapname}'
        rc=game(rt,home,mapname,scen,out/f'{mapname}-ab.log',timeout=480)
        txt=logs(home,out,mapname+'-ab')
        assert rc==0 and 'BLOOM_AB_MAP_COMPLETE' in txt,(mapname,rc)
        import re
        view_re=re.compile(r'PROOF_VIEW shot=(\d+) time=\d+ eye=([^ ]+) forward=([^ ]+)')
        proof_views={int(m.group(1)):(m.group(2),m.group(3)) for m in view_re.finditer(txt)}
        cvar_re=re.compile(r'PROOF_CVAR shot=(\d+) name=([^ ]+) value=([^\r\n]+)')
        proof_cvars={}
        for m in cvar_re.finditer(txt):
            proof_cvars.setdefault(int(m.group(1)),{})[m.group(2)]=m.group(3).strip()
        for name,target,eye,ang,pn in meta:
            files={}
            for state in ('OFF','ON'):
                hits=list(home.rglob(f'{name}_{state}.tga'))
                assert len(hits)==1,(name,state,hits)
                dest=out/f'{name}_{state}.png'
                Image.open(hits[0]).convert('RGB').save(dest)
                files[state]=dest.name
            # Strict A/B acceptance: bracket the frozen OFF/ON capture by two runtime camera probes.
            # CGame does not advance while frozen, so no PROOF_VIEW event is expected inside the frozen interval.
            anchor_shot,check_shot=pn*2-1,pn*2
            assert anchor_shot in proof_views and check_shot in proof_views,(mapname,name,'missing bracket PROOF_VIEW',proof_views)
            assert proof_views[anchor_shot]==proof_views[check_shot],(mapname,name,'camera drift across frozen A/B',proof_views[anchor_shot],proof_views[check_shot])
            oc=proof_cvars.get(anchor_shot,{}); nc=proof_cvars.get(check_shot,{})
            assert oc.get('r_bloom')=='0',(mapname,name,'pre-freeze r_bloom',oc.get('r_bloom'))
            assert nc.get('r_bloom')=='1',(mapname,name,'post-freeze r_bloom',nc.get('r_bloom'))
            assert oc.get('r_bloomMode')=='2' and nc.get('r_bloomMode')=='2'
            for k,v in DIAG:
                assert oc.get(k)==v and nc.get(k)==v,(mapname,name,k,oc.get(k),nc.get(k),v)
            for k in ('r_ssgi','r_volumetricSun','r_volumetricLocal','r_volumetricFire','r_forceSun'):
                assert oc.get(k)==nc.get(k),(mapname,name,'non-bloom cvar drift',k,oc.get(k),nc.get(k))
            report['pairs'].append({'pair':pn,'map':mapname,'name':name,'target':target,'camera_origin':eye,'camera_angles':ang,'proof_eye_forward':proof_views[anchor_shot],'snapshot_frozen_between_off_on':True,'off':files['OFF'],'on':files['ON']})
            pair_images.append((pn,mapname,name,out/files['OFF'],out/files['ON']))

    # Build a literal side-by-side contact sheet: OFF left, ON right.
    thumb_w,thumb_h=640,360
    header=54
    canvas=Image.new('RGB',(thumb_w*2, (thumb_h+header)*len(pair_images)),(24,24,24))
    draw=ImageDraw.Draw(canvas)
    for row,(pn,mapname,name,offp,onp) in enumerate(pair_images):
        y=row*(thumb_h+header)
        draw.text((10,y+8),f'Pair {pn} | {mapname} | {name} | OFF',fill='white')
        draw.text((thumb_w+10,y+8),f'Pair {pn} | {mapname} | {name} | ON (EXAGGERATED BLOOM)',fill='white')
        off=Image.open(offp).convert('RGB');on=Image.open(onp).convert('RGB')
        off.thumbnail((thumb_w,thumb_h));on.thumbnail((thumb_w,thumb_h))
        canvas.paste(off,(0,y+header));canvas.paste(on,(thumb_w,y+header))
    canvas.save(out/'BLOOM_AB_CONTACT_SHEET_OFF_ON.png')

    (out/'BLOOM_AB_RUNTIME_PROOF.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()
