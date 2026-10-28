#!/usr/bin/env bash
set -Eeuo pipefail
python3 -m py_compile integration/crypt1-shadow-residency-v1/{apply,test,package}.py
mkdir -p evidence/crypt1-before/SP/code/rend2 evidence/crypt1-replay/SP/code/rend2 evidence/crypt1-regression
cp sept-source/SP/code/rend2/tr_main.c evidence/crypt1-before/SP/code/rend2/tr_main.c
cp sept-source/SP/code/rend2/tr_main.c evidence/crypt1-replay/SP/code/rend2/tr_main.c
# Verify the exact accepted Sun3 + Fire E renderer source state before the
# separate point-shadow change. No rebase onto a different production tree.
python3 - <<'PY'
import json,pathlib
p=json.loads(pathlib.Path('evidence/SUN3_FIRE_E_CLEAN_SOURCE_PROOF.json').read_text())
assert p['exact_binary_base_run']==40480112714
assert p['Sun']=='V3_MODE_3_DUAL_VISIBILITY_6_PERCENT_CSM'
assert p['Fire']=='E_40_RAY_STEPS_DEPTH_5X5_9_TAP'
assert p['new_diagnostic_cvars']==[]
print('DW_CRYPT1_BASE_SUN3_FIRE_E_PROVENANCE_PASS')
PY
python3 integration/crypt1-shadow-residency-v1/apply.py sept-source --proof evidence/CRYPT1_SHADOW_PRIORITY_SOURCE_PROOF.json | tee evidence/CRYPT1_SHADOW_PRIORITY_APPLY.txt
grep -Fxq DW_CRYPT1_PERSISTENT_FIRE_SHADOW_PRIORITY_SOURCE_PASS evidence/CRYPT1_SHADOW_PRIORITY_APPLY.txt
python3 integration/crypt1-shadow-residency-v1/test.py sept-source --out evidence/crypt1-regression | tee evidence/CRYPT1_SHADOW_PRIORITY_REGRESSION_TESTS.txt
grep -Fq DW_CRYPT1_SHADOW_STATIC_AND_REGRESSION_TESTS_PASS evidence/CRYPT1_SHADOW_PRIORITY_REGRESSION_TESTS.txt
git -C sept-source diff --check
diff -u --label a/SP/code/rend2/tr_main.c --label b/SP/code/rend2/tr_main.c \
 evidence/crypt1-before/SP/code/rend2/tr_main.c sept-source/SP/code/rend2/tr_main.c > evidence/CRYPT1_SHADOW_PRIORITY_ONLY_SOURCE.patch || test "$?" -eq 1
test -s evidence/CRYPT1_SHADOW_PRIORITY_ONLY_SOURCE.patch
git -C sept-source apply --reverse --check ../evidence/CRYPT1_SHADOW_PRIORITY_ONLY_SOURCE.patch
if python3 integration/crypt1-shadow-residency-v1/apply.py sept-source --proof evidence/SECOND_APPLY_SHOULD_FAIL.json > evidence/SECOND_APPLY_RESULT.txt 2>&1; then
 echo 'ERROR: DUPLICATE_SHADOW_PATCH_WAS_ACCEPTED' >&2
 exit 1
fi
python3 integration/crypt1-shadow-residency-v1/apply.py evidence/crypt1-replay --proof evidence/CRYPT1_SHADOW_PRIORITY_REPLAY_PROOF.json
cmp sept-source/SP/code/rend2/tr_main.c evidence/crypt1-replay/SP/code/rend2/tr_main.c
python3 - <<'PY'
import json,pathlib
a=json.loads(pathlib.Path('evidence/CRYPT1_SHADOW_PRIORITY_SOURCE_PROOF.json').read_text())
b=json.loads(pathlib.Path('evidence/CRYPT1_SHADOW_PRIORITY_REPLAY_PROOF.json').read_text())
assert a['marker']=='DARKWOLF_CRYPT1_PERSISTENT_FIRE_SHADOW_PRIORITY_FIX_V1_20261028'
assert a['modified_source_files']==['SP/code/rend2/tr_main.c']
assert a['before_sha256']==b['before_sha256']
assert a['after_sha256']==b['after_sha256']
assert a['new_cvars']==[] and a['telemetry'] is False
assert a['source_base_run']==40512393634
print('DW_CRYPT1_SOURCE_ALLOWLIST_REVERSE_REPLAY_NO_DIAGNOSTICS_PASS')
PY
echo DW_CRYPT1_SHADOW_PRIORITY_ACCEPTED_SOURCE_TESTS_PASS
