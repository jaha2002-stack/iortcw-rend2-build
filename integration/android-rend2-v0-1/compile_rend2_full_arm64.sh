#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORKDIR="${1:-$ROOT/.android-rend2-work}"
SOURCE_DIR="$WORKDIR/source"
NDK_ROOT="${ANDROID_NDK_ROOT:?ANDROID_NDK_ROOT is required}"
API="${ANDROID_API:-29}"
CC="$NDK_ROOT/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android${API}-clang"

test -x "$CC"
test -d "$SOURCE_DIR/SP/code/rend2"

OUT="$WORKDIR/full-renderer"
OBJ="$OUT/obj"
LOG="$OUT/log"
rm -rf "$OUT"
mkdir -p "$OBJ" "$LOG"

COMMON=(
  -std=gnu11 -fPIC -O0 -fno-strict-aliasing -fsigned-char -ferror-limit=0
  -D__ANDROID__ -DANDROID -DARM64
  -DUSE_LOCAL_HEADERS -DUSE_OPENGLES -DDARKWOLF_ANDROID_GLES
  -DNO_VM_COMPILED
  -DARCH_STRING=\"arm64\"
  -DPRODUCT_VERSION=\"DarkWolf-Android-TestLab-v0.1\"
  -I"$SOURCE_DIR/SP/code"
  -I"$SOURCE_DIR/SP/code/SDL2/include"
  -I"$SOURCE_DIR/SP/code/jpeg-8c"
  -I"$SOURCE_DIR/SP/code/zlib-1.2.11"
)

mapfile -t FILES < <(
  {
    find "$SOURCE_DIR/SP/code/rend2" -maxdepth 1 -type f -name '*.c' -printf '%P\n' | sort | sed 's#^#SP/code/rend2/#'
    printf '%s\n' "SP/code/sdl/sdl_glimp.c" "SP/code/sdl/sdl_gamma.c"
  }
)

failed=0
: > "$OUT/summary.txt"
for rel in "${FILES[@]}"; do
  name="$(echo "$rel" | tr '/.' '__')"
  obj="$OBJ/$name.o"
  log="$LOG/$name.log"
  if "$CC" "${COMMON[@]}" -c "$SOURCE_DIR/$rel" -o "$obj" >"$log" 2>&1; then
    echo "PASS $rel" | tee -a "$OUT/summary.txt"
  else
    echo "FAIL $rel" | tee -a "$OUT/summary.txt"
    sed -n '1,180p' "$log"
    failed=1
  fi
done

total="${#FILES[@]}"
passed="$(grep -c '^PASS ' "$OUT/summary.txt" || true)"
failed_count="$(grep -c '^FAIL ' "$OUT/summary.txt" || true)"
{
  echo "TOTAL=$total"
  echo "PASS_COUNT=$passed"
  echo "FAIL_COUNT=$failed_count"
  echo "ANDROID_ABI=arm64-v8a"
  echo "ANDROID_API=$API"
} | tee -a "$OUT/summary.txt"

test "$passed" -eq "$total" || failed=1
exit "$failed"
