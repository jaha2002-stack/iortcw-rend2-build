# Crypt1 close-up grate — 28-frame verified A/B, run 40114380523

**Date:** 2026-10-24  
**Status:** native real-map A/B test **SUCCESS**; user Windows GPU/subjective quality acceptance still pending.  
**Run:** https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40114380523  
**Artifact:** `RC4-V05-Crypt1-Grate-NearContact-CAS-A2C-SSGI-Shadow-Images`, ID `12568158252`, 20,816,856 bytes, SHA256 (artifact ZIP) `b6ac899c816a4bed200d3ae69aa2576619b12d070f3f6e84fc5fdda2c624972d`; 45 artifact files including **28 PNG captures**, 4 six/seven-way contact sheets, proof logs and numeric evidence.

## Provenance and scenario

- Original FourWeek Master SourceDefaultsON + the user's on-PC visually accepted LUT V05 code. CSM, Bloom v2, Fire/Tesla containment, Texture/Material Fidelity, volumetrics, CAS/A2C and SSGI present.
- Exact pinned V05 source reconstructed and verified, Win64 source compile passed, separate Linux/Mesa renderer built for pixel capture. **Renderer source unchanged by TestLab instrumentation**.
- Protected original retail `maps/crypt1.bsp`, actual game engine/GL framebuffer, `llvmpipe` with MSAA 4, 1280x720. **Not** NVIDIA RTX 3060 Ti on Windows.
- Camera oriented toward gate behind spawn at yaw 180°. Two collision-validated positions: X=-240 (48 units forward from spawn) and X=-264 (72 units), Y=1664, Z=512.125; pitches 28° and 42°.
- Seven variants per view: baseline (`r_dlightShadowStrength=0.88 r_ssgi=1 r_dwCasStrength=0.55 r_dwA2C=1 r_lightmap=0`); dynamic shadow strength 0; SSGI 0; CAS strength 0; A2C 0; lightmap diagnostic mode `r_lightmap=1`; restored baseline.
- Runtime exit 0; `PROOF_READY` true, `CRYPT1_GRATE_CLOSEUP_AB_COMPLETE` true, 28/28 captures, per-screenshot actual CVar values logged and verified, camera origin/direction identical within each view. Restored baseline **pixel-identical** to initial baseline across all four poses.

## Numerical pixel differences compared with original (1280×720, 921,600 pixels)

The last column is global mean absolute difference per 8-bit RGB channel, **not** an objective perceptual quality score.

| Camera | Effect disabled | Changed pixels | % of full frame | Global mean absolute RGB delta |
|---|---|---:|---:|---:|
| X=-240, pitch 28 | dynamic shadow strength | 97,658 | 10.597% | 0.532 |
| X=-240, pitch 28 | SSGI | 86,492 | 9.385% | 0.081 |
| X=-240, pitch 28 | CAS strength | 59,453 | 6.451% | 0.076 |
| X=-240, pitch 28 | A2C | **0** | **0%** | 0 |
| X=-240, pitch 42 | dynamic shadow strength | 137,861 | 14.959% | 1.749 |
| X=-240, pitch 42 | SSGI | 90,856 | 9.859% | 0.095 |
| X=-240, pitch 42 | CAS strength | 53,390 | 5.793% | 0.067 |
| X=-240, pitch 42 | A2C | **0** | **0%** | 0 |
| X=-264, pitch 28 | dynamic shadow strength | 146,525 | 15.899% | 1.023 |
| X=-264, pitch 28 | SSGI | 16,696 | 1.812% | 0.011 |
| X=-264, pitch 28 | CAS strength | 19,517 | 2.118% | 0.020 |
| X=-264, pitch 28 | A2C | **0** | **0%** | 0 |
| X=-264, pitch 42 | dynamic shadow strength | 184,548 | 20.025% | 1.342 |
| X=-264, pitch 42 | SSGI | 20,750 | 2.252% | 0.015 |
| X=-264, pitch 42 | CAS strength | 24,820 | 2.693% | 0.026 |
| X=-264, pitch 42 | A2C | **0** | **0%** | 0 |
| ALL | restored baseline | **0** in all 4 views | **0%** | 0 |

- Lightmap-only visualization changed **100%** of pixels in all four views by design; that comparison is a different rendering mode, not a direct on/off for a single physical shadow contribution.
- The shadow-strength toggle has visible lighting effects in the floor region, but jagged edge silhouettes and the large triangular spikes **remain**. SSGI and CAS off also leave the authored angular outlines; A2C has no pixel difference for these views.
- Both CAS and dynamic shadows can affect edge contrast or local brightness; the numbers do not establish that either caused the geometry contour. A2C 0 having no visible effect is consistent with the gate's opaque material and code gating A2C to alpha-tested geometry.
- **No production fix established.** This test cannot honestly prove the exact user Windows pixel aliasing regressions are cured. Escalating `r_dlightShadowMapSize` and `r_shadowMapSize` on the user's PC earlier had no visible effect.

## Independent original map and material corroboration

- BSP geometry run [40114121072](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40114121072) maps near-bar X≈-280 original 3D triangle surfaces using `textures/broken_castle/wall_c21m`, whose gate-adjacent triangles use original baked lightmap index 14.
- Shader/material audit run [40114479924](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40114479924) found this material opaque, based on a JPG texture, with no `alphaFunc`/blend shader override in the protected original assets.
- In `r_lightmap 1` full-frame diagnostic screenshot, the same angular bar/spike silhouettes remain; the surface color changes dramatically as lightmap is displayed. Thus angular geometry and/or baked shadowing explain significant appearance; the precise mixture of original triangulation and aliasing in user's earlier screenshot remains to be isolated.

## Decision and next experiment

1. **Do not modify** verified FourWeek Master + LUT V05, CSM or Fire/Tesla. Disabling SSGI/CAS or scaling up dynamic-shadow maps globally has no established fix for the observed gate outline.
2. To test user's observation that an **earlier renderer looked smoother**, capture **the same four close cameras with prior accepted RC4 Bloom v2 + CSM Guard and current V05**, same game resources, resolution, gamma and shadow settings. This is a necessary old/new regression test before treating an original map's authored sharp silhouettes as a new engine bug.
3. If earlier render genuinely smooths gate shadows but both use identical mesh, compare original shadow/lightmap filtering and final image AA/resolving paths (CAS/Texture Material Fidelity), not just shadow-map texture resolution.
4. Preserve per-camera original RGB PNG and metadata; no user GPU proof until their PC later becomes available.
