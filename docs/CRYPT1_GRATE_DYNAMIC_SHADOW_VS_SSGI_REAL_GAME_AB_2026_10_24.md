# Crypt1 grate shadow A/B — actual RTCW TestLab results (2026-10-24)

## Reproducible provenance
- Base: **DarkWolf Rend2 FourWeek Master SourceDefaultsON + accepted LUT V05**. Reference source commit `2ef7ad6bd9dbe8e03b561b4be6279953e51ceee1` plus isolated V05 patch `integration/lut-v05/LUT_V05_ATLAS_BYPASS_ONLY.patch`.
- Workflow: `.github/workflows/RC4_LUT_V05_CRYPT1_GRATE_SHADOW_AB.yml`, GitHub Actions [#40110824975](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40110824975) **SUCCESS**, head commit `3181e06e7be5e0436010c42bd736dc52fe1bd12a`.
- Artifact `RC4-V05-Crypt1-Spawn-Grate-RealGame-AB-Screenshots`, artifact ID `12566986364`, external GitHub Actions artifact SHA256 `f7cdb29f3a450f33199bd7d3c78461881b8f68fd48da8987454855ee94551023`.
- Exact renderer source SHA inventory compared before/after game-only camera instrumentation; **renderer unchanged**. Native Linux executable rebuilt from that renderer source; commercial retail RTCW `crypt1.bsp` loaded only on authorized private GitHub runner; NO licensed retail PK3 uploaded as evidence.
- Renderer runtime: actual RTCW crypt1 map under xvfb + Mesa llvmpipe software, not Windows/NVIDIA GPU performance validation.
- Camera: from Crypt1 initial player spawn, eye `(-192.000,1664.000,512.125)`, yaw rotated by +180 degrees; two fixed view pitches 18 and 33 deg, looking at the correct large spike grate and floor. Same eye and forward vector across each within-pitch A/B.
- Settings: SSGI 1, CAS 0.55, procedural LUT V05 0.80, volumetrics enabled, Bloom v2, MSAA 4x, `r_dlightShadowStrength 0.88` (control).
- Real screenshot proof: **10 / 10 images captured**, runtime exit 0, `PROOF_READY` and `CRYPT1_GRATE_AB_COMPLETE` present, all CVar values logged and verified. Baseline restored **pixel-identical** to first shot (zero changed pixels) at both viewpoints.

## Tested toggles and measured 1280x720 frame differences

Each viewpoint: baseline (0.88, SSGI1) -> only shadow strength0 (SSGI1) -> only SSGI0 (shadow0.88) -> both off -> baseline restored.

| Pitch | Change | Changed pixels | Mean abs RGB delta | Ground region mean delta |
|---|---|---:|---:|---:|
| 18° | r_dlightShadowStrength 0 only | 23218 | 0.04612 | 0.09174 |
| 18° | r_ssgi 0 only | 245276 | 0.44536 | 0.70607 |
| 18° | both zero | 252450 | 0.47980 | 0.77432 |
| 18° | restored | 0 | 0.00000 | 0.00000 |
| 33° | r_dlightShadowStrength 0 only | 43706 | 0.52388 | 0.79260 |
| 33° | r_ssgi 0 only | 354083 | 0.58740 | 1.00685 |
| 33° | both zero | 367558 | 1.07102 | 1.73183 |
| 33° | restored | 0 | 0.00000 | 0.00000 |

## Visual inspection conclusions

- Confirmed matching physical grate from user's screenshot, at the rear of Crypt1 spawn.
- Disabling dynamic shadow strength produces localized changes around the grate/ground but **does not eliminate large triangular/staircase silhouettes**.
- Disabling SSGI produces broader darkening / changes across architecture and floor, but **does not eliminate those silhouettes or their jagged contour**.
- Turning off both also leaves the spike/bar silhouette essentially intact. Therefore **neither of the requested commands solves the original perceived jagged-grate regression in this Linux Mesa A/B**.
- This does **NOT** conclusively identify the root cause. Next isolated diagnosis should distinguish mesh geometry/triangle outlines, alpha-tested cutout/A2C/MSAA coverage, shadow caster rasterization, and pixel resolution/FBO. Do not deploy production changes or disable SSGI globally based solely on this test.

## Evidence files (in artifact)
- `CRYPT1_GRATE_FIVE_WAY_AB_CONTACT_SHEET.png`: 5 variants x 2 camera angles.
- `CRYPT1_GRATE_GROUND_DETAIL_PITCH18.png`, `CRYPT1_GRATE_GROUND_DETAIL_PITCH33.png`: unaltered crop comparisons of floor.
- `crypt1_grate_pitch18_*.png`, `crypt1_grate_pitch33_*.png`: full-resolution 1280x720 actual game screenshots.
- `CRYPT1_GRATE_CAPTURE_REPORT.json`, `CRYPT1_GRATE_PIXEL_DIFF_REPORT.json`: camera, CVar, numerical evidence.
- Console stdout/source build/provenance logs.
- Artifact lifecycle subject to GitHub Actions 90-day retention; source workflow and this report remain as durable Git evidence, PNG should be backed up separately before expiration.

## Explicit result boundary
CI SUCCESS means the **Linux Mesa real-game A/B executed correctly**, not Windows RTX 3060 Ti GPU acceptance. This test answers the two user-requested command toggles at the correct Crypt1 grate; it does NOT establish a production rendering fix.
