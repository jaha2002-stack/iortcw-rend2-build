#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE_AUDIT="${1:-source-audit}"
EVIDENCE="${2:-evidence}"
mkdir -p "$EVIDENCE/v206_frames" "$EVIDENCE/v206_logs"
test -d authored_v206

ESC_PK3="$(find authored_v206 -type f -path '*escape_snow*' -name 'variant_1.pk3' -print -quit)"
CRYPT_PK3="$(find authored_v206 -type f -path '*crypt_wall*' -name 'variant_1.pk3' -print -quit)"
test -n "$ESC_PK3"
test -n "$CRYPT_PK3"

retail_main="$(cat "$EVIDENCE/retail_main_path.txt")"
test -d "$retail_main"

python3 integration/pbr-v206-twoframe/derive_crypt_wall_camera.py   "$retail_main"   "$EVIDENCE/CRYPT1_WALL_CAMERA.json"   "$EVIDENCE/crypt_wall.env"
source "$EVIDENCE/crypt_wall.env"

exe_src="$(find "$SOURCE_AUDIT/SP/build" -type f -iname 'iowolfsp*' -perm -111 -print -quit)"
test -n "$exe_src"
buildroot="$(dirname "$exe_src")"

capture_one() {
  local label="$1"
  local map="$2"
  local shader="$3"
  local material_pk3="$4"
  local x="$5"
  local y="$6"
  local z="$7"
  local yaw="$8"
  local forcesun="${9:-0}"
  local sunlightmode="${10:-0}"

  local runtime="runtime_${label}"
  local home="home_${label}"
  rm -rf "$runtime" "$home"
  mkdir -p "$runtime/main" "$home"
  cp -a "$buildroot/." "$runtime/"
  find "$retail_main" -maxdepth 1 -type f -iname '*.pk3' -exec cp -a {} "$runtime/main/" \;
  cp "$material_pk3" "$runtime/main/zzzz_dw_v206_ai_material.pk3"

  local exe
  exe="$(find "$runtime" -maxdepth 1 -type f -iname 'iowolfsp*' -perm -111 -print -quit)"
  test -n "$exe"

  set +e
  LIBGL_ALWAYS_SOFTWARE=1 xvfb-run -a timeout -k 12s 175s "$exe"     +set fs_basepath "$PWD/$runtime" +set fs_homepath "$PWD/$home"     +set com_introplayed 1 +set s_initsound 0 +set logfile 2 +set developer 0 +set con_notifytime 0     +set r_fullscreen 0 +set r_renderer rend2 +set r_mode -1 +set r_customwidth 1280 +set r_customheight 720     +set r_pbr 3 +set r_cubeMapping 1 +set r_normalMapping 1 +set r_specularMapping 1     +set r_parallaxMapping 2 +set r_parallaxMapShadows 1 +set r_pomShadowStrength 0.18     +set r_pomMinLayers 20 +set r_pomMaxLayers 56 +set r_pomRefineSteps 5 +set r_pomMaxOffset 0.028     +set r_dlightmode 2 +set r_forcesun 1     +devmap "$map" +wait 2 +setviewpos "$x" "$y" "$z" "$yaw" +wait 15     +r_pbrMaterialAudit "$shader" +wait 1 +screenshot "$label" +wait 1 +quit
  local rc=$?
  set -e

  echo "$rc" > "$EVIDENCE/v206_logs/${label}_exit.txt"
  local qlog
  qlog="$(find "$home" -type f \( -iname 'qconsole.log' -o -iname 'rtcwconsole.log' \) -print -quit)"
  test -n "$qlog"
  cp "$qlog" "$EVIDENCE/v206_logs/${label}.log"

  grep -Fq 'normalType=NORMALHEIGHT heightAlpha=1' "$EVIDENCE/v206_logs/${label}.log"
  grep -Fq 'packedORM=1' "$EVIDENCE/v206_logs/${label}.log"
  grep -Fq 'pomV32=ACTIVE' "$EVIDENCE/v206_logs/${label}.log"

  find "$home" -type f \( -iname "${label}*.tga" -o -iname "${label}*.png" -o -iname "${label}*.jpg" \) -exec cp {} "$EVIDENCE/v206_frames/" \;
  test -n "$(find "$EVIDENCE/v206_frames" -maxdepth 1 -type f -iname "${label}*" -print -quit)"
}

capture_one   escape_wetsnow_v1   escape1   textures/snow/s_cathedrale_c06   "$ESC_PK3"   -2475.551 263.887 952 107.241 1 2

capture_one   crypt_wall_wet_v1   crypt1   textures/crypt/crypt_wall_03   "$CRYPT_PK3"   "$CRYPT_X" "$CRYPT_Y" "$CRYPT_Z" "$CRYPT_YAW" 0 0

sha256sum "$EVIDENCE"/v206_frames/* | tee "$EVIDENCE/V206_TWO_FRAME_SHA256.txt"
echo DARKWOLF_V206_TWO_REAL_GAMEPLAY_FRAMES_PASS
