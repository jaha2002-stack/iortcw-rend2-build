# DarkWolf Rend2 — Sun Volumetric AA Clean Production

**CLEAN PRODUCTION — STABLE** для Windows x64. Сборка сохраняет системные файлы Run 45788582832, на котором владелец подтвердил исчезновение ступеней при `r_volumetricSun 1`. Исправление полос Local Volumetric в режимах 2, 3 и 5 также входит в состав.

## Установка

1. Сделайте копию рабочей установки RTCW и резервную копию настроек и сохранений.
2. Распакуйте содержимое верхнего каталога ZIP в корень установки. Оставьте свои игровые PK3/PK4 в `Main`. Если пользуетесь отдельным модулем восстановления текстур, сохраните существующий `Main/dw_ai/`.
3. Запускайте игру прежним способом с прежним `fs_homepath`. Для нового профиля доступен `RUN_DARKWOLF_IFLC_CLEAN.bat`, который принимает существующий homepath первым аргументом.
4. Для солнечного volumetric выберите Rend2 с HDR и `r_volumetricSun 1`. Встроенные шейдеры используются при `r_externalGLSL 0`. Настройки MSAA применяются после `vid_restart`.

В режиме MSAA композит учитывает покрытие пикселя по исходным выборкам глубины. При MSAA 0 применяется приближение на ступенчатых краях фона. Встроенные шейдеры поставляются в Rend2 DLL. В архиве восемь Win64 EXE/DLL, 19 CFG, три BAT, CHANGELOG, манифест и внутренний список SHA-256. Лицензии в `LICENCE.md` и `docs/licenses/`. Справка IFLC и Lamp Control сохранена.

[Публичный релиз, отчёт и точный снимок исходников](https://github.com/jaha2002-stack/iortcw-rend2-build/releases/tag/darkwolf-sun-volumetric-silhouette-aa-clean-production-20261126)
