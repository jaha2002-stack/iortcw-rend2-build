# DarkWolf Rend2 · LocalVol Lamp Coverage · Clean Production для Windows x64

В Win64 Run `45953757143` владелец подтвердил исчезновение лесенок на прутьях решётки. Production ZIP побайтно сохраняет проверенные бинарники, конфигурации и скрипты запуска. [Проверенная сборка](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/45953757143)

При HDR и MSAA сглаживание применяется к объёмному свету ламп в режимах LocalVol `2`, `3` и `5`. На границе объекта вклад света смешивается по долям сэмплов переднего и заднего планов.

## Установка

1. Сверьте SHA-256 архива по опубликованному файлу `SHA256SUMS.txt`.
2. Распакуйте содержимое корневой папки ZIP в отдельную копию установленной игры. Используйте PK3 из своей установки Return to Castle Wolfenstein.
3. Запускайте игру тем же способом. Используйте прежний `fs_homepath`, чтобы загрузить сохранения, настройки и профили освещения.

Для отката доступен архив предыдущего ForceSun and Point-Light Cubemap Clean Production Run `45948709842`. [Предыдущий Production Release](https://github.com/jaha2002-stack/iortcw-rend2-build/releases/tag/darkwolf-forcesun-dlight-cubemap-clean-production-20261127)
