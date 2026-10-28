#!/usr/bin/env bash
set -Eeuo pipefail
mkdir -p dist evidence
gh api "repos/${GITHUB_REPOSITORY}/actions/artifacts/12796125440/zip" > evidence/XLABS_V2_FROZEN_BASE_ARTIFACT.zip
printf '%s\n' '51b946bd21c7a80f9c4940612b61b01fcd7c83eccfb7e4684a681727764a9be6  evidence/XLABS_V2_FROZEN_BASE_ARTIFACT.zip' | sha256sum -c -
unzip -p evidence/XLABS_V2_FROZEN_BASE_ARTIFACT.zip dist/DarkWolf_Sun3_FireE_Crypt1_Shadow_Fidelity_Clean_Production_Win64.zip > evidence/EXACT_XLABS_V2_BASE_40640998083.zip
printf '%s\n' 'd43a166c3f7c0b9ecb92767401c1617aecfea0337c137e28ae175b3d4db900b1  evidence/EXACT_XLABS_V2_BASE_40640998083.zip' | sha256sum -c -
python3 integration/xlabs-escape1-origin-test-v2/package.py \
  --base-zip evidence/EXACT_XLABS_V2_BASE_40640998083.zip \
  --renderer build-binaries/renderer_sp_rend2_x64.dll \
  --cgame build-binaries/cgame_sp_x64.dll \
  --proof evidence/XLABS_ESCAPE1_V2_SOURCE_PROOF.json \
  --qa evidence/v2-qa/V2_QA.json --out dist | tee evidence/XLABS_ESCAPE1_V2_PACKAGING.txt
grep -Fq DW_XLABS_ESCAPE1_V2_PACKAGE_EXACT_BASE_PASS evidence/XLABS_ESCAPE1_V2_PACKAGING.txt
echo DW_XLABS_ESCAPE1_V2_WIN64_PACKAGING_COMPLETE
