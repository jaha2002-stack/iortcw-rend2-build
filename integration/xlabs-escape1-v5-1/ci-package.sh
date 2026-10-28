#!/usr/bin/env bash
set -Eeuo pipefail
mkdir -p dist evidence
gh api "repos/${GITHUB_REPOSITORY}/actions/artifacts/12796125440/zip" > evidence/FROZEN_40640998083_ARTIFACT.zip
printf '%s\n' '51b946bd21c7a80f9c4940612b61b01fcd7c83eccfb7e4684a681727764a9be6  evidence/FROZEN_40640998083_ARTIFACT.zip' | sha256sum -c -
unzip -p evidence/FROZEN_40640998083_ARTIFACT.zip dist/DarkWolf_Sun3_FireE_Crypt1_Shadow_Fidelity_Clean_Production_Win64.zip > evidence/EXACT_FROZEN_40640998083_BASE.zip
printf '%s\n' 'd43a166c3f7c0b9ecb92767401c1617aecfea0337c137e28ae175b3d4db900b1  evidence/EXACT_FROZEN_40640998083_BASE.zip' | sha256sum -c -
python3 - <<'PY'
import json
p=json.load(open("evidence/v5-1-full-shaders/V5_1_FULL_GLSL_QA.json"))
assert p["status"]=="FULL_SHADER_GLSL_120_130_150_PASS"
assert len(p["full_shader_variants_compiled"])==7
assert p["previous_fragment_loader_capacity"]==32000 and p["repaired_fragment_loader_capacity"]==65536
print("V5_1_LOADER_FULL_GLSL_7_VARIANTS_PRESENT")
PY
python3 integration/xlabs-escape1-v5-1/package.py \
 --base-zip evidence/EXACT_FROZEN_40640998083_BASE.zip \
 --renderer build-binaries/renderer_sp_rend2_x64.dll \
 --qa evidence/v5-glsl/V5_TESLA_GLSL_QA.json \
 --out dist | tee evidence/XLABS_ESCAPE1_V5_1_PACKAGE.txt
grep -Fq V5_EXACT_FROZEN_ACCEPTED_REPACKAGE_PASS evidence/XLABS_ESCAPE1_V5_1_PACKAGE.txt
mv dist/XLABS_ESCAPE1_V5_FINAL_AUDIT.json dist/XLABS_ESCAPE1_V5_1_FINAL_AUDIT.json
python3 - <<'PY'
import hashlib,json,zipfile
p='dist/DarkWolf_Xlabs_Tesla_CubeFace_Filter_Escape1_Native_Attribution_Test_V5_1_Win64.zip'
data=json.load(open('dist/XLABS_ESCAPE1_V5_1_FINAL_AUDIT.json'))
assert hashlib.sha256(open(p,'rb').read()).hexdigest()==data['final_sha256']
assert data['unchanged_original_files']==38 and data['new_cfg_files']==15
with zipfile.ZipFile(p) as z:
 assert z.testzip() is None
 assert len(z.namelist())==57
 assert any('DW_V5_AUDIT_MAIN_ONCE.cfg' in n for n in z.namelist())
 assert any('DW_V5_X1_PLUS32_F2_CUBEFACE4X4_TENT.cfg' in n for n in z.namelist())
 assert any('DW_V5_E1_ESCAPE1_SOURCE_A_ONLY.cfg' in n for n in z.namelist())
print('DW_XLABS_ESCAPE1_V5_INDEPENDENT_CI_ZIP_PASS')
PY
