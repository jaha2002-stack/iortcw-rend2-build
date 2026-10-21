#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORKDIR="${1:-$ROOT/.android-rend2-work}"
SOURCE_DIR="$WORKDIR/source"
NDK_ROOT="${ANDROID_NDK_ROOT:?ANDROID_NDK_ROOT is required}"
API="${ANDROID_API:-29}"
CC="$NDK_ROOT/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android${API}-clang"

OUT="$WORKDIR/engine-probe"
OBJ="$OUT/obj"
LOG="$OUT/log"
rm -rf "$OUT"
mkdir -p "$OBJ" "$LOG"

COMMON=(
  -std=gnu11 -fPIC -O0 -fno-strict-aliasing -fsigned-char -ferror-limit=0
  -D__ANDROID__ -DANDROID -DARM64 -DNO_VM_COMPILED
  -DUSE_LOCAL_HEADERS -DUSE_OPENGLES -DDARKWOLF_ANDROID_GLES
  -DARCH_STRING=\"arm64\"
  -DPRODUCT_VERSION=\"DarkWolf-Android-TestLab-v0.1\"
  -I"$SOURCE_DIR/SP/code"
  -I"$SOURCE_DIR/SP/code/SDL2/include"
  -I"$SOURCE_DIR/SP/code/zlib-1.2.11"
)

FILES=(
  # qcommon / collision / VM interpreter
  SP/code/qcommon/cm_load.c
  SP/code/qcommon/cm_patch.c
  SP/code/qcommon/cm_polylib.c
  SP/code/qcommon/cm_test.c
  SP/code/qcommon/cm_trace.c
  SP/code/qcommon/cmd.c
  SP/code/qcommon/common.c
  SP/code/qcommon/cvar.c
  SP/code/qcommon/files.c
  SP/code/qcommon/huffman.c
  SP/code/qcommon/md4.c
  SP/code/qcommon/md5.c
  SP/code/qcommon/msg.c
  SP/code/qcommon/net_chan.c
  SP/code/qcommon/net_ip.c
  SP/code/qcommon/puff.c
  SP/code/qcommon/q_math.c
  SP/code/qcommon/q_shared.c
  SP/code/qcommon/vm.c
  SP/code/qcommon/vm_interpreted.c

  # client core, software mixer and codecs that require no external SDK
  SP/code/client/cl_avi.c
  SP/code/client/cl_cgame.c
  SP/code/client/cl_cin.c
  SP/code/client/cl_console.c
  SP/code/client/cl_input.c
  SP/code/client/cl_keys.c
  SP/code/client/cl_main.c
  SP/code/client/cl_net_chan.c
  SP/code/client/cl_parse.c
  SP/code/client/cl_scrn.c
  SP/code/client/cl_ui.c
  SP/code/client/snd_adpcm.c
  SP/code/client/snd_codec.c
  SP/code/client/snd_codec_wav.c
  SP/code/client/snd_dma.c
  SP/code/client/snd_main.c
  SP/code/client/snd_mem.c
  SP/code/client/snd_mix.c
  SP/code/client/snd_wavelet.c

  # integrated SP server
  SP/code/server/sv_bot.c
  SP/code/server/sv_ccmds.c
  SP/code/server/sv_client.c
  SP/code/server/sv_game.c
  SP/code/server/sv_init.c
  SP/code/server/sv_main.c
  SP/code/server/sv_net_chan.c
  SP/code/server/sv_snapshot.c
  SP/code/server/sv_world.c

  # SDL/platform boundary
  SP/code/sdl/sdl_input.c
  SP/code/sdl/sdl_snd.c
  SP/code/sys/con_log.c
  SP/code/sys/con_passive.c
  SP/code/sys/sys_main.c
  SP/code/sys/sys_unix.c
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
    sed -n '1,220p' "$log"
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
