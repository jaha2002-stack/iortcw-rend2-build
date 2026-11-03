#!/usr/bin/env python3
"""Real Crypt1/Crypt2 coverage of material families plus exact V1 shadow repro.
The one bypass and audit command exist only in this disposable native TestLab.
Production DLL/source are archived BEFORE instrumentation; retail data stay local.
"""
import argparse, hashlib, importlib.util, json, math, os, re, shutil, signal, struct, subprocess, sys, tempfile, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'testlab/scripts'))
from rc4_assault_camera import World
import rc4_requested_views as camera

def instrument(src):
    camera.instrument(src)
    p=src/'SP/code/rend2/tr_iflc_fixture.inc';t=p.read_text();s='int R_IFLC_ShadowFixture(const dlight_t *dl)\n{\n    int i;'
    assert t.count(s)==1
    p.write_text(t.replace(s,s+'\n    if (ri.Cvar_VariableIntegerValue("r_iflcFixtureTestBypass")) return 0;'))
    p=src/'SP/code/cgame/cg_view.c';t=p.read_text();s='"r_ssgi","r_volumetricSun"';assert t.count(s)==1
    p.write_text(t.replace(s,'"r_iflcFixtureTestBypass","r_dwFireLightControl","r_dlightShadowMaxLights","r_dlightWorldContainment","r_hdr","r_postProcess","r_volumetricFireV07Mode","r_volumetricFireSourceMode","r_ssgi","r_volumetricSun"'))
    p=src/'SP/code/rend2/tr_local.h';t=p.read_text();p.write_text(t+'\nvoid R_IFLC_TestAudit_f(void);\n')
    p=src/'SP/code/rend2/tr_init.c';t=p.read_text();s='ri.Cmd_AddCommand( "dw_fl_select", R_IFLC_Select_f );';assert t.count(s)==1
    t=t.replace(s,s+'\n\tri.Cmd_AddCommand("dw_fl_test_audit", R_IFLC_TestAudit_f);')
    s='ri.Cmd_RemoveCommand( "dw_fl_select" );';assert t.count(s)==1
    p.write_text(t.replace(s,s+'\n\tri.Cmd_RemoveCommand("dw_fl_test_audit");'))
    p=src/'SP/code/rend2/tr_iflc.inc'
    with p.open('a') as f:f.write(r'''
/* Native TestLab only. Never compiled into the distributed DLL. */
void R_IFLC_TestAudit_f(void) {
    int i,j;
    if (!R_IFLC_EnsureCatalog()) return;
    R_IssuePendingRenderCommands();
    if (ri.Cmd_Argc()>1 && !strcmp(ri.Cmd_Argv(1),"catalog")) {
        for(i=0;i<s_iflcOwnerCount;++i) {
            R_IFLC_PrepareFixture(i);
            ri.Printf(PRINT_ALL,"IFLC11_OWNER map=%s key=%s route=%s origin=%.3f,%.3f,%.3f surfaces=%d selfCasters=%d ids=",
                s_iflcMap,s_iflcOwners[i].key,R_IFLC_Route(&s_iflcOwners[i]),s_iflcOwners[i].origin[0],s_iflcOwners[i].origin[1],s_iflcOwners[i].origin[2],s_iflcOwners[i].surfaceCount,s_iflcFixtures[i].count);
            for(j=0;j<s_iflcFixtures[i].count;++j)ri.Printf(PRINT_ALL,"%d,",s_iflcFixtures[i].surfaces[j]);
            ri.Printf(PRINT_ALL,"\n");
        }
    }
    for(i=0;i<tr.refdef.num_dlights && i<MAX_DLIGHTS;++i) {
        const dlight_t *dl=&tr.refdef.dlights[i];
        int slot=tr.refdef.dlightWorldSlot[i],fixture=R_IFLC_ShadowFixture(dl);
        unsigned int key=slot>=0 && slot<DLIGHT_WORLD_CACHE_MAX?tr.dlightWorldCache[slot].iflcFixtureKey:0;
        ri.Printf(PRINT_ALL,"IFLC11_LIGHT index=%d optin=%d native=%d promoted=%d origin=%.3f,%.3f,%.3f radius=%.3f color=%.6f,%.6f,%.6f policy=%u cachePolicy=%u worldSlot=%d ordinarySlot=%d\n",
            i,dl->iflcOptIn,dl->fireVolumetricNativeOrdinal,dl->staticPromoteFixtureId,dl->origin[0],dl->origin[1],dl->origin[2],dl->radius,dl->color[0],dl->color[1],dl->color[2],R_IFLC_FixturePolicyKey(fixture),key,slot,(int)tr.refdef.dlightShadowSlot[i]);
    }
}
''')
    print('IFLC11_NATIVE_TEST_INSTRUMENTATION_ONLY')

def maps(retail):
    result={}
    for p in sorted(retail.iterdir()):
        if p.suffix.lower()!='.pk3':continue
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                if n.lower() in ('maps/crypt1.bsp','maps/crypt2.bsp'):result[Path(n).stem.lower()]=z.read(n)
    assert set(result)=={'crypt1','crypt2'}
    return result

def discover(data,mapname):
    world=World(data)
    def lump(i):
        o,n=struct.unpack_from('<ii',data,8+8*i);return data[o:o+n]
    vv=list(struct.iter_unpack('<10f4B',lump(10)));ss=list(struct.iter_unpack('<12i12f2i',lump(13)))
    first,count=struct.unpack_from('<6f4i',lump(7))[6:8]
    groups={}
    for i in range(first,first+count):
        s=ss[i];shader=world.shaders[s[0]][0].split(b'\0')[0].decode('latin1')
        if not ('xflame' in shader or 'torch_ember' in shader or shader.startswith('textures/lights/') or 'firehead' in shader):continue
        v=vv[s[3]:s[3]+s[4]]
        if not v:continue
        anchor=[sum(a[k] for a in v)/len(v) for k in range(3)]
        group=groups.setdefault(shader,[])
        if any(math.dist(x['anchor'],anchor)<24 for x in group):continue
        group.append({'surface':i,'shader':shader,'anchor':anchor,'kind':'fire' if 'xflame' in shader or 'torch_ember' in shader else 'lamp' if shader.startswith('textures/lights/') else 'firehead'})
    start=next((list(map(float,e['origin'].split())) for e in world.entities if e.get('classname')=='info_player_start'),[0,0,0])
    views=[];coverage={}
    # Reference camera/target are test data, never production correction logic.
    if mapname=='crypt1':
        for g in groups.values():
            for a in g:
                if a['surface']==2992:
                    views.append({**a,'eye':[-181.63945557510993,1647.9745076412642,488.0],'angles':[-29.744881296942214,247.5,0],'name':'repro_2992'})
    for shader,anchors in groups.items():
        ordered=sorted(anchors,key=lambda a:(any(math.dist(a['anchor'],v['anchor'])<160 for v in views),math.dist(a['anchor'],start)))
        found=None
        for a in ordered:
            target=a['anchor'];choices=[]
            for distance in (128,192):
                for step in range(16):
                    ang=step*math.pi/8
                    for dz in (-40,-16,16):
                        eye=[target[0]+distance*math.cos(ang),target[1]+distance*math.sin(ang),target[2]+dz]
                        if world.solid(eye) or any(world.solid([eye[k]+off[k] for k in range(3)]) for off in ((8,0,0),(-8,0,0),(0,8,0),(0,-8,0),(0,0,-16))):continue
                        hit=world.trace(eye,target)
                        if hit and hit.get('fraction',0)<(.98 if a['kind']=='fire' else .88):continue
                        d=[target[k]-eye[k] for k in range(3)]
                        angles=[-math.degrees(math.atan2(d[2],math.hypot(d[0],d[1]))),math.degrees(math.atan2(d[1],d[0]))%360,0]
                        choices.append((abs(dz+40)+distance*.01,{**a,'eye':eye,'angles':angles}))
            if choices:
                found=min(choices,key=lambda x:x[0])[1];break
        coverage[shader]={'instances':len(anchors),'camera_found':bool(found)}
        if found:
            found['name']=f"{len(views):02d}_{found['kind']}_{found['surface']}";views.append(found)
    for v in views:
        target=v['anchor'];eye=v['eye'];d=[eye[k]-target[k] for k in range(3)];length=math.sqrt(sum(x*x for x in d))
        probe=[target[k]+d[k]*32/length for k in range(3)]
        v['probe']=eye if world.solid(probe) else probe
    return views,coverage

def capture(src,retail,out,mapname):
    from PIL import Image,ImageDraw
    import numpy as np
    out.mkdir(parents=True,exist_ok=True)
    data=maps(retail)[mapname];views,coverage=discover(data,mapname)
    (out/'COVERAGE.json').write_text(json.dumps({'map':mapname,'bsp_sha256':hashlib.sha256(data).hexdigest(),'coverage':coverage,'views':views},indent=2)+'\n')
    runtime=Path(tempfile.mkdtemp(prefix='iflc11-'+mapname+'-',dir=out.parent)).resolve();main=runtime/'main';main.mkdir()
    build=src/'SP/build/release-linux-x86_64'
    for p in build.iterdir():
        if p.is_file():shutil.copy2(p,runtime/p.name)
    for p in (build/'main').glob('*.so'):shutil.copy2(p,main/p.name)
    for p in retail.iterdir():
        if p.suffix.lower()=='.pk3':(main/p.name.lower()).symlink_to(p.resolve())
    cmd=['set con_notifytime -1','set cg_draw2D 0','set cg_drawGun 0','set cg_bobup 0','set cg_bobpitch 0','set cg_bobroll 0','set r_autoExposure 0','set r_forceAutoExposure 0','set r_forceSunPause 1','god','notarget','wait 12','dw_fl_test_audit catalog']
    shots=[]
    def shot(view,label):
        n=len(shots)+1;name=f'{mapname}_{view["name"]}_{label}'
        cmd.extend([f'echo IFLC11_STATE {n} {view["name"]} {label}','dw_fl_info','dw_fl_test_audit','maplight_list',f'set dw_proofShot {n}','wait 3',f'screenshot {name}','wait 2'])
        shots.append({'id':n,'view':view['name'],'variant':label,'name':name,'kind':view['kind']})
    for v in views:
        cmd.extend(['set dw_proofShot 0','set dw_proofFreeze 0','set r_dwFireLightControl 0','set r_iflcFixtureTestBypass 0','set r_mapLightingLearn 1','set r_mapLightingLearnShow 0','set r_mapLightingProfileEnable 0','maplight_clear_memory confirm','maplight_zone_new IFLC11',
                    'proofView '+' '.join(f'{x:.6f}' for x in v['probe']+v['angles']),'wait 8','maplight_add_cluster',
                    'proofView '+' '.join(f'{x:.6f}' for x in v['eye']+v['angles']),'wait 20','maplight_add_cluster','maplight_baked 0.2','maplight_status'])
        if v['kind']=='lamp':cmd.extend(['r_staticPromoteInspect','r_staticPromoteLearn','wait 12','r_staticPromoteInspect'])
        cmd.extend(['set dw_proofFreeze 1','wait 8','dw_fl_select','dw_fl_next','wait 2'])
        shot(v,'baseline_off')
        if v['kind']=='fire':
            cmd.extend(['set r_dwFireLightControl 1','dw_fl_set enabled 1','dw_fl_set direct 3','dw_fl_set radius 1','dw_fl_set volume 1','set r_iflcFixtureTestBypass 1','wait 8']);shot(v,'v1_shadow')
            cmd.extend(['set r_iflcFixtureTestBypass 0','wait 8']);shot(v,'v11_shadow')
            cmd.extend(['set r_iflcFixtureTestBypass 1','wait 8']);shot(v,'v1_repeat')
            cmd.extend(['set r_iflcFixtureTestBypass 0','wait 8']);shot(v,'v11_repeat')
            cmd.extend(['dw_fl_set volume 0','wait 8']);shot(v,'v11_volume0')
            cmd.extend(['set r_dwFireLightControl 0','wait 8']);shot(v,'master_off')
            cmd.extend(['dw_fl_reset','wait 4'])
        else:
            cmd.extend(['set r_dwFireLightControl 1','set r_iflcFixtureTestBypass 1','wait 8']);shot(v,'other_v1')
            cmd.extend(['set r_iflcFixtureTestBypass 0','wait 8']);shot(v,'other_v11')
            cmd.extend(['set r_dwFireLightControl 0','wait 8']);shot(v,'master_off')
        if v['kind']=='lamp':cmd.extend(['r_staticPromoteAuto','wait 4'])
    cmd.extend(['echo IFLC11_DONE','set dw_proofFreeze 0','quit'])
    (main/'IFLC11_TEST.cfg').write_text('\n'.join(cmd)+'\n');shutil.copy2(main/'IFLC11_TEST.cfg',out/'IFLC11_TEST.cfg')
    setup=['set r_mode -1','set r_customwidth 960','set r_customheight 540','set r_fullscreen 0','set r_renderer rend2','set cl_renderer rend2','set r_hdr 1','set r_postProcess 1','set r_bloom 1','set r_bloomMode 2','set r_dwCas 1','set r_dwA2C 1','set r_ssgi 1','set r_forceSun 1','set r_sunShadows 1','set r_dlightMode 2','set r_dlightShadowMaxLights 3','set r_dlightWorldContainment 2','set r_volumetricSun 1','set r_volumetricLocal 1','set r_volumetricFire 1','set r_volumetricFireV07Mode 2','set r_volumetricFireSourceMode 2','set r_volumetricFireMode 2','set r_volumetricFireMaxActive 8','set r_volumetricFireSamples 40','set r_ext_framebuffer_multisample 4','set r_cameraExposure 1','set r_autoExposure 0','set r_forceAutoExposure 0','set r_dwFireLightControl 0','set r_iflcFixtureTestBypass 0','set s_initsound 0','set r_swapInterval 0','set fixedtime 100','set con_notifytime -1']
    (main/'IFLC11_SETUP.cfg').write_text('\n'.join(setup)+'\n');shutil.copy2(main/'IFLC11_SETUP.cfg',out/'IFLC11_SETUP.cfg')
    home=runtime/'home';home.mkdir();exe=next(p for p in runtime.iterdir() if p.name.startswith('iowolfsp') and p.is_file());exe.chmod(0o755)
    args=['xvfb-run','-a','-s','-screen 0 1280x720x24',str(exe),'+safe','+set','fs_basepath',str(runtime),'+set','fs_homepath',str(home),'+set','com_introplayed','1','+set','com_recommendedSet','1','+set','logfile','2','+set','dw_proofAutomation','1','+set','r_renderer','rend2','+set','cl_renderer','rend2','+exec','IFLC11_SETUP.cfg','+vid_restart','+set','dw_proofScenario','IFLC11_TEST.cfg','+spdevmap',mapname]
    env={k:v for k,v in os.environ.items() if not any(s in k.upper() for s in ('TOKEN','SECRET','PASSWORD','CREDENTIAL'))};env.update(LIBGL_ALWAYS_SOFTWARE='1',LP_NUM_THREADS='2',SDL_AUDIODRIVER='dummy')
    with (out/'stdout.log').open('w') as log:
        process=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        try:rc=process.wait(timeout=1800)
        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait();rc=124
    texts=[]
    for i,p in enumerate(sorted(home.rglob('*console*.log'))):shutil.copy2(p,out/f'console-{i}.log');texts.append(p.read_text(errors='replace'))
    text='\n'.join(texts);images={}
    for s in shots:
        p=list(home.rglob(s['name']+'.tga'))
        if len(p)==1:
            im=Image.open(p[0]).convert('RGB');im.save(out/(s['name']+'.png'));images[s['name']]=np.array(im).astype(np.int16)
    states={};current=None;proof={}
    for line in text.splitlines():
        m=re.search(r'IFLC11_STATE (\d+) (\S+) (\S+)',line)
        if m:current=states.setdefault(int(m[1]),{'view':m[2],'variant':m[3],'lines':[],'lights':[]})
        if current is not None and line.startswith(('IFLC:','IFLC11_LIGHT','MAPLIGHT')):current['lines'].append(line)
        m=re.search(r'PROOF_VIEW shot=(\d+) time=(\d+) eye=([\d.,-]+) forward=([\d.,-]+)',line)
        if m:
            proof[int(m[1])]={'time':int(m[2]),'eye':list(map(float,m[3].split(','))),'forward':list(map(float,m[4].split(',')))}
            current=None
        if current is not None and line.startswith('IFLC11_LIGHT '):current['lights'].append(dict(re.findall(r'(\w+)=([^\s]+)',line)))
    comparisons=[];faults=[];review=[]
    for view in views:
        these=[s for s in shots if s['view']==view['name']];snap=[proof.get(s['id']) for s in these]
        if any(x is None for x in snap) or len({x['time'] for x in snap if x})!=1 or any(math.dist(x['eye'],view['eye'])>.01 for x in snap if x):faults.append(view['name']+': camera/time evidence')
        for s in these:
            state=states.get(s['id'],{})
            for light in state.get('lights',[]):
                if light.get('optin')=='1' and light.get('policy')!=light.get('cachePolicy'):faults.append(s['name']+': policy/cache mismatch')
        pairs=[('v1_shadow','v11_shadow'),('v1_shadow','v1_repeat'),('v11_shadow','v11_repeat'),('baseline_off','master_off')] if view['kind']=='fire' else [('other_v1','other_v11'),('baseline_off','master_off')]
        for aa,bb in pairs:
            an=f'{mapname}_{view["name"]}_{aa}';bn=f'{mapname}_{view["name"]}_{bb}'
            if an not in images or bn not in images:continue
            d=np.abs(images[an]-images[bn]);metrics={'view':view['name'],'a':aa,'b':bb,'changed_pixels':int(np.any(d>0,axis=2).sum()),'mean_abs_rgb':float(d.mean()),'max_abs_rgb':int(d.max())};comparisons.append(metrics)
            if aa=='v1_shadow' and bb=='v11_shadow' and metrics['changed_pixels']==0:review.append(view['name']+': no correction response; inspect route/classification')
        selected=[s for s in these if s['name'] in images]
        board=Image.new('RGB',(960,292*max(1,math.ceil(len(selected)/2))),(20,20,24));draw=ImageDraw.Draw(board)
        for i,s in enumerate(selected):
            im=Image.open(out/(s['name']+'.png'));im.thumbnail((480,270));x=i%2*480;y=i//2*292;draw.text((x+8,y+4),s['variant'],fill='white');board.paste(im,(x,y+22))
        board.save(out/(view['name']+'_comparison.png'))
    owners=[line for line in text.splitlines() if line.startswith('IFLC11_OWNER ')]
    report={'map':mapname,'exit':rc,'ready':'PROOF_READY' in text,'complete':'IFLC11_DONE' in text,'requested':len(shots),'captured':len(images),'coverage':coverage,'shots':shots,'states':states,'proof':proof,'owner_catalog':owners,'comparisons':comparisons,'faults':faults,'review_notes':review,'visual_status':'PENDING_MANUAL_REVIEW','scope':'material-family samples and full source catalog; no claim of every camera on every map; Linux software rendering not Windows FPS acceptance'}
    (out/'IFLC11_RUNTIME_REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('map','exit','ready','complete','requested','captured','faults','review_notes')},indent=2),flush=True)
    assert rc==0 and report['ready'] and report['complete'] and len(images)==len(shots) and not faults,'Incomplete real-game verification'

if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='cmd',required=True);a=s.add_parser('instrument');a.add_argument('source',type=Path);a=s.add_parser('capture');a.add_argument('source',type=Path);a.add_argument('retail',type=Path);a.add_argument('output',type=Path);a.add_argument('map',choices=['crypt1','crypt2']);a=p.parse_args()
    if a.cmd=='instrument':instrument(a.source.resolve())
    else:capture(a.source.resolve(),a.retail.resolve(),a.output.resolve(),a.map)
