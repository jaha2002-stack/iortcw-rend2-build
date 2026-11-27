# DarkWolf Rend2 · r_forceSun и точечный свет · Clean Production для Windows x64

Владелец подтвердил, что полосы на стене исчезли в Win64-сборке Run `45835840244`. Production ZIP сохраняет проверенные бинарники, конфиги и скрипты запуска побайтно. [Проверенная сборка](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/45835840244)

## Установка

1. Сверьте SHA-256 ZIP по файлу `SHA256SUMS.txt` из релиза.
2. Распакуйте содержимое корневой папки ZIP в отдельную копию установленной игры. Используйте PK3 из своей установки Return to Castle Wolfenstein.
3. Запускайте игру тем же способом и используйте прежний `fs_homepath`, чтобы загрузить сохранённые настройки, лампы и профили.

При `r_forceSun 0` принудительное солнце отключается. Если карта задаёт собственное солнце, оно продолжает работать. Команды для проверки масок ELSS и IFLC приведены в `docs/FIXTURE_SELFSHADOW_VERIFICATION_RU.md`.

Для отката используйте Win64 ZIP и контрольные суммы из Fixture Self-Shadow Clean Production Run `45818977157`. [Предыдущий Production Release](https://github.com/jaha2002-stack/iortcw-rend2-build/releases/tag/darkwolf-fixture-selfshadow-clean-production-20261126)
