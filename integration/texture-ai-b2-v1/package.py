#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,zipfile

dist=Path("dist")
base=dist/"DarkWolf_Clean_Production_FireVol_Final_From_41982135692_Win64.zip"
third=Path("third_party/realesrgan_win")
assert base.exists(),base
assert third.exists(),third

sha=lambda b:hashlib.sha256(b).hexdigest()
entries={}
with zipfile.ZipFile(base) as z:
    assert z.testzip() is None
    roots={n.split("/",1)[0] for n in z.namelist() if "/" in n}
    assert len(roots)==1,roots
    for n in z.namelist():
        if n.endswith("/"): continue
        rel=n.split("/",1)[1]
        entries[rel]=z.read(n)

dll=entries["renderer_sp_rend2_x64.dll"]
for marker in (b"dw_tex_pick",b"dw_tex_ai_build",b"dw_tex_ai_info",
               b"dw_tex_ab",b"dw_tex_save",b"DWTR AI B2",
               b"realesrgan-x4plus"):
    assert marker in dll,marker
assert b'dw_tex_restore"' not in dll, "conservative command unexpectedly registered"

exe=list(third.rglob("realesrgan-ncnn-vulkan.exe"))
assert len(exe)==1,exe
backend_root=exe[0].parent
param=list(backend_root.rglob("realesrgan-x4plus.param"))
binf=list(backend_root.rglob("realesrgan-x4plus.bin"))
assert len(param)==1,param
assert len(binf)==1,binf

backend_files=0
for p in backend_root.rglob("*"):
    if not p.is_file(): continue
    rel=p.relative_to(backend_root).as_posix()
    entries["Main/dw_ai/"+rel]=p.read_bytes()
    backend_files+=1

assert "Main/dw_ai/realesrgan-ncnn-vulkan.exe" in entries
assert "Main/dw_ai/models/realesrgan-x4plus.param" in entries
assert "Main/dw_ai/models/realesrgan-x4plus.bin" in entries

entries["README_DW_TEXTURE_AI_B2_V1.txt"]=Path(
    "integration/texture-ai-b2-v1/README_B2_V1.txt").read_bytes()

notice='''DarkWolf B2 V1 third-party AI backend

Real-ESRGAN:
https://github.com/xinntao/Real-ESRGAN

Portable Real-ESRGAN ncnn/Vulkan Win64 package:
https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0

The portable backend and model files in Main/dw_ai are redistributed from the
official Real-ESRGAN release. Real-ESRGAN uses the BSD 3-Clause license.
Upstream license/notice files bundled with the portable release are retained
inside Main/dw_ai when present.

The B2 renderer does not contact GitHub or any Internet service at runtime.
'''
entries["THIRD_PARTY_DW_TEXTURE_AI_B2.txt"]=notice.encode()

manifest={
  "status":"TEST_CANDIDATE",
  "version":"DW_LOCAL_AI_TEXTURE_RESTORATION_B2_V1",
  "base_clean_production_run":42198541106,
  "base_clean_production_sha":"5ba3e923803674c9acee71600412720a0eeaf81e",
  "build_run":os.environ.get("GITHUB_RUN_ID"),
  "commit":os.environ.get("GITHUB_SHA"),
  "renderer_sha256":sha(dll),
  "ai_backend":"Real-ESRGAN ncnn/Vulkan portable Win64",
  "ai_model":"realesrgan-x4plus",
  "scale":4,
  "network_required_at_runtime":False,
  "telemetry":False,
  "vulkan_required":True,
  "scope":"opaque BSP world diffuse textures",
  "workflow":["dw_tex_pick","dw_tex_ai_info","dw_tex_ai_build","dw_tex_ab","dw_tex_save"],
  "conservative_builder_registered":False,
  "persistence":"zz_dwtr_<texture-path-hash>.pk3",
  "backend_files":backend_files,
  "backend_exe_sha256":sha(entries["Main/dw_ai/realesrgan-ncnn-vulkan.exe"]),
  "model_param_sha256":sha(entries["Main/dw_ai/models/realesrgan-x4plus.param"]),
  "model_bin_sha256":sha(entries["Main/dw_ai/models/realesrgan-x4plus.bin"])
}
entries["DW_TEXTURE_AI_B2_V1_BUILD_STATUS.json"]=(json.dumps(manifest,indent=2)+"\n").encode()
entries.pop("SHA256SUMS.txt",None)
entries["SHA256SUMS.txt"]="".join(
    sha(b)+"  "+n+"\n" for n,b in sorted(entries.items())).encode()

name="DarkWolf_Local_AI_Texture_Restoration_B2_V1_From_42198541106_Win64_TEST"
out=dist/(name+".zip")
with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for n,b in sorted(entries.items()):
        z.writestr(name+"/"+n,b)
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None

(dist/"SHA256SUMS_DW_TEXTURE_AI_B2_V1.txt").write_text(
    sha(out.read_bytes())+"  "+out.name+"\n"+
    sha(dll)+"  renderer_sp_rend2_x64.dll\n"+
    manifest["backend_exe_sha256"]+"  Main/dw_ai/realesrgan-ncnn-vulkan.exe\n"+
    manifest["model_bin_sha256"]+"  Main/dw_ai/models/realesrgan-x4plus.bin\n"
)
print(json.dumps({
  "package":str(out),
  "sha256":sha(out.read_bytes()),
  "renderer_sha256":sha(dll),
  "backend_files":backend_files,
  "package_files":len(entries),
  "backend_exe_sha256":manifest["backend_exe_sha256"],
  "model_bin_sha256":manifest["model_bin_sha256"]
},indent=2))
