DARKWOLF RTCW — REND2 v4.4.6 FULL PERFORMANCE TELEMETRY
=========================================================

ЦЕЛЬ
----
Это НЕ оптимизированный релиз. Это точная v4.4.6 с диагностическим слоем,
который собирает данные, необходимые для принятия решения о финальной
оптимизации без изменения визуального качества.


ИЗОЛЯЦИЯ НАСТРОЕК
-----------------
RUN_DWPERF_CAPTURE.bat запускает игру с двойной защитой от старых пользовательских настроек:
- отдельный fs_homepath/com_homepath: DWPerfHome;
- команда +safe, при которой ioRTCW не выполняет wolfconfig.cfg и autoexec.cfg.

Перед каждым тестом DWPerfHome создаётся заново. В нём создаются пустые wolfconfig.cfg и autoexec.cfg как дополнительная страховка.
Обычная домашняя папка ioRTCW и её конфиги не читаются этим benchmark-запуском.

После safe-start применяются только контролируемые настройки релиза:
1. default.cfg движка;
2. UNIFIED_PRODUCTION.cfg;
3. DWPERF_HIGH_QUALITY.cfg.

Профиль теста: HIGH QUALITY из native v4.4 profile contract.
Ключевые параметры: 4x MSAA, SSGI=1, Local Volumetric=1, Volumetric Sun=1,
2048 dynamic-light shadow maps, 3 persistent dlight shadow slots, StaticPromote max 32,
PBR=0, fullscreen, native desktop resolution (r_mode -2), VSync=0, com_maxfps=0.

КАК ЗАПУСТИТЬ
-------------
1. Распакуйте релиз в отдельную копию вашей рабочей папки RTCW с retail pak*.pk3.
2. Запустите RUN_DWPERF_CAPTURE.bat двойным щелчком.
3. Игра запустится автоматически с Rend2, VSync=0 и com_maxfps=0 только для тестовой сессии.
4. Играйте как обычно. Телеметрия пишется автоматически.
5. После завершения тестов выйдите из игры через меню.
6. Скрипт автоматически создаст:
   DWPerfTelemetry_YYYYMMDD_HHMMSS.zip
7. Передайте этот ZIP мне в чат. Другие файлы вручную собирать не нужно.

РЕКОМЕНДУЕМЫЙ НАБОР ТЕСТОВ
--------------------------
Не требуется точный маршрут. Важно провести несколько минут в разных типах нагрузки.

A. escape1
   - обычное перемещение внутри помещений;
   - комната охраны/стол с тремя лампами;
   - участки с большим количеством StaticPromote lights;
   - стрельба и динамические тени.

B. swf
   - участки с большим количеством ламп;
   - активно двигайтесь и вращайте камеру;
   - по возможности вызовите несколько взрывов.

C. dam
   - прожекторы;
   - local volumetric;
   - открытые и закрытые участки.

D. forest или другая открытая карта с солнцем
   - участки под r_forceSun 1;
   - двигайтесь вперёд и быстро вращайте камеру;
   - проведите часть теста с большим количеством видимой геометрии.

E. crypt1
   - несколько факелов/огней;
   - volumetric fire/local volumetric;
   - динамические тени рядом с источниками света.

Желательно 2–4 минуты на каждую доступную сцену. Если какая-либо карта неудобна,
пропустите её. Даже 10–15 минут обычной игры в разных тяжёлых местах дадут
полезный набор данных.

ЧТО СОБИРАЕТСЯ
--------------
Обычные кадры (без GPU-синхронизации):
- wall frame time;
- frontend/backend CPU time;
- R_RenderView count;
- main/shadow view counts;
- CPU стоимость R_GenerateDrawSurfs и R_SortDrawSurfs;
- CPU стоимость StaticPromote;
- CPU стоимость point-light shadow frontend;
- количество point-light cubemap faces;
- entities/dlights/drawsurfs;
- BSP leaf/dlight surface counters;
- surfaces/batches/vertices/indexes;
- VAO draws/binds;
- GLSL program binds и типы draw calls;
- FBO bind calls / реальные FBO changes;
- blit/FastBlit counts.

Редкие probe-кадры (примерно один на 240 кадров):
- dynamic point-light shadow pass;
- Sun CSM shadow pass;
- FireVol synthetic shadow pass;
- other shadow pass;
- shadow-map capture/copy;
- depth prepass;
- main draw;
- MSAA resolve;
- SSAO composite;
- SSGI;
- volumetric sun;
- local volumetric;
- volumetric fire;
- ToneMap;
- SunRays;
- Bokeh;
- final blit;
- полный postprocess.

Probe-кадры используют qglFinish для изоляции этапов и ПОМЕЧЕНЫ probe=1.
Они автоматически исключаются из обычной frame-time статистики.

Также собираются:
- CPU;
- GPU и версия драйвера;
- Windows build;
- power plan;
- dxdiag;
- используемые Rend2 cvars;
- полный qconsole.log;
- автоматическая сводка p50/p95/p99 по картам.

ВАЖНО
------
- В тестовом renderer нет будущих performance-оптимизаций.
- Качество эффектов v4.4.6 намеренно не снижается.
- Производственные лимиты 32 StaticPromote / 3 persistent shadow slots не меняются.
- PBR остаётся выключенным согласно production profile.
- Существующая Sun CSM optimization v4.4.4 сохраняется.
- Ваша wolfconfig.cfg резервируется перед тестом и восстанавливается после него.

ПОСЛЕ ПОЛУЧЕНИЯ ZIP
-------------------
По телеметрии будет построен рейтинг bottleneck-ов и принято решение, какие
оптимизации реально внедрять. Затем будет создан отдельный clean production
workflow: без DWPERF, без qglFinish probes и без диагностических cvar.
