#!/usr/bin/env bash
set -e

git clone --depth 1 https://github.com/iortcw/iortcw.git source
cd source
git apply ../patches/iortcw-rend2-dlightmode1-enhanced-perpixel.patch

cd SP
if [ -f ./cross-make-mingw64.sh ]; then
  chmod +x ./cross-make-mingw64.sh
  ./cross-make-mingw64.sh
else
  PLATFORM=mingw32 ARCH=x86_64 make
fi

cd ../MP
if [ -f ./cross-make-mingw64.sh ]; then
  chmod +x ./cross-make-mingw64.sh
  ./cross-make-mingw64.sh
else
  PLATFORM=mingw32 ARCH=x86_64 make
fi
