#!/usr/bin/env python3
"""Repackage exact #40512393634 accepted Sun3+FireE runtime, replacing only Rend2 DLL."""
import argparse,hashlib,io,json,re,zipfile
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument("--base-zip",type=Path,required=True)
p.add_argument("--renderer",type=Path,required=True)
p.add_argument("--proof",type=Path,required=True)
p.add_argument("--tests",type=Path,required=True)
p.add_argument("--out",type=Path,required=True)
a=p.parse_args()
H=lambda b:hashlib.sha256(b).hexdigest()
BASE_RUN=40512393634
BASE_ARCHIVE_SHA="f8c2a08ae6185123a2eb01b15a4be66bb457465563e3781bdd5688adc7e00460"
BASE_RENDERER_SHA="1c6804154166b7bff22e9225cc10c6729ffdf72b3e1c350c5d2df63b11b19bcc"
MARK="DARKWOLF_CRYPT1_PERSISTENT_FIRE_SHADOW_PRIORITY_FIX_V1_20261028"
base=a.base_zip.read_bytes()
assert H(base)==BASE_ARCHIVE_SHA,("WRONG_SUN3_FIRE_E_BASE",H(base))
newdll=a.renderer.read_bytes()
assert newdll[:2]==b"MZ" and len(newdll)>2000000
assert H(newdll)!=BASE_RENDERER_SHA
proof=json.loads(a.proof.read_text())
tests=json.loads(a.tests.read_text())
assert proof["marker"]==MARK and proof["source_base_run"]==BASE_RUN
assert proof["modified_source_files"]==["SP/code/rend2/tr_main.c"]
assert proof["new_cvars"]==[] and proof["telemetry"] is False
assert tests["marker"]==MARK and tests["no_new_cvars"] is True and len(tests["numeric_regression_cases"])>=12
assert all(tests["static_checks"].values())
with zipfile.ZipFile(io.BytesIO(base)) as z:
 assert z.testzip() is None
 original={i.filename:z.read(i) for i in z.infolist() if not i.is_dir()}
assert len(original)==33,("ORIGINAL_FILE_COUNT_CHANGED",len(original))
root="DarkWolf_Sky404801_Sun3_FireE_Clean_Production_Win64"
assert {k.split("/")[0] for k in original}=={root}
assert all(k.startswith(root+"/") and ".." not in Path(k).parts for k in original)
renderer="renderer_sp_rend2_x64.dll"
assert H(original[root+"/"+renderer])==BASE_RENDERER_SHA
for must in (
 "ioWolfSP.x64.exe","renderer_sp_opengl1_x64.dll",
 "Main/cgame_sp_x64.dll","Main/qagame_sp_x64.dll","Main/ui_sp_x64.dll",
 "Main/DW_SUN3_FIRE_E_PRODUCTION.cfg"):
 assert root+"/"+must in original
entries={k.split("/",1)[1]:v for k,v in original.items()}
entries[renderer]=newdll
assert not any(re.search(r"(^|/)pak[0-9]*\.pk3$",k,re.I) for k in entries)
manifest={
  "release":"DarkWolf_Crypt1_Shadow_Priority_Clean_Production_V1",
  "base_run":BASE_RUN,"base_archive_sha256":BASE_ARCHIVE_SHA,
  "base_renderer_sha256":BASE_RENDERER_SHA,
  "new_renderer_sha256":H(newdll),
  "source":proof,
  "unit_tests":{"cases":len(tests["numeric_regression_cases"]),"all_pass":True},
  "changed_existing_files":[renderer,"docs/SHA256SUMS.txt"],
  "unchanged_existing_files":len(original)-2,
  "added_files":["docs/CRYPT1_SHADOW_PRIORITY_CLEAN_MANIFEST.json",
                 "README_CRYPT1_SHADOW_PRIORITY_CLEAN_RU.txt"],
  "preserved":["Sun3 dual visibility","FireE 5x5 9tap 40 steps",
               "Local user-approved","Sky Single-Sample",
               "CSM primary areamask guard","SSGI","Tesla",
               "physical lamp fixture grouping","3 persistent + 2 dynamic shadow slots"],
  "no_new_cvars":True,"no_telemetry":True,
  "known_limitations":[
      "GPU quality on Crypt1 must still be accepted by the user",
      "The September 8 build already documented a separate local-player-shadow defect",
      "Fix targets proven priority inversion risk; Crypt1-specific causal verification needs A/B runtime"],
  "status":"CI_CLEAN_PRODUCTION_CANDIDATE_GPU_ACCEPTANCE_PENDING"
}
entries["docs/CRYPT1_SHADOW_PRIORITY_CLEAN_MANIFEST.json"]=(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n").encode("utf8")
readme="""DarkWolf Crypt1 Shadow Priority - Clean Production Candidate V1
============================================================
Exact runtime base: Sun3 + FireE Clean Production, GitHub Actions #40512393634.
This is a real compiled Win64 Rend2 renderer, not a CFG-only change.

Surgical correction: in R_RenderDlightCubemaps the late physical shadow
resident-set could fill all 3 persistent slots before a much stronger
visible PERSISTENT_FIRE source was considered. One weakest physical resident
may now be released *only* when a visible eligible persistent fire beats its
shadow selection score by the existing hysteresis threshold (minimum 25%).
The original score-based selector still chooses the new owner. Legacy
history-hold cannot silently restore the evicted owner in the same frame.

UNCHANGED:
- Three persistent physical/fire shadow slots, two transient slots.
- Stable StaticPromote grouping/capture and Direct lights.
- 2048 default point-shadow cubemap size; shadow filter/bias.
- Stage11 material caster/receiver logic and alpha cutout shadows.
- Sun3 Dual Visibility, Fire E 5x5/9-tap, Local, Sky Single-Sample.
- CSM Guard, SSGI, Tesla, Bloom v2, gameplay binaries, PBR exclusion.
- No new CVars, no telemetry or diagnostic modes.

A/B GAME TESTS, WITH THE EXACT SAME CFG/SAVE/VIEW:
1. Crypt1: start flames, player shadow, nearby torch surfaces, walk between
   several nearby fires and promoted lights. Record still screenshots and
   short video (shadows should not disappear on camera movement).
2. Escape1: stove/player shadow, guard room, doctor room, native lamps.
3. SWF: three lamps in a row, confirm stable ownership and no flicker.
4. Factory: room with broken window, fire shadows and SSGI lamp halo.
5. Assault/Forest: directional Sun3, CSM, Sky Single-Sample.
6. Test Fire E and Local shadow receiver without changing their settings.
7. Compare FPS / frametimes for Crypt1 and Escape1 for 10s per fixed camera.

Baseline rollback: keep original #40512393634 in a separate folder.
This candidate passes source/binary/static checks but no external GPU run has
yet proved the specific Crypt1 symptom fixed. The Sep 8 release itself
recorded an older player-shadow defect, not automatically fixed here.
Licensed RTCW pak*.pk3 game assets are NOT included.
"""
entries["README_CRYPT1_SHADOW_PRIORITY_CLEAN_RU.txt"]=readme.encode("utf8")
entries["docs/SHA256SUMS.txt"]=("".join(H(v)+"  "+k+"\n" for k,v in sorted(entries.items())
                                          if k!="docs/SHA256SUMS.txt")).encode("ascii")
assert len(entries)==len(original)+2
a.out.mkdir(parents=True,exist_ok=True)
stem="DarkWolf_Sun3_FireE_Crypt1_Shadow_Priority_Clean_Production_Win64"
outfile=a.out/(stem+".zip")
with zipfile.ZipFile(outfile,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
 for k,v in sorted(entries.items()):
  info=zipfile.ZipInfo(stem+"/"+k,date_time=(2026,10,28,0,0,0))
  info.compress_type=zipfile.ZIP_DEFLATED
  z.writestr(info,v)
with zipfile.ZipFile(outfile) as z:
 assert z.testzip() is None
 found={k.split("/",1)[1]:z.read(k) for k in z.namelist() if not k.endswith("/")}
 assert len(found)==len(entries)
 assert H(found[renderer])==H(newdll)
 assert not any("VOL_DIAG" in n or "DW_SUN_V3_" in n for n in found)
 for key,blob in original.items():
  rel=key.split("/",1)[1]
  if rel not in (renderer,"docs/SHA256SUMS.txt"):
   assert found[rel]==blob,("REGRESSION_EXISTING_FILE",rel)
 assert "seta r_volumetricFireSamples \"40\"" in found["Main/DW_SUN3_FIRE_E_PRODUCTION.cfg"].decode()
manifest["archive_sha256"]=H(outfile.read_bytes())
(a.out/(outfile.name+".sha256")).write_text(manifest["archive_sha256"]+"  "+outfile.name+"\n")
(a.out/"CRYPT1_SHADOW_PRIORITY_FINAL_AUDIT.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
print("DW_CRYPT1_SHADOW_CLEAN_ARCHIVE_PASS",str(outfile),"sha256="+manifest["archive_sha256"],
      "renderer="+H(newdll),"unchanged_existing="+str(len(original)-2))
