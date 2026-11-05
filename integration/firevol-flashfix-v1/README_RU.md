# DarkWolf FireVol Flash Fix V1 — TEST

База: GitHub Run **#41982135692** (ELSS V1.0.1 Persistence Fix).

Цель: убрать резкую FireVol-вспышку, подтверждённую тем, что `r_volumetricFire 0` полностью устраняет дефект.

Три независимых исправления включены по умолчанию:

1. **Warm-up Guard** — synthetic FireVol не рисуется без готовой архитектурной cubemap; после готовности плавно появляется за 300 мс.
2. **Additive Energy Guard** — близкие flame anchors одного физического огня не суммируют энергию выше 1.0.
3. **FLC Direct Fade** — FLC-created Direct DLight после PVS/бюджетного возврата набирает яркость за 250 мс вместо мгновенного скачка.

Auto Exposure, PCF4x4, `renderCap=8`, shadow budgets, IFLC/ELSS profile format не меняются.

Тестовые cvar:
- `r_dwFireVolFlashFix 0|1` — master A/B.
- `r_dwFireVolWarmupGuard 0|1`.
- `r_dwFireVolEnergyGuard 0|1`.
- `r_dwFireVolFLCFade 0|1`.
- `r_dwFireVolFlashDiag 0|1` — компактная строка `FIREVOL_FLASHFIX_V1` раз в секунду.
