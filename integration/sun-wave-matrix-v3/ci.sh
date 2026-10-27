#!/usr/bin/env bash
set -Eeuo pipefail
python3 -m py_compile integration/sun-wave-matrix-v3/{apply,test,package}.py
mkdir -p evidence/sunv3-before/SP/code/rend2/glsl evidence/sunv3-replay/SP/code/rend2/glsl evidence/sunv3-shaders
for rel in tr_backend.c glsl/volumetricsun_fp.glsl; do
  cp "sept-source/SP/code/rend2/$rel" "evidence/sunv3-before/SP/code/rend2/$rel"
  cp "sept-source/SP/code/rend2/$rel" "evidence/sunv3-replay/SP/code/rend2/$rel"
done
printf '%s\n' '0cfcad4ad18882691f16749697d09a48e832b9344de4e58a11e36c3b7efb405e  sept-source/SP/code/rend2/tr_backend.c' | sha256sum -c -
printf '%s\n' '8e22ade3bba934b471b270fd5db3e6066e500acb47bc1ea03588abe1bcd780ab  sept-source/SP/code/rend2/glsl/volumetricsun_fp.glsl' | sha256sum -c -
python3 integration/sun-wave-matrix-v3/apply.py sept-source --proof evidence/SUN_V3_SOURCE_PROOF.json | tee evidence/SUN_V3_APPLY.txt
python3 integration/sun-wave-matrix-v3/test.py sept-source --out evidence/sunv3-shaders --require-glslang | tee evidence/SUN_V3_SHADER_TESTS.txt
grep -Fxq DW_SUN_WAVE_MATRIX_V3_SOURCE_PASS evidence/SUN_V3_APPLY.txt
grep -Fxq DW_SUN_WAVE_V3_SOURCE_GUARDS_PASS evidence/SUN_V3_SHADER_TESTS.txt
git -C sept-source diff --check
: > evidence/SUN_V3_ONLY_SOURCE.patch
for rel in tr_backend.c glsl/volumetricsun_fp.glsl; do
  path="SP/code/rend2/$rel"
  diff -u --label "a/$path" --label "b/$path" "evidence/sunv3-before/$path" "sept-source/$path" >> evidence/SUN_V3_ONLY_SOURCE.patch || test "$?" -eq 1
done
test -s evidence/SUN_V3_ONLY_SOURCE.patch
git -C sept-source apply --reverse --check ../evidence/SUN_V3_ONLY_SOURCE.patch
if python3 integration/sun-wave-matrix-v3/apply.py sept-source --proof evidence/SUN_V3_REPEATED.json >/dev/null 2>&1; then
  echo 'REPEAT_APPLY_NOT_REJECTED' >&2
  exit 1
fi
python3 integration/sun-wave-matrix-v3/apply.py evidence/sunv3-replay --proof evidence/SUN_V3_REPLAY.json
for rel in tr_backend.c glsl/volumetricsun_fp.glsl; do
  cmp "sept-source/SP/code/rend2/$rel" "evidence/sunv3-replay/SP/code/rend2/$rel"
done
python3 - <<'PY'
import json
p=json.load(open('evidence/SUN_V3_SOURCE_PROOF.json'))
assert p['fixture_only'] is False
assert p['exact_base_run']==40487188767
assert sorted(p['modified_files'])==sorted(['SP/code/rend2/tr_backend.c','SP/code/rend2/glsl/volumetricsun_fp.glsl'])
assert p['sha256_before']['tr_backend.c']=='0cfcad4ad18882691f16749697d09a48e832b9344de4e58a11e36c3b7efb405e'
assert p['sha256_before']['glsl/volumetricsun_fp.glsl']=='8e22ade3bba934b471b270fd5db3e6066e500acb47bc1ea03588abe1bcd780ab'
assert set(p['frozen']) >= {'Fire E','Local Volumetric','CSM producers','Sky Single-Sample'}
print('DW_SUN_V3_SOURCE_ALLOWLIST_EXACT_SHA_PASS')
PY
echo DW_SUN_V3_EXACT_REPLAY_GLSL_PASS
