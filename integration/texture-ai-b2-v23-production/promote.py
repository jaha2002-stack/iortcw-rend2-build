#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, sys, zipfile

SOURCE_RUN = 42581487296
SOURCE_COMMIT = "aa60e4d0c68260b6752920cddd8011b718c7dbba"
SOURCE_INNER_SHA256 = "a56667f751236a64092532a22a09d7bd073b71d46e62cbcd9fc99e03720e5512"
RENDERER_SHA256 = "9ceb28910bb517e54ce45ac5165a081bd73ce7ed6a79b1496d71422529d4c927"
EXE_SHA256 = "d70ee80eaff64c1fe90fc62b2528e98c8052102d523437eb32596a81aa20dec9"
AI_EXE_SHA256 = "07e49f7cbb4ede01ae4dd4c399d3a7e5846e3d2085c3128eff881e55cb7b1a0c"
MODEL_BIN_SHA256 = "713ee713b0353afaa27976f0563a64a5043bd70b9bd8936c2e26e25ebcdbcddf"

def sha(b):
    return hashlib.sha256(b).hexdigest()

if len(sys.argv) != 3:
    raise SystemExit("usage: promote.py <downloaded-artifact-dir> <dist-dir>")

src_dir = Path(sys.argv[1]).resolve()
dist = Path(sys.argv[2]).resolve()
dist.mkdir(parents=True, exist_ok=True)

inner = list(src_dir.rglob("DarkWolf_Local_AI_Texture_Restoration_B2_V23_From_42198541106_Win64_TEST.zip"))
assert len(inner) == 1, inner
inner = inner[0]
assert sha(inner.read_bytes()) == SOURCE_INNER_SHA256

entries = {}
with zipfile.ZipFile(inner) as z:
    assert z.testzip() is None
    roots = {n.split("/",1)[0] for n in z.namelist() if "/" in n}
    assert len(roots) == 1, roots
    old_root = next(iter(roots))
    for n in z.namelist():
        if n.endswith("/"):
            continue
        rel = n.split("/",1)[1] if n.startswith(old_root + "/") else n
        entries[rel] = z.read(n)

for p in (
    "ioWolfSP.x64.exe",
    "renderer_sp_rend2_x64.dll",
    "Main/dw_ai/realesrgan-ncnn-vulkan.exe",
    "Main/dw_ai/models/realesrgan-x4plus.bin",
):
    assert p in entries, p

assert sha(entries["ioWolfSP.x64.exe"]) == EXE_SHA256
assert sha(entries["renderer_sp_rend2_x64.dll"]) == RENDERER_SHA256
assert sha(entries["Main/dw_ai/realesrgan-ncnn-vulkan.exe"]) == AI_EXE_SHA256
assert sha(entries["Main/dw_ai/models/realesrgan-x4plus.bin"]) == MODEL_BIN_SHA256

for p in (
    "README_DW_TEXTURE_AI_B2_V23.txt",
    "DW_TEXTURE_AI_B2_V23_BUILD_STATUS.json",
    "SHA256SUMS.txt",
):
    entries.pop(p, None)

production_notes = """DarkWolf Local AI Texture Restoration B2 V2.3 — CLEAN PRODUCTION

PROMOTION SOURCE
GitHub Actions Run #42581487296
Source commit: aa60e4d0c68260b6752920cddd8011b718c7dbba
Promotion method: REPACK ONLY — NO RECOMPILATION.

The ioWolfSP.x64.exe and renderer_sp_rend2_x64.dll in this package are the
exact byte-for-byte binaries that were tested by the user from Run #42581487296.

USER-VALIDATED FUNCTIONALITY
- Local Real-ESRGAN x4plus restoration works.
- FAITHFUL / BALANCED / STRONG variants work.
- /dw_tex_next and /dw_tex_prev work.
- In-game A/B preview works.
- Orientation fix works.
- Single cumulative zzzzzz_DW_TextureRestoration.pk3 persistence works.
- Saved textures load after game restart.
- Re-saving the same texture updates the cumulative pack instead of creating
  another per-texture PK3.

KNOWN LIMITATION
Some doors and some special/non-standard textures are still not updated by the
current picker. This is a known scope limitation for future development.

RUNTIME
- AI: Real-ESRGAN realesrgan-x4plus
- Backend: ncnn/Vulkan Win64
- Internet required at runtime: NO
- Telemetry: NO

IMPORTANT
Do not replace the included ioWolfSP.x64.exe with the executable from an older
build. B2 V2.3 cumulative-PK3 startup promotion is implemented in qcommon and
therefore requires this exact executable together with the matching renderer.
"""

manifest = {
    "status": "CLEAN_PRODUCTION",
    "version": "DarkWolf Local AI Texture Restoration B2 V2.3",
    "promotion_only": True,
    "recompiled": False,
    "source_run": SOURCE_RUN,
    "source_commit": SOURCE_COMMIT,
    "source_test_zip_sha256": SOURCE_INNER_SHA256,
    "base_clean_production_run": 42198541106,
    "user_tested_pass": True,
    "accepted_features": [
        "local Real-ESRGAN x4plus",
        "FAITHFUL/BALANCED/STRONG",
        "next/prev",
        "A/B preview",
        "orientation fix",
        "WORLD + MOD_BRUSH picker",
        "single cumulative PK3 persistence",
        "startup pending promotion"
    ],
    "known_limitations": [
        "some doors and some special/non-standard textures are not updated by the current picker"
    ],
    "binary_hashes": {
        "ioWolfSP.x64.exe": EXE_SHA256,
        "renderer_sp_rend2_x64.dll": RENDERER_SHA256,
        "Main/dw_ai/realesrgan-ncnn-vulkan.exe": AI_EXE_SHA256,
        "Main/dw_ai/models/realesrgan-x4plus.bin": MODEL_BIN_SHA256,
    },
    "network_required_at_runtime": False,
    "telemetry": False,
}

entries["README_DW_TEXTURE_AI_B2_V23_CLEAN_PRODUCTION.txt"] = production_notes.encode()
entries["DW_TEXTURE_AI_B2_V23_PRODUCTION_MANIFEST.json"] = (
    json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
).encode("utf-8")

entries["SHA256SUMS.txt"] = "".join(
    sha(data) + "  " + name + "\n"
    for name, data in sorted(entries.items())
).encode()

assert sha(entries["ioWolfSP.x64.exe"]) == EXE_SHA256
assert sha(entries["renderer_sp_rend2_x64.dll"]) == RENDERER_SHA256

name = "DarkWolf_Local_AI_Texture_Restoration_B2_V23_CLEAN_PRODUCTION_Win64"
out = dist / (name + ".zip")
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for rel, data in sorted(entries.items()):
        z.writestr(name + "/" + rel, data)

with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    root = name + "/"
    names = z.namelist()
    assert root + "DW_TEXTURE_AI_B2_V23_PRODUCTION_MANIFEST.json" in names
    assert root + "README_DW_TEXTURE_AI_B2_V23_CLEAN_PRODUCTION.txt" in names
    assert root + "DW_TEXTURE_AI_B2_V23_BUILD_STATUS.json" not in names
    assert root + "README_DW_TEXTURE_AI_B2_V23.txt" not in names
    assert sha(z.read(root + "ioWolfSP.x64.exe")) == EXE_SHA256
    assert sha(z.read(root + "renderer_sp_rend2_x64.dll")) == RENDERER_SHA256

(dist / "SHA256SUMS_DW_TEXTURE_AI_B2_V23_CLEAN_PRODUCTION.txt").write_text(
    sha(out.read_bytes()) + "  " + out.name + "\n"
    + EXE_SHA256 + "  ioWolfSP.x64.exe\n"
    + RENDERER_SHA256 + "  renderer_sp_rend2_x64.dll\n"
    + AI_EXE_SHA256 + "  Main/dw_ai/realesrgan-ncnn-vulkan.exe\n"
    + MODEL_BIN_SHA256 + "  Main/dw_ai/models/realesrgan-x4plus.bin\n"
)

print(json.dumps({
    "output": str(out),
    "output_sha256": sha(out.read_bytes()),
    "file_count": len(entries),
    "source_run": SOURCE_RUN,
    "source_inner_sha256_verified": True,
    "recompiled": False,
    "exact_exe_sha256": EXE_SHA256,
    "exact_renderer_sha256": RENDERER_SHA256
}, indent=2))
