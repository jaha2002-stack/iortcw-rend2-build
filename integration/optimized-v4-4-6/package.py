#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,zipfile,struct
root=Path(__file__).resolve().parent;repo=root.parent.parent
src=Path(sys.argv[1]);base=Path(sys.argv[2]);evidence=Path(sys.argv[3]);dist=Path(sys.argv[4]);dist.mkdir(exist_ok=True)
name='DarkWolf-ioRTCW-Rend2-v4.4.6-Optimized-Clean-Candidate-Win64-SP'
stage=dist/name
if stage.exists():raise SystemExit('Refusing to overwrite staging directory')
(stage/'Main').mkdir(parents=True);(stage/'docs').mkdir()
lock=json.loads((root/'baseline_source_manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
build=src/'SP/build/release-mingw32-x86_64'; baseline=base/'SP/build/release-mingw32-x86_64'
files=['ioWolfSP.x64.exe','renderer_sp_rend2_x64.dll','main/cgame_sp_x64.dll','main/qagame_sp_x64.dll','main/ui_sp_x64.dll']
def pe(p):
 b=p.read_bytes();assert b[:2]==b'MZ',p
 off=struct.unpack_from('<I',b,0x3c)[0];assert b[off:off+4]==b'PE\0\0' and struct.unpack_from('<H',b,off+4)[0]==0x8664,p
 for marker in [b'DWPERF_FRAME',b'DWPERF_PROBE',b'DWPERF_CFG',b'DARKWOLF_V446_FULL_PERF_TELEMETRY_V01',b'DARKWOLF_TESTLAB_V0_1']:
  assert marker not in b,(p,marker)
 return b
comparison={}
for name0 in files:
 target=name0.replace('main/','Main/');p=build/name0;b=pe(p);pe(baseline/name0)
 shutil.copy2(p,stage/target)
 comparison[target]={'baseline_rebuild_sha256':sha(baseline/name0),'optimized_sha256':sha(p),'historical_binary_sha256':lock['baseline_binaries'][target]}
 if 'renderer_sp_rend2' not in name0:assert sha(p)==sha(baseline/name0),('unchanged component differs',name0)
assert b'DARKWOLF_VOLUMETRIC_COVERAGE_AA_FINAL_V1' in (stage/'renderer_sp_rend2_x64.dll').read_bytes()
for path,digest in lock['payload'].items():
 p=(src/'SP/code/libs/win64'/path) if path.endswith('.dll') else (root/'payload'/path)
 assert sha(p)==digest;shutil.copy2(p,stage/path)
for f in ['RUN_DARKWOLF_OPTIMIZED_CLEAN.bat','README_INSTALL_RU.md']:
 shutil.copy2(root/f,stage/f)
shutil.copy2(root/'PRODUCTION_HIGH_QUALITY.cfg',stage/'Main/PRODUCTION_HIGH_QUALITY.cfg')
shutil.copy2(src/'SP/COPYING.txt',stage/'COPYING.txt')
shutil.copy2(src/'LICENCE.md',stage/'LICENCE.md')
# Upstream ships SDL/OpenAL licensing with these runtime dependencies.
for p in (src/'SP/code/libs/win64').iterdir():
 if p.is_file() and p.suffix.lower() in ['.txt','.md']:shutil.copy2(p,stage/'docs'/p.name)
provenance={'status':'CANDIDATE_FOR_LOCAL_VERIFICATION','builder_sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),'baseline_source_tree':lock['baseline_source_tree'],'upstream_sha':lock['upstream_sha'],'patches':lock['patches'],'optimized_patch_sha256':sha(root/'optimized.patch'),'binary_comparison':comparison,'GPU_PERFORMANCE':'NOT_RUN','WINDOWS_RUNTIME':'NOT_RUN','VISUAL_ACCEPTANCE':'NOT_RUN','source_url':'https://github.com/jaha2002-stack/iortcw-rend2-build/tree/rend2-v4-4-6-clean-optimization','compile_flags':'see evidence build.log; baseline Makefile flags, no new optimization flags'}
(stage/'docs/BUILD_PROVENANCE.json').write_text(json.dumps(provenance,indent=2)+'\n')
shutil.copy2(repo/'docs/optimization-v4-4-6/OPTIMIZATION_DECISIONS.md',stage/'CHANGELOG_OPTIMIZATION_RU.md')
paths=sorted(p for p in stage.rglob('*') if p.is_file())
assert not any(p.name.lower().startswith('pak') and p.suffix.lower()=='.pk3' for p in paths)
hashes={p.relative_to(stage).as_posix():sha(p) for p in paths}
(stage/'docs/SHA256SUMS.txt').write_text(''.join(f'{v}  {k}\n' for k,v in hashes.items()))
with zipfile.ZipFile(dist/(name+'.zip'),'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(stage.rglob('*')):
  if p.is_file():
   info=zipfile.ZipInfo(str(p.relative_to(dist)),(2026,10,5,5,13,12));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,p.read_bytes())
p=dist/(name+'.zip')
with zipfile.ZipFile(p) as z:
 assert z.testzip() is None
 for key,value in hashes.items():assert hashlib.sha256(z.read(name+'/'+key)).hexdigest()==value
(dist/(name+'.zip.sha256')).write_text(sha(p)+'  '+p.name+'\n')
(dist/'BUILD_PROVENANCE.json').write_text(json.dumps(provenance,indent=2)+'\n')
(evidence/'binary-comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
print('CLEAN_PACKAGE_INTEGRITY_PASS',sha(p))
