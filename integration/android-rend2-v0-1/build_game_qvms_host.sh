#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORKDIR="${1:-$ROOT/.android-rend2-work}"
SRC="$WORKDIR/source"
OUT="$WORKDIR/game-qvms"
BUILD="$OUT/build"

test -f "$SRC/SP/Makefile"
command -v make >/dev/null
command -v gcc >/dev/null

rm -rf "$OUT"
mkdir -p "$OUT"/{bin,log}
trap 'rc=$?; echo "GAME_QVM_BUILD_FAILED=$rc"; test ! -f "$OUT/log/build.log" || tail -n 240 "$OUT/log/build.log"; exit $rc' ERR

make -C "$SRC/SP" -j2 release \
  BUILD_DIR="$BUILD" \
  BUILD_CLIENT=0 \
  BUILD_SERVER=0 \
  BUILD_GAME_SO=0 \
  BUILD_GAME_QVM=1 \
  BUILD_BASEGAME=1 \
  USE_OPENAL=0 \
  USE_CURL=0 \
  USE_CODEC_VORBIS=0 \
  USE_CODEC_OPUS=0 \
  USE_MUMBLE=0 \
  USE_VOIP=0 \
  USE_FREETYPE=0 \
  >"$OUT/log/build.log" 2>&1

for module in ui cgame qagame; do
  src="$(find "$BUILD" -type f -path "*/main/vm/$module.sp.qvm" -print -quit)"
  test -n "$src"
  test -s "$src"
  cp "$src" "$OUT/bin/$module.sp.qvm"
done

sha256sum "$OUT/bin/"*.sp.qvm | tee "$OUT/SHA256SUMS.txt"
{
  echo "EXACT_SOURCE_SP_QVM_BUILD=PASS"
  echo "QVM_ARCH=architecture-independent"
  echo "QVM_UI_BYTES=$(stat -c %s "$OUT/bin/ui.sp.qvm")"
  echo "QVM_CGAME_BYTES=$(stat -c %s "$OUT/bin/cgame.sp.qvm")"
  echo "QVM_QAGAME_BYTES=$(stat -c %s "$OUT/bin/qagame.sp.qvm")"
} | tee "$OUT/A6_QVM_BUILD_AUDIT.txt"
