#!/usr/bin/env bash
set -Eeuo pipefail
src="${1:?source tree}"; evidence="${2:?evidence dir}"
mkdir -p "$evidence"
x86_64-w64-mingw32-gcc-posix --version > "$evidence/compiler.txt"
dpkg-query -W binutils-mingw-w64-x86-64 gcc-mingw-w64-x86-64-posix g++-mingw-w64-x86-64-posix > "$evidence/toolchain.txt"
# Match baseline flags. No fast-math/LTO or quality substitutions are introduced.
export SOURCE_DATE_EPOCH=1791177192
make -C "$src/SP" -j2 release \
 PLATFORM=mingw32 ARCH=x86_64 \
 CC=x86_64-w64-mingw32-gcc-posix CXX=x86_64-w64-mingw32-g++-posix WINDRES=x86_64-w64-mingw32-windres \
 BUILD_CLIENT=1 BUILD_SERVER=0 BUILD_GAME_SO=1 BUILD_GAME_QVM=0 \
 BUILD_BASEGAME=1 BUILD_RENDERER_REND2=1 USE_RENDERER_DLOPEN=1 2>&1 | tee "$evidence/build.log"
