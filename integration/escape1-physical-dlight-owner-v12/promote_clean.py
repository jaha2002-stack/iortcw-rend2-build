#!/usr/bin/env python3
from pathlib import Path
import hashlib, io, json, os, sys, zipfile

EXPECTED_TEST_PACKAGE_SHA = "753fbac125b0956a33eb0f610f1c2c989285f7a527093b75e3dec5892a5c4137"
EXPECTED_RENDERER_SHA = "3898cbd5b9cee55fe185333a00156d6877c7347b876c8f494516e3a2b2ced4d4"
SOURCE_RUN = 42575742812
SOURCE_COMMIT = "60ea59d9cce705333dad49a937ba85c71735aa2d"
BASE_RUN = 42217883095

wrapper = Path(sys.argv[1])
out_dir = Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)

sha = lambda b: hashlib.sha256(b).hexdigest()

with zipfile.ZipFile(wrapper) as z:
    candidates = [n for n in z.namelist()
                  if n.endswith("DarkWolf_Escape1_Physical_DLight_Owner_Residency_V1.2_From_42217883095_Win64_TEST.zip")]
    assert len(candidates) == 1, candidates
    test_zip_bytes = z.read(candidates[0])

assert sha(test_zip_bytes) == EXPECTED_TEST_PACKAGE_SHA, (
    sha(test_zip_bytes), EXPECTED_TEST_PACKAGE_SHA
)

with zipfile.ZipFile(io.BytesIO(test_zip_bytes)) as z:
    assert z.testzip() is None
    names = [n for n in z.namelist() if not n.endswith("/")]
    roots = sorted(set(n.split("/",1)[0] for n in names if "/" in n))
    assert len(roots) == 1, roots
    old_root = roots[0]
    entries = {}
    for n in names:
        if not n.startswith(old_root + "/"):
            continue
        rel = n[len(old_root)+1:]
        entries[rel] = z.read(n)

renderer = entries["renderer_sp_rend2_x64.dll"]
assert sha(renderer) == EXPECTED_RENDERER_SHA, (
    sha(renderer), EXPECTED_RENDERER_SHA
)

# Remove only TEST/AUDIT-facing V1.2 package files. Renderer DLL is untouched.
for rel in [
    "Main/DW_ESCAPE1_PHYSICAL_DLIGHT_OWNER_V12_ON_TEST.cfg",
    "Main/DW_ESCAPE1_PHYSICAL_DLIGHT_OWNER_V12_OFF_TEST.cfg",
    "Main/DW_ESCAPE1_PHYSICAL_DLIGHT_OWNER_V12_AUDIT_TEST.cfg",
    "README_ESCAPE1_PHYSICAL_DLIGHT_OWNER_V12_TEST.txt",
    "ESCAPE1_PHYSICAL_DLIGHT_OWNER_V12_TEST_STATUS.json",
    "SHA256SUMS.txt",
]:
    entries.pop(rel, None)

production_cfg = """// DarkWolf Clean Production - Electric Physical Owner V1 + Escape1 Physical DLight Owner Residency V1.2
// Renderer binary is byte-identical to visually approved Win64 TEST from Run #42575742812.
seta r_dwElectricPhysicalOwner "1"
seta r_dwElectricPhysicalOwnerDiag "0"
seta r_dwElectricOwnerAudit "0"
seta r_dwEscape1PhysicalDlightOwnerResidency "1"
seta r_dwEscape1ExternalNativeReserve "9"
seta r_dwEscape1PhysicalDlightOwnerDiag "0"
seta r_dwEscape1DlightResidencyAudit "0"
"""
entries["Main/DW_CLEAN_PRODUCTION_ELECTRIC_OWNER_V1_ESCAPE1_V12.cfg"] = production_cfg.replace("\n","\r\n").encode("ascii")

readme = f"""DarkWolf Clean Production
Electric Physical Owner V1 + Escape1 Physical DLight Owner Residency V1.2

Promotion source
----------------
Base Clean Production: Run #{BASE_RUN}
Validated V1.2 source run: #{SOURCE_RUN}
Validated source commit: {SOURCE_COMMIT}

This is a PROMOTION, not a new renderer build.
The renderer_sp_rend2_x64.dll is byte-for-byte identical to the visually approved
V1.2 Win64 TEST renderer.

Preserved fixes
---------------
- DarkWolf Electric Physical Owner V1:
  owner-aware Shadow + LocalVol dedup for electric StaticPromote/synthetic fixtures.
  Direct light energy is not deduplicated or changed by this mechanism.

- Escape1 Physical DLight Owner Residency V1.2:
  owner-first stable residency at the hard 32-DLight boundary.
  Native/promoted route changes do not change the physical owner set.
  Guard-room lamps 740-745 were visually confirmed stable on the user's PC.

Production diagnostics
----------------------
All V1/V1.2 audit and diagnostic cvars are OFF in the included production cfg.
TEST/AUDIT cfg files are intentionally not included in this Clean Production package.

Optional explicit production cfg:
  /exec DW_CLEAN_PRODUCTION_ELECTRIC_OWNER_V1_ESCAPE1_V12.cfg
"""
entries["README_CLEAN_PRODUCTION_ELECTRIC_OWNER_V1_ESCAPE1_V12.txt"] = readme.replace("\n","\r\n").encode("utf-8-sig")

status = {
    "status": "CLEAN_PRODUCTION",
    "promotion_only": True,
    "new_renderer_compile": False,
    "base_run": BASE_RUN,
    "validated_source_run": SOURCE_RUN,
    "validated_source_commit": SOURCE_COMMIT,
    "renderer_sha256": EXPECTED_RENDERER_SHA,
    "renderer_byte_identical_to_validated_test": True,
    "electric_physical_owner_v1": True,
    "escape1_physical_dlight_owner_residency_v12": True,
    "escape1_v11_withdrawn": True,
    "direct_energy_mutated": False,
    "max_dlights_changed": False,
    "diagnostic_cfgs_removed": True,
    "production_diagnostics_default_off": True,
}
entries["CLEAN_PRODUCTION_ELECTRIC_OWNER_V1_ESCAPE1_V12_STATUS.json"] = (
    json.dumps(status, indent=2) + "\n"
).encode("utf-8")

entries["SHA256SUMS.txt"] = "".join(
    sha(b) + "  " + n + "\n" for n,b in sorted(entries.items())
).encode("ascii")

new_root = "DarkWolf_Clean_Production_ElectricOwnerV1_Escape1PhysicalOwnerV12_From_42217883095_Win64"
target = out_dir / (new_root + ".zip")
with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for rel, data in sorted(entries.items()):
        z.writestr(new_root + "/" + rel, data)

with zipfile.ZipFile(target) as z:
    assert z.testzip() is None
    packed_renderer = z.read(new_root + "/renderer_sp_rend2_x64.dll")
    assert sha(packed_renderer) == EXPECTED_RENDERER_SHA

proof = {
    "package": str(target),
    "package_sha256": sha(target.read_bytes()),
    "renderer_sha256": sha(renderer),
    "expected_renderer_sha256": EXPECTED_RENDERER_SHA,
    "renderer_byte_identical": sha(renderer) == EXPECTED_RENDERER_SHA,
    "source_test_package_sha256": sha(test_zip_bytes),
    "source_run": SOURCE_RUN,
    "source_commit": SOURCE_COMMIT,
    "base_run": BASE_RUN,
    "new_renderer_compile": False,
}
(out_dir / "PROMOTION_PROOF.json").write_text(json.dumps(proof, indent=2) + "\n")
(out_dir / "SHA256SUMS.txt").write_text(
    proof["package_sha256"] + "  " + target.name + "\n" +
    proof["renderer_sha256"] + "  renderer_sp_rend2_x64.dll\n"
)
print(json.dumps(proof, indent=2))
