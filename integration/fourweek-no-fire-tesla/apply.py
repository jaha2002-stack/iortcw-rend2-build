#!/usr/bin/env python3
"""Exact original Oct 15 Fire/Tesla 15-file revert + diagnostic-only SSGI fix."""
from pathlib import Path
import sys,subprocess,hashlib,json,re
root=Path(sys.argv[1]);patch=Path(sys.argv[2]);out=Path(sys.argv[3])
text=patch.read_bytes();assert hashlib.sha256(text).hexdigest()=="e3600847ed0d1def868439af0c94f5ce250e2e7afbb0584fbb151459ea009a2f"
files=re.findall(rb"^diff --git a/([^ ]+) b/([^\n]+)$",text,re.M)
assert len(files)==15 and all(a==b for a,b in files)
subprocess.run(["git","-C",str(root),"apply","--reverse","--check",str(patch)],check=True)
subprocess.run(["git","-C",str(root),"apply","--reverse",str(patch)],check=True)
subprocess.run(["git","-C",str(root),"diff","--check"],check=True)
check=["DARKWOLF_REF_WORLD_OCCLUSION","u_DlightWorldMap","DlightWorldVisibility","R_RenderDlightWorldOcclusion","dlightWorldCache"]
for f in ("SP/code/rend2/tr_scene.c","SP/code/rend2/tr_local.h","SP/code/rend2/tr_glsl.c","SP/code/rend2/glsl/dlight_fp.glsl","SP/code/rend2/glsl/lightall_fp.glsl","SP/code/cgame/cg_ents.c"):
 s=(root/f).read_text()
 for word in check:assert word not in s,(f,word)
p=root/"SP/code/rend2/tr_backend.c";s=p.read_text()
mark="DARKWOLF_CRYPT1_LIGHTMAP_SSGI_ISOLATION_V1"
anchor="\t\tif (r_ssgi && r_ssgi->integer)"
assert s.count(anchor)==1 and mark not in s
p.write_text(s.replace(anchor,"\t\t// "+mark+": SSGI unchanged in gameplay.\n\t\tif (r_ssgi && r_ssgi->integer && !(r_lightmap && r_lightmap->integer))",1))
manifest={"base":"OFFICIAL_FOURWEEK_MASTER_V03","fire_tesla_rollback":"FULL_EXACT_SOURCE_PATCH_REVERSE",
 "original_oct15_patch_sha256":hashlib.sha256(text).hexdigest(),
 "reverted_fire_tesla_source_files":[a.decode() for a,_ in files],
 "ssgi_lightmap_only_guard":"APPLIED",
 "ssgi_condition":"r_ssgi && !r_lightmap",
 "preserved":"CSM Guard, Bloom v2, SSGI gameplay, Texture Material Fidelity, CAS, A2C, LUT V03, 4x MSAA, volumetrics",
 "not_included":"PCF4 and SSGI Fire Receiver V04 experiments"}
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(manifest,indent=2)+"\n")
print("NO_FIRE_TESLA_EXACT_REVERSE_AND_SSGI_LIGHTMAP_GUARD_PASS",len(files),flush=True)
