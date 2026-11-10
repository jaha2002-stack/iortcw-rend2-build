#!/usr/bin/env python3
from pathlib import Path
import hashlib,io,json,struct,sys,zipfile

if len(sys.argv)!=5:
    raise SystemExit("usage: package.py <owner-clean-artifact.zip> <texture-clean-artifact.zip> <build-dir> <out-dir>")

owner_outer=Path(sys.argv[1]); texture_outer=Path(sys.argv[2]); build=Path(sys.argv[3]); outdir=Path(sys.argv[4])
outdir.mkdir(parents=True,exist_ok=True)
H=lambda b:hashlib.sha256(b).hexdigest()

def find_inner(outer_path,suffix):
    with zipfile.ZipFile(outer_path) as outer:
        hits=[n for n in outer.namelist() if n.endswith(suffix)]
        assert len(hits)==1,(outer_path,hits)
        return outer.read(hits[0])

owner_inner=find_inner(owner_outer,"DarkWolf_Clean_Production_ElectricOwnerV1_Escape1PhysicalOwnerV12_From_42217883095_Win64.zip")
with zipfile.ZipFile(io.BytesIO(owner_inner)) as z:
    assert z.testzip() is None
    roots={n.split("/",1)[0] for n in z.namelist() if "/" in n}
    assert len(roots)==1,roots
    oldroot=next(iter(roots))
    entries={}
    for n in z.namelist():
        if n.endswith("/") or not n.startswith(oldroot+"/"): continue
        entries[n[len(oldroot)+1:]]=z.read(n)

texture_inner=find_inner(texture_outer,"DarkWolf_Local_AI_Texture_Restoration_B2_V23_CLEAN_PRODUCTION_Win64.zip")
with zipfile.ZipFile(io.BytesIO(texture_inner)) as z:
    assert z.testzip() is None
    roots={n.split("/",1)[0] for n in z.namelist() if "/" in n}
    assert len(roots)==1,roots
    troot=next(iter(roots))+"/"
    ai_files=0
    ai_hashes={}
    for n in z.namelist():
        if n.endswith("/") or not n.startswith(troot+"Main/dw_ai/"): continue
        rel=n[len(troot):]
        data=z.read(n)
        entries[rel]=data
        ai_hashes[rel]=H(data)
        ai_files+=1
assert ai_files>0,ai_files

# Replace the two binaries with the newly compiled unified source.
exe_candidates=list(build.rglob("ioWolfSP.x64.exe"))
dll_candidates=list(build.rglob("renderer_sp_rend2_x64.dll"))
assert exe_candidates,build
assert dll_candidates,build
exe=exe_candidates[0].read_bytes()
dll=dll_candidates[0].read_bytes()
assert exe[:2]==b"MZ" and dll[:2]==b"MZ"
for data in (exe,dll):
    pe=struct.unpack_from("<I",data,60)[0]
    assert data[pe:pe+4]==b"PE\0\0"
entries["ioWolfSP.x64.exe"]=exe
entries["renderer_sp_rend2_x64.dll"]=dll

# Remove stale per-component/test metadata that would describe old binary hashes.
for rel in list(entries):
    u=rel.upper()
    if u.endswith("_TEST.CFG") or "AUDIT_TEST.CFG" in u or "ON_TEST.CFG" in u or "OFF_TEST.CFG" in u:
        del entries[rel]
    elif u.endswith("BUILD_STATUS.JSON"):
        del entries[rel]
    elif rel in ("SHA256SUMS.txt","CLEAN_PRODUCTION_ELECTRIC_OWNER_V1_ESCAPE1_V12_STATUS.json"):
        del entries[rel]

owner_cfg="""// DarkWolf Unified Clean Production
// Electric Physical Owner V1 + Escape1 Physical DLight Owner Residency V1.2
seta r_dwElectricPhysicalOwner "1"
seta r_dwElectricPhysicalOwnerDiag "0"
seta r_dwElectricOwnerAudit "0"
seta r_dwEscape1PhysicalDlightOwnerResidency "1"
seta r_dwEscape1ExternalNativeReserve "9"
seta r_dwEscape1PhysicalDlightOwnerDiag "0"
seta r_dwEscape1DlightResidencyAudit "0"
"""
entries["Main/DW_UNIFIED_CLEAN_PRODUCTION.cfg"]=owner_cfg.replace("\n","\r\n").encode("ascii")

pbr_cfg="""// DarkWolf PBR V3.2 Physical Relief / POM
// Optional explicit PBR V3.2 activation. Material Binding Audit remains a manual console command.
seta r_pbr "3"
seta r_normalMapping "1"
seta r_specularMapping "1"
seta r_cubeMapping "1"
seta r_parallaxMapping "2"
seta r_parallaxMapShadows "0"
seta r_pomMinLayers "20"
seta r_pomMaxLayers "56"
seta r_pomRefineSteps "5"
seta r_pomMaxOffset "0.028"
seta r_pomDepthScale "1.0"
seta r_pomGrazingFadeStart "0.24"
seta r_pomGrazingFadeEnd "0.62"
seta r_pomShadowStrength "0.45"
vid_restart
"""
entries["Main/DW_PBR32_PHYSICAL_RELIEF_POM.cfg"]=pbr_cfg.replace("\n","\r\n").encode("ascii")

# Binary markers prove the three feature families really coexist in the packaged build.
for marker in (
    b"r_dwElectricPhysicalOwner",
    b"r_dwEscape1PhysicalDlightOwnerResidency",
    b"dw_tex_save",
    b"zzzzzz_DW_TextureRestoration.pk3",
    b"r_pbrMaterialAudit",
    b"r_pomMinLayers",
):
    assert marker in dll,marker
for marker in (b"DWTR B2 V2.3:",b"zzzzzz_DW_TextureRestoration.pk3"):
    assert marker in exe,marker

manifest={
    "status":"CLEAN_PRODUCTION",
    "version":"DarkWolf Rend2 Unified Clean Production",
    "new_combined_compile":True,
    "base_clean_production_run":42217883095,
    "components":{
        "electric_owner_escape1_residency":{
            "clean_promotion_run":42598872025,
            "validated_source_run":42575742812,
            "validated_source_commit":"60ea59d9cce705333dad49a937ba85c71735aa2d",
            "electric_physical_owner_v1":True,
            "escape1_physical_dlight_owner_residency_v12":True,
            "v11_withdrawn":True,
            "diagnostics_default_off":True,
            "max_dlights_changed":False,
            "direct_dlight_energy_changed":False
        },
        "pbr":{
            "source_run":42619078136,
            "source_commit":"6605640a47b52a89f05b42490146e6c021301d83",
            "feature":"PBR V3.2 Physical Relief / POM + Material Binding Audit",
            "true_ggx_ibl_v31":True,
            "material_binding_audit":True
        },
        "texture_ai":{
            "clean_promotion_run":42588886276,
            "validated_source_run":42581487296,
            "validated_source_commit":"aa60e4d0c68260b6752920cddd8011b718c7dbba",
            "feature":"Local AI Texture Restoration B2 V2.3",
            "single_cumulative_pk3":"zzzzzz_DW_TextureRestoration.pk3",
            "startup_pending_promotion":True,
            "known_picker_limitation":"some doors and special/non-standard textures are not updated"
        }
    },
    "binary_hashes":{
        "ioWolfSP.x64.exe":H(exe),
        "renderer_sp_rend2_x64.dll":H(dll)
    },
    "ai_files":ai_files,
    "ai_hashes":ai_hashes,
    "network_required_at_runtime":False,
    "telemetry":False
}
entries["DW_UNIFIED_CLEAN_PRODUCTION_MANIFEST.json"]=(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n").encode("utf-8")

readme="""DarkWolf Rend2 — Unified Clean Production

This release combines three accepted lineages into one new Win64 build:

1. Clean Production Electric Physical Owner V1 + Escape1 Physical DLight Owner Residency V1.2
   Promotion Run #42598872025; validated source Run #42575742812; base #42217883095.
   V1.1 is not included. MAX_DLIGHTS remains 32. Direct DLight energy/color/radius are not modified.
   Owner/audit diagnostics are OFF by default.

2. PBR V3.2 Physical Relief / POM + Material Binding Audit
   Run #42619078136.
   Includes PBR V3.1 True GGX prefiltered environment + BRDF LUT and V3.2 adaptive POM.
   r_pbrMaterialAudit remains available as a manual diagnostic command and is not continuously active.

3. Local AI Texture Restoration B2 V2.3
   Clean Production Run #42588886276; user-tested source Run #42581487296.
   Includes local Real-ESRGAN, FAITHFUL/BALANCED/STRONG, A/B, next/prev,
   WORLD + MOD_BRUSH picker, one cumulative zzzzzz_DW_TextureRestoration.pk3,
   and qcommon startup promotion of .pending updates.
   Known limitation remains: some doors and special/non-standard textures are not updated.

Why binaries have new hashes:
The three accepted lineages modify overlapping renderer code, and B2 V2.3 also modifies qcommon/files.c.
Therefore a new combined compile is technically required. No component is represented as a byte-identical
promotion in this unified release; instead the accepted source changes are combined and regression-tested.

Production configs:
  /exec DW_UNIFIED_CLEAN_PRODUCTION.cfg
  /exec DW_PBR32_PHYSICAL_RELIEF_POM.cfg

PBR V3.2 activation remains explicit through its cfg; owner diagnostics remain disabled by default.
"""
entries["README_DARKWOLF_UNIFIED_CLEAN_PRODUCTION.txt"]=readme.replace("\n","\r\n").encode("utf-8-sig")

entries["SHA256SUMS.txt"]="".join(H(v)+"  "+k+"\n" for k,v in sorted(entries.items())).encode("ascii")

name="DarkWolf_Rend2_Unified_Clean_Production_PBR32_OwnerV12_TextureB2V23_Win64"
target=outdir/(name+".zip")
with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for rel,data in sorted(entries.items()):
        z.writestr(name+"/"+rel,data)

with zipfile.ZipFile(target) as z:
    assert z.testzip() is None
    names=z.namelist()
    root=name+"/"
    assert root+"ioWolfSP.x64.exe" in names
    assert root+"renderer_sp_rend2_x64.dll" in names
    assert root+"Main/dw_ai/realesrgan-ncnn-vulkan.exe" in names
    assert root+"Main/DW_UNIFIED_CLEAN_PRODUCTION.cfg" in names
    assert root+"Main/DW_PBR32_PHYSICAL_RELIEF_POM.cfg" in names
    assert root+"DW_UNIFIED_CLEAN_PRODUCTION_MANIFEST.json" in names
    assert not any(n.upper().endswith("_TEST.CFG") or "AUDIT_TEST.CFG" in n.upper() for n in names)

proof={
    "package":str(target),
    "package_sha256":H(target.read_bytes()),
    "exe_sha256":H(exe),
    "renderer_sha256":H(dll),
    "file_count":len(entries),
    "base_run":42217883095,
    "component_runs":[42598872025,42619078136,42588886276],
    "validated_source_runs":[42575742812,42619078136,42581487296],
    "clean_production":True
}
(outdir/"UNIFIED_CLEAN_PRODUCTION_PROOF.json").write_text(json.dumps(proof,indent=2)+"\n")
(outdir/"SHA256SUMS_UNIFIED.txt").write_text(
    proof["package_sha256"]+"  "+target.name+"\n"+
    proof["exe_sha256"]+"  ioWolfSP.x64.exe\n"+
    proof["renderer_sha256"]+"  renderer_sp_rend2_x64.dll\n"
)
print(json.dumps(proof,indent=2))
