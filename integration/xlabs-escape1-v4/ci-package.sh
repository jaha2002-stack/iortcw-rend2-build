#!/usr/bin/env bash
set -Eeuo pipefail
mkdir -p dist evidence
gh api "repos/${GITHUB_REPOSITORY}/actions/artifacts/12796125440/zip" > evidence/FROZEN_40640998083_ARTIFACT.zip
printf '%s\n' '51b946bd21c7a80f9c4940612b61b01fcd7c83eccfb7e4684a681727764a9be6  evidence/FROZEN_40640998083_ARTIFACT.zip' | sha256sum -c -
unzip -p evidence/FROZEN_40640998083_ARTIFACT.zip dist/DarkWolf_Sun3_FireE_Crypt1_Shadow_Fidelity_Clean_Production_Win64.zip > evidence/EXACT_FROZEN_40640998083_BASE.zip
printf '%s\n' 'd43a166c3f7c0b9ecb92767401c1617aecfea0337c137e28ae175b3d4db900b1  evidence/EXACT_FROZEN_40640998083_BASE.zip' | sha256sum -c -
python3 integration/xlabs-escape1-v4/package.py \
 --base-zip evidence/EXACT_FROZEN_40640998083_BASE.zip \
 --renderer build-binaries/renderer_sp_rend2_x64.dll \
 --proof evidence/XLABS_ESCAPE1_V4_SOURCE_PROOF.json \
 --out dist | tee evidence/XLABS_ESCAPE1_V4_PACKAGE.txt
grep -Fq DW_XLABS_ESCAPE1_V4_EXACT_BASE_PACKAGE_PASS evidence/XLABS_ESCAPE1_V4_PACKAGE.txt
python3 - <<'PY'
import hashlib,json,zipfile
p='dist/DarkWolf_Xlabs_Tesla_Escape1_World_Capture_Main_Audit_Test_V4_Win64.zip'
data=json.load(open('dist/XLABS_ESCAPE1_V4_FINAL_AUDIT.json'))
assert hashlib.sha256(open(p,'rb').read()).hexdigest()==data['release_sha256']
assert data['unchanged_original_files']==38 and data['new_cfg_count']==9
assert data['source']['sky_portal_audit_excluded']
with zipfile.ZipFile(p) as z:
 assert z.testzip() is None
 assert len(z.namelist())==51
 assert any('DW_V4_AUDIT_MAIN_ONCE.cfg' in n for n in z.namelist())
print('DW_XLABS_ESCAPE1_V4_INDEPENDENT_CI_ZIP_PASS')
PY
