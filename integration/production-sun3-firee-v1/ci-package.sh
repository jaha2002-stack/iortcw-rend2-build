#!/usr/bin/env bash
set -Eeuo pipefail
gh api "repos/${GITHUB_REPOSITORY}/actions/artifacts/12722282984/zip" > evidence/SKY_40480112714_ARTIFACT.zip
printf '%s\n' '67a551870f5070809a38bf744d11ffeb99afdcffa57dfd89195e054f7e11eef3  evidence/SKY_40480112714_ARTIFACT.zip' | sha256sum -c -
unzip -p evidence/SKY_40480112714_ARTIFACT.zip dist/DarkWolf_Sky_Portal_Universal_Single_Sample_V1_Win64.zip > evidence/ACCEPTED_SKY_40480112714_EXACT_BASE.zip
printf '%s\n' '05e6d68fe1b59924f074b18a2e60e54fee79bd4d39fb151a4978f5f6a406c8eb  evidence/ACCEPTED_SKY_40480112714_EXACT_BASE.zip' | sha256sum -c -
python3 integration/production-sun3-firee-v1/package.py --base-zip evidence/ACCEPTED_SKY_40480112714_EXACT_BASE.zip --renderer build-binaries/renderer_sp_rend2_x64.dll --proof evidence/SUN3_FIRE_E_CLEAN_SOURCE_PROOF.json --out dist | tee evidence/SUN3_FIRE_E_CLEAN_PACKAGE.txt
grep -Fq DW_SUN3_FIRE_E_404801_CLEAN_PACKAGE_PASS evidence/SUN3_FIRE_E_CLEAN_PACKAGE.txt
echo DW_SUN3_FIRE_E_EXACT_SKY404801_RELEASE_PACKAGE_COMPLETE
