# Точный снимок исходников Rend2 для сборки Run 45778124832

Снимок содержит 1691 файл дерева `SP/` после интеграции. Для проверки выполните из корня распакованного снимка `sha256sum -c SOURCE_SHA256SUMS.txt`. `integration/fix.patch` уже применён к этому дереву. Собранные EXE и DLL в снимке отсутствуют, кроме библиотек зависимостей из дерева ioRTCW, используемых Makefile.

Источники соответствуют ревизии ioRTCW `438e7d413b5f7277187c35b032eb0ef9093ae778`, рецепту интеграции `250669a231dc7bd571b4e2b3405c045f90ba64c1` и патчу из сборочного коммита `e5b1938884bc09abc1fe649bd0af854f41caf05f`. Замороженный runtime поставляется отдельно. Его полная сборка объединяет ранее выпущенные компоненты донора Run 43414829881 и Rend2 из Run 45778124832.

Для воспроизведения конфигурации Rend2 используйте Ubuntu 24.04, MinGW-w64 GCC/G++ POSIX `13.2.0-6ubuntu1+26.1`, binutils `2.41.90.20240122-1ubuntu1+11.4`, Git и GNU Make.

```bash
make -C SP -j2 release \
  VERSION=1.51d-SP_DarkWolf-Lamp-Control-V12-Exact-Visible \
  PLATFORM=mingw32 ARCH=x86_64 \
  BUILD_CLIENT=1 BUILD_SERVER=0 BUILD_GAME_SO=1 BUILD_GAME_QVM=0 BUILD_BASEGAME=1 \
  BUILD_RENDERER_REND2=1 USE_RENDERER_DLOPEN=1 \
  CC=x86_64-w64-mingw32-gcc-posix CXX=x86_64-w64-mingw32-g++-posix \
  WINDRES=x86_64-w64-mingw32-windres
```

Для побитового возврата используйте Production ZIP и его SHA-256. Повторная сборка может отличаться по PE timestamp и данным toolchain. Путь к собранному модулю `SP/build/release-mingw32-x86_64/renderer_sp_rend2_x64.dll`. Лицензия в `SP/COPYING.txt`.
