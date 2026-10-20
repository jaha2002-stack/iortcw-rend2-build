#!/usr/bin/env bash
set -Eeuo pipefail
mkdir -p source parent evidence dist
gh api "repos/${GITHUB_REPOSITORY}/actions/artifacts/12004010089/zip" > parent.zip
echo '6c6c2d2302e2f4f45bad9d7e3df7e2573fd79a72646bcf049596440cb62f7659  parent.zip' | sha256sum -c -
unzip -q parent.zip -d parent
(cd parent && mkdir -p dist && ln -s ../DarkWolf-v446-RC4-BloomV2-Production-Win64-SP-source.tar.gz dist/DarkWolf-v446-RC4-BloomV2-Production-Win64-SP-source.tar.gz && sha256sum -c DarkWolf-v446-RC4-BloomV2-Production-Win64-SP-source.tar.gz.sha256)
tar -xzf parent/DarkWolf-v446-RC4-BloomV2-Production-Win64-SP-source.tar.gz -C source
git -C source init -q
git -C source add -A
test "$(git -C source write-tree)" = bb1432b459a4daf72a324f3fb477744bdb51fd4a
python3 integration/rc4-final-csm/apply_csm_guard.py source
python3 integration/texture-material-fidelity/apply_fidelity.py source --manifest evidence/fidelity-manifest.json
grep -Fq DARKWOLF_RC4_FORCE_SUN_CSM_REPRIME_V1 source/SP/code/rend2/tr_scene.c
git -C source -c user.name=DarkWolf-CI -c user.email=ci@example.invalid add -A
git -C source -c user.name=DarkWolf-CI -c user.email=ci@example.invalid commit -qm baseline
echo 'f1c7cd39e81bd1ccab1a0ff358b8f0d348da193d22de5097ed4110c2f3e0a537  integration/cas-a2c-lut/feature.patch' | sha256sum -c -
git -C source apply --check "$GITHUB_WORKSPACE/integration/cas-a2c-lut/feature.patch"
git -C source apply "$GITHUB_WORKSPACE/integration/cas-a2c-lut/feature.patch"
git -C source add -A
git -C source diff --cached --check
git -C source diff --cached --name-only | LC_ALL=C sort > evidence/changed-files.txt
python3 - <<'PY'
from pathlib import Path
expected=set(['SP/Makefile']+[f'SP/code/rend2/{p}' for p in ('tr_init.c','tr_local.h','tr_image.c','tr_glsl.c','tr_backend.c','tr_shade.c','glsl/generic_fp.glsl','glsl/lightall_fp.glsl','glsl/dwfinal_fp.glsl','glsl/dwfinal_vp.glsl')])
actual=set(Path('evidence/changed-files.txt').read_text().splitlines())
assert actual==expected,(actual^expected)
print('PASS: only 11 declared feature files changed')
PY
sudo apt-get -o Acquire::Retries=3 update
sudo apt-get -o Acquire::Retries=3 install -y --no-install-recommends gcc-mingw-w64-x86-64-posix=13.2.0-6ubuntu1+26.1 g++-mingw-w64-x86-64-posix=13.2.0-6ubuntu1+26.1 binutils-mingw-w64-x86-64=2.41.90.20240122-1ubuntu1+11.4
make -C source/SP -j2 release VERSION=1.51d-SP_DarkWolf-v4.4.6-Clean-RC4 PLATFORM=mingw32 ARCH=x86_64 BUILD_CLIENT=1 BUILD_SERVER=0 BUILD_GAME_SO=1 BUILD_GAME_QVM=0 BUILD_BASEGAME=1 BUILD_RENDERER_REND2=1 USE_RENDERER_DLOPEN=1 CC=x86_64-w64-mingw32-gcc-posix CXX=x86_64-w64-mingw32-g++-posix WINDRES=x86_64-w64-mingw32-windres > evidence/windows-build.log 2>&1 || { tail -120 evidence/windows-build.log; exit 1; }
find source/SP/build -name renderer_sp_rend2_x64.dll -exec cp -v '{}' dist/renderer_sp_rend2_x64.dll \;
test -s dist/renderer_sp_rend2_x64.dll
file dist/renderer_sp_rend2_x64.dll | tee evidence/pe-header.txt
grep -Fq PE32+ evidence/pe-header.txt
for name in r_dwCas r_dwA2C r_dwLut; do strings -a dist/renderer_sp_rend2_x64.dll | grep -F "$name" >/dev/null; done
sha256sum dist/renderer_sp_rend2_x64.dll > dist/RENDERER.sha256
cp integration/cas-a2c-lut/feature.patch dist/
cp evidence/changed-files.txt dist/
printf '%s\n' 'WIN64_DLL_BUILD=PASS' 'REAL_GAME_SCREENSHOTS=NOT_RUN_IN_THIS_JOB' 'WINDOWS_GPU_PERFORMANCE=NOT_MEASURED' > dist/ACCEPTANCE_STATUS.txt
echo 3FX_WINDOWS_BUILD_OK
