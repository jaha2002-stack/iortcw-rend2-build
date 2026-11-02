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
echo '6d143993ecd24537aa1b66e6649b43ba5281c3d5f21cee527192ef20c1336dec  integration/cas-a2c-lut/feature.patch' | sha256sum -c -
git -C source apply --check "$GITHUB_WORKSPACE/integration/cas-a2c-lut/feature.patch"
git -C source apply "$GITHUB_WORKSPACE/integration/cas-a2c-lut/feature.patch"
# Only v03 CAS shader and LUT generator may change; guard A2C and lighting sources.
for file in SP/code/rend2/tr_shade.c SP/code/rend2/glsl/generic_fp.glsl SP/code/rend2/glsl/lightall_fp.glsl SP/code/rend2/tr_scene.c; do
  sha256sum "source/$file"
done > evidence/safety-files-before.sha256
echo 'b9f83421ebc55e5bc1d9ab3fc023eece71cc6e0a3203ab4e6eafd3d8ae83059a  integration/cas-a2c-lut/DARKWOLF_3FX_VISIBLE_V03.patch' | sha256sum -c -
git -C source apply --check "$GITHUB_WORKSPACE/integration/cas-a2c-lut/DARKWOLF_3FX_VISIBLE_V03.patch"
git -C source apply "$GITHUB_WORKSPACE/integration/cas-a2c-lut/DARKWOLF_3FX_VISIBLE_V03.patch"
sha256sum -c evidence/safety-files-before.sha256
grep -Fq '9-tap neighborhood' source/SP/code/rend2/glsl/dwfinal_fp.glsl
grep -Fq 'DARKWOLF_3FX_VISIBLE_V03' source/SP/code/rend2/tr_image.c
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
# Four-week master clean release: change ONLY source-level defaults after all validated feature patches.
# Do not alter approved shader algorithms, CSM, fire/light containment, bloom or game modules.
python3 - <<'PYDEFAULTS'
from pathlib import Path
import re, hashlib, difflib, json
p = Path('source/SP/code/rend2/tr_init.c')
before = p.read_text()
rules = {
  'r_dwTextureFidelity': ('0','1'),
  'r_dwMaterialFidelity': ('0','1'),
  'r_dwCas': ('0','1'),
  'r_dwCasStrength': ('0.35','0.55'),
  'r_dwA2C': ('0','1'),
  'r_dwLut': ('0','1'),
  'r_dwLutStrength': ('0.35','0.80'),
  'r_forceSun': ('0','1'),
  'r_ssgi': ('0','1'),
  'r_ext_framebuffer_multisample': ('0','4'),
}
after = before
for name,(old,new) in rules.items():
    expression = re.compile(r'(\b'+re.escape(name)+r'\s*=\s*ri\.Cvar_Get\(\s*"'+re.escape(name)+r'"\s*,\s*)"'+re.escape(old)+r'"')
    after,count=expression.subn(lambda m: m.group(1)+'"'+new+'"',after)
    assert count==1,(name,'unexpected source drift, expected exactly one CVar default',count)
p.write_text(after)
for name,(old,new) in rules.items():
    expression = re.compile(r'\b'+re.escape(name)+r'\s*=\s*ri\.Cvar_Get\(\s*"'+re.escape(name)+r'"\s*,\s*"'+re.escape(new)+r'"')
    assert len(expression.findall(after))==1,(name,'unexpected after-state')
assert 'r_bloom = ri.Cvar_Get( "r_bloom", "1"' in after,'Bloom v2 default changed'
assert 'r_dlightMode = ri.Cvar_Get( "r_dlightMode", "2"' in after,'Approved dynamic-light mode changed'
assert 'r_volumetricSun = ri.Cvar_Get( "r_volumetricSun", "1"' in after,'Sun volumetrics changed'
assert 'r_volumetricLocal = ri.Cvar_Get( "r_volumetricLocal", "1"' in after,'Local volumetrics changed'
assert 'DARKWOLF_TEXTURE_MATERIAL_FIDELITY_V01' in after
assert 'DARKWOLF_CAS_A2C_LUT_V01' in after
assert 'DARKWOLF_RC4_FORCE_SUN_CSM_REPRIME_V1' in Path('source/SP/code/rend2/tr_scene.c').read_text()
d = ''.join(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),
                fromfile='a/SP/code/rend2/tr_init.c',tofile='b/SP/code/rend2/tr_init.c'))
Path('dist/RELEASE_CODE_DEFAULTS.patch').write_text(d)
Path('dist/RELEASE_SOURCE_DEFAULTS.json').write_text(json.dumps({
  'build':'DARKWOLF_REND2_4WEEK_CLEAN_MASTER_20261024',
  'reference':'RC4 Bloom v2 38798189322 + CSM Guard + Texture Fidelity + A2C/CAS/LUT V03',
  'source_before_sha256': hashlib.sha256(before.encode()).hexdigest(),
  'source_after_sha256': hashlib.sha256(after.encode()).hexdigest(),
  'default_changes':{k:{'from':v[0],'to':v[1]} for k,v in rules.items()},
  'preexisting_verified_defaults':{'r_bloom':'1','r_bloomMode':'2','r_dlightMode':'2',
       'r_volumetricSun':'1','r_volumetricLocal':'1'},
  'unchanged_source_files':'all other source files',
  'real_windows_gpu_acceptance':'PENDING_USER_TEST'
},indent=2)+'\n')
print('PASS_CODE_DEFAULTS_10_SOURCE_ONLY',hashlib.sha256(after.encode()).hexdigest())
PYDEFAULTS
git -C source diff --check

# DARKWOLF_LUT_V05_PROCEDURAL_GRADE_GPU_ATLAS_BYPASS:
# Exact user-failed FourWeek SourceDefaultsON renderer, then ONLY three bounded
# diagnostic source changes. Do not touch the accepted game/GPU effect pipeline.
for entry in \
  'ba66fc58016b3e109ae45a69b6d24c0704cc257178f6ac18d67abe784f773fb2 SP/code/rend2/tr_backend.c' \
  '8f0bb610e830a65b3f935ae552c179f6ffd45f7e3d6e1d95879985c960a3ef0e SP/code/rend2/tr_glsl.c' \
  '816c6ecc51cb16120d3ffa05316f7ae294580d98540464c6219c07f4c81d9445 SP/code/rend2/glsl/dwfinal_fp.glsl'; do
  set -- $entry
  test "$(sha256sum "source/$2" | cut -d' ' -f1)" = "$1"
done
echo '740e046b27709d1bbd8799d19020fe6475e66c0dcb1ac61b608af0ce4e162b22  integration/lut-v05/LUT_V05_ATLAS_BYPASS_ONLY.patch' | sha256sum -c -
git -C source diff --name-only | LC_ALL=C sort > evidence/v05-unstaged-before.txt
git -C source apply --check "$GITHUB_WORKSPACE/integration/lut-v05/LUT_V05_ATLAS_BYPASS_ONLY.patch"
git -C source apply "$GITHUB_WORKSPACE/integration/lut-v05/LUT_V05_ATLAS_BYPASS_ONLY.patch"
git -C source diff --check
python3 integration/lut-v05/test_lut_v05.py source | tee evidence/lut-v05-static-tests.log
git -C source diff --name-only | LC_ALL=C sort > evidence/v05-unstaged-after.txt
python3 - <<'PY_V05_DELTA'
from pathlib import Path
before=set(Path('evidence/v05-unstaged-before.txt').read_text().splitlines())
after=set(Path('evidence/v05-unstaged-after.txt').read_text().splitlines())
expected={
 'SP/code/rend2/tr_backend.c',
 'SP/code/rend2/tr_glsl.c',
 'SP/code/rend2/glsl/dwfinal_fp.glsl',
}
assert after-before==expected,(after-before, expected)
assert not before-after,(before-after)
assert before=={'SP/code/rend2/tr_init.c'},before
print('LUT_V05_THREE_FILE_ISOLATION_PASS', sorted(expected))
PY_V05_DELTA
cp integration/lut-v05/LUT_V05_ATLAS_BYPASS_ONLY.patch dist/
cp evidence/lut-v05-static-tests.log dist/
printf '%s\n' \
  'BUILD_STATUS=DIAGNOSTIC_ONLY' \
  'PRODUCTION_ACCEPTANCE=NO' \
  'LUT_BACKEND=PURE_GLSL_BOUNDED_ANALYTIC_GRADE_NO_ATLAS_TEXTURE_SAMPLE' \
  'CAS_MODE=UNCHANGED' \
  'BLOOM_V2_CSM_GUARD_FIRE_TESLA_SSGI_VOLUMETRIC=UNCHANGED' \
  'RUNTIME_MARKER=DARKWOLF_LUT_V05_PROCEDURAL_ACTIVE' \
  'WINDOWS_GPU_TEST=PENDING' > dist/LUT_V05_TEST_STATUS.txt

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
cp integration/cas-a2c-lut/DARKWOLF_3FX_VISIBLE_V03.patch dist/
cp evidence/changed-files.txt dist/
printf '%s\n' 'WIN64_DLL_BUILD=PASS' 'CAS_LUT_V03_SOURCE=PASS' 'A2C_CSM_PRESERVED=PASS_SHA256' 'REAL_GAME_SCREENSHOTS=SEE_SEPARATE_V03_WORKFLOW' 'WINDOWS_GPU_PERFORMANCE=NOT_MEASURED' > dist/ACCEPTANCE_STATUS.txt
echo 3FX_VISIBLE_V03_WINDOWS_BUILD_OK

# End-to-end safety proof for the compiled Win64 renderer (not a game-runtime substitute).
for name in r_dwTextureFidelity r_dwMaterialFidelity r_dwAdaptiveUpsample r_dwCutoutMip r_dwCas r_dwA2C r_dwLut r_bloom r_forceSun r_ssgi r_volumetricFire r_volumetricLocal r_volumetricSun r_dlightMode; do
  strings -a dist/renderer_sp_rend2_x64.dll | grep -Fx "$name" > /dev/null || { echo "Missing registered CVar: $name"; exit 1; }
done
cp evidence/fidelity-manifest.json dist/
python3 - <<'PYSEAL'
from pathlib import Path
import hashlib,json
dll=Path('dist/renderer_sp_rend2_x64.dll').read_bytes()
report=json.loads(Path('dist/RELEASE_SOURCE_DEFAULTS.json').read_text())
report['renderer_sha256']=hashlib.sha256(dll).hexdigest()
report['renderer_size_bytes']=len(dll)
report['status']='WIN64_DLL_COMPILE_AND_SOURCE_GATES_PASS'
report['fire_light_containment']='INHERITED_FROM_APPROVED_BLOOM_V2_RC4_SOURCE'
report['gpu_fps']='NOT_MEASURED'
Path('dist/RELEASE_SOURCE_DEFAULTS.json').write_text(json.dumps(report,indent=2)+'\n')
Path('dist/ACCEPTANCE_STATUS.txt').write_text(
    'WIN64_DLL_BUILD=PASS\nCSM_GUARD=APPLIED_AND_SOURCE_VERIFIED\n'
    'TEXTURE_MATERIAL_FIDELITY=DEFAULT_ON_IN_SOURCE\n'
    'CAS_A2C_LUT_VISIBLE_V03=DEFAULT_ON_IN_SOURCE\n'
    'MSAA_DEFAULT=4X\nBLOOM_V2=SOURCE_VERIFIED_ON\n'
    'SOURCE_INVENTORY=APPROVED_V03_PLUS_10_DEFAULT_VALUES_ONLY\n'
    'REAL_WINDOWS_GPU_TEST=USER_ACCEPTANCE_PENDING\n')
PYSEAL
# Final artifact identity for on-device Windows confirmation.
strings -a dist/renderer_sp_rend2_x64.dll | grep -F 'DARKWOLF_LUT_V05_PROCEDURAL_ACTIVE'
echo 'LUT_V05_DIAGNOSTIC_COMPILE_PASS'
echo DARKWOLF_4WEEK_MASTER_WIN64_BUILD_OK
