#!/usr/bin/env python3
"""PCPS V5 separate FireVol/point/world and shadow provenance, exact accepted SAFE Clean."""
import argparse,io,json,hashlib,zipfile,struct
from pathlib import Path
BASE="DarkWolf_PointShadow_SAFE_Clean_Production_TextureV2_Boss1_2026-11-01_Win64"
NAME="DarkWolf_PCPS_V5_FIRE_PATH_ATTRIBUTION_Win64"
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
                  b"dw_ps_overlay",b"PCPS V3: crosshair BSP",b"gfx/2d/hudchars",
                  b"dw_ps_firepick",b"dw_ps_firelinks",b"PCPS V4 FIRE:",
                  b"textures/sfx/",b"dw_pcps/",
                  b"dw_ps_fire_link",b"dw_ps_fire_world_off",b"dw_ps_fire_point_off",
                  b"dw_ps_fire_audit_start",b"dw_ps_fire_audit_save",
                  b"PCPS V5 FIRE ATTRIBUTION",b"BAKED BSP LIGHTMAP: UNKNOWN"):
  assert required in dll,required
 for banned in (b"DW_PS_V5_SOURCE_LOCAL_SKIP",b"r_dwPointV5ProofMode",b"r_dwPointV4Mode"):
  assert banned not in dll,banned
 preserved={k:v for k,v in files.items() if k not in ("renderer_sp_rend2_x64.dll","docs/SHA256SUMS.txt")}
 files["renderer_sp_rend2_x64.dll"]=dll
 readme=Path(__file__).with_name("README_RU.md").read_bytes()
 files["README_PCPS_V5_FIRE_ATTRIBUTION_RU.md"]=readme
 proof=json.loads(a.proof.read_text(encoding="utf-8"))
 assert proof["feature"]=="PCPS_V5_SOURCE_LOCAL_FIRE_PATH_ATTRIBUTION"
 assert proof["parent_workflow"]==41443968165
 assert proof["accepted_clean"]==41297344177
 assert proof["unchanged_shader_files"] and proof["unchanged_cvars_defaults"]
 assert proof["changed_files"]==["SP/code/rend2/tr_main.c","SP/code/rend2/tr_backend.c"]
 assert proof["v4_sha256"]["tr_main.c"]=="fe45d4079c28610a25efe50988258a1a318b96ef4049ce7d8f5352f2affdbbe9"
 manifest={"kind":"PCPS_V5_FIRE_PATH_ATTRIBUTION_EXPERIMENTAL_NOT_CLEAN",
   "accepted_parent_run":41297344177,
   "accepted_pcps_v3_run":41435724668,
   "accepted_pcps_v4_run":41443968165,
   "accepted_parent_renderer_sha256":BASE_DLL_SHA,
   "new_renderer_sha256":H(dll),
   "defaults":"no graphics/shadow changes unless user invokes PCPS V5 controls",
   "separate_fire_channels":["FIREVOL_SYNTHETIC","DLIGHT_POINT","DLIGHT_WORLD_OCCLUSION"],
   "baked_lightmap":"diagnostic UNKNOWN, unchanged",
   "caster_proof":"source-local tess surfaces processed/excluded, NOT GPU depth owner",
   "stable_source_link":"manual fire-linked dlight confirmation, per-BSP SHA-protected original A/B",
   "world_occlusion_warning":"opt-in disable may cause architectural light leaks",
   "gpu_acceptance":"PENDING user GPU test, no default enablement",
   "source_proof":proof}
 files["docs/PCPS_V5_MANIFEST.json"]=(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode()
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
 print("DW_PCPS_V5_ATTRIBUTION_PACKAGE_VERIFIED",H(dll),H(output.read_bytes()),len(files))
if __name__=="__main__":main()
