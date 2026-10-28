#!/usr/bin/env bash
set -Eeuo pipefail
mkdir -p dist evidence
gh api "repos/${GITHUB_REPOSITORY}/actions/artifacts/12813424598/zip" > evidence/FROZEN_40683914514_ARTIFACT.zip
printf '%s\n' '2a4d36a7b63adb6373052b2f7394875a4ffc9975bd7cc657039baedd3bec8cbc  evidence/FROZEN_40683914514_ARTIFACT.zip' | sha256sum -c -
unzip -p evidence/FROZEN_40683914514_ARTIFACT.zip dist/DarkWolf_Sun3_FireE_Crypt1_TeslaX2_F2_Escape1A_Clean_Production_Win64.zip > evidence/FROZEN_40683914514_INNER.zip
printf '%s\n' '5527c6725b02fc067ef652f4aa2346342804b04a7f3d0a972c8b9d8d506d5e92  evidence/FROZEN_40683914514_INNER.zip' | sha256sum -c -
python3 integration/xlabs-snapshot-pvs-v1/package.py \
  --base-zip evidence/FROZEN_40683914514_INNER.zip \
  --engine build-binaries/ioWolfSP.x64.exe \
  --proof evidence/XLABS_SNAPSHOT_V1_SOURCE_PROOF.json \
  --patch evidence/XLABS_SNAPSHOT_V1_EXACT_SOURCE.patch \
  --qa evidence/xlabs-snapshot-v1-qa/XLABS_SNAPSHOT_V1_QA.json \
  --out dist | tee evidence/XLABS_SNAPSHOT_V1_PACKAGING.txt
grep -Fq DW_XLABS_TESLA_PVS_TEST_V1_EXACT_PARENT_PACKAGE_PASS evidence/XLABS_SNAPSHOT_V1_PACKAGING.txt
python3 - <<'PY'
from pathlib import Path
import json,zipfile,hashlib
path=Path("dist/DarkWolf_Xlabs_Active_Tesla_Local_Snapshot_PVS_Test_V1_Win64.zip")
a=json.loads(Path("dist/XLABS_TESLA_PVS_TEST_V1_FINAL_AUDIT.json").read_text())
assert hashlib.sha256(path.read_bytes()).hexdigest()==a["package_sha256"]
assert a["original_byte_identical_files"]==41 and a["total_files"]==46
assert a["changed_existing_files"]==2
with zipfile.ZipFile(path) as z:
 assert z.testzip() is None and len(z.namelist())==46
 names=z.namelist()
 assert sum(n.endswith("/ioWolfSP.x64.exe") for n in names)==1
 assert any(n.endswith("/Main/qagame_sp_x64.dll") for n in names)
 assert any(n.endswith("/renderer_sp_rend2_x64.dll") for n in names)
 assert any(n.endswith("/README_XLABS_ACTIVE_TESLA_SNAPSHOT_PVS_TEST_V1_RU.txt") for n in names)
print("DW_XLABS_SNAPSHOT_V1_INDEPENDENT_WIN64_46_FILES_PASS")
PY
