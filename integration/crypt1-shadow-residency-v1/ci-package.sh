#!/usr/bin/env bash
set -Eeuo pipefail
gh api "repos/${GITHUB_REPOSITORY}/actions/artifacts/12737503925/zip" > evidence/ACCEPTED_SUN3_FIRE_E_RUN_40512393634_ARTIFACT.zip
printf '%s\n' 'e19b0c96eb1f513d67e72de410df9ed8af6aa3b6d89fa67aacc697c2b1b95924  evidence/ACCEPTED_SUN3_FIRE_E_RUN_40512393634_ARTIFACT.zip' | sha256sum -c -
unzip -p evidence/ACCEPTED_SUN3_FIRE_E_RUN_40512393634_ARTIFACT.zip dist/DarkWolf_Sky404801_Sun3_FireE_Clean_Production_Win64.zip > evidence/ACCEPTED_SUN3_FIRE_E_EXACT_RUNTIME.zip
printf '%s\n' 'f8c2a08ae6185123a2eb01b15a4be66bb457465563e3781bdd5688adc7e00460  evidence/ACCEPTED_SUN3_FIRE_E_EXACT_RUNTIME.zip' | sha256sum -c -
python3 integration/crypt1-shadow-residency-v1/package.py --base-zip evidence/ACCEPTED_SUN3_FIRE_E_EXACT_RUNTIME.zip --renderer build-binaries/renderer_sp_rend2_x64.dll --proof evidence/CRYPT1_SHADOW_PRIORITY_SOURCE_PROOF.json --tests evidence/crypt1-regression/CRYPT1_SHADOW_SOURCE_TESTS.json --out dist | tee evidence/CRYPT1_SHADOW_PRIORITY_PACKAGE.txt
grep -Fq DW_CRYPT1_SHADOW_CLEAN_ARCHIVE_PASS evidence/CRYPT1_SHADOW_PRIORITY_PACKAGE.txt
echo DW_CRYPT1_SHADOW_SUN3_FIRE_E_CLEAN_PACKAGE_COMPLETE
