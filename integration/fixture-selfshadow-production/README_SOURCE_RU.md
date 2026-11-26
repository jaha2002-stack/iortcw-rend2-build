# Точный снимок исходников Rend2 из Run 45806188774

Дерево `SP/` включает 1691 файл. Выполните `sha256sum -c SOURCE_SHA256SUMS.txt` из корня снимка. Вложенные патчи LocalVol, SunVol и Fixture Self-Shadow уже применены. Лицензия находится в `SP/COPYING.txt`.

В основе ioRTCW `438e7d413b5f7277187c35b032eb0ef9093ae778` и Production Run `45799720282`. Win64 DLL собрана в Run `45806188774` на коммите `1713c867b7c87d682e4b12314a6d4be0ae19702f`. Сборочный workflow фиксирует окружение Ubuntu 24.04, зависимости MinGW-w64 POSIX и параметры `make`. [Конфигурация сборки](https://github.com/jaha2002-stack/iortcw-rend2-build/blob/1713c867b7c87d682e4b12314a6d4be0ae19702f/.github/workflows/DW_FIXTURE_SELFSHADOW_WIN64.yml)

Для побайтового восстановления готовой DLL используйте Production ZIP и опубликованный SHA-256.
