# Crypt1 — grate behind initial spawn: shadow-strength vs SSGI A/B (2026-10-24)

**Result:** Real map screenshot capture SUCCESS, GitHub Actions run **40110824975**, job 120921987596, artifact **12566986364** (`RC4-V05-Crypt1-Spawn-Grate-RealGame-AB-Screenshots`), GitHub outer artifact SHA256 `f7cdb29f3a450f33199bd7d3c78461881b8f68fd48da8987454855ee94551023`, size 10,919,690 bytes, expiry 2027-01-22.

**Question:** Does either `r_dlightShadowStrength 0` or `r_ssgi 0` remove the apparent jagged/grate-shadow artifacts reported by the user on the **Crypt1 grate immediately behind initial player spawn**?

## Baseline identity and runtime
- Exact FourWeek Master SourceDefaultsON plus **user-verified LUT V05 procedural** source reconstructed and hash-checked using `integration/lut-v05/ci_lut_v05_candidate.sh`; Win64 source build PASS, native Linux build PASS.
- `DARKWOLF_LUT_V05_PROCEDURAL_ACTIVE atlasSampling=0 builtinDwfinal=1 mode=1 strength=0.80` printed by renderer.
- Protected, legally obtained original RTCW game assets were loaded temporarily on GitHub runner (not stored in public artifacts).
- Linux `llvmpipe`, Mesa OpenGL 4.5, virtual Xvfb, **not** an RTX3060Ti/Windows GPU reproduction.
- Isolated proof camera/game helpers alter **no renderer source files**. Camera at the actual spawn origin; yaw turned exactly +180 degrees; pitches 18° and 33°. Final eye: `(-192,1664,512.125)`. All A/B images at each pitch have matching camera origin and forward vector, screenshot 1280x720, MSAA 4.
- Real map `crypt1`, `PROOF_READY` true, `CRYPT1_GRATE_AB_COMPLETE` true, process exit 0; 10/10 full PNG images captured. Control repeated at end is pixel-identical: 0 changed pixels for both pitches.

## 5 settings compared (same camera for each pitch)

1. Baseline: `r_dlightShadowStrength=0.88`, `r_ssgi=1`.
2. `r_dlightShadowStrength=0`, `r_ssgi=1`.
3. `r_dlightShadowStrength=0.88`, `r_ssgi=0`.
4. `r_dlightShadowStrength=0`, `r_ssgi=0`.
5. Baseline restored: `0.88`, `1`.

All CVar values directly proven by `PROOF_CVAR` logs. Other expected effects remained enabled: Bloom v2, forceSun, LUT V05 0.80, CAS 0.55, 4x MSAA, volumetrics etc.

## Quantitative image differences relative to the baseline (full 1280x720 frame)

| Pitch | Setting | Changed pixels | Mean absolute RGB change (0–255) | Max channel delta |
|:--|:--|--:|--:|--:|
|18°| Dynamic shadow strength 0 | 23,218 (2.52%) | 0.046 | 51 |
|18°| SSGI 0 | 245,276 (26.61%) | 0.445 | 107 |
|18°| Both 0 | 252,450 (27.39%) | 0.480 | 107 |
|18°| Baseline restored | **0 (0%)** | **0** | 0 |
|33°| Dynamic shadow strength 0 | 43,706 (4.74%) | 0.524 | 79 |
|33°| SSGI 0 | 354,083 (38.42%) | 0.587 | 17 |
|33°| Both 0 | 367,558 (39.88%) | 1.071 | 79 |
|33°| Baseline restored | **0 (0%)** | **0** | 0 |

## Visual review and interpretation
- Disabling dynamic shadow strength visibly alters some shadows (notably the player's foreground shadow at pitch33), proving command was effective. **The spiked triangular shapes and stair-stepped contours around/on the grate remain.**
- Disabling SSGI changes diffuse illumination over a much larger number of pixels (mostly low-amplitude), but the grate's triangular silhouettes and stepped outlines **also remain**.
- **Neither single CVar provides a proven fix to the reported jagged edges** at these views. More shadow-map resolution did not help in the user's prior local test.
- Potential remaining causes: actual sharp low-poly grate geometry, alpha-test cutout edges and antialiasing, baked lightmap/shadow geometry or another shadow/depth path. Root cause **not determined**; do not declare a shader/graphics defect fixed.
- Caveat: user's supplied screenshot was taken very close to the grate, while lab follows exact **spawn + 180-degree turn with no forward movement**. The perspective/distance differs. For a definitive near-contact reproduction, use BSP collision-validated forward positions and screenshot the original floor area; do not put camera through bars/walls.
- Run is a successful visual **diagnostic** only, not a Windows RTX GPU quality acceptance and not a changed Clean Release.

## Evidence names inside artifact
- `CRYPT1_GRATE_FIVE_WAY_AB_CONTACT_SHEET.png`
- `CRYPT1_GRATE_GROUND_DETAIL_PITCH18.png`
- `CRYPT1_GRATE_GROUND_DETAIL_PITCH33.png`
- `crypt1_grate_pitch18_{baseline,no_dlight_shadow,no_ssgi,both_disabled,baseline_restored}.png`
- `crypt1_grate_pitch33_{baseline,no_dlight_shadow,no_ssgi,both_disabled,baseline_restored}.png`
- `CRYPT1_GRATE_PIXEL_DIFF_REPORT.json`, `CRYPT1_GRATE_CAPTURE_REPORT.json`, `crypt1-console-0.log`, `source-reconstruction-and-win64-build.log`.

**Do not alter existing accepted FourWeek Master or LUT V05 release on this evidence alone.**
