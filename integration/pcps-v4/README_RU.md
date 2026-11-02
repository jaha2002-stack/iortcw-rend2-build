# DarkWolf PCPS V4 — Fire Synthetic Shadow Control (TEST ONLY)

**Статус:** отдельная экспериментальная Windows x64 версия, а не Clean Production. Основа: PCPS V3 из GitHub Actions [#41435724668](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/41435724668); проверочный V3 [#41435724698](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/41435724698). Сохранены SAFE Clean #41297344177 и Texture/Material Fidelity V2 #41286257713.

## Зачем нужна V4

На Crypt1 PCPS V3 обнаруживал BSP-поверхность `textures/sfx/xflame2_1200` (в игровом тесте ID 3006), но не находил `dlight` в обычном списке. В DarkWolf есть отдельная система **FireVol synthetic shadow**, которая не обязана иметь запись `tr.refdef.dlights`.

## Выбор и управление

1. На Crypt1 наведи прицел прямо на видимое пламя.
2. Выполни `/dw_ps_picklight` либо `/dw_ps_firepick`. Ожидается предварительный выбор `PCPS V4 FIRE: BSP FLAME ...`. Если у источника нет активного FireVol-hint, это будет отмечено.
3. Выполни `/dw_ps_confirm` и `/dw_ps_info`. Сначала убедись, что это именно целевой факел.
4. `/dw_ps_light_off` выключает **только его синтетическую FireVol-тень**, не выключая сам огонь и прямое освещение. `/dw_ps_light_on` восстанавливает её.
5. Для отдельного BSP-предмета выбери нужный огонь, направь прицел на предмет и выполни `/dw_ps_pickcaster`, затем `/dw_ps_caster_off`. Восстановление: `/dw_ps_caster_on`.
6. `/dw_ps_firelinks` показывает ближайшие обычные динамические `dlight` факела; обычные point shadows управляются отдельно через `/dw_ps_select N`.
7. `/dw_ps_file` показывает состояние хранения. `/dw_ps_overlay 0` убирает экранные метки, не изменяя тени.

Правила автоматически сохраняются в текущем `fs_homepath/Main/dw_pcps/<карта>_a.dat` и `_b.dat` с защитой A/B и BSP signature. Если разные BAT используют разные `fs_homepath`, файлы изолированы.

**Важная граница:** FireVol synthetic shadows, обычные динамические point shadows и другие огненные маски — разные механизмы. Не ожидай, что отключение одного автоматически устранит все тени факела.

## Инженерные ограничения

- Только явное действие пользователя. При отсутствии правил поведение совпадает с PCPS V3.
- В тестовой версии нет изменений Sun/CSM, Volumetric, Fire/Tesla direct light, Bloom, SSGI, CAS/LUT/A2C, материалов и текстур, главных shadow-slot бюджетов и пяти CFG.
- Новый Fire source идентифицируется локальной BSP flame surface и подтверждённым FireVol origin; полное физическое соответствие требует проверки на пользовательском GPU.
- Несовпадение карты, подписи геометрии и неоднозначные источники должны игнорироваться (fail-open).
- Это не инструмент определения истинного depth-owner любой тени и не поддержка всех динамических моделей.
- Перед испытанием сохрани копию проверенной V3 DLL; тестируй только в отдельной папке игры.

## Первая приёмка

Сначала Factory: `/dw_ps_select 23` проверить известный light origin `(-96,-952,-203)` и сохранение V3. Затем Crypt1: `/dw_ps_firepick` → `/dw_ps_confirm` → `/dw_ps_info` → `/dw_ps_light_off` → screenshot → `/dw_ps_light_on`. После этого отдельно проверить BSP caster, выход/вход и `dw_ps_overlay 0`.

**CI компиляция и статический тест не являются GPU-подтверждением.** Не переносить V4 в Clean без кадров Crypt1 и проверок Factory/Escape1.
