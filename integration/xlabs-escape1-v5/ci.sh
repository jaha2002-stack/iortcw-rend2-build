#!/usr/bin/env bash
set -Eeuo pipefail
python3 -m py_compile integration/xlabs-escape1-v5/qa.py integration/xlabs-escape1-v5/package.py
# The complete V4 guard and replay already ran in this workflow.
printf '%s\n' \
  'f4f37f8c46b0e7b5e5ee7d24d6f069093f58fa3536685d026489b4d64d4a957f  sept-source/SP/code/rend2/tr_main.c' \
  '58e2a3aeb784558575de9d40bb64e15d1f5a7c7a8730a2d5d0d626f748d5ab37  sept-source/SP/code/rend2/tr_scene.c' \
  '1651e1e14c8154aead2616856ba2d7c1c5ab66b69fb26bd049a5dd9e236ed08c  sept-source/SP/code/rend2/glsl/dlight_fp.glsl' \
  'f5d93f15acedb9139f648658774bc409690d07ef0a34f52058fe053c13bee2cd  sept-source/SP/code/rend2/glsl/lightall_fp.glsl' | sha256sum -c -
git -C sept-source apply --check ../integration/xlabs-escape1-v5/TEST_ONLY_SOURCE.patch
git -C sept-source apply ../integration/xlabs-escape1-v5/TEST_ONLY_SOURCE.patch
git -C sept-source apply --reverse --check ../integration/xlabs-escape1-v5/TEST_ONLY_SOURCE.patch
printf '%s\n' \
  '701cce8ca117b49d20d641066bfc582148d0b1804cc23b0db9549170dd046a2e  sept-source/SP/code/rend2/tr_main.c' \
  '1bc97779bbc74279a5ab879a62a07ab7182fdc4c485ca3f7d77552f768e1a545  sept-source/SP/code/rend2/tr_scene.c' \
  '3f0f27878f34b87f4b0877c83c195e30f89231ceab4e70cf8d694ab1867727cd  sept-source/SP/code/rend2/glsl/dlight_fp.glsl' \
  '22c39b8796a9829a7b6ce951a3ad077dbe5b5d7643b8836692ee8d541a7655db  sept-source/SP/code/rend2/glsl/lightall_fp.glsl' \
  'e08d1f94b186fd46b078fbaf740e38c8cea93170836c2701c27801ad443f495f  sept-source/SP/code/rend2/tr_backend.c' \
  'f4eb7ced3eb8a18b08726cb7f5ecf55614ae9a9ae077c62f326b27b5b5c38d2fd  sept-source/SP/code/rend2/glsl/volumetricsun_fp.glsl' | sha256sum -c -
if git -C sept-source apply --check ../integration/xlabs-escape1-v5/TEST_ONLY_SOURCE.patch >/dev/null 2>&1; then
  echo V5_DOUBLE_APPLICATION_UNEXPECTED >&2; exit 1
fi
python3 integration/xlabs-escape1-v5/qa.py sept-source evidence/v5-glsl
echo DW_XLABS_ESCAPE1_V5_SOURCE_GUARD_REVERSE_REPLAY_GLSL_PASS
