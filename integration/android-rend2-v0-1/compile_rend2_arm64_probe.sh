#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORKDIR="${1:-$ROOT/.android-rend2-work}"
SOURCE_DIR="$WORKDIR/source"
NDK_ROOT="${ANDROID_NDK_ROOT:?ANDROID_NDK_ROOT is required}"
API="${ANDROID_API:-29}"
TRIPLE="aarch64-linux-android"
CC="$NDK_ROOT/toolchains/llvm/prebuilt/linux-x86_64/bin/${TRIPLE}${API}-clang"

test -x "$CC"
test -d "$SOURCE_DIR/SP/code"

python3 "$ROOT/integration/android-rend2-v0-1/apply_android_rend2_v0_1.py" "$SOURCE_DIR"

OUT="$WORKDIR/probe"
OBJ="$OUT/obj"
LOG="$OUT/log"
rm -rf "$OUT"
mkdir -p "$OBJ" "$LOG"

COMMON=(
  -std=gnu11
  -fPIC
  -O0
  -fno-strict-aliasing
  -fsigned-char
  -D__ANDROID__
  -DANDROID
  -DARM64
  -DUSE_LOCAL_HEADERS
  -DUSE_OPENGLES
  -DDARKWOLF_ANDROID_GLES
  -DNO_VM_COMPILED
  -DARCH_STRING=\"arm64\"
  -DPRODUCT_VERSION=\"DarkWolf-Android-TestLab-v0.1\"
  -I"$SOURCE_DIR/SP/code"
  -I"$SOURCE_DIR/SP/code/SDL2/include"
)

FILES=(
  "SP/code/rend2/tr_glsl.c"
  "SP/code/rend2/tr_extensions.c"
  "SP/code/rend2/tr_dsa.c"
  "SP/code/rend2/tr_fbo.c"
  "SP/code/rend2/tr_vbo.c"
  "SP/code/rend2/tr_postprocess.c"
  "SP/code/rend2/tr_scene.c"
  "SP/code/rend2/tr_backend.c"
  "SP/code/sdl/sdl_glimp.c"
)

failed=0
: > "$OUT/summary.txt"
for rel in "${FILES[@]}"; do
  name="$(echo "$rel" | tr '/.' '__')"
  obj="$OBJ/$name.o"
  log="$LOG/$name.log"
  echo "=== $rel ===" | tee -a "$OUT/summary.txt"
  if "$CC" "${COMMON[@]}" -c "$SOURCE_DIR/$rel" -o "$obj" >"$log" 2>&1; then
    echo "PASS $rel" | tee -a "$OUT/summary.txt"
  else
    echo "FAIL $rel" | tee -a "$OUT/summary.txt"
    sed -n '1,220p' "$log"
    failed=1
  fi
done

{
  echo
  echo "CC=$CC"
  echo "ANDROID_API=$API"
  echo "ANDROID_ABI=arm64-v8a"
  echo "OBJECT_COUNT=$(find "$OBJ" -type f -name '*.o' | wc -l)"
} | tee -a "$OUT/summary.txt"

cat "$OUT/summary.txt"
exit "$failed"
