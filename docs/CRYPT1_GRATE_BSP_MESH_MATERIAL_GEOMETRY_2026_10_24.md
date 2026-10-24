# Crypt1 gate / grate: BSP triangulation and shadow diagnosis — 2026-10-24

## Runtime baseline and user problem
- User's game frame at the grate immediately behind the Crypt1 starting spawn contains large angular spikes and stair-stepped contours; the user describes them as pixelated shadows.
- In actual GitHub Linux/Mesa runtime on run [40110824975](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40110824975), BOTH `r_dlightShadowStrength 0` and `r_ssgi 0` changed image contributions but neither removed the gate outline triangles. This is not enough to prove exact cause, due to camera distance.
- User reports increasing `r_dlightShadowMapSize` and `r_shadowMapSize` to 4096 has no visible effect on the complained-about contours.

## Verified local map geometry from protected original retail Crypt1 BSP
- [Run 40114121072](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40114121072) = **SUCCESS**, artifact `Crypt1-Grate-NearSpawn-BSP-Geometry-Inventory` ID `12567294294`, outer ZIP SHA256 `2c2e5f3479f824034310c4331ac0bc396a57299c9b43314bae891078c2209354`.
- Actual retail map is `pak0.pk3/maps/crypt1.bsp`; scanned **14,103 BSP draw surfaces**, **70,481 BSP vertices**, **1,223 entities**, not decompiled guesses.
- Starting camera eye `(-192.0, 1664.0, 512.125)` faces **yaw 180°** to turn toward grate. Solid BSP collision is encountered around X `-276` (ray hit material `textures/broken_castle/wall_c21m`). Collision-validated near-contact cameras: eye X `-240`, `-252`, `-264` at same Y/Z. TestLab must not position camera beyond `-276` or inside wall.
- The grate region around X ≈ `-280`, Y ≈ `1624–1704`, Z ≈ `462–582` contains **many authored triangular BSP surfaces** under material `textures/broken_castle/wall_c21m`, often 3-vertex/1-triangle faces, with **lightmap index 14**. This is strong evidence for true angular mesh outlines, rather than a purely postprocess-generated shadow pattern.
- The nearby floor `textures/crypt/crypt_d01_step` is a different material/lightmap region. Do not attribute all black polygons to shadow projection without exact screen-space material comparison.

## Verified authored material / alpha behavior
- [Run 40114479924](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40114479924) = **SUCCESS**, artifact `Crypt1-Grate-Material-Alpha-and-BSP-Shader-Audit` ID `12566969514`, outer digest `151649e2d4ef44af78ce4cddc7e4ceb675936315835571cbe81143ed26c65254`.
- The `textures/broken_castle/wall_c21m` material appears on **179 BSP draw surfaces** (404 triangles) across Crypt1, with `surfaceFlags=0`, `contentFlags=1`, a `.jpg` texture in `pak0.pk3` and **no shader-script override** in the licensed assets.
- No alpha-tested, blended, transparent, alpha-shadow or alpha-to-coverage shader stage was found for this material. CAS/A2C texture-edge interaction is unlikely to change the geometry silhouette; A2C in source only applies to `GLS_ATEST_GE_80` passes.
- These BSP source-level numbers do not prove the original screenshot's exact pixel belongs to a specific polygon; for that, capture camera-aligned close-up images and compare to shader-affected photos.

## Next real-game close-range capture (not yet validated in this document)
- Run workflow `.github/workflows/RC4_LUT_V05_CRYPT1_GRATE_CLOSEUP_AB.yml` based on pinned **FourWeek Master SourceDefaultsON + accepted LUT V05** with renderer source unchanged.
- Candidate front-of-grate views: X=-240 and -264, Y=1664, eye Z=512.125, yaw 180°, downward pitch 28° and 42°.
- Record A/B `r_dlightShadowStrength`, `r_ssgi`, `r_dwCasStrength`, `r_dwA2C`, `r_lightmap`, plus restored baseline. Verify actual logged CVars and matching camera per view. Native Linux Mesa reproductions do not prove Windows RTX runtime.
- Do not modify the verified original FourWeek Master, LUT V05 DLL or published Draft Release on this evidence alone.

**Status:** Real source geometry and material attribution verified; user-observed polygon/shadow cause pending final camera-aligned near-contact A/B review.
