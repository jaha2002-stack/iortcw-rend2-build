# DarkWolf Rend2 — аудит грубых и утолщённых динамических теней

**Дата:** 2026-10-30  
**Единственная актуальная Production-база:** [GitHub Actions #41019985033](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/41019985033).  
**SHA-256 принятой DLL:** `d7423e8648e2de556f79c7cddecf1a8df16b9f60a46c503d1440089876116b45`.  
**Восстановление точного shadow source:** [#41030449949](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/41030449949), PASS, артефакт `DarkWolf-Exact-408787-PointShadow-Source-Forensic`.  
**Статус:** статический кодовый и исторический аудит; на текущем Windows GPU ещё НЕ выполнено синхронное A/B сравнение всех трёх сцен.

## 1. Вывод

Наиболее вероятная точка расширения геометрии динамических теней — **16 сентября 2026 г., Stage 11 Unified Asset Shadow Coverage**. Историческая цепочка:

- [#34962735592](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/34962735592), 15.09 — контрольный источник до Stage 11.
- [#35071483766](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/35071483766), 16.09 — опыт с alpha-tested opaque caster.
- [#35098010299](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/35098010299), 16.09 — alpha caster clean candidate.
- [#35117854581](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/35117854581), 16.09 — Unified Asset Shadow Coverage experiment. В delta менялись 12 исходных файлов, включая `tr_shade.c`, `tr_backend.c`, `tr_main.c`, `tr_scene.c`, `dlight_fp.glsl`.
- [#35150218437](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/35150218437), 16.09 — Clean Production, **встроил принятую Stage 11 логику постоянно**. Его `STAGE11_UNIFIED_ASSET_SHADOW_COVERAGE_CLEAN_PRODUCTION_V1_CONTRACT.txt` прямо устанавливает `stage11_behavior_activation=SOURCE_INTEGRATED_ALWAYS_ON_FOR_ACCEPTED_PATHS`.

Появление расширенного списка кастеров — **подтверждённое изменение семантики**. Но точное первое появление пользовательского дефекта «толстых теней» может быть установлено лишь A/B одной и той же камеры на предыдущей и следующей DLL. Указанные CI Success не являются таким визуальным доказательством.

Дополнительный независимый механизм появился позже: **архитектурная 256×256 world-mask для Fire / stationary Tesla**, использующая cubemap глубины и сглаживание PCF 2×2, не связанное с основным 2048×2048 shadow map. Уже в заметках Clean Freeze [#40640998083](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40640998083) отмечалось, что при `r_dlightWorldContainment 2` тени Crypt1 несколько толще/грубее, чем при 0.

## 2. Почему Stage 11 может давать большие чёрные проекции

**Файлы:** `SP/code/rend2/tr_shade.c`, `tr_backend.c`, `tr_main.c`.

- `R_DarkWolfClassifyShadowMaterial()` включает `SS_OPAQUE` и неблендовые alpha-cutout этапы, кроме sky/nodraw/nodlight. `R_DarkWolfSupportedShadowCasterMaterial()` транслирует эти классы в включение кастера.
- `RB_DarkWolfRejectDepthFillShader()` использует этот же классификатор для point-shadow и ортографических depth-shadow; в `RB_StageIteratorGeneric()` non-Fire point shadows вызывают `RB_RenderShadowmap(input,qfalse/qtrue)` в зависимости от класса.
- Новый receiver path позволяет старому `ProjectDlightTexture` получать тень через выбранный cubemap, если `r_dlightMode >= 2` и корректны slot / shadow mask.
- **Ключевой пробел в данном участке:** классификатор проверяет материал, но не проверяет, является ли полигон/модель частью корпуса *того самого* светильника, чья shadow cubemap сейчас записывается. У near-source корпуса `d(light,caster)` мал, поэтому размер тени на удалённой стене может быть намного больше самого корпуса (точечная проекция, масштаб ~ `distance(light,receiver)/distance(light,caster)`). Это вероятное объяснение толстых силуэтов корпуса прожектора и близких деталей ламп.
- Для синтетических StaticPromote есть отдельный stable capture-origin offset (до 32 units), но он не является общим emitter-aware исключением casters.
- **`r_dlightShadowCasterMode 0` НЕ отключает Stage 11.** В current source его default 0, а классификатор Stage 11 в non-Fire point depth path вызывается независимо от этого cvar.

Это не основание отменить все улучшения Stage 11: настоящие тени решёток/архитектуры были причиной его разработки. Нужна семантическая коррекция self-occlusion/near-emitter geometry, а не глобальное удаление caster.

## 3. Второй механизм: Fire / world containment

**Файлы:** `tr_scene.c`, `tr_main.c`, `tr_local.h`, `glsl/dlight_fp.glsl`, `glsl/lightall_fp.glsl`.

- `#define DLIGHT_WORLD_SIZE 256` создаёт отдельный `dlightWorldFbo` 256×256 на грань; основной point cubemap по умолчанию **2048×2048**.
- В `DlightWorldVisibility()` на обычном Fire/world path четыре бинарных сравнения глубины смешиваются как PCF 2×2, после чего **умножают** вклад света. Это отдельная маска, а не часть фильтра `r_dlightShadowFilter`.
- Обычные native лампы и StaticPromote явно исключены из стандартного world containment. Исключения: защищённый Escape1 источник A и определённые promoted red Alarm; для FireVol source mask применяется при `r_dlightWorldContainment >= 1`, для stationary Tesla при >=2.
- В коде Tesla F2 есть отдельный исправленный 4×4 sampling с учётом знака OpenGL cubemap face. Сам комментарий в исходнике отмечает: прежний 2×2 использовал несогласованные мировые оси. Поэтому обычный 2×2 Fire/world path требует отдельного face-orientation аудита. Это **обоснованное подозрение**, не доказанная причина показанной тени.
- На Crypt1 в freeze-документации #40640998083 прямо оставлена пометка: containment 2 даёт более толстые/грубые тени, чем 0.

Следствие: увеличение `r_dlightShadowMapSize 2048 -> 4096` не повышает разрешение **256-пиксельной** архитектурной маски. Запрещено заменять её «в лоб» увеличенным буфером без анализа памяти, cache invalidation и light leaks.

## 4. Третьи факторы: PCF, bias, baked geometry

Действующие значения, восстановленные **из самого Main/DW_SEPTEMBER_FOURWEEK_VISUAL_BASE.cfg архива #41019985033**:
- `r_dlightMode 2`;
- `r_dlightWorldContainment 2`;
- `r_dlightShadowFilter 2`;
- `r_dlightShadowMapSize 2048`;
- `r_dlightShadowMaxLights 3`;
- `r_forceSun 1`.

Кодовые defaults: `r_dlightShadowBias 0.0033`, `r_dlightShadowSoftness 1.70`, `r_dlightShadowStrength 0.88`, `r_dlightShadowKernelMode 0`.

`FilterDlightShadow()` при filter=2/kernel=0 использует девять взвешенных сравнений; kernel=1 включает более плотный фильтр из 17 выборок. PCF определяет толщину **переходной кромки**, но не обязан объяснять большой чёрный силуэт. Bias способен дать acne или смещение, но глобально менять его без проверки опасно.

Не путать `r_shadowFilter` (солнечные каскады CSM) с `r_dlightShadowFilter` (точечные лампы). Также в ряде старых карт часть тёмных треугольников — настоящая BSP-геометрия или запечённый свет. Это подтверждено отдельными проверками Crypt1 с `r_dlightShadowStrength 0` / `r_ssgi 0`, где остались реальные силуэты решётки. Такие формы нельзя исправить PCF.

## 5. Три предоставленных снимка: рабочая классификация

1. Каменный туннель, лестница, широкие полосы: **вероятен** point-shadow архитектуры/лестницы, но отличать тень от BSP-плоскостей нужно в игре.
2. Подвесной огонь, большая чёрная многоугольная форма: **возможны** main point-shadow, отдельная Fire world-mask или сама BSP/запечённая геометрия. По одному кадру не установлено, какая ветка виновна.
3. Прожектор, крупный прямоугольный тёмный силуэт: **сильный кандидат на near-emitter self-shadow корпуса**, но также необходимо исключить тёмную видимую грань самой модели.

## 6. Безопасный A/B на единственной принятой DLL #41019985033

Не менять PK3 и DLL. На одинаковых savegame/camera/exposure сделать четыре кадра для каждой сцены:

```cfg
// A: исходная принятая конфигурация
seta r_dlightShadowStrength "0.88"
seta r_dlightWorldContainment "2"
seta r_dlightShadowSoftness "1.70"

// B: отключить только основную point-cubemap тень
seta r_dlightShadowStrength "0"

// C: вернуть main shadow, исключить только world-mask
seta r_dlightShadowStrength "0.88"
seta r_dlightWorldContainment "0"

// D: восстановить маску, испытать меньшую ширину PCF
seta r_dlightWorldContainment "2"
seta r_dlightShadowSoftness "0.80"
```

Изменение B **не обязано выключать** `DlightWorldVisibility()` — это самостоятельный множитель. Изменение C способно вернуть ранее исправленные Fire/Tesla утечки, поэтому **только для краткого диагностического теста**.

Для отдельного сравнения main filter `r_dlightShadowFilter 0` против 2 потребуется `vid_restart`, потому что CVar латched и используется при компиляции вариантов GLSL; это второстепенный тест. Не менять `r_shadowFilter` и не использовать старые экспериментальные PK3.

После теста:

```cfg
seta r_dlightShadowStrength "0.88"
seta r_dlightWorldContainment "2"
seta r_dlightShadowSoftness "1.70"
seta r_dlightShadowFilter "2"
vid_restart
```

Обязательная фиксация: тот же ракурс, разрешение, exposure, `r_dlightMode 2`, fps, имя сцены, три группы A/B/C/D и результат изменения **конкретной** тени.

## 7. Безопасная стратегия будущего узкого фикса

1. Не трогать принятый HDR16F Sun (Factory Visual PASS), его DLL, Sun/CSM, SSGI, Bloom, Local/Fire Volumetric, StaticPromote light identity и производительные настройки.
2. Отделить код/визуальное изменение **Stage 11 material/receiver eligibility** от более позднего **Fire world-mask**, с помощью зафиксированных до/после Stage 11 исходников.
3. Добавить в *отдельной test-ветке* корректный emitter-aware caster exclusion только для физически связанного корпуса текущего источника и только в его собственном shadow capture. Не исключать этот корпус из теней других источников. Для арх. стен/дверей/решёток сохранить приём и отбрасывание.
4. Для Fire world-mask независимо испытать корректную OpenGL face orientation, переменный размер буфера и безопасную границу PCF. Сохранять solid-wall rejection, без утечек на Crypt1/Escape1/Xlabs.
5. Тестировать выход Windows DLL в A/B перед любым Production-слиянием. Сравнивать FPS, утечки, тени проходов/решёток, стабильность источников и динамический бюджет.

## 8. Границы доказательства

ПРОВЕРЕНО: origin релиза #41019985033, Stage 11 source-integrated, текущие значения cvars, различие 2048/256, независимое применение `DlightWorldVisibility`, отсутствие emitter-identity проверки в Stage 11 material classifier, наличие исторического указания на грубость shadows при containment 2.

НЕ ДОКАЗАНО: что именно крупная чёрная область на каждом присланном кадре производится конкретным shader pass; физическая локализация source vs geometry; что откат только Stage 11 устраняет проблему; точный FPS/внешний вид фикса на пользовательском GPU.

**Вердикт:** начинать с диагностики Stage 11 расширения caster/receiver и near-source self-shadow, но не объединять это объяснение с проблемой Fire architectural 256-mask. Фикс без A/B на данных трёх сценах преждевременен.
