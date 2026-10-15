# Clean Production RC2 Complete — фактический результат 15.10.2026

## Выпуск

Run https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/38672198355 — COMPLETED/SUCCESS, attempt 1. Builder `985531ce2a7a5647b93c7a86a55e489f88630520`. Ветка `rend2-v4-4-6-clean-optimization`, прежний единственный production workflow. Этот отчёт — docs-only, не новая сборка. Main не изменялся, merge не выполнялся.

Игровой ZIP: `DarkWolf-ioRTCW-Rend2-v4.4.6-Optimized-Clean-Production-RC2-Complete-Win64-SP.zip`.
SHA256: `094ceee1e80f89db2fa0c90d453d9378017269b32f3ba3f175602237cfbc5a06`.
Размер: 5 620 057 байт. Основной artifact ID `11944962109`, его внешний SHA256 `2b40435e97722d8391a9dd7f68512e953f8be86362bab0ae38722a50cc535e57`.
Evidence artifact `11944897103`, SHA256 `e0a88e1c3d4d9adbfd671ee21f3fbee75e4785febbdbbfeb5cb87114633cf631`.

Родитель: выпущенный RC2 ZIP `125c456bbfe5490a05c3d85c0d30aebab19f2a57f69d4d55e2a40200f570a9b5`, source tree `a5434fd5d8d139b6622f90c48b46639988828fc0`.
Новый source tree: `c369e629136f8feef70d3ed91a121b3ad7ace151`.
Предыдущий RC1 ZIP `d005ca823debf7b5bfab025a11d360752ed1033c258fc9d22797e5291306014f` остаётся предком.

## Не потерянные изменения и корректный подсчёт

Сохранены все изменения уже выпущенного RC2. Из десяти пунктов альтернативного R2 source-kit один — адаптивная radix-сортировка — уже был реализован в RC2. Он сохранён без замены и повторного подсчёта. Остальные девять добавлены поверх существующего RC2; пакет содержит все десять запрошенных возможностей, но не десять новых уникальных изменений относительно предыдущего RC2.

| Пункт | Реализация |
|---|---|
| R2-01 | Существующая стабильная адаптивная radix-сортировка RC2 сохранена |
| R2-02 | CCDF: hash учитывает точную плоскость/fog/cubemap/culling; прежние exact checks и canonical сохранены |
| R2-03 | Классификация последнего shader огня переиспользуется только внутри вызова |
| R2-04 | Окончательный DlightInfo uniform передаётся один раз перед первым draw |
| R2-05 | Receiver-side SSGI: повторное использование центра и отложенная обработка края |
| R2-06 | Точно пустая entity mask пропускает ненужную работу по прежнему cutoff |
| R2-07 | Видимая solar shadowmask: дополнительные проекции каскадов только по необходимости |
| R2-08 | Неизменные на луче параметры формы/оттенка огня вынесены из цикла |
| R2-09 | Local/fire extinction: начальные exp и рекуррентное обновление, включая rejected samples |
| R2-10 | Coverage AA: пропуск неиспользуемых directional taps только при blend == 0 |

Сохранены прежние saturated-mask exits SSGI и ранний lateral fire guard, а также исправления filesystem, BSP, particles/trails, viewport/scissor, матриц и far-plane cache. Только шесть renderer-файлов отличаются от предыдущего RC2. Остальные 1637 файлов SP/code идентичны по независимому сравнению полного дерева.

## Проверки именно этого run

Оба артефакта скачаны и независимо проверены: внешние SHA256, CRC ZIP, sidecar игрового ZIP, 20 записей внутреннего манифеста и все 21 файл пакета. Проверены пять компонентов PE AMD64/PE32+, их SHA в provenance, отсутствие проверяемых DWPERF/TestLab/sanitizer markers и отсутствие retail pak*.pk3. Собственные PK3, runtime dependencies, High Quality и BAT побитово сохранены относительно предыдущего игрового пакета.

Обе Win64 SP сборки прошли одним закреплённым toolchain. EXE/cgame/qagame/UI совпадают между контрольной пересборкой RC2 и Complete; renderer отличается. Строка PRODUCT_VERSION обеих контрольных сборок нормализована одинаково; совпадение всех исторических EXE со старым ZIP не заявляется. Renderer Complete SHA256: `6ccb1e3b92b1530ba432b5a4b6107874746e7965ea9bf851c96e2bfc78143d9b`.

Повторены прежние RC2-тесты. Новые native tests извлекают реальные функции из полных деревьев: четыре C-harness в двух режимах (UBSan и inherited -O3/-ffast-math), все восемь прошли. 1200 сортировочных наборов; 128 миров/32768 CCDF surfaces; 256 сцен классификации; 3000 uniform cases. Синтетическое уменьшение CCDF pair visits 941830 -> 29173, shader evidence calls 186356 -> 79199; это не FPS.

GLSL: 28 successful program links, 1188 synthetic float-FBO A/B, GLSL120/150. CI renderer llvmpipe LLVM20.1.2, Mesa25.2.8. В проверенной выборке SSGI/shadowmask/coverage: max error 0; local/fire: 9.834766387939453e-7. Local/fire recurrence численно близка, не побитово эквивалентна. Эти синтетические тесты не являются игровыми скриншотами.

Свежие игровые smoke: escape1, swf, dam, crypt1, assault, forest High Quality и escape1 Quality для обоих вариантов — 14 SMOKE_PASS. Подтверждены exit0, gameplay readiness, actual cvars, одинаковые параметры A/B и точное совпадение PNG с raw TGA. Разрешение640x480, software Mesa. Старые176кадров ламп не использованы как доказательства Complete. Движение/события/Windows gameplay/FPS этим не проверены.

## Существенное ограничение ручного визуального просмотра

Просмотрены все14свежих PNG и отдельно SWF. В кадрах SWF присутствует сплошная белая полоса снизу высотой66пикселей У ОБОИХ вариантов — RC2 control и Complete. Первопричина не установлена. Это не доказательство новой регрессии от патча, но данный ракурс нельзя считать визуально принятым. Автоматический SMOKE_PASS не равен отсутствию всех графических дефектов. SWF view acceptance: NOT_ACCEPTED; полная VISUAL_ACCEPTANCE: NOT_RUN. Остальные статические кадры также не доказывают временную эквивалентность.

## Конфигурация и статус

High Quality сохраняет forceSun1, dlightMode2, StaticPromote32, persistent shadows3, SSGI и local/sun/fire volumetric; PBR0. SSAO0 и indirectLighting0 — прежние явно отмеченные исключения, это не all-effects-on. В отдельном тестовом Quality SSGI0/localVol0 в ОБОИХ вариантах; это не снижение основного выпускного High Quality и не benchmark.

Фактические gates: BUILD PASS, STATIC_DIFFERENTIAL PASS, SYNTHETIC_SHADER_AB PASS, MESA_SMOKE PASS(14), CAPTURE_INTEGRITY PASS(14 raw/PNG pairs). WINDOWS_RUNTIME NOT_RUN, GPU_PERFORMANCE NOT_RUN, полная VISUAL_ACCEPTANCE NOT_RUN, motion/event regression NOT_RUN.

Статус CANDIDATE_FOR_LOCAL_VERIFICATION. Clean Production описывает чистоту упаковки, а не завершённую аппаратную/художественную приёмку. Пользователь выполняет реальный ПК-тест. 75FPS или измеренное ускорение не заявляются. Установка в отдельную легальную RTCW SP; запуск через RUN_DARKWOLF_OPTIMIZED_CLEAN.bat с изолированным DWOptimizedHome.
