# DarkWolf Point Shadow V3.2 — Boss1 GPU Visual Acceptance

Date: 2026-11-01
Accepted unchanged production baseline: GitHub Actions **#41019985033**
Experimental V3.2 build: GitHub Actions **#41290226774**, CI success
Test archive received: `DW_PS_V32_BOSS1_RECOVERED_20261101_135643.zip`

## Evidence integrity

The uploaded ZIP passed CRC verification and contains exactly the three expected 1280×768 JPEGs, console telemetry, recovery status, and SHA-256 CSV.

| Phase | Screenshot | JPEG SHA-256 |
|---|---|---|
| 01 Baseline | `DW_PS_V32_BOSS1_01_BASELINE.jpg` | `1e9c24f2c4110e8c0c59274831b520a6b689554b2c6d8fea959dfe2c684409cf` |
| 02 Source-local guard ON | `DW_PS_V32_BOSS1_02_GUARD_ON.jpg` | `c41ec5d282b09bab40303b8250ea6b78a8ff7005d6ae55bf5c5837fabc80e19e` |
| 03 Restored | `DW_PS_V32_BOSS1_03_RESTORED.jpg` | `250b8817f8f385daa9054e7ff02d746dd76d0af0f98c476e22904f433a30e2f2` |

## Console evidence

- `Wrote screenshots/DW_PS_V32_BOSS1_01_BASELINE.jpg`
- `DW_PS_V32_PHASE_01_DONE baseline`
- The cvar change was latched and `RE_Shutdown(1)` / renderer re-init executed.
- `DW_PS_V32_GUARD_APPLIED map=boss1 surface=7232 material=textures/metal_misc/ametal_m03dm capture=(-2764 -219 -24) scope=ONE_ORDINARY_POINT_SHADOW_FACE worldVisible=1 otherLightCasting=1 stage11Unchanged=1`
- `Wrote screenshots/DW_PS_V32_BOSS1_02_GUARD_ON.jpg`
- `DW_PS_V32_PHASE_02_DONE guard_on_source_local_7232`
- The cvar change was latched and renderer re-initialized again.
- `Wrote screenshots/DW_PS_V32_BOSS1_03_RESTORED.jpg`
- `DW_PS_V32_AUTOTEST_DONE fixture_guard_off` and `Dumped console text`

## Visual A/B/A result

All screenshots were taken at the same apparent camera, without visible scene movement.

1. Baseline: giant solid dark polygon behind the lamp head is visible.
2. Guard ON: the giant polygon disappears; the lamp, narrow frame/bracket and stand shadows remain.
3. Restored: the same giant solid polygon returns.

In raw JPEG RGB comparisons with >15/255 maximum-channel threshold:
- 01↔02 excluding top 75 HUD/telemetry rows: **34,689 changed pixels**, bounding rectangle **x445–741, y75–334**.
- 01↔03 excluding top 75 rows: **0 changed pixels** above threshold.
- 01↔02 for y420–767 (stand/base area): **0 changed pixels** above threshold.
- The small FPS labels are not comparable performance measurements.

**Result: GPU_VISUAL_A_B_A_PASS for the exact Boss1 spotlight scenario.**

## Scoped implementation and limitations

V3.2's optional default-OFF `r_dwPointV32FixtureGuard` skips only world surface 7232 in an ordinary point-shadow capture matching `(-2764,-219,-24)`, `boss1`, BSP surface counts, material name and bounds. It leaves the visible scene and normal other-light caster path untouched by code construction. This is a source-scoped shadow-map omission, not mesh deletion.

What is **proven**: the selective removal eliminates the oversized projected polygon in this reproducible Boss1 scene and leaves the intended holder/base shadow geometry visible.

What is **not proven**: physical reason for that projection, correctness in all camera positions, other maps (Factory/Crypt1), all lighting profiles, or impact on memory/performance/other shaders under arbitrary conditions. It is not an accepted generic solution. The engine's log statements about "worldVisible" and "otherLightCasting" describe code scope; they do not substitute for multi-light GPU verification.

**Do not copy numeric surface ID 7232 or hardcoded coordinates into general production policy.** The next scalable approach should classify source-attached/near-emitter fixture geometry by robust source association, classify true independent occluders separately, and validate physical source origin and shadow projection. Preserve full Stage11 Caster/Receiver coverage for other lights and receiver paths; no global class/material removal. Maintain Sun/CSM, Fire/Tesla, SSGI and full 3-slot budget. Keep original Clean Production **#41019985033 unchanged** until cross-map GPU acceptance.
