# DarkWolf Point Shadow V3.2 — Evidence-based Boss1 source-local fixture guard

Date: 2026-11-01. Accepted production: #41019985033, unmodified. Experimental source branch only.

## Inputs

- Five JPEGs from uploaded `DW_PS_V31_BOSS1_FIXTURE_RESULTS_20261101_134055_84a4ae.zip`, all 1280 x 768; ZIP CRC valid.
- The earlier uploaded Boss1 V3.1 JSON: `rendererTotal=7791`, `mainWorld=7274`, `capture=(-2764,-219,-24)`, world surface `7232` shader `textures/metal_misc/ametal_m03dm`.
- Prior A/B/C/D/E tests established that removing ordinary point-shadow caster group `3637..7273` clears the huge silhouette, and modifying the wrong capture does not.

## Matched-view controlled GPU interventions

| Screenshot phase | Intervention | Solid dark silhouette | Fixture stand / bracket shadows |
| --- | --- | --- | --- |
| 01 baseline | all original castors | PRESENT | PRESENT |
| 02 `7232` excluded | one world caster omitted only from selected point shadow | GONE | PRESERVED |
| 03 `7234` excluded | emissive surface only | PRESENT | PRESERVED |
| 04 `7229..7234` excluded | six fixture-like world casters | GONE | ADDITIONAL SHADOWS LOST |
| 05 restored | all original casters | PRESENT | PRESENT |

Numerical image QA on unchanged camera, excluding top 70 HUD/diagnostic pixels:
- Baseline vs phase 02: **23,493** pixels differ by >15 intensity in at least one RGB channel; bounding box **x486..706, y93..337**.
- Baseline vs phase 03: **0** pixels differ by >15 outside top HUD region.
- Baseline vs phase 04: **39,513** pixels differ by >15; bounding box **x429..706, y93..669**, consistent with removing additional legitimate fixture shadows.
- Baseline vs phase 05: **0** pixels differ by >15 outside HUD region.
- Controlled test confirms phase 02 clears the unwanted large polygon while preserving the narrower holder/stand shadows.

## Causal conclusion and limits

World surface ID `7232` is **experimentally causal for the large shadow on Boss1 in the tested source/camera**.
It is NOT proven that the surface's world geometry is defective, nor that permanently removing it globally would be physically correct. With a point shadow capture near a large physical fixture, a source-local self-occlusion/projection artifact is plausible.

## V3.2 experimental solution

- Add a new non-archived, **latched and default-OFF** `r_dwPointV32FixtureGuard`.
- When ON, omit only world BSP surface ID 7232 from **that source's ordinary point shadow capture**; the surface is still visible in ordinary scene rendering and still casts shadows for other lights.
- Strict fail-open guards: `boss1`, world and total surface counts 7274/7791, shader name, matching AABB, world entity, point-shadow flags and capture origin (-2764,-219,-24) within 0.25.
- No global material or model exclusion, no changes to surface/receiver graphics, no changes to Fire/Tesla/sun CSM/other effects.
- A one-command 3-phase GPU test (baseline, targeted ON, restore) is required before accepting the **new compiled binary**.
- This remains an **explicit map/source rule**, not a generalized algorithm for every BSP spotlight.
