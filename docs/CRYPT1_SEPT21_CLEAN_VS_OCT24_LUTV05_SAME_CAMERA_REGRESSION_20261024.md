# Crypt1 grate: Sep 18 Clean Production (as of Sep 21) vs Oct 24 FourWeek + LUT V05

**Comparison CI:** [Run 40117844454](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40117844454), SUCCESS, commit `eb7b72afc4fa3ded4ad5d4d3e10efbb0a89ab541`.  
**Artifact:** [12570018333](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40117844454/artifacts/12570018333), `Crypt1-Sep21-CleanProduction-vs-Oct24-FourWeek-LUTV05-RealGame-Comparison`, 34,785,724 bytes, SHA256 of outer artifact ZIP `c2b81dafacab74b8292853c891ce01819503d93073b0e374b6fe0652c06c11b0`. Preserve a local copy because Actions artifacts can expire.

## Exact historical release selected

No September 21 Clean Production workflow run found in the recorded Sep 19–22 Actions history. The **last explicitly Clean Production build no later than September 21** was [September 18 Run 35361762179](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/35361762179), Clean Production v1 (not Sep 20 Tesla/table-shadow experiments, not Sep 22 Unified Production V1). Historical artifact ID `10555091293`, outer SHA256 `6cd0e66d9e8e68ac4499a2e41b9ab0286b40942e14106b4b6ddc92ba38e3abb1`.

The September workflow's exact original WIN64 DLL, ZIP checksum, 67-file cumulative source patch and pinned upstream RTCW commit `438e7d413b5f7277187c35b032eb0ef9093ae778` were checked; source postimage was reconstructed, instrumented with **game/cgame screenshot controls only** (renderer source remained unchanged), and compiled as a native Linux/Mesa TestLab build.

The October comparator is the previously tested FourWeek Master SourceDefaultsON + user-accepted LUT V05 renderer, real-game [run 40114380523](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40114380523) artifact `12568158252`. Do not confuse this with the later Direct-EXE Clean plus new Tram fog guard.

## Method and quality gates

- Both source versions used the same original licensed RTCW Crypt1 BSP from protected TestAssets, Linux Mesa llvmpipe 4.5, OpenGL actual game renderer, 1280×720 screenshots.
- Four collision-validated identical camera poses behind initial spawn: X=-240 and -264, Y=1664, eye Z=512.125, yaw=180°, pitch=28°/42°. Matched actual eye and forward vectors via `PROOF_VIEW` console logs.
- September run captured all **28 of 28** screenshots; `CRYPT1_GRATE_REAL_CLOSEUP_AB_PASS 28 identical_repeat=True` in CI logs. October had earlier passed the same 28 captures, same pose. Camera alignment and 16 cross-version image pairs passed.
- In each version, compared normal baseline `r_dlightShadowStrength=.88, r_ssgi=1`, shadow-strength 0, SSGI 0, CAS strength 0, A2C 0, `r_lightmap=1` diagnostic and baseline restored. At each same-version pose, restored baseline was pixel-identical.
- **Caveat:** These are DIFFERENT graphics feature generations. The Sept renderer does not contain the Oct LUT V05/CAS pipeline, and both base lighting and tone handling differ. Pixel differences alone do not establish the exact culprit or perceptual quality. Windows/NVIDIA RTX 3060Ti GPU was not tested by CI.

## Central finding: the October rendering degrades the old shadow/lightmap appearance

On every close-up camera inspected, the **September 18 Clean Production** displays brighter, smoother gradations of the grate's shadow on floor and nearby surfaces. The October **FourWeek Master + LUT V05** displays materially darker illumination and more pronounced large **stair-step/rectangular boundaries**, including around the star-shaped bars on the ground.

This establishes that the present rendering appearance is **not merely explained by the mesh's original triangles**. The same original Crypt1 BSP geometry is rendered by both versions, yet image-space shadow/lighting presentation differs significantly.

Most discriminating image: `comparison/grate_near72_pitch42_SEPT21_CLEAN_VS_V05_GATE_GROUND_DETAIL.png`. The four original-exposure baseline/no-shadow/no-SSGI sheets are `comparison/grate_near{48,72}_pitch{28,42}_SEPT21_CLEAN_VS_V05_ORIGINAL_RGB.png`. The ground detail sheets contain original-exposure top row and equally brightness-adjusted ×2.25 copies in the second row, clearly labeled.

### Lightmap diagnostic difference

`r_lightmap 1` at identical X=-264/pitch42 shows a visibly smooth/interpolated Sept floor but **repeated horizontal banding** and geometric stair-stepping on the Oct diagnostic view. IMPORTANT: this mode still passes through the current renderer's other stages/postprocessing; it does **not by itself prove** the lightmap texture upload or bilinear sampler is the culprit. It makes lightmap/lightall sampling or **interaction with postprocessing** a high-priority candidate.

### Exact cross-version numeric metrics

Different feature profiles mean changed-pixel percentages should not be read as antialiasing quality:

| Camera | Baseline mean absolute RGB delta across full frame | Gate/floor ROI mean absolute RGB delta | ROI pixels > 4 RGB delta |
|---|---:|---:|---:|
| X=-240 pitch28 | 11.0326 | 12.6352 | 93.837% |
| X=-240 pitch42 | 13.9275 | 14.1802 | 91.558% |
| X=-264 pitch28 | 9.1773 | 11.4505 | 83.212% |
| X=-264 pitch42 | 10.0455 | 13.1154 | 85.026% |

For the **no_dynamic_shadow** images, same gate/floor ROI mean absolute channel differences are 18.291, 19.574, 16.661, and 21.054 respectively. Modern staircase contours **persist even with** `r_dlightShadowStrength 0`; thus that one setting does not control the entire failure. Same persists with `r_ssgi 0`; CAS and A2C toggles in October did not remove it in prior run 40114380523 (A2C affected 0 screenshot pixels).

Prior static BSP audit [40114121072](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40114121072) confirmed real triangular geometry of star-grate material `textures/broken_castle/wall_c21m`. Material audit [40114479924](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40114479924) confirmed this material is opaque JPG, not alpha-test cutout. **Both are true:** original mesh is angular AND Oct rendering introduces worsened shadow/lightmap-looking staircase appearance.

## Decision and next precise experiment

**Regression in observed grate-shadow/lighting quality confirmed under real-game Mesa A/B. Exact code change NOT YET isolated.** Do not accept a global shadow-resolution increase or remove historical FX based on these results. Leave accepted production binaries and historical release unchanged.

Next source-backed fail-closed **Oct-only same-camera controlled matrix** at X=-240/-264:
1. `r_lightmap 1` baseline, `r_lightmap 1;r_ssgi 0`, `r_lightmap 1;r_postProcess 0` to distinguish lightmap texture content from postprocessing; compare horizontal stripes.
2. `r_dwTextureFidelity 0`, `r_dwMaterialFidelity 0` (only if implemented live in source; preserve others); separately verify whether these affect world/lightmap textures.
3. `r_mergeLightmaps 0` requires separate renderer restart / fresh process with the exact same view; diagnose packed/merged lightmap atlas sampling, not global shipping recommendation.
4. If none explain, binary search specific source patches/changelog between verified Sep source postimage and Oct V05 to narrow CSM, lightmap staging, FBO resolve, HDR/tone/SSGI interactions.
5. Propose a guarded fix and only promote after same-camera A/B, all 4 Crypt1 views plus existing Factory/Escape1/Assault GPU regression, no effect removal.

**No public GitHub release should be published.**

## How to reproduce

- Workflow `.github/workflows/CRYPT1_SEP21_CLEAN_VS_V05_REALGAME_AB.yml` and side-by-side script `testlab/scripts/crypt1_compare_sep21_clean_vs_lutv05.py` in branch `rend2-crypt1-sep21-vs-v05-realgame-20261024`.
- Artifact ZIP contains 28 historical raw RGB screenshots, historical run stdout, logs, camera/CVar proofs, 4 x 3-view cross-release montage PNGs, 4 enhanced-visibility floor-detail montage PNGs, and `SEPT21_CLEAN_VS_LUTV05_CRYPT1_CROSS_RELEASE_COMPARISON.json` with 16 numeric pairs.

