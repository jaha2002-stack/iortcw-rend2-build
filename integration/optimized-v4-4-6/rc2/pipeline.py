#!/usr/bin/env python3
"""RC2 provenance, source policy, and clean packaging. No performance assertions."""
from pathlib import Path
import hashlib,json,os,shutil,struct,subprocess,sys,zipfile
HERE=Path(__file__).resolve().parent
KIT=HERE.parent
REPO=KIT.parent.parent
LOCK=json.loads((HERE/'rc2-lock.json').read_text())
E=Path('evidence').resolve()
NAME='DarkWolf-ioRTCW-Rend2-v4.4.6-Optimized-Clean-RC2-Win64-SP'
BANNED=[b'DWPERF_FRAME',b'DWPERF_PROBE',b'DWPERF_CFG',b'DARKWOLF_V446_FULL_PERF_TELEMETRY_V01',b'DARKWOLF_TESTLAB_V0_1']
def require(ok,message):
    if not ok: raise RuntimeError(message)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(*args,**kwargs): return subprocess.run([str(x) for x in args],check=True,**kwargs)
def capture(*args): return subprocess.check_output([str(x) for x in args],text=True).strip()
def dump(p,value):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2)+'\n')
def commit_tree(folder,label):
    run('git','-C',folder,'add','-A')
    tree=capture('git','-C',folder,'write-tree')
    run('git','-C',folder,'-c','user.name=DarkWolf Engineering','-c','user.email=ci@example.invalid','commit','-qm',label)
    return tree

def prepare():
    E.mkdir(exist_ok=True);(E/'rc1').mkdir(exist_ok=True)
    run(sys.executable,KIT/'reconstruct.py','original-source')
    run('git','clone','-q','--shared','original-source','rc1-source')
    run('git','-C','rc1-source','apply','--check',KIT/'optimized.patch')
    run('git','-C','rc1-source','apply',KIT/'optimized.patch')
    run(sys.executable,KIT/'apply_targeted_shader_optimizations.py','rc1-source',E/'rc1')
    run(sys.executable,KIT/'test_equivalence.py','rc1-source','original-source',E/'rc1')
    run(sys.executable,KIT/'test_targeted_shader_math.py',E/'rc1/shader-math.json')
    run(sys.executable,KIT/'validate_source.py','rc1-source','original-source',E/'rc1')
    tree=commit_tree('rc1-source','Exact RC1 d005ca82 source')
    require(tree==LOCK['rc1_source_tree'],'RC1 tree mismatch')
    run('git','clone','-q','--shared','rc1-source','source')
    run(sys.executable,HERE/'apply_rc2.py','source')
    patch=subprocess.check_output(['git','-C','source','diff','--binary','--abbrev=7'])
    require(hashlib.sha256(patch).hexdigest()==LOCK['patch_sha256'],'RC2 generated patch digest mismatch')
    (HERE/'rc2.patch').write_bytes(patch)
    run('git','-C','source','apply','--reverse','--check',HERE/'rc2.patch')
    run('git','-C','source','diff','--check')
    changed=capture('git','-C','source','diff','--name-only').splitlines()
    require(set(changed)==set(LOCK['source_delta']),'Unexpected changed file set')
    for name,digests in LOCK['source_delta'].items():
        require(sha(Path('rc1-source')/name)==digests['before'],'RC1 hash drift: '+name)
        require(sha(Path('source')/name)==digests['after'],'RC2 hash drift: '+name)
    for p in Path('source/SP/code').rglob('*'):
        if p.is_file() and p.suffix in ('.c','.h','.glsl'):
            require(not any(x in p.read_bytes() for x in BANNED),'Instrumentation: '+str(p))
    backend=Path('source/SP/code/rend2/tr_backend.c').read_text()
    for call in ('qglViewport(', 'qglScissor('):
        require(backend.count(call)==2,'Unexpected raw rectangle writer')
        for p in Path('source/SP/code/rend2').glob('*.c'):
            if p.name!='tr_backend.c': require(call not in p.read_text(),'Untracked state writer: '+str(p))
    for name,target in [('Main/PRODUCTION_HIGH_QUALITY.cfg',KIT/'PRODUCTION_HIGH_QUALITY.cfg'),('Main/UNIFIED_PRODUCTION.cfg',KIT/'payload/Main/UNIFIED_PRODUCTION.cfg'),('Main/darkwolf_ignition_rc_v0_6.pk3',KIT/'payload/Main/darkwolf_ignition_rc_v0_6.pk3')]:
        require(sha(target)==LOCK['rc1_package_files'][name],'RC1 quality/payload changed: '+name)
    tree=commit_tree('source','RC2: ten source-visible optimizations over exact RC1')
    require(tree==LOCK['rc2_source_tree'],'RC2 tree mismatch')
    dump(E/'rc2-source-policy.json',dict(status='PASS',rc1_source_tree=LOCK['rc1_source_tree'],rc2_source_tree=tree,base_package_sha256=LOCK['base_package_sha256'],source_delta=LOCK['source_delta'],quality_preset_byte_identical=True,all_other_tracked_files_byte_identical=True,GPU_PERFORMANCE='NOT_RUN'))
    print('RC2_SOURCE_POLICY_PASS',tree,flush=True)

def pe(path):
    b=path.read_bytes();require(len(b)>1024 and b[:2]==b'MZ','Bad PE '+str(path))
    off=struct.unpack_from('<I',b,0x3c)[0]
    require(b[off:off+4]==b'PE\0\0' and struct.unpack_from('<H',b,off+4)[0]==0x8664,'Not PE AMD64 '+str(path))
    require(struct.unpack_from('<H',b,off+24)[0]==0x20b,'Not PE32+ '+str(path))
    require(not any(x in b for x in BANNED),'Instrumented binary '+str(path));return b

def stage():
    stage=Path('dist')/NAME;require(not stage.exists(),'Refusing overwrite')
    (stage/'Main').mkdir(parents=True);(stage/'docs').mkdir()
    comparison={}
    changed={'ioWolfSP.x64.exe','renderer_sp_rend2_x64.dll','Main/cgame_sp_x64.dll'}
    for name in ['ioWolfSP.x64.exe','renderer_sp_rend2_x64.dll','Main/cgame_sp_x64.dll','Main/qagame_sp_x64.dll','Main/ui_sp_x64.dll']:
        local=name.replace('Main/','main/')
        p=Path('source/SP/build/release-mingw32-x86_64')/local
        baseline=Path('rc1-source/SP/build/release-mingw32-x86_64')/local
        pe(p);pe(baseline)
        equal=sha(p)==sha(baseline)
        require(equal==(name not in changed),'Unexpected binary change/no change '+name)
        comparison[name]={'rc1_rebuilt':sha(baseline),'rc1_historical':LOCK['rc1_binaries'][name],'rc2':sha(p),'historical_rebuild_identical':sha(baseline)==LOCK['rc1_binaries'][name]}
        shutil.copy2(p,stage/name)
    renderer=(stage/'renderer_sp_rend2_x64.dll').read_bytes()
    for marker in [b'DARKWOLF_VOLUMETRIC_COVERAGE_AA_FINAL_V1',b'DARKWOLF_V446_OPT09_SHARED_RAW_DEPTH',b'DARKWOLF_V446_OPT06_FIRE_GAUSSIAN_SQRT_ELIMINATION',b'DARKWOLF_V446_OPT04_LOCALVOL_LOOP_INVARIANTS',b'DARKWOLF_V446_OPT02_SUN_TRANSMITTANCE_RECURRENCE',b'RC2-08',b'RC2-09']:
        require(marker in renderer,'Compiled shader marker missing '+repr(marker))
    payload=json.loads((KIT/'baseline_source_manifest.json').read_text())['payload']
    for name,digest in payload.items():
        p=Path('source/SP/code/libs/win64')/name if name.endswith('.dll') else KIT/'payload'/name
        require(sha(p)==digest,'Payload drift '+name);shutil.copy2(p,stage/name)
    for name in ['RUN_DARKWOLF_OPTIMIZED_CLEAN.bat','README_INSTALL_RU.md']:
        data=(KIT/name).read_bytes()
        if name.endswith('.bat'): data=data.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
        (stage/name).write_bytes(data)
    require(sha(stage/'RUN_DARKWOLF_OPTIMIZED_CLEAN.bat')==LOCK['rc1_package_files']['RUN_DARKWOLF_OPTIMIZED_CLEAN.bat'],'Launcher drift')
    shutil.copy2(KIT/'PRODUCTION_HIGH_QUALITY.cfg',stage/'Main/PRODUCTION_HIGH_QUALITY.cfg')
    for src,dst in [('SP/COPYING.txt','COPYING.txt'),('LICENCE.md','LICENCE.md'),('SP/code/SDL2/include/SDL_copying.h','docs/SDL_COPYING.txt')]:
        shutil.copy2(Path('source')/src,stage/dst)
    for p in Path('source/SP/code/libs/win64').iterdir():
        if p.is_file() and p.suffix.lower() in ('.md','.txt'):shutil.copy2(p,stage/'docs'/p.name)
    for name in ['AUDIT_RC2.md','rc2-lock.json','rc2.patch']:
        shutil.copy2(HERE/name,stage/'docs'/name)
    shutil.copy2(HERE/'AUDIT_RC2.md',stage/'CHANGELOG_OPTIMIZATION_RC2.md')
    shutil.copy2(E/'unit/rc2-tests.json',stage/'docs/SOURCE_DIFFERENTIAL_TESTS.json')
    provenance={'status':'CANDIDATE_FOR_LOCAL_VERIFICATION','builder_sha':os.environ['GITHUB_SHA'],'run_id':os.environ['GITHUB_RUN_ID'],'source_rc1_tree':LOCK['rc1_source_tree'],'source_rc2_tree':LOCK['rc2_source_tree'],'base_package_sha256':LOCK['base_package_sha256'],'rc2_patch_sha256':LOCK['patch_sha256'],'source_delta':LOCK['source_delta'],'binary_comparison':comparison,'BUILD':'PASS','STATIC_DIFFERENTIAL':'PASS','WINDOWS_RUNTIME':'NOT_RUN','GPU_PERFORMANCE':'NOT_RUN','VISUAL_ACCEPTANCE':'NOT_RUN','profile_note':'Identical RC1 preset: SSAO=0 and indirectLighting=0 remain explicit inherited exceptions; not all-effects-on.'}
    dump(stage/'docs/BUILD_PROVENANCE.json',provenance)
    dump(E/'binary-comparison.json',comparison)
    print('RC2_CLEAN_STAGE_PASS',flush=True)

def finish():
    stage=Path('dist')/NAME;p=stage/'docs/BUILD_PROVENANCE.json';prov=json.loads(p.read_text())
    smoke={};total=0
    for variant in ['rc1','rc2']:
        q=E/(variant+'-runtime/runtime-results.json')
        if q.exists():
            rows=json.loads(q.read_text());require(len(rows)==7 and all(r['status']=='SMOKE_PASS' for r in rows),'Incomplete/failing Mesa smoke')
            smoke[variant]=rows;total+=len(rows)
    require(total in (0,14),'Only one variant has smoke evidence')
    prov['MESA_SMOKE']='PASS' if total==14 else 'NOT_RUN'
    prov['MESA_SMOKE_SCENARIOS']=total
    prov['RING_TABLE_REGRESSION']='NOT_RUN_RC2: prior RC1 evidence is not reused as RC2 evidence'
    prov['CAPTURE_INTEGRITY']='NOT_RUN'
    if total==14:
        from PIL import Image,ImageChops
        for a,b in zip(smoke['rc1'],smoke['rc2']):
            for k in ['map','profile','resolution','preset_sha256','hardware']:require(a[k]==b[k],'Mismatched A/B smoke '+k)
            for variant in ['rc1','rc2']:
                tag=a['map'] if a['profile']=='high' else a['map']+'-'+a['profile']
                folder=E/(variant+'-runtime')
                png=folder/(tag+'.png');tga=folder/(tag+'.tga')
                require(png.is_file() and tga.is_file(),'Missing actual smoke frame')
                with Image.open(png) as x,Image.open(tga) as y:
                    require(x.size==y.size==tuple(a['resolution']),'Smoke size mismatch')
                    require(ImageChops.difference(x.convert('RGB'),y.convert('RGB')).getbbox() is None,'PNG/TGA pixels differ')
        prov['CAPTURE_INTEGRITY']='PASS_14_SMOKE_IMAGES_ONLY'
    dump(E/'rc2-acceptance.json',prov);dump(p,prov);dump(Path('dist/BUILD_PROVENANCE.json'),prov)
    paths=sorted(x for x in stage.rglob('*') if x.is_file())
    require(not any(x.name.lower().startswith('pak') and x.suffix.lower()=='.pk3' for x in paths),'Retail package inclusion')
    sums={x.relative_to(stage).as_posix():sha(x) for x in paths}
    (stage/'docs/SHA256SUMS.txt').write_text(''.join(f'{v}  {k}\n' for k,v in sums.items()))
    archive=Path('dist')/(NAME+'.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for x in sorted(stage.rglob('*')):
            if x.is_file():
                info=zipfile.ZipInfo(NAME+'/'+x.relative_to(stage).as_posix(),(2026,10,15,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,x.read_bytes())
    with zipfile.ZipFile(archive) as z:
        require(z.testzip() is None,'ZIP CRC failure')
        for k,v in sums.items():require(hashlib.sha256(z.read(NAME+'/'+k)).hexdigest()==v,'Archive member hash mismatch '+k)
    digest=sha(archive);Path(str(archive)+'.sha256').write_text(digest+'  '+archive.name+'\n')
    print('RC2_CLEAN_PACKAGE_PASS',digest,flush=True)

if __name__=='__main__':
    actions={'prepare':prepare,'stage':stage,'finish':finish}
    require(len(sys.argv)==2 and sys.argv[1] in actions,'Usage: pipeline.py prepare|stage|finish')
    actions[sys.argv[1]]()
