#!/usr/bin/env bash
set -Eeuo pipefail
python3 -m py_compile integration/xlabs-escape1-origin-test-v2/{apply,test,package}.py
mkdir -p evidence/v2-before/SP/code/cgame evidence/v2-before/SP/code/rend2 \
 evidence/v2-replay/SP/code/cgame evidence/v2-replay/SP/code/rend2 evidence/v2-qa
for rel in SP/code/cgame/cg_main.c SP/code/cgame/cg_local.h SP/code/cgame/cg_ents.c SP/code/rend2/tr_main.c; do
    cp "sept-source/$rel" "evidence/v2-before/$rel"
    cp "sept-source/$rel" "evidence/v2-replay/$rel"
done
printf '%s\n' '357779fb9ccb05b0f5c062d0c8d4b91037b22201b0386081ed0f47a3104abc01  sept-source/SP/code/cgame/cg_main.c' | sha256sum -c -
printf '%s\n' 'da191b91d8fe4f0b61c67ad3167111e10e31b326f44f4af93165a451c290e310  sept-source/SP/code/cgame/cg_local.h' | sha256sum -c -
printf '%s\n' '388404c23a0d091f3b929f66e805e2eff8949578a066891fe90c3130ed7dcc6c  sept-source/SP/code/cgame/cg_ents.c' | sha256sum -c -
printf '%s\n' '070f2bfa3c3f1d7beb02333f2ce124afc456e472e971a05afd68b6161448d0ea  sept-source/SP/code/rend2/tr_main.c' | sha256sum -c -
python3 integration/xlabs-escape1-origin-test-v2/apply.py sept-source --proof evidence/XLABS_ESCAPE1_V2_SOURCE_PROOF.json | tee evidence/XLABS_ESCAPE1_V2_APPLY.txt
grep -Fxq DW_TESLA_FIRE_DIAG_V2_PATCH_PASS evidence/XLABS_ESCAPE1_V2_APPLY.txt
python3 integration/xlabs-escape1-origin-test-v2/test.py sept-source --out evidence/v2-qa | tee evidence/XLABS_ESCAPE1_V2_TESTS.txt
grep -Fxq DW_TESLA_FIRE_DIAG_V2_SOURCE_REGRESSION_PASS evidence/XLABS_ESCAPE1_V2_TESTS.txt
git -C sept-source diff --check
: > evidence/XLABS_ESCAPE1_V2_ONLY_SOURCE.patch
for rel in SP/code/cgame/cg_main.c SP/code/cgame/cg_local.h SP/code/cgame/cg_ents.c SP/code/rend2/tr_main.c; do
    diff -u --label "a/$rel" --label "b/$rel" "evidence/v2-before/$rel" "sept-source/$rel" >> evidence/XLABS_ESCAPE1_V2_ONLY_SOURCE.patch || test "$?" -eq 1
done
test -s evidence/XLABS_ESCAPE1_V2_ONLY_SOURCE.patch
git -C sept-source apply --reverse --check ../evidence/XLABS_ESCAPE1_V2_ONLY_SOURCE.patch
if python3 integration/xlabs-escape1-origin-test-v2/apply.py sept-source > evidence/V2_DOUBLE_APPLY.txt 2>&1; then
    echo 'DOUBLE_APPLY_UNEXPECTEDLY_SUCCEEDED' >&2
    exit 1
fi
python3 integration/xlabs-escape1-origin-test-v2/apply.py evidence/v2-replay --proof evidence/XLABS_ESCAPE1_V2_REPLAY.json
for rel in SP/code/cgame/cg_main.c SP/code/cgame/cg_local.h SP/code/cgame/cg_ents.c SP/code/rend2/tr_main.c; do
    cmp "sept-source/$rel" "evidence/v2-replay/$rel"
done
python3 - <<'PY'
import json
p=json.load(open('evidence/XLABS_ESCAPE1_V2_SOURCE_PROOF.json'))
r=json.load(open('evidence/XLABS_ESCAPE1_V2_REPLAY.json'))
assert p['marker']=='DARKWOLF_XLABS_ESCAPE1_DIAGNOSTIC_V2_20261028'
assert p['source_sha256_after']==r['source_sha256_after']
assert p['source_sha256_before']==r['source_sha256_before']
assert p['frozen_binary_run']==40640998083
assert len(p['changed_source_files'])==4
assert len(p['temporary_test_cvars'])==2
assert p['telemetry_on_by_default'] is False
print('DW_XLABS_ESCAPE1_V2_SOURCE_REPLAY_AND_FROZEN_LINEAGE_PASS')
PY
echo DW_XLABS_ESCAPE1_V2_CI_SOURCE_PREFLIGHT_PASS
