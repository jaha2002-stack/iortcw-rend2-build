#!/usr/bin/env python3
from pathlib import Path
import json,math,os,shutil,signal,subprocess,sys,time,zipfile

BLOOM_ART=12004010089
TREE='bb1432b459a4daf72a324f3fb477744bdb51fd4a'
CV=[('r_bloom','1'),('r_bloomMode','2'),('r_bloomThreshold','1.20'),('r_bloomStrength','0.65'),('r_bloomRadius','1.50'),('r_bloomBlurPasses','1'),('r_bloomPyramidRadius','1.35'),('r_bloomPyramidNearWeight','0.35'),('r_bloomPyramidMidWeight','0.55'),('r_bloomPyramidFarWeight','0.90')]
TARGETS={
'escape1':[('escape1_guard_furnace',[-1226.,602.,-64.]),('escape1_guard_lamp',[-1076.,1172.,96.])],
'crypt1':[('crypt1_spawn_dlight',[-152.,1668.,636.]),('crypt1_spawn_lamp',[-132.,1842.,516.])],
'assault':[('assault_spawn_cagelight',[4660.,7136.,1280.]),('assault_burning_truck',[2127.,3210.,94.])],
'forest':[('forest_cagelight_near_camp',[1728.,-5248.,568.]),('forest_cagelight_mid',[-3514.,-64.,324.])],
'dam':[('dam_xlight_corridor',[-1676.,-2464.,1232.]),('dam_xlight_upper',[-2300.,-1600.,2428.])]}
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
    cfg=['exec PRODUCTION_HIGH_QUALITY.cfg','set r_mode -1','set r_customwidth 1600','set r_customheight 900','set r_fullscreen 0','set r_renderer rend2','set cl_renderer rend2','set r_hdr 1','set r_postProcess 1','set r_toneMap 1','set r_ssgi 1','set r_volumetricSun 1','set r_volumetricLocal 1','set r_volumetricFire 1','set r_swapInterval 0','set s_initsound 0','set cg_draw2D 0','set cg_drawGun 1','set con_notifytime -1','set fixedtime 100']+[f'set {k} {v}' for k,v in CV]
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
    _,retail_s,release_s,out_s,variant=sys.argv[1:6];out=Path(out_s);out.mkdir(parents=True,exist_ok=True)
    if variant!='candidate':(out/'base-skip.json').write_text('{"status":"skipped"}\n');return
    retail=Path(retail_s);release=Path(release_s);sh(['sudo','apt-get','-o','Acquire::Retries=3','install','-y','--no-install-recommends','ffmpeg'])
    root=source();instrument(root);b=build(root,out);rt,main=runtime(b,retail,release)
    report={'bloom':dict(CV),'screenshots_from_run':38839497144,'videos':[],'source_tree':TREE,'build_run':38798189322}
    for mapname,pts in [('escape1',ESC),('crypt1',CRYPT)]:
        seq=['set con_notifytime -1','set r_customwidth 640','set r_customheight 360','set cl_aviFrameRate 20','vid_restart','wait 8','god','notarget','give all','set dw_proofShot 99','wait 3',f'video {mapname}_bloom_v2','wait 2']
        for p,a in lerp(pts):seq+=['proofView '+' '.join(f'{x:.6f}' for x in p+a),'wait 1']
        seq+=['wait 3','stopvideo','echo BLOOM_VIDEO_COMPLETE','wait 2','quit'];sc=f'{mapname}_video.cfg';(main/sc).write_text('\n'.join(seq)+'\n');home=rt/f'home-video-{mapname}';rc=game(rt,home,mapname,sc,out/f'{mapname}-video.log',timeout=420);txt=logs(home,out,mapname+'-video')
        for k,v in CV:assert f'name={k} value={v}' in txt,(mapname,k,v)
        avi=list(home.rglob(f'{mapname}_bloom_v2.avi'));assert len(avi)==1,(mapname,avi)
        mp4=out/f'{mapname}-bloom-v2-runtime.mp4';sh(['ffmpeg','-y','-loglevel','error','-i',str(avi[0]),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(mp4)])
        dur=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(mp4)],text=True).strip())
        assert mp4.stat().st_size>100000 and rc==0 and 'BLOOM_VIDEO_COMPLETE' in txt and 9.5<=dur<=15.5,(mapname,mp4.stat().st_size,rc,dur)
        report['videos'].append({'map':mapname,'file':mp4.name,'seconds':dur,'resolution':'640x360','avi_fps':20})
    (out/'BLOOM_RUNTIME_PROOF.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
