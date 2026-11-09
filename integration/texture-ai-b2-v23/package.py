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

# FireVol production packagers historically replace renderer artifacts but do
# not need to replace the main ioWolfSP executable. V2.3 changes qcommon/files.c,
# so explicitly inject the freshly compiled EXE and renderer from this run.
build=Path("source/SP/build/release-mingw32-x86_64")
built_exe=build/"ioWolfSP.x64.exe"
built_rend2=build/"renderer_sp_rend2_x64.dll"
assert built_exe.exists(),built_exe
assert built_rend2.exists(),built_rend2
entries["ioWolfSP.x64.exe"]=built_exe.read_bytes()
entries["renderer_sp_rend2_x64.dll"]=built_rend2.read_bytes()

dll=entries["renderer_sp_rend2_x64.dll"]
for marker in (
    b"DWTR AI B2 V2.3",b"zzzzzz_DW_TextureRestoration.pk3",
    b"dw_tex_save",b"PICK source=BRUSH",b"PICK source=WORLD",
    b"dw_tex_next",b"dw_tex_prev",b"FAITHFUL",b"BALANCED",b"STRONG",
    b"realesrgan-x4plus"
):
    assert marker in dll,marker

exe_hits=[(n,b) for n,b in entries.items()
          if n.lower().endswith(".exe") and b"DWTR B2 V2.3:" in b]
assert exe_hits, "qcommon pending-promotion marker missing from packaged EXE"
main_exe_name,main_exe=exe_hits[0]

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

entries["README_DW_TEXTURE_AI_B2_V23.txt"]=Path(
    "integration/texture-ai-b2-v23/README_B2_V23.txt").read_bytes()

manifest={
  "status":"TEST_CANDIDATE",
  "version":"DW_LOCAL_AI_TEXTURE_RESTORATION_B2_V23",
  "base_clean_production_run":42198541106,
  "inherits_b2_v22_run":42580281924,
  "build_run":os.environ.get("GITHUB_RUN_ID"),
  "commit":os.environ.get("GITHUB_SHA"),
  "renderer_sha256":sha(dll),
  "main_executable":main_exe_name,
  "main_executable_sha256":sha(main_exe),
  "ai_backend":"Real-ESRGAN ncnn/Vulkan portable Win64",
  "ai_model":"realesrgan-x4plus",
  "scale":4,
  "network_required_at_runtime":False,
  "telemetry":False,
  "cumulative_pack":"zzzzzz_DW_TextureRestoration.pk3",
  "pending_pack":"zzzzzz_DW_TextureRestoration.pk3.pending",
  "persistence_policy":"one cumulative PK3; new qpaths added; same qpath replaced",
  "startup_promotion":"qcommon promotes pending before PK3 scan",
  "legacy_migration":"merge/delete old 2..10-z *_dwtr_<hash>.pk3 after cumulative save",
  "picker_scope":["WORLD BSP","RT_MODEL MOD_BRUSH"],
  "variants":["FAITHFUL","BALANCED","STRONG"],
  "default_variant":"BALANCED",
  "backend_files":backend_files,
  "backend_exe_sha256":sha(entries["Main/dw_ai/realesrgan-ncnn-vulkan.exe"]),
  "model_bin_sha256":sha(entries["Main/dw_ai/models/realesrgan-x4plus.bin"])
}
entries["DW_TEXTURE_AI_B2_V23_BUILD_STATUS.json"]=(json.dumps(manifest,indent=2)+"\n").encode()
entries.pop("SHA256SUMS.txt",None)
entries["SHA256SUMS.txt"]="".join(
    sha(b)+"  "+n+"\n" for n,b in sorted(entries.items())).encode()

name="DarkWolf_Local_AI_Texture_Restoration_B2_V23_From_42198541106_Win64_TEST"
out=dist/(name+".zip")
with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for n,b in sorted(entries.items()):
        z.writestr(name+"/"+n,b)
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None

(dist/"SHA256SUMS_DW_TEXTURE_AI_B2_V23.txt").write_text(
    sha(out.read_bytes())+"  "+out.name+"\n"+
    sha(dll)+"  renderer_sp_rend2_x64.dll\n"+
    sha(main_exe)+"  "+main_exe_name+"\n"+
    manifest["backend_exe_sha256"]+"  Main/dw_ai/realesrgan-ncnn-vulkan.exe\n"+
    manifest["model_bin_sha256"]+"  Main/dw_ai/models/realesrgan-x4plus.bin\n"
)
print(json.dumps({
  "package":str(out),
  "sha256":sha(out.read_bytes()),
  "renderer_sha256":sha(dll),
  "main_executable":main_exe_name,
  "main_executable_sha256":sha(main_exe),
  "backend_files":backend_files,
  "package_files":len(entries)
},indent=2))
