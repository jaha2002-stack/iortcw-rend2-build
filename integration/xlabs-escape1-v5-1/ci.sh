#!/usr/bin/env bash
set -Eeuo pipefail
python3 -m py_compile integration/xlabs-escape1-v5-1/qa.py integration/xlabs-escape1-v5-1/package.py
# Only after exact V4+V5 replay and GLSL120/130 unit tests have passed.
printf '%s\n' \
  '8f0bb610e830a65b3f935ae552c179f6ffd45f7e3d6e1d95879985c960a3ef0e  sept-source/SP/code/rend2/tr_glsl.c' \
  '22c39b8796a9829a7b6ce951a3ad077dbe5b5d7643b8836692ee8d541a7655db  sept-source/SP/code/rend2/glsl/lightall_fp.glsl' \
  '3f0f27878f34b87f4b0877c83c195e30f89231ceab4e70cf8d694ab1867727cd  sept-source/SP/code/rend2/glsl/dlight_fp.glsl' | sha256sum -c -
git -C sept-source apply --check ../integration/xlabs-escape1-v5-1/LOADER_BUFFER_ONLY.patch
git -C sept-source apply ../integration/xlabs-escape1-v5-1/LOADER_BUFFER_ONLY.patch
git -C sept-source apply --reverse --check ../integration/xlabs-escape1-v5-1/LOADER_BUFFER_ONLY.patch
printf '%s\n' '61be71110ad88bc58c9a61dc19fdb1650b0b70d240c547ccfd56131c5d02e508  sept-source/SP/code/rend2/tr_glsl.c' | sha256sum -c -
# Independent reverse/replay on a single disposable copy, so no source tree is mutated.
mkdir -p evidence/v5-1-replay/SP/code/rend2
cp sept-source/SP/code/rend2/tr_glsl.c evidence/v5-1-replay/SP/code/rend2/tr_glsl.c
git -C evidence/v5-1-replay apply --reverse ../../integration/xlabs-escape1-v5-1/LOADER_BUFFER_ONLY.patch
printf '%s\n' '8f0bb610e830a65b3f935ae552c179f6ffd45f7e3d6e1d95879985c960a3ef0e  evidence/v5-1-replay/SP/code/rend2/tr_glsl.c' | sha256sum -c -
git -C evidence/v5-1-replay apply ../../integration/xlabs-escape1-v5-1/LOADER_BUFFER_ONLY.patch
printf '%s\n' '61be71110ad88bc58c9a61dc19fdb1650b0b70d240c547ccfd56131c5d02e508  evidence/v5-1-replay/SP/code/rend2/tr_glsl.c' | sha256sum -c -
python3 integration/xlabs-escape1-v5-1/qa.py sept-source evidence/v5-1-full-shaders
echo DW_XLABS_V5_1_GLSL_LOADER_BUFFER_AND_FULL_SHADER_VALIDATE_PASS
