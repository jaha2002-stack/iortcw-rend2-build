set -Eeuo pipefail
python3 -m py_compile integration/volumetric-overlap-diagnostic-v1/{test,package}.py
mkdir -p evidence/diag-before/SP/code/rend2/glsl evidence/diag-replay/SP/code/rend2/glsl evidence/diag-shader-tests
for rel in tr_backend.c glsl/volumetriclocal_fp.glsl; do
  cp "sept-source/SP/code/rend2/$rel" "evidence/diag-before/SP/code/rend2/$rel"
  cp "sept-source/SP/code/rend2/$rel" "evidence/diag-replay/SP/code/rend2/$rel"
done
printf '%s\n' '781410a360c485d8e37d95b56d1f900d8fc989f85225517dae03dc97119503ca  integration/volumetric-overlap-diagnostic-v1/LOCAL_OVERLAP_DIAG_V1.patch' | sha256sum -c -
printf '%s\n' '0cfcad4ad18882691f16749697d09a48e832b9344de4e58a11e36c3b7efb405e  sept-source/SP/code/rend2/tr_backend.c' | sha256sum -c -
printf '%s\n' 'ef616bfc50be66a048fe0817971e4308574ff91cab4393185f6153999dd26a67  sept-source/SP/code/rend2/glsl/volumetriclocal_fp.glsl' | sha256sum -c -
git -C sept-source apply --check ../integration/volumetric-overlap-diagnostic-v1/LOCAL_OVERLAP_DIAG_V1.patch
git -C sept-source apply ../integration/volumetric-overlap-diagnostic-v1/LOCAL_OVERLAP_DIAG_V1.patch
git -C sept-source diff --check
git -C sept-source apply --reverse --check ../integration/volumetric-overlap-diagnostic-v1/LOCAL_OVERLAP_DIAG_V1.patch
python3 integration/volumetric-overlap-diagnostic-v1/test.py sept-source --out evidence/diag-shader-tests --require-glslang | tee evidence/VOL_DIAG_STATIC_TESTS.txt
grep -Fxq DW_VOL_OVERLAP_DIAG_V1_STATIC_PASS evidence/VOL_DIAG_STATIC_TESTS.txt
python3 - <<'PY'
import hashlib,json,pathlib
r=pathlib.Path('sept-source/SP/code/rend2')
b=pathlib.Path('evidence/diag-before/SP/code/rend2')
fn=['tr_backend.c','glsl/volumetriclocal_fp.glsl']
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={f:h(b/f) for f in fn}
assert before['tr_backend.c']=='0cfcad4ad18882691f16749697d09a48e832b9344de4e58a11e36c3b7efb405e'
assert before['glsl/volumetriclocal_fp.glsl']=='ef616bfc50be66a048fe0817971e4308574ff91cab4393185f6153999dd26a67'
p={'marker':'DARKWOLF_VOL_OVERLAP_DIAG_V1_20261027','source_base':'40487188767','fixture_only':False,
   'modified_files':['SP/code/rend2/'+f for f in fn],
   'sha256_before':before,'sha256_after':{f:h(r/f) for f in fn},
   'frozen':'Sun shader, Fire E, CSM, Sky Single-Sample, SSGI, Tesla',
   'runtime_validation':'NOT_TESTED'}
pathlib.Path('evidence/VOL_DIAG_SOURCE_PROOF.json').write_text(json.dumps(p,indent=2)+'\n')
print('DW_VOL_DIAG_EXACT_BASE_SHA_PASS')
PY
if git -C sept-source apply --check ../integration/volumetric-overlap-diagnostic-v1/LOCAL_OVERLAP_DIAG_V1.patch >/dev/null 2>&1; then
  echo 'ERROR: same diagnostic patch applied twice' >&2
  exit 1
fi
(cd evidence/diag-replay && git init -q && git apply ../../integration/volumetric-overlap-diagnostic-v1/LOCAL_OVERLAP_DIAG_V1.patch)
for rel in tr_backend.c glsl/volumetriclocal_fp.glsl; do
  cmp "sept-source/SP/code/rend2/$rel" "evidence/diag-replay/SP/code/rend2/$rel"
done
echo DW_VOL_DIAG_EXACT_SOURCE_REVERSE_REPLAY_PASS
