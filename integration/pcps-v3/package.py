#!/usr/bin/env python3
"""PCPS V3 visual selection & Main/dw_pcps/ profile package; parent exact SAFE Clean #41297344177."""
import argparse,io,json,hashlib,zipfile,struct
from pathlib import Path
BASE="DarkWolf_PointShadow_SAFE_Clean_Production_TextureV2_Boss1_2026-11-01_Win64"
NAME="DarkWolf_PCPS_V3_AIM_PICK_VISUAL_FOLDER_Win64"
BASE_SHA="887cc7c7e8b6b66bed039aebda80486b10b80596c9990eeac720fd0d9ca32885"
BASE_DLL_SHA="3e436aa1a52f424574622af6702aabb2eccef2b2733965d42949eecbdc67cdb2"
def H(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--outer-artifact",type=Path,required=True)
 p.add_argument("--renderer",type=Path,required=True)
 p.add_argument("--out",type=Path,required=True)
 p.add_argument("--proof",type=Path,required=True)
 a=p.parse_args()
 with zipfile.ZipFile(a.outer_artifact) as z:
  assert z.testzip() is None
  nested="dist/"+BASE+".zip"
  raw=z.read(nested)
  assert H(raw)==BASE_SHA,("SAFE baseline changed",H(raw))
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  assert z.testzip() is None
  files={n[len(BASE)+1:]:z.read(n) for n in z.namelist() if n.startswith(BASE+"/") and not n.endswith("/")}
 assert len(files)==63,len(files)
 assert H(files["renderer_sp_rend2_x64.dll"])==BASE_DLL_SHA
 dll=a.renderer.read_bytes()
 assert dll[:2]==b"MZ"
 pe=struct.unpack_from("<I",dll,60)[0]
 assert dll[pe:pe+4]==b"PE\0\0"
 for required in (b"dw_ps_lights",b"dw_ps_picklight",b"dw_ps_pickcaster",b"dw_ps_light_off",
                  b"dw_ps_caster_off",b"textures/metal_misc/ametal_m03dm",
                  b"r_dwA2C",b"r_dwLut",b"r_dwCas",
                  b"dw_ps_save",b"dw_ps_reload",b"dw_ps_file",
                  b"DWPCPS_V2",b"dw_pcps/",b"dw_ps_confirm",b"dw_ps_candidates",
                  b"dw_ps_overlay",b"PCPS V3: crosshair BSP",b"gfx/2d/hudchars"):
  assert required in dll,required
 for banned in (b"DW_PS_V5_SOURCE_LOCAL_SKIP",b"r_dwPointV5ProofMode",b"r_dwPointV4Mode"):
  assert banned not in dll,banned
 preserved={k:v for k,v in files.items() if k not in ("renderer_sp_rend2_x64.dll","docs/SHA256SUMS.txt")}
 files["renderer_sp_rend2_x64.dll"]=dll
 readme=Path(__file__).with_name("README.md").read_bytes()
 files["README_PCPS_V3_AIM_PICK_RU.md"]=readme
 proof=json.loads(a.proof.read_text(encoding="utf-8"))
 assert proof["parent_PCPS_V2_run"]==41427487879
 assert proof["parent_safe_clean_run"]==41297344177
 assert not proof["new_GLSL_shaders"] and not proof["new_CVar"] and not proof["new_GPU_shadows_or_slot_budgets"]
 assert proof["modified_renderer_sources"]==["SP/code/rend2/tr_main.c","SP/code/rend2/tr_scene.c"]
 assert proof["saved_profile_directory"]=="active fs_homepath/Main/dw_pcps"
 manifest={"kind":"PCPS_V3_AIM_PICK_VISUAL_FOLDER_EXPERIMENTAL_NOT_PRODUCTION",
   "accepted_parent_run":41297344177,
   "accepted_pcps_v1_run":41322232296,
   "accepted_pcps_v2_run":41427487879,
   "accepted_parent_renderer_sha256":BASE_DLL_SHA,
   "new_renderer_sha256":H(dll),
   "defaults":"all original graphics defaults unchanged",
   "lighting_shadow_reuse":"unchanged V2; 3 persistent and 2 dynamic slots",
   "candidate_picker":"BSP ray nearest hit and source angular ranks (top5)",
   "safety":"no shadow edits until dw_ps_confirm after preview",
   "overlay":"2D after postprocess, light IDs and candidate list and selected BSP mesh wire; controllable dw_ps_overlay",
   "persistence":"active fs_homepath/Main/dw_pcps/<map>_a.dat and _b.dat",
   "migration":"one-time valid V2 flat profile import only when V3 files absent, no removal of originals",
   "GPU_acceptance":"PENDING user test",
   "source_proof":proof}
 files["docs/PCPS_V3_MANIFEST.json"]=(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode()
 for k,v in preserved.items(): assert files[k]==v,k
 files["docs/SHA256SUMS.txt"]="".join(H(v)+"  "+k+"\n" for k,v in sorted(files.items()) if k!="docs/SHA256SUMS.txt").encode()
 a.out.mkdir(parents=True,exist_ok=True)
 output=a.out/(NAME+".zip")
 with zipfile.ZipFile(output,"w",zipfile.ZIP_DEFLATED,compresslevel=7) as z:
  for k,v in sorted(files.items()):
   zi=zipfile.ZipInfo(NAME+"/"+k,(2026,11,1,12,0,0))
   zi.external_attr=0o100644<<16
   zi.compress_type=zipfile.ZIP_DEFLATED
   z.writestr(zi,v)
 with zipfile.ZipFile(output) as z:
  assert z.testzip() is None
  out={k[len(NAME)+1:]:z.read(k) for k in z.namelist()}
  for row in out["docs/SHA256SUMS.txt"].decode().splitlines():
   digest,k=row.split("  ",1);assert H(out[k])==digest,k
  assert all(out[k]==v for k,v in preserved.items())
 (a.out/(NAME+".zip.sha256")).write_text(H(output.read_bytes())+"  "+output.name+"\n")
 print("DW_PCPS_V3_VISUAL_PICK_FOLDER_PACKAGE_VERIFIED",H(dll),H(output.read_bytes()),len(files))
if __name__=="__main__":main()
