# Архив исходников Rend2 из Run 45788582832

Снимок включает 1691 файл дерева `SP/` с ведомостью `SOURCE_SHA256SUMS.txt`. Из корня снимка выполните `sha256sum -c SOURCE_SHA256SUMS.txt`. Вложенные патчи `integration/localvol-235.patch` и `integration/sun-volumetric-edge.patch` уже применены. В основе ioRTCW `438e7d413b5f7277187c35b032eb0ef9093ae778`, прежний Production Run 45778124832 и исходный Run 45788582832 на коммите `c7e13e20bda4fe6671f4fd16791b03247bb087b2`.

Для воспроизведения сборочной конфигурации нужны Ubuntu 24.04, MinGW-w64 GCC/G++ POSIX `13.2.0-6ubuntu1+26.1`, binutils `2.41.90.20240122-1ubuntu1+11.4`, Git и GNU Make.

```bash
make -C SP -j2 release \
  VERSION=1.51d-SP_DarkWolf-Lamp-Control-V12-Exact-Visible \
  PLATFORM=mingw32 ARCH=x86_64 BUILD_CLIENT=1 BUILD_SERVER=0 BUILD_GAME_SO=1 \
  BUILD_GAME_QVM=0 BUILD_BASEGAME=1 BUILD_RENDERER_REND2=1 USE_RENDERER_DLOPEN=1 \
  CC=x86_64-w64-mingw32-gcc-posix CXX=x86_64-w64-mingw32-g++-posix \
  WINDRES=x86_64-w64-mingw32-windres
```

Rend2 DLL появится в `SP/build/release-mingw32-x86_64`. Production ZIP хранит принятый DLL и семь унаследованных бинарников. Для побитового возврата используйте опубликованный ZIP с его SHA-256. Новая компиляция может отличаться по времени в PE и метаданным toolchain. Лицензия в `SP/COPYING.txt`.
