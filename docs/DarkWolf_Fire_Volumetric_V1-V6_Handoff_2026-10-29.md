# DARKWOLF / ioRTCW Rend2 SP — Fire Volumetric Occlusion: Research Handoff (V1–V6)

**Дата фиксации:** 2026-10-29 · **Статус:** CLOSED / DEFERRED (исследовательская ветка приостановлена по решению пользователя).  
**Область:** ONLY `ioRTCW Rend2 Single Player`, не DarkWolf D3D12 / DXR.  
**Протокол:** DarkWolf Engineering Protocol из `Инструкция для ИИ.docx`.  
**Каноническая неизменяемая Clean Production база:** [GitHub Actions #40822067963](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40822067963) (X-Labs Tesla Geometric PVS Clean Production Candidate V1, пользователь подтвердил исправление Tesla).  
**HEAD SHA этого run:** `120b654336c66a2641c95f612290e5864c32803c`; **GitHub artifact ID:** `12874828494`; **ZIP SHA-256:** `16d6d376a91dfda21d179a1761c778bc27f2389e3e329619e33f19aeb29a2a0d`.  
**Правило:** Fire Volumetric V1–V6 ни в какой форме НЕ переносить в Clean Production. Сохранить исходную реализацию Fire Volumetric, как в #40822067963. Из всей этой серии пользователь отдельно санкционировал только clean-fix **Alarm Local Volumetric**, который должен быть независим от Fire.

---

## 1. Задача, с которой начали

Исправить сквозную засветку через BSP-перекрытия у двух классов источников, универсально по всей игре, без привязки к картам:

- **Crypt1:** обычный динамический свет огня и собственно **Fire Volumetric**, особенно тёплый свет, видимый из помещения *под* полом, над которым находятся факелы / свечи / огни. Аналогичные места возможны на Escape1 и других картах.
- **Tram:** красная Alarm лампа, прямой dlight плюс **Local Volumetric**, дающие красную засветку через стены / лестницу.

Не менять пламенный спрайт, визуальную стилистику RTCW, PBR, X-Labs Tesla PVS, CSM, кадровую производительность и три штатных динамических теневых слота. Максимум 32 активных StaticPromote источника и существующее разделение теневых бюджетов сохраняются. Промежуточные эксперименты *могут* иметь управляющие CVAR/аудит; Production — нет.

## 2. Подтверждённые факты (не гипотезы)

1. **Прямое динамическое освещение огня Crypt1:** world-occlusion mask для подходящих тёплых авторских источников заметно уменьшает засветку. Это подтверждено A/B на Crypt1, исходный тест V1. **Но** основную оставшуюся тёплую засветку под полом оно не устраняет.
2. **Fire Volumetric под полом Crypt1:** с включённой архитектурной защитой прямого света остаётся; при `r_volumetricFire 0` тёплая засветка существенно/полностью исчезает. Таким образом, это самостоятельная объёмная составляющая, а не просто повышение HDR exposure.
3. **Alarm / Tram:** красные источники из второго теста размечены `local=1`, `red=1`, `fixture=243, 246, 259`, `native=0`; режим V2 назначал им world-slots, но видимая утечка практически не изменилась.
4. **Alarm Local Volumetric:** в V3 профили D/E, использующие `r_dwV3LocalVolumetricWorld 1` и архитектурную маску, **устранили красную объёмную засветку** в пользовательских A/B/C/D. Пользователь подтвердил это отдельно. Именно данный алгоритмический путь утверждён для **чистой Alarm-only интеграции**, без Fire-пути.
5. **V4 Fire ownership:** реальный Fire dlight имел `v4Owner=12`, `worldReady=1`, `pointReady=1`, но синтетические Fire эмиттеры оставались без world-map (`v4Owner=-1`, `worldReady=0`, часто `pointReady=1`). Исходная засветка не исчезла. Одного исправления поиска реального владельца недостаточно.
6. **V5 synthetic Fire:** собственные синтетические cubemap подключились как `worldLight=-2 ... -8`, `worldReady=1` (семь наблюдавшихся объектов), с сохранением существующих восьми синтетических кеш-слотов. Режимы **C** (world volume gate) и **D** (world-only capture + gate) устранили засветку *под полом Crypt1*.
7. **V5 REGRESSION:** возле свечи/камина Escape1 C даёт резкие грязные тёмные пятна, полосы, угловатые области вместо мягкого объёма. D выглядит ближе к исходному, но без доказанной корректности. Сам факт исчезновения света под полом не равен правильной окклюзии.
8. **V6 REGRESSION NOT ACCEPTED:** четыре профиля A/B/C/D на Escape1 около свечи визуально не устроили пользователя (новые кадры 2026-10-29 ~12:33). Ни один не признан приемлемым; **отложить всю Fire Volumetric работу**. Никаких «тихих» исправлений RGB/PCF в production.
9. В V4/V5 диагностике отдельно встречается локальный `fixture=444` с `worldReady=0`, `pointReady=0`. Он не обязан использовать ту же cubemap, что синтетический огонь. Истинная роль в конкретной засветке ещё не изолирована.
10. **Тестовая сборка CI SUCCESS ≠ RUNTIME ACCEPTED.** Каждый из V1–V6 проходил source/Win64 CI, но исследуемый Fire-фикс не прошёл согласованные пользователем визуальные регрессии.

## 3. Хронология тестов, результаты и вердикты

| Run | Эксперимент | Изменения / CVAR | Пользовательский runtime результат | Вердикт |
|---|---|---|---|---|
| [#40830222750](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40830222750) | **V1** Native World Gate | `r_dwNativeWorldLeakTest=0/1/2`, world occlusion для цветовой группы authored dlights | `1` на Crypt1 убрал часть прямого тёплого dlight; `2` на Tram не помог | V1 тест; не переносить в production |
| [#40833785591](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40833785591) | **V2** Promoted Red World Mask | `r_dwPromotedRedWorldTest`, red StaticPromote world mask + аудит всех dlight | Tram `local=1/red=1`, worldSlot появлялся; A≈B, C≈D с выключенным Local Volumetric | Маска прямого света — необходимая подсистема, но одна недостаточна |
| [#40845221337](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40845221337) | **V3** Universal DLight / Fire / Local Volumetric | `r_dwV3PhysicalWorldMode=3`, `r_dwV3FireVolumetricWorld`, `r_dwV3LocalVolumetricWorld`; shader `u_DlightWorldMap`, `u_DlightWorldOrigin` | **Alarm Local Vol D/E исправлен**; Crypt1 прямой dlight ограничен, Fire Vol всё ещё течёт | Alarm path принять как основу clean; Fire path пока не принят |
| [#40863089582](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40863089582) | **V4** Exact Fire Owner | `r_dwV4FireOwnerFix`, source-index из Fire residency вместо сравнения позиции скопированного света | A≈B, тёплая объёмная засветка сохраняется | НЕ фикс |
| [#40866858865](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40866858865) | **V5** Synthetic Architecture Occlusion | Независимые режимы synthetic world-only capture и world volume gate (A/B/C/D), кеш 8 сохраняется | C/D подавляют утечку Crypt1; B может делать её сильнее; C/D грязнят свет свечи/камина Escape1 | **Критическая визуальная регрессия** |
| [#40872753200](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40872753200) | **V6** RGB24 Depth / single PCF | A=V5 D, B=correct RGB24, C=correct+soft5, D=single 9-tap point | Все четыре выглядят неудовлетворительно на Escape1 около свечи | **ОТКЛОНЕНО пользователем; работу остановить** |

Отдельно исходная **#40822067963** остаётся визуальным и бинарным эталоном Fire Volumetric. **Не использовать V5/V6 как новые базы Clean Production.**

## 4. Где именно лежит код

Пути все относительно восстановленной исходной базы `sept-source/SP/`:

- `code/rend2/tr_scene.c` — `RE_AddLightToScene`, флаги `DARKWOLF_REF_NATIVE_AUTHORED_DLIGHT`, `DARKWOLF_REF_LOCALVOL_LAMP`, разметка `dl->worldOcclusion`, `dl->fireVolumetricSource`, `staticPromoteFixtureId`, `nativeAuthoredDlight`, существующее исключение Escape1.
- `code/rend2/tr_backend.c` — `RB_LocalVolumetricRenderEx`, выбор `pointShadowSlot`, выбор Fire source copy vs physical light source, установление `u_DlightShadowMap`, экспериментальная (V3+) связка `u_DlightWorldMap`, `u_DlightWorldOrigin`; Fire modes преимущественно 5–9, LocalVol point mode 3.
- `code/rend2/tr_main.c` — `R_RenderFireVolumetricSyntheticShadows`, захват/кеш синтетических Fire cubemap. В V5 менялись world-only capture и доступность двойных граней. Эти изменения **ОТКЛОНЕНЫ** для чистого релиза.
- `code/rend2/glsl/volumetriclocal_fp.glsl` — Fire medium, `localDlightVisibility`, выбор PCF, нормализованная/упакованная depth, mixed volume+world visibility в V3–V6. **Все Fire-изменения V3–V6 должны остаться экспериментальными**.
- При дальнейшем аудите также проверить actual shadow write path `shadowfill_fp.glsl`, `tr_glsl.c`, uniforms, cube coordinate conventions, `tr_local.h` (dlight structure), `tr_init.c` (GLSL linking).

**Проверенная полная source-цепочка:** GitHub Actions Clean #40822067963 (верхний SHA выше) и *отдельные* тестовые ветки / patches артефактов V1–V6. Все build experiments были на исходниках, восстановленных из September exact source, с октябрьскими clean delta; нельзя брать старый vanilla upstream и выдавать его за финальную базу.

### Проверяемые сигнатуры и диагностические поля

- `DW_V3_VOLUME` — поля `class`, `mode`, `worldLight`, `worldReady`, `pointReady`, `fixture`, `native`, `fire`, `radius`.
- V4 добавил `v4Owner`, который показывал `12` для физического dlight и `-1` для synthetic. Это не означает, что все `-1` физически являются неисправными — часть сознательно synthetic.
- V5 выдавал `worldLight=-2 ... -8` и `worldReady=1` для синтетических Fire shadows, что подтверждает binding. Это **не** подтверждает корректный формат глубины или нужную физическую видимость.
- V2 `DW_ALARM_PROMOTED_V2_LIGHT` на Tram: `native=0`, `local=1`, `red=1`, `fixture=243/246/259`; `worldSlot=2/3/4` при экспериментальном включении.
- Отдельное значение `fixture=444`, `worldReady=0`, `pointReady=0` не смешивать с synthetic cubemap и не назначать ему чужой slot.

## 5. Критичные гипотезы и ограничения — не объявлять доказанными

**Гипотеза по V5 грязному свету:** decoder `decodeDlightShadowDepth()` в исходном volumetric shader использовал `dot(rgb, vec3(1/65536, 1/256, 1))`, тогда как V3 world-gate был добавлен с `dot(rgb, vec3(1, 1/255, 1/65025))`. Для одинакового формата RGB возможно грубое расхождение. Модельный тест подтвердил математическую ошибку V3, но **V6 с экспериментальными поправками не прошёл визуальную проверку**. Исправление RGB-формулы само по себе **не гарантирует** верную объёмную окклюзию.

**Возможные другие причины:** двойное применение одной кубической тени (point × world); захват двухсторонних BSP-полигонов; неверная ориентация cube face; нормализация направления; bias масштабирован не в той системе координат; светокеш синтетического Fire не соответствует сцене; over-occlusion вблизи источника; накопление shadow factor на каждом шаге raymarch; отражение/атмосфера `r_ssgi` как отдельный слой. Эти варианты НЕ установлены окончательно; не нужно сразу переписывать PCF, писать raytracing или увеличивать слоты.

**Особое требование к визуальному качеству:** мягкая непрерывная форма объёма возле свечи и камина Escape1 важна не меньше, чем отсутствие засветки под полом Crypt1. Измерение средней яркости по кадрам — лишь вспомогательный сигнал, не критерий физической корректности.

## 6. Что СОХРАНИТЬ в любом новом Clean Production

**Строго неизменные:** бинарная и исходная функциональность Fire Volumetric как в GitHub #40822067963; все Sun3, Fire E, Texture Fidelity, CSM, Sky Portal Single Sample, Tesla PVS и другие принятые эффекты; EXE, CGame, QAGame, UI, GLSL других эффектов; динамический shadow budget. Не переносить патчи V4, V5, V6, `tr_main.c` из V5 или Fire-ветки `volumetriclocal_fp.glsl` из V3–V6.

**Отдельно разрешённая работа:** чистый алгоритм **Alarm promoted red world-occlusion + Local Volumetric world-gate**, взятый из успешного V3 D/E; без экспериментальных `r_dw*Test`, `r_dwV3*`, однократной телеметрии и без диффузного изменения всех ламп. Предпочтение — классификатор только `localVolumetricLamp`, красная цветовая группа, стабильный `fixtureId`, существующий world mask; ни одного условия по карте Tram или координатам. Fire modes 5–9 в исходном коде не менять.

## 7. Регрессионная матрица на БУДУЩЕЕ (только если пользователь решит возобновить)

| Место | Что проверять | Критерий успеха |
|---|---|---|
| Crypt1 — под перекрытием | DLight ON/OFF, FireVol ON/OFF, behind-solid volume | Нет тёплой утечки; остальная сцена нормальная |
| Crypt1 — непосредственно возле факела | FireVol shape, softness, brightness, dynamic shadows | Пламя и мягкий объём сохранены |
| Escape1 — свеча на столе, обе ниши | близкий ракурс 1–2 м, вид на каменную стену | Нет чёрных пятен, полос, резких angular silhouettes |
| Escape1 — камин/печь, внешняя стена | volumetric vs direct light | Нет сквозной засветки; красивое локальное свечение |
| Tram — Alarm | red direct + LocalVol | Нет красного свечения через стены, но возле лампы свет сохранён |
| X-Labs — Tesla | SP snapshot, blue lamp and electric bolt | Tesla Geometric PVS не регрессировал |
| Escape1/Assault outdoor | CSM sun/r_forcesun | Нет новых GPU падений FPS |

Оставить прежние константы и эффекты (`r_dlightmode 2`, `r_forcesun 1` в принятых config profiles), не вводить PBR, не менять Bloom v2 HDR Pyramid, не трогать StaticPromote 32/3. На медленных сценах измерять frame-time в дополнение к FPS; «не заметил падения» ≠ полноценный профайлинг.

## 8. Продолжение работы — если пользователь когда-нибудь даст команду

1. Начать **с визуального отрицательного доказательства V6**: он отвергнут даже после RGB24/soft5/single-point. Не предлагать повтор V6 и не объявлять его fixed.
2. Скачать/открыть точную source-base и побайтовые patch diffs из перечисленных GitHub Actions; подтвердить hashes, mode semantics, shadow map encoding и cache ownership.
3. Выделить один проблемный Fire-источник по `fixtureId`/source ordinal, отсоединить вклад остальных источников в строго локальном лабораторном тесте. Прозрачная визуализация source-to-cubemap и shadow-depth mismatch предпочтительнее случайных новых CVAR.
4. Исследовать **write-read depth contract** (packed RGB channels, projection range, inverse direction, bias) и актуальность синтетического cache. Не расходовать дополнительные 3 dynamic shadow slots.
5. Только после доказательства и компиляции — 1 комплексный TEST; проверять сразу и Crypt1 под полом, и Escape1 у свечи; без глянцевых «production» заявлений до реальных runtime результатов.
6. Для **clean Alarm** не использовать этот список как разрешение на Fire изменения. Alarm и Fire — разные acceptance ветки.

## 9. Ссылки на артефакты и собственные доказательства

Clean reference: [#40822067963](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40822067963)  
V1: [#40830222750](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40830222750)  
V2: [#40833785591](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40833785591)  
V3: [#40845221337](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40845221337)  
V4: [#40863089582](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40863089582)  
V5: [#40866858865](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40866858865)  
V6: [#40872753200](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40872753200)

Консольные свидетельства в файловой сессии: `Alarm_TEST_V1.txt`, `Alarm_TEST_V2.txt`, `crypt1_TEST_V2.txt`, `DW_V4_FIRE_OWNER_A.txt`, `DW_V4_FIRE_OWNER_B.txt`, `DW_V5_FIRE_RESULTS.txt`. Кадры пользователя: последовательные A/B/C/D на Crypt1, Tram, Escape1 (включая последний набор V6 у свечи). У этих изображений нет автоматизированной привязки к FOV/frame-time/позиции, так что не считать различия абсолютной GPU-метрикой.

**Решение пользователя 2026-10-29:** остановить исследования Fire Volumetric; сохранить данные в этом `.md`; в новый Clean Production перенести *только* устранение утечки Alarm, применив его к принятой #40822067963 и оставив Fire в точности как было.
