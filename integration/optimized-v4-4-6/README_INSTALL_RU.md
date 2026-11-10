# DarkWolf Rend2 v4.4.6 — чистый оптимизированный кандидат

Статус: CANDIDATE_FOR_LOCAL_VERIFICATION. Сборка и проверки алгоритмов не доказывают FPS, Windows gameplay или отсутствие визуальных регрессий. OPT-02, OPT-04, OPT-06, OPT-09 требуют подтверждения на реальном Windows GPU.

Распакуйте в отдельную копию легальной RTCW, где Main содержит retail pak*.pk3. Они не включены. Запустите RUN_DARKWOLF_OPTIMIZED_CLEAN.bat. Отдельный DWOptimizedHome хранит новые сохранения; старый профиль не удаляется. com_recommendedSet=1 исключает подмену пресета автонастройкой первого запуска. +safe исключает автоматическое выполнение wolfconfig.cfg/autoexec.cfg. При каждом таком запуске применяется контролируемый High Quality; новые настройки из wolfconfig также не читаются. Для старых сохранений вручную скопируйте только папку сохранений в новый профиль.

Сохранены 32 StaticPromote, 3 persistent shadow slots и существующий дополнительный резерв для динамических эффектов, 4x MSAA, SSGI, Local/Sun/Fire volumetric. PBR=0. Этот чистый профиль по требованию оптимизации запускает r_forceSun=1; исходная яркость, каскады и качество теней не снижены. Для сравнения с обычным профилем без принудительного солнца выставьте r_forceSun 0 вручную. Bloom/ToneMap/Exposure не изменены. Разрешение, VSync и FPS cap не форсируются benchmark-параметрами.

Нет DWPERF, принудительных GPU probes или автоматического сборщика. Исторические игровые средства редактирования сохранены. Лаунчер и Windows runtime требуют локальной проверки, включая пути с кириллицей.

Исходники и воспроизведение: https://github.com/jaha2002-stack/iortcw-rend2-build/tree/rend2-v4-4-6-clean-optimization/integration/optimized-v4-4-6 . Полные контрольные суммы — docs/SHA256SUMS.txt; provenance — docs/BUILD_PROVENANCE.json. Исходники движка GPL; см. COPYING.txt, LICENCE.md и лицензии библиотек.
