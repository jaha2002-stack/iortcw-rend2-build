#!/usr/bin/env bash
set -Eeuo pipefail
python3 -m py_compile integration/production-sun3-firee-v1/{apply,test,package}.py
python3 -m py_compile integration/volumetric-wave-clean-v2/apply.py
mkdir -p evidence/prod-before/SP/code/rend2/glsl evidence/prod-replay/SP/code/rend2/glsl evidence/prod-glsl
for rel in tr_backend.c tr_init.c glsl/volumetricsun_fp.glsl glsl/volumetriclocal_fp.glsl glsl/volumetriclocal_upscale_fp.glsl; do
  cp "sept-source/SP/code/rend2/$rel" "evidence/prod-before/SP/code/rend2/$rel"
  cp "sept-source/SP/code/rend2/$rel" "evidence/prod-replay/SP/code/rend2/$rel"
done
printf '%s\n' '505ef716a0e316a99f00f0ce8d2e4e81ecef650424bfd22a537227ffbfbb37ba  sept-source/SP/code/rend2/tr_backend.c' | sha256sum -c -
printf '%s\n' '166dce445e85d5bf93d2b7779656ac201d78fa98b977c95ad6cfe5bd50098fff  sept-source/SP/code/rend2/tr_init.c' | sha256sum -c -
printf '%s\n' 'dfbb9f92db919fbb54de80eb19a0f1e23a22c8df7742119aafcf638ba4e0e74d  sept-source/SP/code/rend2/glsl/volumetricsun_fp.glsl' | sha256sum -c -
printf '%s\n' 'a39bd6eaa3dd81e2a30f75bb9d90343cc0d057ce48c58bea8f7fadcdf60b28a6  sept-source/SP/code/rend2/glsl/volumetriclocal_fp.glsl' | sha256sum -c -
printf '%s\n' 'dc85c8fa6133ea484236a230950c10f00a2c4096c678c93e5b8c36091429ff8e  sept-source/SP/code/rend2/glsl/volumetriclocal_upscale_fp.glsl' | sha256sum -c -
python3 integration/production-sun3-firee-v1/apply.py sept-source --proof evidence/SUN3_FIRE_E_CLEAN_SOURCE_PROOF.json | tee evidence/SUN3_FIRE_E_CLEAN_APPLY.txt
grep -Fxq DW_SUN3_FIRE_E_EXACT_CLEAN_PRODUCTION_SOURCE_PASS evidence/SUN3_FIRE_E_CLEAN_APPLY.txt
python3 integration/production-sun3-firee-v1/test.py sept-source --out evidence/prod-glsl --require-glslang | tee evidence/SUN3_FIRE_E_CLEAN_GLSL_TESTS.txt
grep -Fxq DW_SUN3_FIRE_E_CLEAN_PRODUCTION_GLSL_STATIC_PASS evidence/SUN3_FIRE_E_CLEAN_GLSL_TESTS.txt
git -C sept-source diff --check
: > evidence/SUN3_FIRE_E_CLEAN_EXACT_SOURCE.patch
for rel in tr_backend.c tr_init.c glsl/volumetricsun_fp.glsl glsl/volumetriclocal_fp.glsl glsl/volumetriclocal_upscale_fp.glsl; do
  src="SP/code/rend2/$rel"
  diff -u --label "a/$src" --label "b/$src" "evidence/prod-before/$src" "sept-source/$src" >> evidence/SUN3_FIRE_E_CLEAN_EXACT_SOURCE.patch || test "$?" -eq 1
done
test -s evidence/SUN3_FIRE_E_CLEAN_EXACT_SOURCE.patch
git -C sept-source apply --reverse --check ../evidence/SUN3_FIRE_E_CLEAN_EXACT_SOURCE.patch
if python3 integration/production-sun3-firee-v1/apply.py sept-source --proof evidence/SECOND_APPLY_SHOULD_NOT_EXIST.json > evidence/SECOND_APPLY_OUTPUT.txt 2>&1; then
  echo 'DUPLICATE_PRODUCTION_PATCH_WAS_NOT_REJECTED' >&2
  exit 1
fi
python3 integration/production-sun3-firee-v1/apply.py evidence/prod-replay --proof evidence/SUN3_FIRE_E_CLEAN_REPLAY_PROOF.json
for rel in tr_backend.c tr_init.c glsl/volumetricsun_fp.glsl glsl/volumetriclocal_fp.glsl glsl/volumetriclocal_upscale_fp.glsl; do
  cmp "sept-source/SP/code/rend2/$rel" "evidence/prod-replay/SP/code/rend2/$rel"
done
python3 - <<'PY'
import json
p=json.load(open("evidence/SUN3_FIRE_E_CLEAN_SOURCE_PROOF.json"))
assert p["exact_binary_base_run"]==40480112714
assert p["user_tested_fire_run"]==40487188767
assert p["user_tested_sun_v3_run"]==40504661395
assert len(p["modified_source_files"])==5
assert p["new_diagnostic_cvars"]==[] and p["telemetry"] is False
assert p["Sun"]=="V3_MODE_3_DUAL_VISIBILITY_6_PERCENT_CSM"
assert p["Fire"]=="E_40_RAY_STEPS_DEPTH_5X5_9_TAP"
print("DW_PRODUCTION_SUN3_FIRE_E_EXACT_LINEAGE_PROOF_PASS")
PY
echo DW_PRODUCTION_SUN3_FIRE_E_EXACT_SOURCE_REPLAY_PASS
