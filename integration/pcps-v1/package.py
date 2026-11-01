#!/usr/bin/env python3
"""PCPS opt-in experimental Win64 package, based on exact SAFE Clean #41297344177."""
import argparse,io,json,hashlib,zipfile,struct
from pathlib import Path
BASE="DarkWolf_PointShadow_SAFE_Clean_Production_TextureV2_Boss1_2026-11-01_Win64"
NAME="DarkWolf_PCPS_V1_OPTIN_SHADOW_TOOL_Win64"
BASE_SHA="887cc7c7e8b6b66bed039aebda80486b10b80596c9990eeac720fd0d9ca32885"
BASE_DLL_SHA="3e436aa1a52f424574622af6702aabb2eccef2b2733965d42949eecbdc67cdb2"
def H(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--outer-artifact",type=Path,required=True)
 p.add_argument("--renderer",type=Path,required=True)
 p.add_argument("--out",type=Path,required=True)
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
                  b"dw_ps_caster_off",b"DARKWOLF_BOSS1_PROVEN_SOURCE_LOCAL_FIX_CLEAN_PRODUCTION_V1",
                  b"r_dwA2C",b"r_dwLut",b"r_dwCas"):
  assert required in dll,required
 for banned in (b"DW_PS_V5_SOURCE_LOCAL_SKIP",b"r_dwPointV5ProofMode",b"r_dwPointV4Mode"):
  assert banned not in dll,banned
 preserved={k:v for k,v in files.items() if k not in ("renderer_sp_rend2_x64.dll","docs/SHA256SUMS.txt")}
 files["renderer_sp_rend2_x64.dll"]=dll
 readme=(
 "DarkWolf PCPS V1 — OPT-IN EXPERIMENTAL CONTROL BUILD (not Clean Production)\n"
 "Parent: verified SAFE Clean #41297344177, Texture Fidelity #41286257713.\n"
 "Load game normally. All PCPS edits are OFF by default and session-only.\n"
 "Console: /dw_ps_help. Then /dw_ps_lights, /dw_ps_picklight or /dw_ps_select N.\n"
 "To turn off a selected light shadow AND free its cubemap slot: /dw_ps_light_off.\n"
 "To restore: /dw_ps_light_on. Direct lighting remains enabled.\n"
 "To select a world BSP object: aim at the object and /dw_ps_pickcaster.\n"
 "Then /dw_ps_caster_off or /dw_ps_caster_on for that SELECTED light only.\n"
 "To restore all: /dw_ps_reset. No saved overrides or config changes.\n"
 "CAVEAT: turning off a caster alone does NOT free a shadow slot; only light-shadow OFF does.\n"
 "The ray picker selects visible BSP triangles, not remote shadow depth owners.\n"
 "Point shadows with separate Fire/Tesla and Sun CSM paths are not edited.\n"
 "This is an experimental GPU acceptance candidate. GPU behavior is NOT yet validated.\n"
 "Revert by restoring renderer_sp_rend2_x64.dll from original SAFE Clean #41297344177.\n"
 )
 files["README_PCPS_V1_OPTIN_RU.txt"]=readme.encode("utf-8")
 manifest={"kind":"OPTIN_EXPERIMENTAL_NOT_PRODUCTION",
 "accepted_parent_run":41297344177,
 "accepted_parent_renderer_sha256":BASE_DLL_SHA,
 "new_renderer_sha256":H(dll),
 "defaults":"unchanged; opt in through console commands",
 "slots":"3 accepted persistent plus 2 accepted dynamic; no increase",
 "free_slot":"source-specific pending shadow bit exclusion before selection",
 "caster_exclusion":"source-specific ordinary point-shadow BSP only",
 "gpu_acceptance":"PENDING",
 "verification":"CI build, PE, feature markers, byte preservation; GPU pending"}
 files["docs/PCPS_V1_MANIFEST.json"]=(json.dumps(manifest,indent=2)+"\n").encode()
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
 print("DW_PCPS_V1_EXPERIMENTAL_PACKAGE_VERIFIED",H(dll),H(output.read_bytes()),len(files))
if __name__=="__main__":main()
