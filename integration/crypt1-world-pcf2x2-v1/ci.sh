#!/usr/bin/env bash
set -Eeuo pipefail
python3 -m py_compile integration/crypt1-world-pcf2x2-v1/{apply,test,package}.py
mkdir -p evidence/worldmask-before/SP/code/rend2/glsl evidence/worldmask-replay/SP/code/rend2/glsl evidence/worldmask-glsl
for file in dlight_fp.glsl lightall_fp.glsl; do
    cp "sept-source/SP/code/rend2/glsl/$file" "evidence/worldmask-before/SP/code/rend2/glsl/$file"
    cp "sept-source/SP/code/rend2/glsl/$file" "evidence/worldmask-replay/SP/code/rend2/glsl/$file"
done
# Confirm exact accepted renderer lineage: Sky #404801 -> Sun3 Fire E
# #40512393634 -> persistent-fire shadow priority #40628480022.
python3 - <<'PY'
import json,pathlib
sun=json.loads(pathlib.Path('evidence/SUN3_FIRE_E_CLEAN_SOURCE_PROOF.json').read_text())
prio=json.loads(pathlib.Path('evidence/CRYPT1_SHADOW_PRIORITY_SOURCE_PROOF.json').read_text())
assert sun['Sun']=='V3_MODE_3_DUAL_VISIBILITY_6_PERCENT_CSM'
assert sun['Fire']=='E_40_RAY_STEPS_DEPTH_5X5_9_TAP'
assert sun['new_diagnostic_cvars']==[]
assert prio['source_base_run']==40512393634
assert prio['modified_source_files']==['SP/code/rend2/tr_main.c']
assert prio['new_cvars']==[] and prio['telemetry'] is False
print('DW_WORLD_MASK_EXACT_SUN3_FIRE_E_SHADOW_PRIORITY_LINEAGE_PASS')
PY
python3 integration/crypt1-world-pcf2x2-v1/apply.py sept-source --proof evidence/CRYPT1_WORLD_MASK_SOURCE_PROOF.json | tee evidence/CRYPT1_WORLD_MASK_APPLY.txt
grep -Fxq DW_CRYPT1_WORLD_PCF2X2_EXACT_SOURCE_PATCH_PASS evidence/CRYPT1_WORLD_MASK_APPLY.txt
python3 integration/crypt1-world-pcf2x2-v1/test.py sept-source --out evidence/worldmask-glsl --require-glslang | tee evidence/CRYPT1_WORLD_MASK_GLSL_TESTS.txt
grep -Fxq DW_CRYPT1_WORLD_PCF2X2_STATIC_GLSL_NUMERIC_PASS evidence/CRYPT1_WORLD_MASK_GLSL_TESTS.txt
git -C sept-source diff --check
: > evidence/CRYPT1_WORLD_GATE_ONLY_SOURCE.patch
for file in dlight_fp.glsl lightall_fp.glsl; do
    rel="SP/code/rend2/glsl/$file"
    diff -u --label "a/$rel" --label "b/$rel" "evidence/worldmask-before/$rel" "sept-source/$rel" >> evidence/CRYPT1_WORLD_GATE_ONLY_SOURCE.patch || test "$?" -eq 1
done
test -s evidence/CRYPT1_WORLD_GATE_ONLY_SOURCE.patch
git -C sept-source apply --reverse --check ../evidence/CRYPT1_WORLD_GATE_ONLY_SOURCE.patch
if python3 integration/crypt1-world-pcf2x2-v1/apply.py sept-source --proof evidence/SECOND_APPLY_UNEXPECTED.json > evidence/SECOND_APPLY_OUTPUT.txt 2>&1; then
    echo 'DOUBLE_WORLD_MASK_PATCH_WAS_NOT_REJECTED' >&2
    exit 1
fi
python3 integration/crypt1-world-pcf2x2-v1/apply.py evidence/worldmask-replay --proof evidence/CRYPT1_WORLD_MASK_REPLAY_PROOF.json
for file in dlight_fp.glsl lightall_fp.glsl; do
    cmp "sept-source/SP/code/rend2/glsl/$file" "evidence/worldmask-replay/SP/code/rend2/glsl/$file"
done
python3 - <<'PY'
import json,pathlib
a=json.loads(pathlib.Path('evidence/CRYPT1_WORLD_MASK_SOURCE_PROOF.json').read_text())
b=json.loads(pathlib.Path('evidence/CRYPT1_WORLD_MASK_REPLAY_PROOF.json').read_text())
expected=['SP/code/rend2/glsl/dlight_fp.glsl','SP/code/rend2/glsl/lightall_fp.glsl']
assert sorted(a['changed_source_files'])==expected
assert a['accepted_binary_base_run']==40628480022
assert a['before_sha256']==b['before_sha256']
assert a['after_sha256']==b['after_sha256']
assert a['new_cvars']==[] and a['telemetry'] is False
assert a['old_world_function_sha256']=='2e518538bb8fb3db37377e539b8642e4c18bd1327e1b1ef1bf1cabdb909348d8'
print('DW_CRYPT1_WORLD_MASK_EXACT_REPLAY_ALLOWLIST_PASS')
PY
echo DW_CRYPT1_WORLD_PCF2X2_FULL_CI_PREFLIGHT_PASS
