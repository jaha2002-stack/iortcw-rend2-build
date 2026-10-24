# Crypt1 close-up grate — verified real-game A/B evidence

Date: 2026-10-24. Source: pinned FourWeek Master SourceDefaultsON + user-accepted LUT V05; **no source changes to renderer**.

## Completed real gameplay test

- [Run #40114380523](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40114380523): **SUCCESS**.
- Artifact #12568158252, `RC4-V05-Crypt1-Grate-NearContact-CAS-A2C-SSGI-Shadow-Images`, 20,816,856 bytes, artifact SHA256 `b6ac899c816a4bed200d3ae69aa2576619b12d070f3f6e84fc5fdda2c624972d`. 28/28 real PNG game framebuffer screenshots, 4 collision-safe cameras, 7 modes each; `CRYPT1_GRATE_CLOSEUP_REPORT.json`, `CRYPT1_GRATE_CLOSEUP_PIXEL_DIFF.json` contain exact cvars and measures.
- Run created 2026-10-24 17:03:28Z, completed 2026-10-24 17:24:12Z.
- Test environment: protected original RTCW Crypt1 BSP, Linux Mesa llvmpipe + Xvfb, 1280x720, HDR/Bloom v2/SSGI/CAS/LUT V05/MSAA4 enabled. **Not** NVIDIA RTX 3060Ti Windows runtime. The DLL from user's Windows installation is not running in Linux; the source is matched.
- Actual spawn origin camera `(-192,1664,512.125)` yaw 180 toward gate. Four collision-validated near-grid viewpoints at X=-240 (48 units) and X=-264 (72 units), pitch 28 and 42 degrees. BSP solid starts near X=-276.
- Repeated baseline bitwise-identical, no camera drift (28/28), CVar snapshots validated (28/28). Game returned exit 0. Unique V05 GLSL runtime marker present.
- A/B seven variants: baseline; `r_dlightShadowStrength 0`; `r_ssgi 0`; `r_dwCasStrength 0`; `r_dwA2C 0`; `r_lightmap 1` debug visualization; baseline restored.

## Pixel-diff summary (per 1280x720 screenshot)

| View (distance, pitch) | Dynamic shadows OFF (% changed) | SSGI OFF | CAS OFF | A2C OFF | Repeated baseline |
|---|---:|---:|---:|---:|---:|
| 48u, 28° | 10.597% | 9.385% | 6.451% | **0.000%** | **0.000%** |
| 48u, 42° | 14.959% | 9.859% | 5.793% | **0.000%** | **0.000%** |
| 72u, 28° | 15.899% | 1.812% | 2.118% | **0.000%** | **0.000%** |
| 72u, 42° | 20.025% | 2.252% | 2.693% | **0.000%** | **0.000%** |

*Changed-pixel ratio is not a measure of artifact quality. Pixel magnitude is recorded separately in the JSON; dynamic shadow strength 0 at 72u/pitch42 mean absolute per-channel delta = 1.34173/255, and at 48u/pitch42 = 1.7491/255. The `r_lightmap 1` frame is an intentionally altered debug visualization of baked lighting, NOT a directly comparable "improved graphics" setting.*

## Visual interpretation of full close-up images

- **The jagged, stair-shaped dark edges on the floor persist with dynamic shadows disabled**, even where the model's dynamic shading changes strongly.
- **The same floor edge shapes persist with SSGI, CAS, and A2C individually disabled**. CAS changes mild local contrast but not the steps. **A2C 0 produces pixel-identical images** for each view: this grate's visible lighting/geometry does not depend on alpha-to-coverage.
- The pointy diagonal **spikes themselves are real polygonal mesh** in `crypt1.bsp`; separate from the jagged projected dark bands on the floor. Do not conflate a real triangular fence with a shadowing artifact.
- The `r_lightmap 1` visualization displays authored lightmap illumination on the ground and obscures original material/lighting composition. It does not directly establish which exact texels cause the floor shadow steps.
- **Strongest remaining hypothesis for floor stair-steps** is low-resolution **static/baked lightmap shadowing**, or another non-dlight shadow/vertex-light path. NOT yet mathematically proven pixel-by-pixel to be solely from baked lightmap.
- Reviewed original Bloom v2 source tar versus final V05 tree: `SP/code/rend2/tr_bsp.c` **unchanged byte-for-byte**, and original lightmap loader uses `DEFAULT_LIGHTMAP_SIZE=128` and creates texture with linear filtering. Raising `r_shadowMapSize` or `r_dlightShadowMapSize` cannot increase baked 128x128 lightmap source resolution.

## What NOT to do

- Do not replace high-quality dynamic shadow paths, delete SSGI or CAS globally, or change A2C based on this bug. Such fixes would cause performance/visual regressions elsewhere and did not remove the steps.
- Do not claim the floor's exact shadow is confirmed baked until a matched old RC4 vs V05 visual A/B plus isolated static-light contribution test is done.
- Do not overwrite canonical FourWeek Master, user-validated V05 renderer DLL, or the unpublished Draft Release.

## Next evidence-based diagnostic step

- Compare **historical visually accepted RC4 Bloom v2 + CSM Guard** against current V05 at these identical camera coordinates in the same Linux Mesa TestLab to detect whether the step-contour appearance is an older RTCW lightmap limitation or newly introduced by an integration.
- If already present in older source, perform *isolated* optional baked-lightmap footprint/edge smoothing in Crypt1 as a TestLab-only experiment, not a global production change; evaluate shadow-edge regularity and lightmap detail/blur on Factory/Escape1/Assault before merging.

### Other proofs
- [Run #40114121072](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40114121072): BSP mesh/near-grate collision metadata.
- [Run #40114479924](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40114479924): material `textures/broken_castle/wall_c21m` is ordinary opaque JPEG, not alpha-masked/alpha-shadow. 179 BSP surfaces, 404 triangulated faces in map.
