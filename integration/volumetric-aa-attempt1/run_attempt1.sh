#!/usr/bin/env bash
set -Eeuo pipefail
mkdir -p evidence base-artifact base-release

echo '=== VAA Attempt 1: verify exact v4.4.2 ==='
run="$(gh api "/repos/${GITHUB_REPOSITORY}/actions/runs/${BASE_RUN_ID}")"
test "$(jq -r .head_sha <<<"$run")" = "$BASE_HEAD_SHA"
test "$(jq -r .conclusion <<<"$run")" = success
row="$(gh api "/repos/${GITHUB_REPOSITORY}/actions/runs/${BASE_RUN_ID}/artifacts?per_page=100" --jq ".artifacts[] | select(.id == ${BASE_ARTIFACT_ID}) | [.name,.expired,.digest] | @tsv")"
IFS=$'\t' read -r n expired digest <<<"$row"
test "$n" = "$BASE_ARTIFACT_NAME"; test "$expired" = false; test "$digest" = "$BASE_ARTIFACT_DIGEST"
gh run download "$BASE_RUN_ID" --repo "$GITHUB_REPOSITORY" --name "$BASE_ARTIFACT_NAME" --dir base-artifact
base_zip="base-artifact/${BASE_ARTIFACT_NAME}.zip"
test "$(sha256sum "$base_zip"|awk '{print $1}')" = "$BASE_INNER_SHA256"
unzip -q "$base_zip" -d base-release
base="$(find base-release -mindepth 1 -maxdepth 1 -type d -print -quit)"
test -n "$base"
test "$(sha256sum "$base/renderer_sp_rend2_x64.dll"|awk '{print $1}')" = "$BASE_RENDERER_SHA256"
test "$(sha256sum "$base/docs/$BASE_CUMULATIVE"|awk '{print $1}')" = "$BASE_CUMULATIVE_SHA256"
test "$(sha256sum "$base/docs/$BASE_UI_V44"|awk '{print $1}')" = "$BASE_UI_V44_SHA256"
test "$(sha256sum "$base/docs/$BASE_UI_V442"|awk '{print $1}')" = "$BASE_UI_V442_SHA256"
echo 'EXACT_V442_BASE_PASS' | tee evidence/01-base-status.txt

echo '=== reconstruct exact source + recover accepted GLSL ==='
rm -rf source
git clone -q "$UPSTREAM_REPO" source
git -C source checkout -q --detach "$UPSTREAM_SHA"
cp "$base/docs/$BASE_CUMULATIVE" base-cumulative.patch
cp "$base/docs/$BASE_UI_V44" ui-v44.patch
cp "$base/docs/$BASE_UI_V442" ui-v442.patch
git -C source apply --binary --whitespace=nowarn ../base-cumulative.patch
git -C source apply --binary --whitespace=nowarn ../ui-v44.patch
git -C source apply --binary --whitespace=nowarn ../ui-v442.patch
bash testlab/scripts/restore_shader_sources.sh source evidence
grep -Fq 'DARKWOLF_LOCAL_VOLUMETRIC_SPOTLIGHT_QUALITY_V0_4' source/SP/code/rend2/glsl/volumetriclocal_upscale_fp.glsl
grep -Fq 'DARKWOLF_FIREVOL_SPATIAL_RECONSTRUCTION_EDGE_QUALITY_PC02' source/SP/code/rend2/glsl/volumetriclocal_upscale_fp.glsl
grep -Fq 'DARKWOLF_SUN_VOLUMETRIC_V0_3' source/SP/code/rend2/glsl/volumetricsun_fp.glsl
grep -Fq 'FBO_FastBlit(tr.renderFbo, NULL, tr.msaaResolveFbo' source/SP/code/rend2/tr_backend.c
git -C source add -A
git -C source -c user.name='DarkWolf VAA Audit' -c user.email='vaa@example.invalid' commit -q -m 'Exact v4.4.2 source plus recovered GLSL'
basecommit="$(git -C source rev-parse HEAD)"
echo 'EXACT_V442_SOURCE_PASS' | tee evidence/02-source-status.txt

echo '=== apply telemetry-first one-file diagnostic delta ==='
python3 "$PATCHER" source
git -C source diff --check "$basecommit" --
mapfile -t changed < <(git -C source diff --name-only "$basecommit" -- | LC_ALL=C sort)
test "${changed[*]}" = 'SP/code/rend2/tr_backend.c'
git -C source diff --binary "$basecommit" -- SP/code/rend2/tr_backend.c > evidence/volumetric-aa-attempt1-source-delta.patch
grep -Fq 'VAA_TRACE pass=' source/SP/code/rend2/tr_backend.c
grep -Fq 'fullres-depth-aware' source/SP/code/rend2/tr_backend.c
grep -Fq 'baseline-quarter-direct' source/SP/code/rend2/tr_backend.c
grep -Fq 'mode == 4 && r_volumetricLocalSpotUpscale && r_volumetricLocalSpotUpscale->integer' source/SP/code/rend2/tr_backend.c
grep -Fq 'mode >= 5 && mode <= 8 && s_rVolumetricFireUpscale' source/SP/code/rend2/tr_backend.c
echo 'ATTEMPT1_ONE_FILE_DELTA_PASS' | tee evidence/03-delta-status.txt

echo '=== apply TestLab automation instrumentation ==='
python3 testlab/scripts/apply_testlab_instrumentation.py source
grep -Fq 'TESTLAB_BRIEFING_BYPASS' source/SP/code/cgame/cg_info.c
grep -Fq 'TESTLAB_STARTCAM_SUPPRESSED' source/SP/code/cgame/cg_servercmds.c
grep -Fq 'DARKWOLF_VOLUMETRIC_AA_DIAG_ATTEMPT1' source/SP/code/rend2/tr_backend.c

echo '=== native Linux Rend2 build ==='
make -C source/SP -j2 BUILD_CLIENT=1 BUILD_SERVER=0 BUILD_GAME_SO=1 BUILD_GAME_QVM=0 BUILD_BASEGAME=1 BUILD_RENDERER_REND2=1 USE_RENDERER_DLOPEN=1
exe="$(find source/SP/build -type f -iname 'iowolfsp.*' -perm -111 -print -quit)"
test -n "$exe" && test -x "$exe"
root="$(dirname "$exe")"
rend2so="$(find "$root" -maxdepth 1 -type f -iname '*rend2*.so' -print -quit)"
test -s "$rend2so"
strings "$rend2so" | grep -Fq 'VAA_TRACE pass='
file "$exe" | tee evidence/native-executable.txt
echo 'NATIVE_COMPILE_PASS' | tee evidence/04-compile-status.txt

echo '=== protected retail asset gate ==='
if [ -z "${ASSET_TOKEN:-}" ]; then
  echo 'BLOCKED_MISSING_RETAIL_ASSET_TOKEN' | tee evidence/runtime-status.txt
  exit 0
fi
retail_main="$(GH_TOKEN="$ASSET_TOKEN" bash testlab/scripts/fetch_private_release_assets.sh "$ASSET_REPO" "$ASSET_RELEASE_TAG" protected-assets | tail -1)"
test -d "$retail_main"

echo '=== assemble native runtime ==='
rm -rf runtime home-local home-sun
mkdir -p runtime/main home-local home-sun evidence/screenshots
cp -a "$root/." runtime/
find "$retail_main" -maxdepth 1 -type f -iname '*.pk3' -exec cp -a {} runtime/main/ \;
cp "$base/Main/UNIFIED_PRODUCTION.cfg" runtime/main/UNIFIED_PRODUCTION.cfg
test -s runtime/main/pak0.pk3 || test -s runtime/main/PAK0.PK3
{
  for p in runtime/main/*.pk3 runtime/main/*.PK3; do
    [ -f "$p" ] || continue
    unzip -Z1 "$p" 2>/dev/null | sed -n 's#^[Mm][Aa][Pp][Ss]/\([^/]*\)\.[Bb][Ss][Pp]$#\1#p'
  done
} | tr '[:upper:]' '[:lower:]' | LC_ALL=C sort -u > evidence/available-maps.txt
grep -Fxq escape1 evidence/available-maps.txt
: > .sun_map
for candidate in village1 village2 forest airfield assault dam castle; do
  if grep -Fxq "$candidate" evidence/available-maps.txt; then echo "$candidate" > .sun_map; break; fi
done
test -s .sun_map
echo "SUN_TEST_MAP=$(cat .sun_map)" | tee evidence/05-sun-map.txt

cat > runtime/main/vaa_local_a1.cfg <<'EOF'
set r_volumetricAATrace 1
set r_volumetricAAKernel 2
set r_volumetricAADepthReject 4
set r_volumetricAAMode 0
set cg_drawGun 1
set cg_draw2D 0
echo VAA_LOCAL_CAMERA fixture=918 origin=384,192,520 view=544,192,456 pitch=-21.801 yaw=180
dw_testView 544.000 192.000 456.000 -21.801 180.000 0
wait 120
screenshot vaa_local_baseline
wait 30
set r_volumetricAAMode 1
wait 120
screenshot vaa_local_fullres
wait 30
set r_volumetricAAMode 0
wait 120
screenshot vaa_local_baseline2
wait 30
quit
EOF

cat > runtime/main/vaa_sun_a1.cfg <<'EOF'
set r_volumetricAATrace 1
set r_volumetricAAKernel 2
set r_volumetricAADepthReject 4
set r_volumetricAAMode 0
wait 120
screenshot vaa_sun_baseline
wait 30
set r_volumetricAAMode 2
wait 120
screenshot vaa_sun_fullres
wait 30
set r_volumetricAAMode 0
wait 120
screenshot vaa_sun_baseline2
wait 30
quit
EOF

run_ab() {
  local pass="$1" map="$2" home="$3" cfg="$4" local_on="$5" sun_on="$6"
  local qlog rc
  set +e
  LIBGL_ALWAYS_SOFTWARE=1 xvfb-run -a timeout -k 15s 300s runtime/"$(basename "$exe")" \
    +set fs_basepath "$PWD/runtime" +set fs_homepath "$PWD/$home" \
    +set com_introplayed 1 +set logfile 2 +set r_fulscreen 0 +set dw_testAutomation 1 \
    +set r_renderer rend2 +set r_mode -1 +set r_customwidth 1280 +set r_customheight 768 \
    +set r_hdr 1 +set r_postProcess 1 +set r_ext_framebuffer_multisample 4 \
    +set r_volumetricLocal "$local_on" +set r_volumetricLocalMode 5 \
    +set r_volumetricSun "$sun_on" +set r_volumetricSunMode 1 +set r_sunlightMode 1 +set r_forceSun 0 \
    +set r_staticPromoteMaxLights 32 +set r_dlightShadowMaxLights 3 \
    +spdevmap "$map" +wait 420 +exec "$cfg"
  rc=$?
  set -e
  echo "$rc" > "evidence/${pass}-exit-code.txt"
  qlog="$(find "$home" -type f \( -iname 'qconsole.log' -o -iname 'rtcwconsole.log' \) -print -quit)"
  test -n "$qlog"
  cp "$qlog" "evidence/${pass}-qconsole.log"
  grep "VAA_TRACE pass=${pass}" "$qlog" > "evidence/${pass}-vaa-trace.txt" || true
  grep -Fq 'path=baseline-quarter-direct' "evidence/${pass}-vaa-trace.txt"
  grep -Fq 'path=fullres-depth-aware' "evidence/${pass}-vaa-trace.txt"
  grep -Fq 'resolvedSource=1' "evidence/${pass}-vaa-trace.txt"
  grep -Fq 'quarter=640x384' "evidence/${pass}-vaa-trace.txt"
  grep -Fq 'scratch=1280x768' "evidence/${pass}-vaa-trace.txt"
  find "$home" -type f -path "*/screenshots/vaa_${pass}_*.tga" -exec cp -a {} evidence/screenshots/ \;
  test "$(find evidence/screenshots -type f -name "vaa_${pass}_*.tga" | wc -l)" -eq 3
  test "$rc" -eq 0
  echo "${pass^^}_RUNTIME_AB_PASS" | tee "evidence/06-${pass}-runtime-status.txt"
}

echo '=== Local A/B ==='
run_ab local escape1 home-local vaa_local_a1.cfg 1 0

echo '=== Sun A/B ==='
run_ab sun "$(cat .sun_map)" home-sun vaa_sun_a1.cfg 0 1

echo '=== image + telemetry analysis ==='
python3 - <<'PY'
from pathlib import Path
from PIL import Image
import numpy as np, json, re
root=Path('evidence/screenshots'); out={'attempt':1}
def load(name):
    p=root/(name+'.tga'); im=Image.open(p).convert('RGB'); im.save(root/(name+'.png')); return np.asarray(im,dtype=np.float32)/255.0
def lum(a): return a[...,0]*.2126+a[..,1]*.7152+a[...,2]*.0722
def edge(a):
    l=lum(a); c=l[1:-1,1:-1]; lap=np.abs(4*c-l[1:-1,:-2]-l[1:-1,2:]-l[:-2,1:-1]-l[2:,1:-1])
    return {'mean':float(lap.mean()),'p99':float(np.quantile(lap,.99))}
for p in ('local','sun'):
    a=load(f'vaa_{p}_baseline'); b=load(f'vaa_{p}_fullres'); c=load(f'vaa_{p}_baseline2')
    mad=float(np.abs(a-b).mean()); drift=float(np.abs(a-c).mean())
    trace=Path(f'evidence/{p}-vaa-trace.txt').read_text(errors='replace').splitlines()
    rows=[dict(re.findall(r'(\w+)=([^\s]+)',x)) for x in trace]
    out[p]={'resolution':[int(a.shape[1]),int(a.shape[0])], 'baseline_vs_fullres_mad':mad,
           'baseline_drift_mad':drift, 'change_over_drift_ratio':mad/max(drift,1e-7),
            'edge_baseline':edge(a), 'edge_fullres':edge(b), 'edge_baseline2':edge(c),
            'trace_tail':rows[-12:]}
Path('evidence/volumetric-aa-attempt1-analysis.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
PY

echo 'ATTEMPT1_RUNTIME_TELEMETRY_COMPLETE' | tee evidence/runtime-status.txt
