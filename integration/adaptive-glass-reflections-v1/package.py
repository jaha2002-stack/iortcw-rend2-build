#!/usr/bin/env python3
"""Package exact #41297344177 parent, modifying renderer DLL only (plus docs and hashes)."""
import argparse,hashlib,io,json,struct,zipfile
from pathlib import Path
NAME="DarkWolf_Adaptive_Glass_Reflections_V1_Clean_Candidate_Win64"
PARENT="DarkWolf_PointShadow_SAFE_Clean_Production_TextureV2_Boss1_2026-11-01_Win64"
PARENT_SHA="887cc7c7e8b6b66bed039aebda80486b10b80596c9990eeac720fd0d9ca32885"
PARENT_DLL_SHA="3e436aa1a52f424574622af6702aabb2eccef2b2733965d42949eecbdc67cdb2"
H=lambda b:hashlib.sha256(b).hexdigest()
README="""DarkWolf Adaptive Glass Reflections V1 — first build from accepted #41297344177.
Static cubemap/Fresnel only. NO screen-space or dynamic reflection update.
Default: r_dwGlassReflect 1, r_dwGlassIntensity 0.60, r_dwGlassAutoDetect 1.
New cvars: glass reflect and auto-detect are latched; /vid_restart after changing.
Original r_cubeMapping remains unchanged and original water path remains isolated.
Old RTCW windows need a glass/window/pane material or SURF_GLASS; some painted
walls do not contain separate glass geometry and cannot reflect.
Existing BSP cubemap entities, AI markers or env.json supply the environment.
If a map has NO valid probe, reflection is intentionally suppressed (fail safe).
Preserve every existing profile and existing HDR, CAS, LUT, A2C, shadows, SSGI,
Sun, Volumetric and Fire/Tesla logic. No SSR or runtime probe updates.
IMPORTANT: CI compilation and static tests do not establish visual correctness on
your actual GPU. Compare identical scenes before declaring final acceptance.
Restore parent renderer DLL for rollback.
"""
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--outer",required=True,type=Path)
 p.add_argument("--renderer",required=True,type=Path)
 p.add_argument("--proof",required=True,type=Path)
 p.add_argument("--out",required=True,type=Path)
 a=p.parse_args()
 with zipfile.ZipFile(a.outer) as z:
  assert z.testzip() is None
  path="dist/"+PARENT+".zip"
  raw=z.read(path)
  assert H(raw)==PARENT_SHA,(H(raw),PARENT_SHA)
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  assert z.testzip() is None
  old={n[len(PARENT)+1:]:z.read(n) for n in z.namelist() if n.startswith(PARENT+"/") and not n.endswith("/")}
 assert len(old)==63,len(old)
 assert H(old["renderer_sp_rend2_x64.dll"])==PARENT_DLL_SHA
 for tier in ("PERFORMANCE","BALANCED","QUALITY","HIGH","ULTRA"):
  assert "Main/DW_HDR16F_V1_"+tier+".cfg" in old
 dll=a.renderer.read_bytes()
 assert dll[:2]==b"MZ" and H(dll)!=PARENT_DLL_SHA
 off=struct.unpack_from("<I",dll,60)[0]
 assert dll[off:off+4]==b"PE\x00\x00"
 for required in (b"r_dwGlassReflect",b"r_dwGlassIntensity",b"r_dwGlassAutoDetect",b"dwglass",
                  b"DARKWOLF_ADAPTIVE_GLASS_V1",b"_dwSunHalfRGBA16F",b"r_dwTextureFidelity",
                  b"r_dwMaterialFidelity",b"r_dwLut",b"r_dwA2C"):
  assert required in dll,required
 proof=json.loads(a.proof.read_text())
 assert proof["base_run"]==41297344177 and proof["dynamic_reflections"]==False
 files=dict(old);files["renderer_sp_rend2_x64.dll"]=dll
 files["README_ADAPTIVE_GLASS_RU.txt"]=README.encode()
 files["docs/DW_ADAPTIVE_GLASS_V1_MANIFEST.json"]=(json.dumps({
  "base_run":41297344177,"base_release_sha256":PARENT_SHA,
  "parent_renderer_sha256":PARENT_DLL_SHA,"new_renderer_sha256":H(dll),
  "type":"CLEAN_CANDIDATE_AWAITING_USER_GPU_AB_VISUAL_ACCEPTANCE",
  "new_runtime_cvars":["r_dwGlassReflect","r_dwGlassAutoDetect","r_dwGlassIntensity"],
  "no_SSR":True,"no_dynamic_cubemap_refresh":True,
  "old_files_byte_identical_except_renderer_and_checksum":61,
  "unverified":"visual reflections across retail RTCW maps and GPU",
  "source_proof":proof
 },indent=2)+"\n").encode()
 files["docs/SHA256SUMS.txt"]="".join(H(v)+"  "+k+"\n" for k,v in sorted(files.items()) if k!="docs/SHA256SUMS.txt").encode()
 assert len(files)==65
 for n in old:
  if n not in ("renderer_sp_rend2_x64.dll","docs/SHA256SUMS.txt"):
   assert old[n]==files[n],n
 a.out.mkdir(exist_ok=True,parents=True)
 out=a.out/(NAME+".zip")
 with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED,compresslevel=7) as z:
  for path,data in sorted(files.items()):
   info=zipfile.ZipInfo(NAME+"/"+path,(2026,11,1,12,0,0))
   info.external_attr=0o100644<<16
   info.compress_type=zipfile.ZIP_DEFLATED
   z.writestr(info,data)
 with zipfile.ZipFile(out) as z:
  assert z.testzip() is None and len(z.namelist())==65
  for line in files["docs/SHA256SUMS.txt"].decode().splitlines():
   digest,path=line.split("  ",1)
   assert digest==H(z.read(NAME+"/"+path))
 (a.out/(NAME+".zip.sha256")).write_text(H(out.read_bytes())+"  "+out.name+"\n")
 print("DW_ADAPTIVE_GLASS_CLEAN_CANDIDATE_65_FILES_VERIFIED",H(dll),H(out.read_bytes()))
if __name__=="__main__":main()
