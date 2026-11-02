#!/usr/bin/env python3
"""PCPS V4 optional FireVol source-specific shadow control, inherited V3 picker and safe base."""
import argparse,io,json,hashlib,zipfile,struct
from pathlib import Path
BASE="DarkWolf_PointShadow_SAFE_Clean_Production_TextureV2_Boss1_2026-11-01_Win64"
NAME="DarkWolf_PCPS_V4_FIRE_SOURCE_CONTROL_CRYPT1_Win64"
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
                  b"textures/sfx/",b"dw_pcps/"):
  assert required in dll,required
 for banned in (b"DW_PS_V5_SOURCE_LOCAL_SKIP",b"r_dwPointV5ProofMode",b"r_dwPointV4Mode"):
  assert banned not in dll,banned
 preserved={k:v for k,v in files.items() if k not in ("renderer_sp_rend2_x64.dll","docs/SHA256SUMS.txt")}
 files["renderer_sp_rend2_x64.dll"]=dll
 readme=Path(__file__).with_name("README_RU.md").read_bytes()
 files["README_PCPS_V4_FIRE_SOURCE_RU.md"]=readme
 proof=json.loads(a.proof.read_text(encoding="utf-8"))
 assert proof["base_pcps_v3_run"]==41435724668
 assert proof["accepted_safe_clean_run"]==41297344177
 assert not proof["new_cvars"] and not proof["new_shaders"] and not proof["new_shadow_slots"]
 assert proof["changed_renderer_sources"]==["SP/code/rend2/tr_main.c","SP/code/rend2/tr_backend.c"]
 assert proof["file_format"].startswith("V3 DWPCPS_V2")
 manifest={"kind":"PCPS_V4_FIRE_SOURCE_CONTROL_CRYPT1_EXPERIMENTAL_NOT_CLEAN",
   "accepted_parent_run":41297344177,
   "accepted_pcps_v3_run":41435724668,
   "accepted_parent_renderer_sha256":BASE_DLL_SHA,
   "new_renderer_sha256":H(dll),
   "defaults":"no changes to HDR16F, CSM, SSGI, Bloom, Fire/Tesla defaults or visual CFG",
   "fire_flame_selector":"world BSP flame shader xflame2, torch_ember and selected flame families",
   "source_identity":"fire source BSP surface ID plus FireVol hint origin; ordinary DLight remains independent",
   "shadow_behavior":"explicit user opt-in, FireVol synthetic capture and cached receiver only",
   "per_caster":"source-local only on VPF_FIREVOL_SYNTHETIC_SHADOW shadow map",
   "persistence":"existing V3 checksummed Main/dw_pcps/ A/B files, fire sourceClass 254",
   "gpu_acceptance":"PENDING user testing on Crypt1, Escape1 and regression Factory",
   "source_proof":proof}
 files["docs/PCPS_V4_FIRE_MANIFEST.json"]=(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode()
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
 print("DW_PCPS_V4_FIRE_CONTROL_PACKAGE_VERIFIED",H(dll),H(output.read_bytes()),len(files))
if __name__=="__main__":main()
