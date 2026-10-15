#!/usr/bin/env python3
"""Combine released RC2 with the pending R2 fixes without replacing prior fixes."""
from pathlib import Path
import gzip,hashlib,importlib.util,json,os,shutil,struct,subprocess,sys,zipfile
H=Path(__file__).resolve().parent
K=H.parent
E=Path('evidence').resolve()
L=json.loads((H/'complete-lock.json').read_text())
NAME='DarkWolf-ioRTCW-Rend2-v4.4.6-Optimized-Clean-Production-RC2-Complete-Win64-SP'
BANNED=(b'DWPERF_FRAME',b'DWPERF_PROBE',b'DWPERF_CFG',b'DARKWOLF_V446_FULL_PERF_TELEMETRY_V01',b'DARKWOLF_TESTLAB_V0_1',b'__asan_init',b'__ubsan_handle')
COMPONENTS=['ioWolfSP.x64.exe','renderer_sp_rend2_x64.dll','Main/cgame_sp_x64.dll','Main/qagame_sp_x64.dll','Main/ui_sp_x64.dll']
def require(ok,why):
    if not ok:raise RuntimeError(why)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(b):return hashlib.sha256(b).hexdigest()
def run(*args,**kw):return subprocess.run(list(map(str,args)),check=True,**kw)
def text(*args):return subprocess.check_output(list(map(str,args)),text=True).strip()
def dump(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')
def unpack():
    E.mkdir(exist_ok=True)
    archive=E/'validation-suite.zip'
    data=b''.join((H/('validation-suite.zip.part'+i)).read_bytes() for i in ('00','01a','01b','02a','02b'))
    require(digest(data)==L['validation_suite_sha256'],'Validation suite hash drift')
    archive.write_bytes(data)
    dst=E/'test-suite';dst.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        require(z.testzip() is None,'Validation archive CRC')
        for info in z.infolist():
            n=Path(info.filename)
            require(not n.is_absolute() and '..' not in n.parts and not info.is_dir(),'Unsafe suite path')
            require(n.suffix=='.py','Unexpected suite content')
            p=dst/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(info))
    return dst

def prepare():
    E.mkdir(exist_ok=True)
    spec=importlib.util.spec_from_file_location('prior_rc2',K/'rc2/pipeline.py')
    prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
    prior.prepare()
    require(text('git','-C','source','rev-parse','HEAD^{tree}')==L['parent_source_tree'],'Wrong released RC2 tree')
    os.rename('source','rc2-source')
    run('git','clone','-q','--shared','rc2-source','source')
    patch=gzip.decompress((H/'complete.patch.gz').read_bytes())
    require(digest(patch)==L['patch_sha256'],'Additional patch hash drift')
    (E/'rc2-complete-delta.patch').write_bytes(patch)
    run('git','-C','source','apply','--check',E/'rc2-complete-delta.patch')
    run('git','-C','source','apply',E/'rc2-complete-delta.patch')
    run('git','-C','source','diff','--check')
    names=text('git','-C','source','diff','--name-only','HEAD').splitlines()
    require(set(names)==set(L['source_delta']),'Unexpected delta outside six-file allowlist')
    require(not text('git','-C','source','ls-files','--others','--exclude-standard'),'Unexpected untracked source')
    for name,pair in L['source_delta'].items():
        require(sha(Path('rc2-source')/name)==pair['before'],'Wrong parent '+name)
        require(sha(Path('source')/name)==pair['after'],'Wrong output '+name)
    for p in Path('source/SP/code').rglob('*'):
        if p.is_file() and p.suffix in ('.c','.h','.glsl'):
            require(not any(x in p.read_bytes() for x in BANNED[:5]),'Instrumentation '+str(p))
    run('git','-C','source','add','-A')
    tree=text('git','-C','source','write-tree')
    require(tree==L['complete_source_tree'],'Complete source tree drift')
    run('git','-C','source','-c','user.name=DarkWolf Engineering','-c','user.email=ci@example.invalid','commit','-qm','Complete RC2: integrate pending R2 renderer fixes')
    dump(E/'complete-source-policy.json',dict(status='PASS',**L,all_other_tracked_files_identical=True))
    unpack()
    print('COMPLETE_SOURCE_TREE_PASS',tree,flush=True)

def tests():
    suite=unpack();out=E/'complete-tests'
    run(sys.executable,suite/'prepare_tests.py',Path('rc2-source').resolve(),Path('source').resolve(),out)
    env={**os.environ,'DW_TEST_ROOT':str(out),'LIBGL_ALWAYS_SOFTWARE':'1'}
    run(sys.executable,suite/'tests/test_native.py',out/'native',env=env)
    run(sys.executable,suite/'tests/test_shaders.py',out/'shaders',env=env)
    run(sys.executable,suite/'tests/test_math.py',out/'math.json',env=env)

def pe(p):
    b=p.read_bytes();require(len(b)>1024 and b[:2]==b'MZ','Invalid PE '+str(p))
    off=struct.unpack_from('<I',b,60)[0]
    require(off+26<=len(b) and b[off:off+4]==b'PE\0\0','Invalid PE offset')
    require(struct.unpack_from('<H',b,off+4)[0]==0x8664,'Not AMD64')
    require(struct.unpack_from('<H',b,off+24)[0]==0x20b,'Not PE32+')
    require(not any(x in b for x in BANNED),'Instrumented production binary '+str(p))
    return b

def stage():
    dst=Path('dist')/NAME;require(not dst.exists(),'Refuse staging overwrite')
    (dst/'Main').mkdir(parents=True);(dst/'docs').mkdir()
    comparison={}
    for name in COMPONENTS:
        rel=name.replace('Main/','main/')
        a=Path('rc2-source/SP/build/release-mingw32-x86_64')/rel
        b=Path('source/SP/build/release-mingw32-x86_64')/rel
        pe(a);pe(b)
        eq=sha(a)==sha(b)
        require(eq==(name!='renderer_sp_rend2_x64.dll'),'Unexpected binary equality/difference '+name)
        comparison[name]={'released_rc2_rebuilt_sha256':sha(a),'complete_sha256':sha(b),'byte_identical':eq}
        shutil.copy2(b,dst/name)
    shader=(dst/'renderer_sp_rend2_x64.dll').read_bytes()
    for marker in [b'DARKWOLF_VOLUMETRIC_COVERAGE_AA_FINAL_V1',b'DARKWOLF_V446_OPT09_SHARED_RAW_DEPTH',b'DARKWOLF_V446_OPT06_FIRE_GAUSSIAN_SQRT_ELIMINATION',b'DARKWOLF_V446_OPT04_LOCALVOL_LOOP_INVARIANTS',b'DARKWOLF_V446_OPT02_SUN_TRANSMITTANCE_RECURRENCE',b'RC2-08',b'RC2-09',b'SsgiSceneEntityGuardMaskFromCenter',b'transmittanceDecay']:
        require(marker in shader,'Missing compiled shader '+repr(marker))
    baseline=json.loads((K/'baseline_source_manifest.json').read_text())
    parent=json.loads((K/'rc2/rc2-lock.json').read_text())
    for name,value in baseline['payload'].items():
        p=Path('source/SP/code/libs/win64')/name if name.endswith('.dll') else K/'payload'/name
        require(sha(p)==value,'Changed payload '+name);shutil.copy2(p,dst/name)
    for name in ['RUN_DARKWOLF_OPTIMIZED_CLEAN.bat','README_INSTALL_RU.md']:
        data=(K/name).read_bytes()
        if name.endswith('.bat'):data=data.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
        (dst/name).write_bytes(data)
    shutil.copy2(K/'PRODUCTION_HIGH_QUALITY.cfg',dst/'Main/PRODUCTION_HIGH_QUALITY.cfg')
    for name in ['RUN_DARKWOLF_OPTIMIZED_CLEAN.bat','Main/PRODUCTION_HIGH_QUALITY.cfg','Main/UNIFIED_PRODUCTION.cfg','Main/darkwolf_ignition_rc_v0_6.pk3']:
        require(sha(dst/name)==parent['rc1_package_files'][name],'Quality/launcher drift '+name)
    for a,b in [('SP/COPYING.txt','COPYING.txt'),('LICENCE.md','LICENCE.md'),('SP/code/SDL2/include/SDL_copying.h','docs/SDL_COPYING.txt')]:shutil.copy2(Path('source')/a,dst/b)
    for p in Path('source/SP/code/libs/win64').iterdir():
        if p.is_file() and p.suffix.lower() in ('.txt','.md'):shutil.copy2(p,dst/'docs'/p.name)
    shutil.copy2(H/'README.md',dst/'CHANGELOG_RC2_COMPLETE.md')
    shutil.copy2(H/'complete-lock.json',dst/'docs/complete-lock.json')
    shutil.copy2(E/'rc2-complete-delta.patch',dst/'docs/rc2-complete-delta.patch')
    # Carry the full historical patch chain in the source repository, not retail assets.
    p=dict(status='CANDIDATE_FOR_LOCAL_VERIFICATION',release='Clean Production RC2 Complete',builder_sha=os.environ['GITHUB_SHA'],run_id=os.environ['GITHUB_RUN_ID'],source_rc1_tree=parent['rc1_source_tree'],source_rc2_tree=L['parent_source_tree'],source_complete_tree=L['complete_source_tree'],parent_zip_sha256=L['parent_zip_sha256'],rc1_zip_sha256=L['rc1_zip_sha256'],patch_sha256=L['patch_sha256'],source_delta=L['source_delta'],requested_round2_items=10,new_items_over_released_rc2=9,overlap=L['overlap'],binary_comparison=comparison,BUILD='PASS',WINDOWS_RUNTIME='NOT_RUN',GPU_PERFORMANCE='NOT_RUN',VISUAL_ACCEPTANCE='NOT_RUN',quality_preset_byte_identical=True,build_version=L['build_version'],source_url='https://github.com/jaha2002-stack/iortcw-rend2-build/tree/'+os.environ['GITHUB_SHA'],profile_note='SSAO=0 and indirectLighting=0 inherited unchanged; not all-effects-on')
    dump(dst/'docs/BUILD_PROVENANCE.json',p);dump(E/'complete-binary-comparison.json',comparison)
    print('CLEAN_COMPLETE_STAGE_PASS',flush=True)

def finish():
    dst=Path('dist')/NAME;p=json.loads((dst/'docs/BUILD_PROVENANCE.json').read_text())
    suite=E/'complete-tests'
    native=json.loads((suite/'native/native-results.json').read_text())
    shaders=json.loads((suite/'shaders/shader-tests.json').read_text())
    math=json.loads((suite/'math.json').read_text())
    require(native['status']=='EXTRACTED_C_DIFFERENTIAL_PASS' and len(native['tests'])==8,'Incomplete native tests')
    require(shaders['status']=='SYNTHETIC_MESA_SHADER_AB_PASS' and len(shaders['program_links'])==28,'Incomplete shader compile')
    cases=sum(x['cases'] for x in shaders['render_tests']);require(cases==1188,'Incomplete shader comparisons')
    require(math['status']=='FLOAT32_STRESS_PASS','Arithmetic failed')
    p.update(STATIC_DIFFERENTIAL='PASS',SYNTHETIC_SHADER_AB='PASS',SHADER_AB_CASES=cases)
    rows={}
    expected=[(m,'high') for m in ['escape1','swf','dam','crypt1','assault','forest']]+[('escape1','quality')]
    for variant in ['rc2','complete']:
        f=E/(variant+'-runtime/runtime-results.json')
        if f.exists():
            value=json.loads(f.read_text())
            require([(r['map'],r['profile']) for r in value]==expected,'Wrong map/profile coverage')
            require(all(r['status']=='SMOKE_PASS' and r['exit_code']==0 and r['gameplay_ready'] and not r['cvar_mismatches'] for r in value),'Failed actual smoke '+variant)
            rows[variant]=value
    require(len(rows) in (0,2),'One-sided smoke evidence')
    p['MESA_SMOKE']='PASS' if rows else 'NOT_RUN'
    p['CAPTURE_INTEGRITY']='NOT_RUN';p['MESA_SMOKE_SCENARIOS']=14 if rows else 0
    if rows:
        from PIL import Image,ImageChops
        for a,b in zip(rows['rc2'],rows['complete']):
            for key in ['map','profile','resolution','preset_sha256','hardware']:require(a[key]==b[key],'A/B differs: '+key)
            for variant,r in [('rc2',a),('complete',b)]:
                tag=r['map'] if r['profile']=='high' else r['map']+'-'+r['profile'];folder=E/(variant+'-runtime')
                with Image.open(folder/(tag+'.png')) as x,Image.open(folder/(tag+'.tga')) as y:
                    require(x.size==y.size==tuple(r['resolution']),'Smoke frame dimensions')
                    require(ImageChops.difference(x.convert('RGB'),y.convert('RGB')).getbbox() is None,'Converted pixels changed')
        p['CAPTURE_INTEGRITY']='PASS_14_SMOKE_IMAGES_ONLY'
    p['MOTION_EVENT_REGRESSION']='NOT_RUN';p['FPS']='NOT_MEASURED_USER_PC_TEST'
    dump(dst/'docs/BUILD_PROVENANCE.json',p);dump(E/'complete-acceptance.json',p);dump('dist/BUILD_PROVENANCE.json',p)
    dump(dst/'docs/SOURCE_TESTS.json',dict(native=native,shaders=shaders,arithmetic=math))
    files=sorted(x for x in dst.rglob('*') if x.is_file())
    require(not any(x.name.lower().startswith('pak') and x.suffix.lower()=='.pk3' for x in files),'Retail in release')
    sums={x.relative_to(dst).as_posix():sha(x) for x in files}
    (dst/'docs/SHA256SUMS.txt').write_text(''.join(f'{v}  {k}\n' for k,v in sums.items()))
    arc=Path('dist')/(NAME+'.zip')
    with zipfile.ZipFile(arc,'w',zipfile.ZIP_DEFLATED) as z:
        for x in sorted(dst.rglob('*')):
            if x.is_file():
                info=zipfile.ZipInfo(NAME+'/'+x.relative_to(dst).as_posix(),(2026,10,15,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,x.read_bytes())
    with zipfile.ZipFile(arc) as z:
        require(z.testzip() is None,'Release CRC')
        for key,value in sums.items():require(digest(z.read(NAME+'/'+key))==value,'Release hash '+key)
    Path(str(arc)+'.sha256').write_text(sha(arc)+'  '+arc.name+'\n')
    print('CLEAN_PRODUCTION_RC2_COMPLETE_ZIP_PASS',sha(arc),flush=True)
if __name__=='__main__':
    action={'prepare':prepare,'tests':tests,'stage':stage,'finish':finish}
    require(len(sys.argv)==2 and sys.argv[1] in action,'usage: pipeline.py prepare|tests|stage|finish')
    action[sys.argv[1]]()
