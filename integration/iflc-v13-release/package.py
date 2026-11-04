#!/usr/bin/env python3
"""Full isolated Win64 TEST, exact accepted runtime + only new renderer.
Never execute or include TestLab hooks before this script completes.
"""
from pathlib import Path,PurePosixPath
import hashlib,json,zipfile,tarfile,subprocess,io,os,struct,re
src=Path('source');ev=Path('evidence');out=Path('dist');out.mkdir(exist_ok=True)
kit=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
archive=ev/'accepted-v12-runtime.zip'
with archive.open('wb') as f:subprocess.run(['gh','api','repos/jaha2002-stack/iortcw-rend2-build/actions/artifacts/13295866558/zip'],stdout=f,check=True)
assert sha(archive.read_bytes())=='64bd28780349c0008e9dd6b1fd995a1459f25e3267efbdc6935c623513710cc7'
def unpack(raw):
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  assert z.testzip() is None
  files={}
  for m in z.infolist():
   if m.is_dir():continue
   p=PurePosixPath(m.filename)
   assert not p.is_absolute() and '..' not in p.parts and '\\' not in m.filename
   assert m.filename not in files
   files[m.filename]=z.read(m)
  return files
outer=unpack(archive.read_bytes());inner=[v for k,v in outer.items() if k.endswith('DarkWolf_IFLC_V1.2_FROM_41758201175_Win64_TEST.zip')];assert len(inner)==1
assert sha(inner[0])=='e6496e99f7323291aedda248074fbfb175a0404a772720245ad40fb1758f5441'
base=unpack(inner[0]);root=next(iter(base)).split('/')[0]+'/';assert all(k.startswith(root) for k in base)
base={k[len(root):]:v for k,v in base.items()}
base_status=json.loads(base['BUILD_STATUS.json']);assert base_status['run']=='41772470237'
assert sha(base['renderer_sp_rend2_x64.dll'])=='0a834ec6075f4c159deec003100fc150e900db47df1ccf7b865324f6cdb277d8'
for line in base['SHA256SUMS.txt'].decode().splitlines():
 digest,name=line.split('  ',1);assert sha(base[name])==digest,name
before=json.loads((ev/'IFLC13_BASE_SHA256.json').read_text())
code={p.relative_to(src).as_posix():p.read_bytes() for p in (src/'SP/code').rglob('*') if p.is_file()}
now={k:sha(v) for k,v in code.items()}
changed=[k for k in sorted(set(now)|set(before)) if before.get(k)!=now.get(k)]
expected=['SP/code/rend2/glsl/volumetriclocal_fp.glsl','SP/code/rend2/tr_backend.c','SP/code/rend2/tr_bsp.c','SP/code/rend2/tr_electric_fixture.inc','SP/code/rend2/tr_local.h','SP/code/rend2/tr_main.c','SP/code/rend2/tr_surface.c']
assert changed==expected,(changed,expected)
assert len(before)==1649 and len(now)==1650
for name in ('tr_iflc.inc','tr_iflc_fixture.inc','tr_scene.c','tr_world.c','tr_shade.c'):
 path='SP/code/rend2/'+name;assert now[path]==before[path],name
assert sha((src/'SP/Makefile').read_bytes())=='9cb33a3b0ce2e449edd449fb97c885a1174c868ce5e77c9b84b0645518351740'
bins=list((src/'SP/build').rglob('renderer_sp_rend2_x64.dll'));assert len(bins)==1
dll=bins[0].read_bytes()
for marker in (b'r_iflc13Electric',b'r_iflc13FireWorld',b'r_iflc13DirectMask',b'dw_fl13_',b'r_iflc12Legacy',b'r_iflc12CastleMask',b'dw_fl12_',b'r_iflcFixtureTestBypass',b'r_iflcShadowAudit'):
 assert marker not in dll,marker
assert b'dw_fl_select' in dll and b'fixtureSelfCasters' in dll
entries=dict(base)
for name in ('BUILD_STATUS.json','README_RU.txt','SHA256SUMS.txt'):
 entries['docs/base-41772470237/'+name]=entries.pop(name)
entries['renderer_sp_rend2_x64.dll']=dll
entries['README_V13_RU.md']=(kit/'README_RU.md').read_bytes()
pe={}
for name,data in entries.items():
 if not name.lower().endswith(('.exe','.dll')):continue
 assert data[:2]==b'MZ',name;o=struct.unpack_from('<I',data,60)[0]
 assert data[o:o+4]==b'PE\0\0' and struct.unpack_from('<H',data,o+4)[0]==0x8664 and struct.unpack_from('<H',data,o+24)[0]==0x20b
 pe[name]={'sha256':sha(data),'bytes':len(data),'base_byte_identical':name!='renderer_sp_rend2_x64.dll' and base.get(name)==data}
assert len(pe)==8
unchanged={n:sha(v) for n,v in base.items() if n not in ('renderer_sp_rend2_x64.dll','BUILD_STATUS.json','README_RU.txt','SHA256SUMS.txt')}
assert all(entries[n]==base[n] for n in unchanged)
profiles={n:sha(v) for n,v in base.items() if re.search(r'DW_HDR16F_V1_(PERFORMANCE|BALANCED|QUALITY|HIGH|ULTRA)\.cfg$',n)}
assert len(profiles)==5 and all(entries[n]==base[n] for n in profiles)
status={'status':'TEST_CANDIDATE','base_run':41772470237,'run':os.environ.get('GITHUB_RUN_ID'),'commit':os.environ.get('GITHUB_SHA'),'renderer_sha256':sha(dll),'changed_source_files':changed,'verified_base_source_files':1649,'source_files':1650,'unchanged_base_files':unchanged,'pe_modules':pe,'quality_profiles':profiles,'iflc_v12_code_and_profiles_unchanged':True,'direct_light_code_unchanged':True,'new_production_cvars':[],'diagnostic_hooks_in_shipped_dll':False,'synthetic_capture_experiment_included':False,'causal_evidence_run':41789875771,'visual_status':'Causal images reviewed separately; final runtime evidence is a separate job','windows_gpu_performance':'NOT_MEASURED','scope':'Recognized own electrical housing and architectural FireVol gate when uniquely associated existing world capture is available; no claim of all lamps or Direct leak correction'}
entries['BUILD_STATUS.json']=(json.dumps(status,indent=2)+'\n').encode()
for name in ('IFLC13_ELECTRIC_PROOF.json','IFLC13_RELEASE_PROOF.json'):
 entries['docs/v13/'+name]=(ev/name).read_bytes()
entries['SHA256SUMS.txt']=''.join(sha(v)+'  '+n+'\n' for n,v in sorted(entries.items())).encode()
name='DarkWolf_IFLC_V1.3_FROM_41772470237_Win64_TEST';zpath=out/(name+'.zip')
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for n,v in sorted(entries.items()):z.writestr(name+'/'+n,v)
check=unpack(zpath.read_bytes());assert len(check)==len(entries)
for n,v in entries.items():assert check[name+'/'+n]==v
with tarfile.open(out/'IFLC_V13_EXACT_SOURCE.tar.gz','w:gz') as t:
 t.add(src/'SP/code',arcname='SP/code');t.add(src/'SP/Makefile',arcname='SP/Makefile')
(ev/'IFLC13_RELEASE_SOURCE_SHA256.json').write_text(json.dumps(now,indent=2)+'\n')
(ev/'IFLC13_PACKAGE_CHECK.json').write_text(json.dumps(status,indent=2)+'\n')
(out/'SHA256SUMS.txt').write_text(''.join(sha(p.read_bytes())+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file() and p.name!='SHA256SUMS.txt'))
print(json.dumps({'package':zpath.name,'bytes':zpath.stat().st_size,'sha256':sha(zpath.read_bytes()),'renderer_sha256':sha(dll),'files':len(entries),'unchanged_base_files':len(unchanged),'unchanged_quality_profiles':len(profiles),'pe_modules':len(pe),'source_files':len(now),'status':'TEST_CANDIDATE_NOT_A_BASELINE_REPLACEMENT'},indent=2))
