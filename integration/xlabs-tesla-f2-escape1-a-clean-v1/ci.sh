#!/usr/bin/env bash
set -Eeuo pipefail
# Runs immediately AFTER accepted Sun3+Fire E, Crypt1 shadow priority and PCF2x2.
name=integration/xlabs-tesla-f2-escape1-a-clean-v1
mkdir -p evidence/dw-prod-base/SP/code/rend2/glsl evidence/dw-prod-replay/SP/code/rend2/glsl evidence/dw-prod-glsl
python3 -m py_compile "$name/qa.py" "$name/package.py"
for f in tr_main.c tr_scene.c tr_glsl.c glsl/dlight_fp.glsl glsl/lightall_fp.glsl; do
  cp "sept-source/SP/code/rend2/$f" "evidence/dw-prod-base/SP/code/rend2/$f"
  cp "sept-source/SP/code/rend2/$f" "evidence/dw-prod-replay/SP/code/rend2/$f"
done
printf '%s\n' \
  '070f2bfa3c3f1d7beb02333f2ce124afc456e472e971a05afd68b6161448d0ea  sept-source/SP/code/rend2/tr_main.c' \
  '2ce98792ab054ea59529ac103a9485443f08d2c8d34b0e8ded42d2aacf9ebcaf  sept-source/SP/code/rend2/tr_scene.c' \
  '8f0bb610e830a65b3f935ae552c179f6ffd45f7e3d6e1d95879985c960a3ef0e  sept-source/SP/code/rend2/tr_glsl.c' \
  '1651e1e14c8154aead2616856ba2d7c1c5ab66b69fb26bd049a5dd9e236ed08c  sept-source/SP/code/rend2/glsl/dlight_fp.glsl' \
  'f5d93f15acedb9139f648658774bc409690d07ef0a34f52058fe053c13bee2cd  sept-source/SP/code/rend2/glsl/lightall_fp.glsl' | sha256sum -c -
sha256sum "$name/EXACT_BASE_DELTA.patch.gz.b64" | tee evidence/X2_F2_A_PAYLOAD_BASE64_SHA256.txt
test "$(sha256sum "$name/EXACT_BASE_DELTA.patch.gz.b64" | cut -d' ' -f1)" = df29ee63e6fc24d5daf8ffafae933f3c4db58ca372154f82ee98dc1da760d8af
base64 -d "$name/EXACT_BASE_DELTA.patch.gz.b64" > evidence/DW_PRODUCTION_DELTA.patch.gz
test "$(sha256sum evidence/DW_PRODUCTION_DELTA.patch.gz | cut -d' ' -f1)" = 08abb946967c89fb207e49048ccc5fdf077934ac3c1d964d066f9d9b2428dfa7
gzip -dc evidence/DW_PRODUCTION_DELTA.patch.gz > evidence/DW_PRODUCTION_EXACT_BASE_PATCH.patch
test "$(sha256sum evidence/DW_PRODUCTION_EXACT_BASE_PATCH.patch | cut -d' ' -f1)" = 78b377e8b45b969f541e82052130babc9db8918e07c92becd7f7fc10e0539a0f
python3 - <<'PY'
from pathlib import Path
p=Path('evidence/DW_PRODUCTION_EXACT_BASE_PATCH.patch').read_text()
starts=[s[6:] for s in p.splitlines() if s.startswith('+++ b/')]
allowed=['SP/code/rend2/tr_main.c','SP/code/rend2/tr_scene.c','SP/code/rend2/tr_glsl.c',
         'SP/code/rend2/glsl/dlight_fp.glsl','SP/code/rend2/glsl/lightall_fp.glsl']
assert starts==allowed,starts
assert p.count('+++ b/')==5 and p.count('--- a/')==5
for bad in ['r_dwTeslaWorldFilterTest','r_dwTeslaWorldCaptureXTest',
            'r_dwEscape1NativeWorldMaskTest','r_dwMainSceneLightAuditOnce','DW_MAIN_SCENE_AUDIT_V4']:
 assert bad not in p,('FORBIDDEN_PRODUCTION_DELTA',bad)
print('DW_CLEAN_PATCH_ALLOWLIST_AND_NO_TEST_CVARS_PASS')
PY
git -C sept-source diff --name-only > evidence/DW_PREVIOUS_SOURCE_DIFFERENCES.txt
git -C sept-source apply --check ../evidence/DW_PRODUCTION_EXACT_BASE_PATCH.patch
git -C sept-source apply ../evidence/DW_PRODUCTION_EXACT_BASE_PATCH.patch
git -C sept-source diff --check
git -C sept-source apply --reverse --check ../evidence/DW_PRODUCTION_EXACT_BASE_PATCH.patch
if git -C sept-source apply --check ../evidence/DW_PRODUCTION_EXACT_BASE_PATCH.patch >/dev/null 2>&1; then
  echo 'CLEAN_PRODUCTION_PATCH_APPLIED_TWICE' >&2; exit 1
fi
printf '%s\n' \
  'a304b1e0a30b9d834c9180e15e9275dd40fc08e939f38e675815f4cadca4da59  sept-source/SP/code/rend2/tr_main.c' \
  '273e7ead08b25a2b035b69578c2e41b34a7712bba3646fee1961042a5154f7c5  sept-source/SP/code/rend2/tr_scene.c' \
  '9de909410773f35e0f967de7fbaff0bc4d5b3e86191734410b5e3f8aff894907  sept-source/SP/code/rend2/tr_glsl.c' \
  'abd8c2330a21bd0101a108104bda0392fe09bc7d74649013d9271c357f6ea701  sept-source/SP/code/rend2/glsl/dlight_fp.glsl' \
  '2b16f2ad0902ba879ee5d854cc2d2f23d8668d80178074568cbcf42735157d3f  sept-source/SP/code/rend2/glsl/lightall_fp.glsl' | sha256sum -c -
# Clean independent replay of the exact source bytes, and successful reverse.
(cd evidence/dw-prod-replay && git apply --check ../DW_PRODUCTION_EXACT_BASE_PATCH.patch && git apply ../DW_PRODUCTION_EXACT_BASE_PATCH.patch)
for f in tr_main.c tr_scene.c tr_glsl.c glsl/dlight_fp.glsl glsl/lightall_fp.glsl; do
  cmp "sept-source/SP/code/rend2/$f" "evidence/dw-prod-replay/SP/code/rend2/$f"
done
(cd evidence/dw-prod-replay && git apply --reverse --check ../DW_PRODUCTION_EXACT_BASE_PATCH.patch && git apply --reverse ../DW_PRODUCTION_EXACT_BASE_PATCH.patch)
for f in tr_main.c tr_scene.c tr_glsl.c glsl/dlight_fp.glsl glsl/lightall_fp.glsl; do
  cmp "evidence/dw-prod-base/SP/code/rend2/$f" "evidence/dw-prod-replay/SP/code/rend2/$f"
done
git -C sept-source diff --name-only > evidence/DW_POST_SOURCE_DIFFERENCES.txt
python3 - <<'PY'
from pathlib import Path
pre=set(Path('evidence/DW_PREVIOUS_SOURCE_DIFFERENCES.txt').read_text().splitlines())
post=set(Path('evidence/DW_POST_SOURCE_DIFFERENCES.txt').read_text().splitlines())
extra=post-pre
allowed={'SP/code/rend2/tr_main.c','SP/code/rend2/tr_scene.c','SP/code/rend2/tr_glsl.c',
 'SP/code/rend2/glsl/dlight_fp.glsl','SP/code/rend2/glsl/lightall_fp.glsl'}
assert extra <= allowed,('UNEXPECTED_SOURCE_CHANGE',extra-allowed)
print('DW_ACCEPTED_FEATURE_CHAIN_UNRELATED_FILES_UNCHANGED',len(extra))
PY
python3 "$name/qa.py" sept-source --out evidence/dw-prod-glsl | tee evidence/DW_CLEAN_GLSL_ALL_PERMUTATIONS.txt
grep -Fq DARKWOLF_X2_F2_ESCAPE1_A_FULL_GLSL_QA_PASS evidence/DW_CLEAN_GLSL_ALL_PERMUTATIONS.txt
echo DARKWOLF_XLABS_F2_X2_ESCAPE1_A_SOURCE_SHADER_REPLAY_CLEAN_PASS
