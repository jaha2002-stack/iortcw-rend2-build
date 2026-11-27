# Точный снимок исходников Rend2 из Run 45835840244

Дерево `SP/` включает 1691 файл. Из корня архива выполните `sha256sum -c SOURCE_SHA256SUMS.txt`. Патчи из папки `integration/` уже применены. Лицензия находится в `SP/COPYING.txt`.

Снимок основан на ioRTCW `438e7d413b5f7277187c35b032eb0ef9093ae778` и Fixture Self-Shadow Production Run `45818977157`. Проверенная Win64 DLL собрана в Run `45835840244` на коммите `30a77cb8b0ae7410fc4796adcee8ed6751626b06`. В сборочном workflow заданы Ubuntu 24.04, MinGW-w64 POSIX и параметры `make`. [Конфигурация сборки](https://github.com/jaha2002-stack/iortcw-rend2-build/blob/30a77cb8b0ae7410fc4796adcee8ed6751626b06/.github/workflows/DW_FORCESUN_CSM_TRANSITION_WIN64.yml)

Для побайтового восстановления DLL используйте Production ZIP и опубликованный SHA-256.
