from pathlib import Path
import hashlib,json,subprocess,sys
root,baseline,out=map(Path,sys.argv[1:]);changed=[]
for p in (root/'SP/code').rglob('*'):
 if p.is_file() and p.read_bytes()!=(baseline/p.relative_to(root)).read_bytes():changed.append(p.relative_to(root).as_posix())
assert sorted(changed)==['SP/code/rend2/tr_main.c','SP/code/rend2/tr_scene.c'],changed
for p in (root/'SP/code/rend2').rglob('*'):
 if p.is_file():
  b=p.read_bytes()
  assert not any(x in b for x in [b'DWPERF_FRAME',b'DWPERF_PROBE',b'DARKWOLF_V446_FULL_PERF_TELEMETRY_V01'])
scene=(root/'SP/code/rend2/tr_scene.c').read_text();main=(root/'SP/code/rend2/tr_main.c').read_text()
assert 'R_StaticPromoteReportIfChanged(' not in scene
assert 'selectionSignature * 33' not in scene
assert main.count('s_dwShadowGroupLabelsActive = qtrue;')==1
assert main.count('s_dwShadowGroupLabelsActive = qfalse;')==2
start=main.index('s_dwShadowGroupLabelsActive = qtrue;');end=main.index('s_dwShadowGroupLabelsActive = qfalse;',start)
assert 'return;' not in main[start:end] # Cache always deactivated before leaving invocation.
assert 'DARKWOLF_VOLUMETRIC_COVERAGE_AA_FINAL_V1' in (root/'SP/code/rend2/glsl/volumetriclocal_upscale_fp.glsl').read_text()
assert 'DarkWolf_InjectIngameSystemRend2Tab' in (root/'SP/code/ui/ui_shared.c').read_text()
assert '+safe' in (Path(__file__).parent/'RUN_DARKWOLF_OPTIMIZED_CLEAN.bat').read_text()
result={'status':'PASS','changed':changed,'all_other_source_files_byte_identical':True,'shaders_byte_identical':True,'changed_sha256':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in changed}}
(out/'source-policy.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
