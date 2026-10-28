#!/usr/bin/env bash
set -Eeuo pipefail
mkdir -p dist evidence
gh api "repos/${GITHUB_REPOSITORY}/actions/artifacts/12796125440/zip" > evidence/EXACT_40640998083_ARTIFACT.zip
printf '%s\n' '51b946bd21c7a80f9c4940612b61b01fcd7c83eccfb7e4684a681727764a9be6  evidence/EXACT_40640998083_ARTIFACT.zip' | sha256sum -c -
unzip -p evidence/EXACT_40640998083_ARTIFACT.zip dist/DarkWolf_Sun3_FireE_Crypt1_Shadow_Fidelity_Clean_Production_Win64.zip > evidence/EXACT_40640998083_ACCEPTED_INNER.zip
printf '%s\n' 'd43a166c3f7c0b9ecb92767401c1617aecfea0337c137e28ae175b3d4db900b1  evidence/EXACT_40640998083_ACCEPTED_INNER.zip' | sha256sum -c -
python3 integration/xlabs-tesla-f2-escape1-a-clean-v1/package.py \
  --base-zip evidence/EXACT_40640998083_ACCEPTED_INNER.zip \
  --renderer build-binaries/renderer_sp_rend2_x64.dll \
  --patch evidence/DW_PRODUCTION_EXACT_BASE_PATCH.patch \
  --qa evidence/dw-prod-glsl/DARKWOLF_CLEAN_PRODUCTION_SOURCE_GLSL_QA.json \
  --out dist | tee evidence/DW_CLEAN_PRODUCTION_PACKAGING.txt
grep -Fq DARKWOLF_TESLA_X2_F2_ESCAPE1_A_CLEAN_PACKAGE_PASS evidence/DW_CLEAN_PRODUCTION_PACKAGING.txt
python3 - <<'PY'
import hashlib,json,zipfile
from pathlib import Path
p=Path('dist/DarkWolf_Sun3_FireE_Crypt1_TeslaX2_F2_Escape1A_Clean_Production_Win64.zip')
a=json.loads(Path('dist/DARKWOLF_CLEAN_PRODUCTION_FINAL_AUDIT.json').read_text())
assert a['original_byte_identical_files']==38 and a['file_count']==43
assert hashlib.sha256(p.read_bytes()).hexdigest()==a['inner_zip_sha256']
with zipfile.ZipFile(p) as z:
 assert z.testzip() is None and len(z.namelist())==43
 assert any(n.endswith('RUN_DARKWOLF_SEPTEMBER_FOURWEEK.bat') for n in z.namelist())
 assert any(n.endswith('Main/DW_CRYPT1_SHADOW_FIDELITY_PRODUCTION.cfg') for n in z.namelist())
 assert not any('DW_V5_' in n or 'DW_V4_' in n or 'DW_TEST_V' in n for n in z.namelist())
 print('DW_CLEAN_PRODUCTION_INDEPENDENT_ZIP_43_FILES_SHA256_PASS',a['inner_zip_sha256'])
PY
