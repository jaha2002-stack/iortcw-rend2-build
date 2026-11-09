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
        entries[n.split("/",1)[1]]=z.read(n)

dll=entries["renderer_sp_rend2_x64.dll"]
for marker in (
    b"dw_tex_ai_build",b"dw_tex_next",b"dw_tex_prev",b"dw_tex_ab",
    b"dw_tex_save",b"DWTR AI B2 V2.1",b"FAITHFUL",b"BALANCED",b"STRONG",
    b"realesrgan-x4plus",b"zzz_dwtr_",b"physical PK3="
):
    assert marker in dll,marker
assert b'"zz_dwtr_%08x.pk3"' not in dll

exe=list(third.rglob("realesrgan-ncnn-vulkan.exe"))
assert len(exe)==1,exe
backend_root=exe[0].parent
assert len(list(backend_root.rglob("realesrgan-x4plus.param")))==1
assert len(list(backend_root.rglob("realesrgan-x4plus.bin")))==1

backend_files=0
for p in backend_root.rglob("*"):
    if not p.is_file(): continue
    rel=p.relative_to(backend_root).as_posix()
    entries["Main/dw_ai/"+rel]=p.read_bytes()
    backend_files+=1

entries["README_DW_TEXTURE_AI_B2_V21.txt"]=Path(
    "integration/texture-ai-b2-v21/README_B2_V21.txt").read_bytes()

manifest={
  "status":"TEST_CANDIDATE",
  "version":"DW_LOCAL_AI_TEXTURE_RESTORATION_B2_V21",
  "base_clean_production_run":42198541106,
  "inherits_b2_v2_run":42574596120,
  "build_run":os.environ.get("GITHUB_RUN_ID"),
  "commit":os.environ.get("GITHUB_SHA"),
  "renderer_sha256":sha(dll),
  "ai_backend":"Real-ESRGAN ncnn/Vulkan portable Win64",
  "ai_model":"realesrgan-x4plus",
  "scale":4,
  "network_required_at_runtime":False,
  "telemetry":False,
  "pk3_prefix":"zzz_dwtr_",
  "pk3_autoload_fix":"avoids RTCW SP zz_ to sp_ filename rewrite",
  "save_root":"fs_homepath/<game>",
  "prints_exact_physical_pk3_path":True,
  "variants":["FAITHFUL","BALANCED","STRONG"],
  "default_variant":"BALANCED",
  "backend_files":backend_files,
  "backend_exe_sha256":sha(entries["Main/dw_ai/realesrgan-ncnn-vulkan.exe"]),
  "model_bin_sha256":sha(entries["Main/dw_ai/models/realesrgan-x4plus.bin"])
}
entries["DW_TEXTURE_AI_B2_V21_BUILD_STATUS.json"]=(json.dumps(manifest,indent=2)+"\n").encode()
entries.pop("SHA256SUMS.txt",None)
entries["SHA256SUMS.txt"]="".join(
    sha(b)+"  "+n+"\n" for n,b in sorted(entries.items())).encode()

name="DarkWolf_Local_AI_Texture_Restoration_B2_V21_From_42198541106_Win64_TEST"
out=dist/(name+".zip")
with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for n,b in sorted(entries.items()):
        z.writestr(name+"/"+n,b)
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None

(dist/"SHA256SUMS_DW_TEXTURE_AI_B2_V21.txt").write_text(
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
  "package_files":len(entries)
},indent=2))
