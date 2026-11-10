#!/usr/bin/env bash
set -Eeuo pipefail
gh api "repos/${GITHUB_REPOSITORY}/actions/artifacts/12790622101/zip" > evidence/ACCEPTED_CRYPT1_40628480022_ARTIFACT.zip
printf '%s\n' '20d80bc539324535548ffeb584f202f4cd823fcd9e6853489aedfc438889c832  evidence/ACCEPTED_CRYPT1_40628480022_ARTIFACT.zip' | sha256sum -c -
unzip -p evidence/ACCEPTED_CRYPT1_40628480022_ARTIFACT.zip dist/DarkWolf_Sun3_FireE_Crypt1_Shadow_Priority_Clean_Production_Win64.zip > evidence/EXACT_CRYPT1_40628480022_BASE.zip
printf '%s\n' '2e4cc61e5371103098063a02c53acc56925403abae25800fb65fe6b6bb9786d7  evidence/EXACT_CRYPT1_40628480022_BASE.zip' | sha256sum -c -
python3 integration/crypt1-world-pcf2x2-v1/package.py --base-zip evidence/EXACT_CRYPT1_40628480022_BASE.zip --renderer build-binaries/renderer_sp_rend2_x64.dll --proof evidence/CRYPT1_WORLD_MASK_SOURCE_PROOF.json --tests evidence/worldmask-glsl/CRYPT1_WORLD_PCF2X2_SHADER_TESTS.json --out dist | tee evidence/CRYPT1_WORLD_MASK_PACKAGE.txt
grep -Fq DW_CRYPT1_WORLD_GATE_PCF2X2_CLEAN_RUNTIME_PACKAGE_PASS evidence/CRYPT1_WORLD_MASK_PACKAGE.txt
echo DW_CRYPT1_WORLD_GATE_PCF2X2_EXACT_RUNTIME_PRODUCED
