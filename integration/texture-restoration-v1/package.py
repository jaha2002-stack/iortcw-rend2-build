#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,zipfile
dist=Path("dist")
base=dist/"DarkWolf_Clean_Production_FireVol_Final_From_41982135692_Win64.zip"
assert base.exists(),base
sha=lambda b:hashlib.sha256(b).hexdigest()
entries={}
with zipfile.ZipFile(base) as z:
    assert z.testzip() is None
    roots={n.split("/",1)[0] for n in z.namelist() if "/" in n}
    assert len(roots)==1,roots
    root=next(iter(roots))
    for n in z.namelist():
        if n.endswith("/"): continue
        rel=n.split("/",1)[1]
        entries[rel]=z.read(n)
dll=entries["renderer_sp_rend2_x64.dll"]
for marker in (b"dw_tex_pick",b"dw_tex_restore",b"dw_tex_ab",b"dw_tex_save",b"DWTR:"):
    assert marker in dll,marker
readme=Path("integration/texture-restoration-v1/README_RU.txt").read_bytes()
entries["README_DW_TEXTURE_RESTORATION_V1.txt"]=readme
manifest={
  "status":"TEST_CANDIDATE",
  "version":"DW_ORIGINAL_TEXTURE_RESTORATION_V1",
  "base_clean_production_run":42198541106,
  "base_clean_production_sha":"5ba3e923803674c9acee71600412720a0eeaf81e",
  "build_run":os.environ.get("GITHUB_RUN_ID"),
  "commit":os.environ.get("GITHUB_SHA"),
  "renderer_sha256":sha(dll),
  "network_required":False,
  "telemetry":False,
  "artistic_backend_enabled":False,
  "workflow":["dw_tex_pick","dw_tex_restore","dw_tex_ab","dw_tex_save"],
  "persistence":"zz_dwtr_<texture-path-hash>.pk3"
}
entries["DW_TEXTURE_RESTORATION_V1_BUILD_STATUS.json"]=(json.dumps(manifest,indent=2)+"\n").encode()
entries.pop("SHA256SUMS.txt",None)
entries["SHA256SUMS.txt"]="".join(sha(b)+"  "+n+"\n" for n,b in sorted(entries.items())).encode()
name="DarkWolf_Original_Texture_Restoration_V1_From_42198541106_Win64_TEST"
out=dist/(name+".zip")
with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for n,b in sorted(entries.items()): z.writestr(name+"/"+n,b)
with zipfile.ZipFile(out) as z: assert z.testzip() is None
(dist/"SHA256SUMS_DWTR_V1.txt").write_text(sha(out.read_bytes())+"  "+out.name+"\n"+sha(dll)+"  renderer_sp_rend2_x64.dll\n")
print(json.dumps({"package":str(out),"sha256":sha(out.read_bytes()),"renderer_sha256":sha(dll),"files":len(entries)},indent=2))
