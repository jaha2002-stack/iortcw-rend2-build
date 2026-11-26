#!/usr/bin/env bash
set -Eeuo pipefail
python3 -m py_compile integration/xlabs-escape1-v5-1/qa_full.py integration/xlabs-escape1-v5-1/package.py
printf '%s\n' \
 '8f0bb610e830a65b3f935ae552c179f6ffd45f7e3d6e1d95879985c960a3ef0e  sept-source/SP/code/rend2/tr_glsl.c' \
 '22c39b8796a9829a7b6ce951a3ad077dbe5b5d7643b8836692ee8d541a7655db  sept-source/SP/code/rend2/glsl/lightall_fp.glsl' \
 '3f0f27878f34b87f4b0877c83c195e30f89231ceab4e70cf8d694ab1867727cd  sept-source/SP/code/rend2/glsl/dlight_fp.glsl' | sha256sum -c -
test "$(wc -c < sept-source/SP/code/rend2/glsl/lightall_fp.glsl)" -eq 34029
grep -Fq 'char fpCode[32000];' sept-source/SP/code/rend2/tr_glsl.c
git -C sept-source apply --check ../integration/xlabs-escape1-v5-1/SHADER_BUFFER_ONLY.patch
git -C sept-source apply ../integration/xlabs-escape1-v5-1/SHADER_BUFFER_ONLY.patch
git -C sept-source apply --reverse --check ../integration/xlabs-escape1-v5-1/SHADER_BUFFER_ONLY.patch
printf '%s\n' \
 '9de909410773f35e0f967de7fbaff0bc4d5b3e86191734410b5e3f8aff894907  sept-source/SP/code/rend2/tr_glsl.c' \
 '22c39b8796a9829a7b6ce951a3ad077dbe5b5d7643b8836692ee8d541a7655db  sept-source/SP/code/rend2/glsl/lightall_fp.glsl' \
 '3f0f27878f34b87f4b0877c83c195e30f89231ceab4e70cf8d694ab1867727cd  sept-source/SP/code/rend2/glsl/dlight_fp.glsl' | sha256sum -c -
mkdir -p evidence/v5_1-fullglsl
python3 integration/xlabs-escape1-v5-1/qa_full.py sept-source --out evidence/v5_1-fullglsl
git -C sept-source apply --reverse ../integration/xlabs-escape1-v5-1/SHADER_BUFFER_ONLY.patch
printf '%s\n' '8f0bb610e830a65b3f935ae552c179f6ffd45f7e3d6e1d95879985c960a3ef0e  sept-source/SP/code/rend2/tr_glsl.c' | sha256sum -c -
git -C sept-source apply ../integration/xlabs-escape1-v5-1/SHADER_BUFFER_ONLY.patch
printf '%s\n' '9de909410773f35e0f967de7fbaff0bc4d5b3e86191734410b5e3f8aff894907  sept-source/SP/code/rend2/tr_glsl.c' | sha256sum -c -
echo DW_V5_1_SHADER_LOADER_EXACT_SOURCE_FULL_GLSL_REPLAY_PASS
