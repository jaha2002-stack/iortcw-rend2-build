# V3.1 Boss1 telemetry analysis and next source-scoped fixture attribution (2026-11-01)

This is an **experimental diagnostic follow-up only**, based on the user's successfully uploaded `DW_PS_V31_BOSS1_TELEMETRY.zip`. Original clean production **GitHub Actions #41019985033 is unchanged**. Test DLL = successful #41286948638 (SHA256 `ca3e5d4ea384a90121469980a6429814965419db7d7e003f90ffcbe5459fa942`).

## Verified JSON

- `format=DW_POINT_SHADOW_V31_BSP_AUTO_AUDIT`, `map=boss1`, `captureOrigin=(-2764,-219,-24)`; range `3637..7273`.
- `rendererTotal=7791`, `mainWorld=7274`, `rangeAabb=3617`.
- `seenInSelectedShadowDrawlist=424`, but `candidateShortlist=160` only. The list does not cover every submitted candidate.
- `captureInsideAabb=0`; `boxDistanceLE16=2`, `LE32=6`, `LE64=8`.
- Two uniquely near-capture candidates **from the exported list**:
  - `id=7232`, `shader=textures/metal_misc/ametal_m03dm`, `surfType=4`, `boxDistance=10.359`, `centerDistance=23.173`, `angularProxy=0.8482`, `boundsMin=(-2799.02,-229.78,-40.53)`, `boundsMax=(-2774.36,-210.73,-16.56)`. Drawlist submitted.
  - `id=7234`, `shader=textures/lights/light_m4`, `surfType=4`, `boxDistance=10.359`, `centerDistance=16.714`, `angularProxy=0.8712`, `boundsMin=(-2784.19,-229.78,-40.53)`, `boundsMax=(-2774.36,-210.73,-20.81)`. Drawlist submitted.
- More same-fixture candidates: `7229`, `7230`, `7231` (each <32 units); `7233` approx. 97.55 units, likely another fixture component. Names and proximity support **hypothesis of lamp self-occlusion**, not proof.
- Ranking first `id=7083 sky_boss1_b25` is AABB-angular heuristic, not a true GPU depth owner. Do not conclude sky is faulty.

## Previously visually confirmed

D excludes 0..3636 (shadow remains). E excludes 3637..7273 (shadow clears). C excludes all BSP for capture (-2764,-219,-24) (shadow clears). The same-capture main-world BSP group **causally affects the shadow**. Individual surface responsible remains unproven.

## Controlled next step, automated no new renderer

A locally authored one-command CFG for V3.1 executes:
1. baseline screenshot,
2. exclude surface 7232 only,
3. exclude surface 7234 only,
4. exclude 7229..7234,
5. restore baseline screenshot and perform condump.

All V3 source matching, scope, receiver, near clip, origin-axis shifts are set to safe defaults; filtering is **temporary and source-scoped**, not a production fix. Run from one fixed Boss1 savepoint; no player movement. Use engine `wait 180`, `vid_restart` and `screenshotJPEG` commands; automatic report collector is included in the test bundle separately supplied to the user.

**Do not mark a root cause verified until the controlled captures show which intervention eliminates the silhouette.** If neither does, create pixel-level GPU depth owner ID diagnostic rather than repeat large manual ranges. Keep Stage11 full caster/receiver coverage, all Fire/Tesla/CSM/sky effects, 3 shadow slots and no production modification.
