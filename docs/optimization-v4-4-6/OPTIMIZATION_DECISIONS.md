# Решения по оптимизации

1. **StaticPromote, tr_scene.c**: удалены построение и передача неиспользуемого отчёта из Frame/AddCandidate/AddSlot. Его получатель уже начинался с безусловного return в production. Остались те же выбор ламп, формулы цвета/радиуса, RE_AddLightToScene, признак forced и tagging. Однократные lazy-load вызовы сохранены явно для manual/disabled paths. Удалён также неиспользуемый signed hash с возможным переполнением. До 65 форматирований за кадр при 32 лампах больше не нужны. Дифференциальный C-тест: 10 000 вариантов, включая заполненный список и null, побитово одинаковый результат. Реальный FPS не измерен.

2. **Группы теней, tr_main.c**: результат исходного BFS сохраняется для всех посещённых членов компоненты только внутри R_RenderDlightCubemaps. На каждом вызове таблица сбрасывается, после вызова отключается. Нет повторного использования shadow map, межкадрового кэша, изменения выбора/порядка/центра захвата. Исходные координаты, цвета, радиусы и классификация в этой фазе не изменяются; изменяются отдельные выходные shadow-mask/slot поля. Вызовы с новым светом, камерой, сценой, картой, настройками получают новую таблицу. Эквивалентность проверена 850 000 запросами на 5 000 наборах с цепочками, отключением grouping, невалидными индексами, одинаковыми fixture ID, изменением цвета/радиуса/eligibility. UBSan включён для harness. 44 110 275 → 899 957 сравнений — синтетическая стоимость алгоритма, не GPU/FPS.

3. **CI/provenance**: восстановлены AA v4.4.3 и UI, отсутствующие в сокращённой telemetry-реконструкции. Патчи, shader donor и non-retail payload закреплены хэшами и больше не скачиваются из истекающих Actions artifacts. Полностью пересобираются EXE, renderer, cgame, qagame, UI.

Решение: ограниченный кандидат для проверки. Алгоритмические тесты подтверждены; окончательное визуальное/Windows GPU acceptance пока не получено. Все GLSL, tr_backend/FBO/world/game/cgame/UI относительно исправленной базы побитово сохранены. Значения качества, cadence CSM, 32 лампы и 3 persistent slots не менялись.

Follow-up cleanup: removed now-unreferenced report-only globals, map-count helpers and local report cvar reads. One-time user/synthetic rule loading remains explicit. Diagnostic TestLab adapters derive the emitted-light count themselves; both adapters are syntax-checked before CI builds. No warning suppression flags were added.


## Дополнительная точечная серия по карте 11.10.2026

4. **OPT-09 (SSGI):** в каждом вызове `SsgiAccumulate` одно чтение raw scene depth для точного UV; из него рассчитываются entity/viewmodel rejection и linear depth. Пороговые значения, UV, число taps, donor/receiver masks не менялись. Центр `SsgiLuma` теперь вычисляется один раз на пиксель, а не в каждой из 12 функций накопления.

5. **OPT-06 (Fire Volumetric):** в core/body/halo гауссианах `length -> square` заменено на `dot/width²`. Радиальный `guardR` оставлен без изменений, художественные коэффициенты и форма пламени сохранены.

6. **OPT-04 (Local Volumetric):** `physicalLightRadius²`, ось и `cosInner/cosOuter` spotlight вычисляются за пределами ray-march цикла; исключены повторные uniform-dependent нормализации. Shadow PCF, samples и depth conventions не менялись.

7. **OPT-02 (Sun Volumetric):** экспонента прозрачности вычисляется один раз для первого ray step и один раз для множителя шага; в цикле рекурсия `T *= decay`. Jitter, sample count, CSM cascade selection, PCF, phase и художественные параметры сохранены. Возможна небольшая ошибка округления; обязательны HDR A/B и GPU pass timings.

8. **Provenance и сборка:** strict SHA256 контроль восстановленного GLSL, одноразовая якорная трансформация только трёх shader files и diff artifact. В исходном пакете оптимизации нет DWPERF/qglFinish. Контрольные значения Python с float32 — только ARITHMETIC_SMOKE_PASS; Windows GPU/игровые кадры — NOT_RUN до проверки пользователя. Сохранены ранее реализованные CPU-оптимизации StaticPromote и shadow-group BFS. Новый release остаётся **CANDIDATE_FOR_LOCAL_VERIFICATION**, пока не подтверждено отсутствие визуальных регрессий и выигрыш в замерах.
