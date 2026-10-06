#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORKDIR="${1:-$ROOT/.android-rend2-work}"
SRC="$WORKDIR/source"
NDK="${ANDROID_NDK_ROOT:?ANDROID_NDK_ROOT is required}"
API="${ANDROID_API:-29}"
TOOL="$NDK/toolchains/llvm/prebuilt/linux-x86_64/bin"
CC="$TOOL/aarch64-linux-android${API}-clang"
CXX="$TOOL/aarch64-linux-android${API}-clang++"
OUT="$WORKDIR/native-runtime"
SDL="$WORKDIR/SDL2"
SDL_SHA="4c2d9014afda49553c76f7045529207bb593f9b5"

rm -rf "$OUT"
mkdir -p "$OUT"/{obj,gen,log,bin}
trap 'rc=$?; echo "NATIVE_RUNTIME_BUILD_FAILED=$rc"; for f in "$OUT"/log/*.log; do [ -f "$f" ] || continue; echo "===== $f ====="; tail -n 200 "$f"; done; exit $rc' ERR

if [ ! -d "$SDL/.git" ]; then
  git clone -q https://github.com/libsdl-org/SDL.git "$SDL"
fi
git -C "$SDL" fetch -q origin "$SDL_SHA"
git -C "$SDL" checkout -q --detach "$SDL_SHA"

cmake -S "$SDL" -B "$OUT/sdl-build" -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE="$NDK/build/cmake/android.toolchain.cmake" \
  -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-${API} \
  -DSDL_SHARED=ON -DSDL_STATIC=OFF -DSDL_TESTS=OFF -DSDL_TEST_LIBRARY=OFF \
  -DCMAKE_BUILD_TYPE=Release >"$OUT/log/sdl-configure.log" 2>&1
cmake --build "$OUT/sdl-build" --target SDL2 -j2 >"$OUT/log/sdl-build.log" 2>&1
SDL_SO="$(find "$OUT/sdl-build" -type f -name 'libSDL2.so' | head -1)"
test -s "$SDL_SO"
cp "$SDL_SO" "$OUT/bin/libSDL2.so"

# Generate the exact fallbackShader_* symbols expected by tr_glsl.c.
cc "$SRC/SP/code/tools/stringify.c" -o "$OUT/stringify"
for glsl in "$SRC"/SP/code/rend2/glsl/*.glsl; do
  base="$(basename "$glsl" .glsl)"
  case "$base" in
    bokeh_fp|bokeh_vp|calclevels4x_fp|calclevels4x_vp|depthblur_fp|depthblur_vp|dlight_fp|dlight_vp|down4x_fp|down4x_vp|fogpass_fp|fogpass_vp|generic_fp|generic_vp|lightall_fp|lightall_vp|pshadow_fp|pshadow_vp|shadowfill_fp|shadowfill_vp|shadowmask_fp|shadowmask_vp|ssao_fp|ssao_vp|texturecolor_fp|texturecolor_vp|tonemap_fp|tonemap_vp)
      "$OUT/stringify" "$glsl" "$OUT/gen/$base.c"
      ;;
  esac
done

CFLAGS=(
  -std=gnu11 -fPIC -O2 -fno-strict-aliasing -fsigned-char
  -D__ANDROID__ -DANDROID -DARM64 -DNO_VM_COMPILED
  -DUSE_LOCAL_HEADERS -DUSE_OPENGLES -DDARKWOLF_ANDROID_GLES
  -DUSE_INTERNAL_JPEG -DUSE_INTERNAL_ZLIB
  -DARCH_STRING=\"arm64\" -DDLL_EXT=\".so\"
  -DPRODUCT_VERSION=\"DarkWolf-Android-TestLab-v0.1\"
  -I"$SRC/SP/code" -I"$SDL/include"
  -I"$SRC/SP/code/jpeg-8c" -I"$SRC/SP/code/zlib-1.2.11"
)
CXXFLAGS=(
  -std=gnu++11 -fPIC -O2 -fno-strict-aliasing -fsigned-char
  -D__ANDROID__ -DANDROID -DARM64 -DNO_VM_COMPILED
  -DUSE_LOCAL_HEADERS -DUSE_OPENGLES -DDARKWOLF_ANDROID_GLES
  -DARCH_STRING=\"arm64\" -DDLL_EXT=\".so\"
  -DPRODUCT_VERSION=\"DarkWolf-Android-TestLab-v0.1\"
  -I"$SRC/SP/code" -I"$SDL/include"
)

ENGINE=(
  SP/code/client/cl_cgame.c SP/code/client/cl_cin.c SP/code/client/cl_console.c
  SP/code/client/cl_input.c SP/code/client/cl_keys.c SP/code/client/cl_main.c
  SP/code/client/cl_net_chan.c SP/code/client/cl_parse.c SP/code/client/cl_scrn.c
  SP/code/client/cl_ui.c SP/code/client/cl_avi.c
  SP/code/qcommon/cm_load.c SP/code/qcommon/cm_patch.c SP/code/qcommon/cm_polylib.c
  SP/code/qcommon/cm_test.c SP/code/qcommon/cm_trace.c SP/code/qcommon/cmd.c
  SP/code/qcommon/common.c SP/code/qcommon/cvar.c SP/code/qcommon/files.c
  SP/code/qcommon/md4.c SP/code/qcommon/md5.c SP/code/qcommon/msg.c
  SP/code/qcommon/net_chan.c SP/code/qcommon/net_ip.c SP/code/qcommon/huffman.c
  SP/code/qcommon/puff.c SP/code/qcommon/q_math.c SP/code/qcommon/q_shared.c
  SP/code/qcommon/vm.c SP/code/qcommon/vm_interpreted.c
  SP/code/client/snd_altivec.c SP/code/client/snd_adpcm.c SP/code/client/snd_dma.c
  SP/code/client/snd_mem.c SP/code/client/snd_mix.c SP/code/client/snd_wavelet.c
  SP/code/client/snd_main.c SP/code/client/snd_codec.c SP/code/client/snd_codec_wav.c
  SP/code/client/snd_codec_ogg.c SP/code/client/snd_codec_opus.c
  SP/code/client/qal.c SP/code/client/snd_openal.c SP/code/client/cl_curl.c
  SP/code/server/sv_bot.c SP/code/server/sv_ccmds.c SP/code/server/sv_client.c
  SP/code/server/sv_game.c SP/code/server/sv_init.c SP/code/server/sv_main.c
  SP/code/server/sv_net_chan.c SP/code/server/sv_snapshot.c SP/code/server/sv_world.c
  SP/code/sdl/sdl_input.c SP/code/sdl/sdl_snd.c
  SP/code/sys/con_log.c SP/code/sys/con_passive.c SP/code/sys/sys_main.c SP/code/sys/sys_unix.c
)

REND2=(
  tr_animation tr_backend tr_bsp tr_cmds tr_curve tr_dsa tr_extramath tr_extensions
  tr_fbo tr_flares tr_font tr_glsl tr_image tr_image_bmp tr_image_jpg tr_image_pcx
  tr_image_png tr_image_tga tr_image_dds tr_init tr_light tr_main tr_marks tr_mesh
  tr_model tr_model_iqm tr_noise tr_postprocess tr_scene tr_shade tr_shade_calc
  tr_shader tr_shadows tr_sky tr_surface tr_vbo tr_world
)

ZLIB=(adler32 crc32 inffast inflate inftrees zutil ioapi unzip)
mapfile -t JPEG < <(find "$SRC/SP/code/jpeg-8c" -maxdepth 1 -type f -name '*.c' -printf '%f\n' | sort)
mapfile -t BOTLIB < <(find "$SRC/SP/code/botlib" -maxdepth 1 -type f -name '*.c' -printf 'SP/code/botlib/%f\n' | sort)
mapfile -t SPLINES < <(find "$SRC/SP/code/splines" -maxdepth 1 -type f -name '*.cpp' -printf 'SP/code/splines/%f\n' | sort)

OBJS=()
compile_c() {
  local rel="$1"; shift
  local key="$(echo "$rel" | tr '/.' '__')"
  local obj="$OUT/obj/$key.o"
  "$CC" "${CFLAGS[@]}" "$@" -c "$SRC/$rel" -o "$obj" >>"$OUT/log/compile.log" 2>&1
  OBJS+=("$obj")
}
compile_cpp() {
  local rel="$1"
  local key="$(echo "$rel" | tr '/.' '__')"
  local obj="$OUT/obj/$key.o"
  "$CXX" "${CXXFLAGS[@]}" -c "$SRC/$rel" -o "$obj" >>"$OUT/log/compile.log" 2>&1
  OBJS+=("$obj")
}

: >"$OUT/log/compile.log"
for rel in "${ENGINE[@]}"; do compile_c "$rel"; done
for rel in "${BOTLIB[@]}"; do compile_c "$rel" -DBOTLIB; done
for rel in "${SPLINES[@]}"; do compile_cpp "$rel"; done
for z in "${ZLIB[@]}"; do compile_c "SP/code/zlib-1.2.11/$z.c"; done
for j in "${JPEG[@]}"; do compile_c "SP/code/jpeg-8c/$j"; done
for r in "${REND2[@]}"; do compile_c "SP/code/rend2/$r.c"; done
compile_c "SP/code/sdl/sdl_glimp.c"
compile_c "SP/code/sdl/sdl_gamma.c"

for gen in "$OUT"/gen/*.c; do
  key="$(basename "$gen" .c)"
  obj="$OUT/obj/glsl_$key.o"
  "$CC" "${CFLAGS[@]}" -c "$gen" -o "$obj" >>"$OUT/log/compile.log" 2>&1
  OBJS+=("$obj")
done

"$CXX" -shared -Wl,--no-undefined -Wl,-soname,libmain.so \
  -L"$(dirname "$SDL_SO")" -o "$OUT/bin/libmain.so" "${OBJS[@]}" \
  -lSDL2 -lGLESv3 -lEGL -landroid -llog -ldl -lm >>"$OUT/log/link.log" 2>&1

file "$OUT/bin/libmain.so" "$OUT/bin/libSDL2.so"
"$TOOL/llvm-readelf" -h "$OUT/bin/libmain.so" | grep -E 'Class:|Machine:'
"$TOOL/llvm-readelf" -d "$OUT/bin/libmain.so" | grep NEEDED | tee "$OUT/NEEDED.txt"
sha256sum "$OUT/bin/libmain.so" "$OUT/bin/libSDL2.so" | tee "$OUT/SHA256SUMS.txt"
echo "ANDROID_NATIVE_RUNTIME_LINK=PASS"
