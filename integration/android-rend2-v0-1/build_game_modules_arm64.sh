#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORKDIR="${1:-$ROOT/.android-rend2-work}"
SOURCE_DIR="$WORKDIR/source"
NDK_ROOT="${ANDROID_NDK_ROOT:?ANDROID_NDK_ROOT is required}"
API="${ANDROID_API:-29}"
CC="$NDK_ROOT/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android${API}-clang"
OUT="$WORKDIR/game-modules"
rm -rf "$OUT"
mkdir -p "$OUT"/{cgame,qagame,ui,bin,log}
trap 'rc=$?; echo "GAME_MODULE_BUILD_FAILED=$rc"; for f in "$OUT"/log/*.log; do [ -f "$f" ] || continue; echo "===== $f ====="; tail -n 160 "$f"; done; exit $rc' ERR

COMMON=(-std=gnu11 -fPIC -O2 -fno-strict-aliasing -fsigned-char -D__ANDROID__ -DANDROID -DARM64 -I"$SOURCE_DIR/SP/code")
QCOMMON=(SP/code/qcommon/q_math.c SP/code/qcommon/q_shared.c)
BG_CGAME=(SP/code/game/bg_animation.c SP/code/game/bg_misc.c SP/code/game/bg_pmove.c SP/code/game/bg_slidemove.c SP/code/game/bg_lib.c)
BG_UI=(SP/code/game/bg_misc.c SP/code/game/bg_lib.c)

mapfile -t CGAME < <(find "$SOURCE_DIR/SP/code/cgame" -maxdepth 1 -type f -name '*.c' -printf 'SP/code/cgame/%f\n' | sort)
mapfile -t QAGAME < <(find "$SOURCE_DIR/SP/code/game" -maxdepth 1 -type f -name '*.c' -printf 'SP/code/game/%f\n' | sort)
mapfile -t UI < <(find "$SOURCE_DIR/SP/code/ui" -maxdepth 1 -type f -name '*.c' -printf 'SP/code/ui/%f\n' | sort)

compile_set() {
  local module="$1"; shift
  local def1="$1"; shift
  local def2="$1"; shift
  local -a files=("$@")
  local -a objs=()
  : > "$OUT/log/$module.log"
  for rel in "${files[@]}"; do
    local base="$(echo "$rel" | tr '/.' '__')"
    local obj="$OUT/$module/$base.o"
    "$CC" "${COMMON[@]}" "$def1" "$def2" -c "$SOURCE_DIR/$rel" -o "$obj" >>"$OUT/log/$module.log" 2>&1
    objs+=("$obj")
  done
  "$CC" -shared -Wl,--no-undefined -Wl,-soname,"$module.sp.arm64.so" \
    -o "$OUT/bin/$module.sp.arm64.so" "${objs[@]}" -lm -llog >>"$OUT/log/$module.log" 2>&1
}

compile_set cgame -DCGAMEDLL -DCGAME "${CGAME[@]}" "${BG_CGAME[@]}" "${QCOMMON[@]}"
compile_set qagame -DGAMEDLL -DQAGAME "${QAGAME[@]}" "${QCOMMON[@]}"
compile_set ui -DUI -DUI "${UI[@]}" "${BG_UI[@]}" "${QCOMMON[@]}"

file "$OUT"/bin/*.so
sha256sum "$OUT"/bin/*.so | tee "$OUT/SHA256SUMS.txt"
"$NDK_ROOT/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-readelf" -h "$OUT/bin/cgame.sp.arm64.so" | grep -E 'Class:|Machine:'
