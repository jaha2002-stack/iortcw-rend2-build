#!/usr/bin/env bash
set -Eeuo pipefail
gh api "repos/${GITHUB_REPOSITORY}/actions/artifacts/12725915808/zip" > evidence/SUN_V3_BASE_ARTIFACT_40487188767.zip
printf '%s\n' 'c787151b9ea488fcefb1533742a551e41bb0121af531ac33c3bdce721e33f404  evidence/SUN_V3_BASE_ARTIFACT_40487188767.zip' | sha256sum -c -
unzip -p evidence/SUN_V3_BASE_ARTIFACT_40487188767.zip dist/DarkWolf_Sky_Portal_Volumetric_Wave_Clean_V2_Win64.zip > evidence/SUN_V3_EXACT_BASE_WIN64.zip
printf '%s\n' '2e882812df4aaa2bbca9cc25e91591a681b3ce2afe0edc0b69f691fcf5029f70  evidence/SUN_V3_EXACT_BASE_WIN64.zip' | sha256sum -c -
python3 integration/sun-wave-matrix-v3/package.py --base-zip evidence/SUN_V3_EXACT_BASE_WIN64.zip --renderer build-binaries/renderer_sp_rend2_x64.dll --proof evidence/SUN_V3_SOURCE_PROOF.json --out dist | tee evidence/SUN_V3_PACKAGE.txt
grep -Fq DW_SUN_WAVE_V3_PACKAGE_PASS evidence/SUN_V3_PACKAGE.txt
echo DW_SUN_V3_SOURCE_CI_WIN64_PACKAGE_PASS
