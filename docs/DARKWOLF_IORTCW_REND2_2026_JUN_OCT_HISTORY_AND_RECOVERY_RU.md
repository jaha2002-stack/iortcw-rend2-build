# DarkWolf / ioRTCW Rend2: сохранение истории июнь–октябрь 2026

> Инженерная карта всей доступной линии разработки (состояние на 24 октября 2026 года).
> **Не заменяет исходники, журналы запусков и пользовательские визуальные испытания.**
> Статус эксперимента и факт успешной компиляции — разные вещи.

## Границы истории

- `jaha2002-stack/DarkWolfRTCW` создан 2026-06-12: ранняя линия DarkWolf, Windows DXR/D3D12, оптимизация RT, свет, BLAS/TLAS, TDR и сопутствующие тесты.
- `jaha2002-stack/DarkWolfRTCW-Lab-Clean2` (создан 2026-07-13) и `DarkWolf-Clean-Visible-Reference` (2026-07-18): последующие июльские DXR/EXP19–22 и clean visual reference.
- `jaha2002-stack/iortcw-rend2-build` создан 2026-07-09. Доступные на 2026-10-24 **450 GitHub Actions runs** охватывают 2026-08-07 — 2026-10-24; основной GitHub репозиторий имеет **52 ветки**. Это отдельная линия ioRTCW Rend2 (не следует механически переносить в неё D3D12 DXR код).
- Другие проекты/движки, включая `DarkWolfRTCW-idTech4` и отдельный Android-порт, имеют собственные зависимости, acceptance и handoff. Не смешивать их исходники, бинарники или runtime-тесты с Win64 SP без отдельной интеграции.
- Начальные эксперименты июня/июля по DXR присутствуют в отдельных Git-репозиториях. **Текущий FourWeek Master не является снимком всей DXR-ветки.**

## Проверенная хронология (не все эксперименты вошли в production)

| Период | Направление | Контрольные точки / отношение к production |
| --- | --- | --- |
| Июнь 2026 | DarkWolfRTCW, Windows DXR, первые функции трассировки лучей, TDR-safe и visibility | `DarkWolfRTCW`, коммиты начиная с 2026-06-12. Самостоятельный предшественник, не прямая патч-ветка Rend2. |
| Июль 2026 | DXR clean visual, EXР19–22: D3D12 динамический свет, SBT/BLAS, визуальная стабильность и performance | `DarkWolfRTCW-Lab-Clean2` и `DarkWolf-Clean-Visible-Reference`, исходники, исходные workflows и README. Не добавлять напрямую к Rend2. |
| 7–13 августа | Новая линия ioRTCW Rend2 Windows x64: visual upgrade, DLight, shadow path, light/color-mask, SUN-3…SUN-5C | Ранние runs `31164904880`, `31175256990`, `31245540989`, `31255568469`, `31703469904`. |
| 14–16 августа | Static Promote / Lamp Learn, ограниченный бюджет теней, SUN, material/reflection/GI PRE-PRODUCTION | Отдельные версии V12, SUN-5C, MAT-0/MAT-1, REF-1, GI-2. Принятые уровни/бюджеты сверять с соответствующим исходным набором, а не с произвольным экспериментом. |
| 17–22 августа | Bloom v1/v1.1/v2; эксперименты с Mode3/Scatter и A/B; HDR, ToneMap и AutoExposure | `32021112553` — Bloom v1.1; `31993514170` — исторический production reference. **Не все Bloom v3 эксперименты приняты**; итоговая v4.4.6 RC4 линия использует сохранённый Bloom **v2 HDR Pyramid** с `r_bloomMode=2`. |
| 23–29 августа | Sun/Local Volumetric; physical-light recognition, BSP PVS/areamask и cross-area, Factory/Escape1 Crypt1 lamps | Sun parent `32636643432`. PCRB диагностика `33158572361`: multi-point LOS и NO_PVS не стали универсальным production-решением; сохранять отчёты, не переносить отвергнутую гипотезу. |
| 30 августа – 5 сентября | Fire volumetric, самостоятельная огненная plume, динамические тени огня, MSAA integrity, shadow-caster/receiver | Fire v0.2 `33299908535`, `33304194713`; часть следующих экспериментов — диагностические, а не обязательные CVar. |
| 6–16 сентября | Light residency / Tier0/1, ограничение теневых источников, Tesla, DLight shadow pop, production shadow casters | R2 `34025927029`, accepted candidate `34012437835`, later production checkpoint `34830717268`. Регрессии Tier2 и shadow pop требовали раздельных проверок. |
| 17–28 сентября | Tesla 351, physical residency/table shadow, ignition/destructible props и игровое меню Rend2 | Tesla accepted reference `35150218437`; integrated production `35696866857`; props RC v0.5 `35862583739`, ignitable RC v0.6 `35884381549`, GUI `36310497602`, v4.4 `36396805525`. |
| 1–9 октября | v4.4.3 volumetric coverage AA, v4.4.4 ForceSun/CSM performance, v4.4.5 spotlight, v4.4.6 cumulative shader/game fixes | v4.4.3 `37233604307`, v4.4.4 candidate `37248863490`. See `integration/optimized-v4-4-6/` and the source provenance docs. |
| 10–13 октября | Отдельная попытка Fire Direct V2.2 исправления утечки печки Escape1 | **REJECTED VISUAL RUNTIME**: опубликованная тестовая попытка не закрыла утечку. НЕЛЬЗЯ повторно наложить на RC4. |
| 14–16 октября | Clean RC4 optimization, accepted Fire/Tesla LightContainment, SSGI/volumetric quality, Bloom v2 | RC4 `38704499119`, LightContainment `38733120730`, Quality `38765428993`, Bloom v2 `38798189322`. Видеопроверка Escape1/Tesla в прошлой работе; исходный патч защищён SHA256. |
| 17–21 октября | CSM Guard, Texture/Material Fidelity, CAS/A2C/LUT Visible V03, A/B и все эффекты ON | CSM `39152821574`, Texture `39208959543`, Visible V03 `39556894566`, галерея `39568968754`. |
| 24 октября | FourWeek Master SourceDefaultsON Win64: новый DLL, полная игровая сборка, точный source archive | DLL `40073883865`; ZIP `40074980554`; итоговые исходники `40076663037`. Финальное GPU-runtime acceptance **не измерено**. |

## Эталонная октябрьская база для всех дальнейших Win64 экспериментов

- Tag: `v4.4.6-rc4-fourweek-master-sourcedefaultson-20261024`.
- Стабильный коммит сборочной цепочки: `2ef7ad6bd9dbe8e03b561b4be6279953e51ceee1`.
- Full Win64 SP ZIP, 42 files: `559d01d3815ef1d58b3f018d1c1f215cb37881d2756ad3508ae5cc891179b2e4`.
- Canonical released renderer: `4112890117f5fb16371ba8387ecd89203257eff361c22d83784db65c67eadd0a`.
- **Exact source snapshot**: `DarkWolf_Rend2_v4.4.6_RC4_FourWeek_Master_SourceDefaultsON_Exact_Source.tar.gz`, SHA256 `9f6f4a79495154d7727384d94d96f57576ed9567015d45c1f21b7a6446480c22`, source tree `9999facb029b2eeaddcb52a28bc29a8382e0a8c8`, 3336 tracked files.
- Полный ZIP, source archive и `SOURCE_SNAPSHOT_PROVENANCE.json` хранятся в **UNPUBLISHED DRAFT Release ID 422588491**. Никогда не публиковать без прямого согласия владельца.
- Отдельный handoff: `docs/FOURWEEK_MASTER_PERMANENT_ENGINEERING_HANDOFF_2026_10_24.md`.
- Bitwise reproducibility of repeated DLL builds **not proven** despite source tree equality. Real Windows gaming GPU FPS/frametime and visuals acceptance **pending user tests**.

## Полный исторический архив текущего Git (для случаев истечения срока GitHub Actions)

Для долговременного хранения требуются:
1. **Git bundle `--all`** текущего `iortcw-rend2-build`: все доступные ветки, теги и все reachable коммиты с полными diff и файловыми blob. Можно делать новые ветки экспериментов из исторических commits, не используя старые ZIP артефакты.
2. Выгрузка **всех** GitHub Actions run metadata (including FAILED/CANCELLED, branch, SHA, time, conclusion) и всех artifact metadata (name, SHA256 digest, expiry, run). После истечения хранения эти индексы останутся, **но удалённые логи/видео из них не восстанавливаются**.
3. Раздельная фиксация решений пользователя, кодовых патчей/тестов, исходных комплектов, критериев acceptance. Исторические chat-транскрипты, видео и логи не гарантированно присутствуют в Git; называть такой индекс «полным архивом всех чатов» нельзя.
4. Ранние июнь–июльские DXR репозитории связаны как **предшественники**, но их source-tree и большой игровой контент не копируются в public `iortcw-rend2-build` или в этот Draft без отдельной политики доступа. Не смешивать с приватными репозиториями.

## Что категорически нельзя потерять

- Fire/Tesla architectural light containment `R_RenderDlightWorldOcclusion`, GLSL `DlightWorldVisibility`; Fire Direct V2.2 — rejected.
- Версия Bloom v2 production с HDR Pyramid; не переносить отклонённые Bloom v3 эксперименты вслепую.
- CSM reprime / ForceSun periodic 1/2/4 cadence; dynamic-caster shadow selection and residence budgets.
- Mappings static promotion/BSP/PVS; не вводить отвергнутый multi-point LOS как универсальное решение.
- Согласованные `r_forceSun 1`, `r_dlightMode 2`, SSGI, volumetric, Texture/Material Fidelity, CAS/A2C/LUT V03.
- Чистые исходники/production CFG без случайной лабораторной телеметрии, тестовых CVars, диагностики и A/B override. Фактические GPU FPS, визуальные дефекты и игру на картах Escape1, Factory, Assault, Crypt1 подтвердить отдельно.
- Различать **production acceptance**, **CI compile success**, **runtime evidence**, **rejected**, **experiment only**.

## Как пользоваться через год

Если Actions #40074980554 и предыдущие исчезнут:
1. Найдите pinned Git tag/commit и этот файл.
2. Используйте Git bundle (после успешного создания) для восстановления всех исторических веток/коммитов. Найдите соответствующие патчи в Git, а не пытаясь восстанавливать C-код из DLL.
3. Возьмите точный source snapshot из **unpublished** Draft Release (только для версии FourWeek Master).
4. Сверьте оба SHA256 (ZIP, source archive) с этой картой и соответствующими манифестами.
5. Для нового эксперимента создайте отдельную branch/Actions workflow, не изменяя tag и исходную базу.

**Ограничение:** копия Git-истории и метаданных Actions не восстанавливает исчезнувшие GitHub Actions logs, удалённые файлы вне Git, незафиксированные локальные эксперименты или полный текст прежних ChatGPT чатов. Для них нужны отдельные исходные экспорты.
