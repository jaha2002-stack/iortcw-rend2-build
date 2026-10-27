set -Eeuo pipefail
gh api "repos/${GITHUB_REPOSITORY}/actions/artifacts/12725915808/zip" > evidence/WAVE_40487188767_ARTIFACT.zip
printf '%s\n' 'c787151b9ea488fcefb1533742a551e41bb0121af531ac33c3bdce721e33f404  evidence/WAVE_40487188767_ARTIFACT.zip' | sha256sum -c -
unzip -p evidence/WAVE_40487188767_ARTIFACT.zip dist/DarkWolf_Sky_Portal_Volumetric_Wave_Clean_V2_Win64.zip > evidence/WAVE_40487188767_EXACT_BASE.zip
printf '%s\n' '2e882812df4aaa2bbca9cc25e91591a681b3ce2afe0edc0b69f691fcf5029f70  evidence/WAVE_40487188767_EXACT_BASE.zip' | sha256sum -c -
python3 integration/volumetric-overlap-diagnostic-v1/package.py --base-zip evidence/WAVE_40487188767_EXACT_BASE.zip --renderer build-binaries/renderer_sp_rend2_x64.dll --proof evidence/VOL_DIAG_SOURCE_PROOF.json --out dist | tee evidence/VOL_DIAG_PACKAGE.txt
grep -Fq DW_VOL_OVERLAP_DIAG_V1_ARCHIVE_PASS evidence/VOL_DIAG_PACKAGE.txt
echo DW_VOL_DIAGNOSTIC_ONLY_BASE_40487188767_PACKAGE_COMPLETE
