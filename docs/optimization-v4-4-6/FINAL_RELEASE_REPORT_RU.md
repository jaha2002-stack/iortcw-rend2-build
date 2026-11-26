# FINAL RELEASE REPORT (candidate) — DarkWolf ioRTCW Rend2 v4.4.6

## Provenance and deliverables

- Authoritative GitHub run: [38619534668](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/38619534668), COMPLETED/SUCCESS, 2026-10-14 20:48:20 UTC.
- Working branch: `rend2-v4-4-6-clean-optimization`; build commit: `9df5ac17dd687437b4c2de39ea2d39b59fa8c179`; PR [#4](https://github.com/jaha2002-stack/iortcw-rend2-build/pull/4) stays DRAFT, no merge.
- Pinned upstream `438e7d413b5f7277187c35b032eb0ef9093ae778`, component-correct v4.4.6 baseline tree `a9afb5a60e26eb112bc5a6af4bb52f4ed08685f1`.
- Baseline run 37266797451, artifact 11326603946, outer SHA256 `51a49587a0c4e7ad9c7ad651d5a4fcc34c7774d89ed9366dd659ed7efa97154b`.
- Release candidate artifact 11928290259; inner ZIP `DarkWolf-ioRTCW-Rend2-v4.4.6-Optimized-Clean-Candidate-Win64-SP.zip` SHA256 `d005ca823debf7b5bfab025a11d360752ed1033c258fc9d22797e5291306014f`; outer artifact SHA256 `08f6b189daa25a54ae18b91c84c5b4905204844b1766270b9a50e9369ab98342`.
- Separate validation artifact 11928055679; GitHub artifact SHA256 `9baa2ca7cfc3b4866f7136ca8356367284cf8076c0163cc0b9ecb24b9d17826a`.

## Exact optimization register

| Area / source | Why / design | Evidence, acceptance and risk |
|---|---|---|
| `tr_scene.c`, StaticPromote light emission, final SHA256 `9425f52eb3e5e08662a907b33af9efc7751704b5bb59039f70cfaff9c91b6647` | Remove formatting/append work for dead report output; keep actual emitted lights/forced tags and lazy loading unchanged. | 10,000 extracted-C cases bitwise equal; 9,411 dead format calls eliminated in test. PASS as a source-level reduction, FPS NOT_MEASURED; light state coupling remains a visual review risk. |
| `tr_main.c`, physical shadow grouping, final SHA256 `ab5bb21b7a0b88db39c264ec1c2bc95806a6d50fcc3cedfb6f9c0347cbce2b25` | Invocation-scoped connected-component BFS labels; reset per `R_RenderDlightCubemaps`, no stale interframe shadow cache. | 850,000 result-equivalence checks; comparison count 44,110,275 -> 899,957 under synthetic inputs; real performance NOT_MEASURED. Dynamic light/eligibility corner cases require gameplay testing. |
| `ssgi_fp.glsl` OPT-09, final SHA256 `51520409b68872ce243d8baa7d0665829c03f7891aa05100120141fe38057ca7` | Reuse per-sample scene raw depth and center luma; preserve twelve taps, entity rejection, UV/thresholds. | Strict source anchors + compilation + Mesa smoke; GPU HDR/temporal parity still NOT_RUN. |
| `volumetriclocal_fp.glsl` OPT-04, final SHA256 `857dcba6df9d77a924ac337d4f7a6c312b07ac2870c9c09dad462a2cbe7b9f70` | Hoist uniform-based physical light radius squared, spotlight axis and cone bounds outside raymarch loops. | Compiler + smoke; no real GPU timing or full spotlight action sequence. |
| `volumetriclocal_fp.glsl` OPT-06, same final SHA256 as OPT-04 | Replace `length()` followed by squaring in core/body/halo Gaussian with squared dot/width expressions. | 20,000 float32 fire samples, max absolute error 1.192e-7; HDR/animated fire appearance not fully accepted. |
| `volumetricsun_fp.glsl` OPT-02, final SHA256 `860b09c86b4e24d3fb5263af871f0222461e65f8484bf55cafe53999b265f1cf` | Hoist exponential extinction setup and reuse a per-step recurrence; preserve CSM sample settings. | 3,000 rays, max absolute float32 error 1.550e-6; real Sun/GPU temporal comparison NOT_RUN. |

Only these five SP/code files are different from the locked component-correct source snapshot. UI/game/cgame/other GLSL source remain byte-identical to that baseline; three optimized shader files do **not** remain byte-identical.

## Verified build and runtime

- Windows cross-compilation baseline + optimized PASS; packaged EXE, renderer, cgame, qagame, UI individually identified as PE AMD64 and hash-matched to `BUILD_PROVENANCE.json`. Unchanged EXE/cgame/qagame/UI A/B hashes match; expected optimized renderer hash `30df52c96fe055d13eef9ff6161657881a092c07ae2375558fda285667fc1857`.
- Outer and inner ZIP CRC checks PASS, sidecar SHA256 PASS, every file listed in `docs/SHA256SUMS.txt` matches, 20 package members; no commercial `pak*.pk3` or forbidden `DWPERF_*`/TestLab binary markers. Normal production launcher `RUN_DARKWOLF_OPTIMIZED_CLEAN.bat` includes isolated `fs_homepath`, `+safe`, and explicit preset execution.
- Linux Mesa llvmpipe SP smoke passed on six maps in High Quality plus escape1 in native Quality, each variant. `r_forceSun=1` was runtime-checked; smoke is 640x480, not Windows gaming-GPU validation.
- Camera/lighting regression: 128 fixture-ring and 48 table cameras per variant, 176 PNG/TGA captures per variant. Baseline and candidate ring analyzers PASS with zero listed failures; camera indices 128/128 valid. Regression comparison reported `PASS_NO_NEW_ANALYZER_FAILURES`, no new failures, `semantic_acceptance=PASS` only within its **limited** analyzer scope.
- The actual screenshots contain diagnostic text and may have different frame-dependent overlays. Full HDR visual A/B, motion, weapon/railing closeups and ordinary Windows playthrough have **not** been signed off.

## Exact config contract and conflicts

`r_forceSun=1`, `r_dlightMode=2`, `r_staticPromoteMaxLights=32`, `r_dlightShadowMaxLights=3`, `r_ssgi=1`, `r_volumetricLocal=1`, `r_volumetricSun=1`, `r_volumetricFire=1`, `r_softParticles=1`, `r_hdr=1`, `r_toneMap=1`, `r_pbr=0` are preserved. **Historical High Quality profile still sets `r_ssao=0` and `r_indirectLighting=0`**, not compatible with describing it as fully all-effects-on. No unverified configuration switch was made to hide this gap.

## Outcome and next real-PC validation

**Actual result: `CANDIDATE_FOR_LOCAL_VERIFICATION`.** Source and packages have passed bounded static/compile/software-GL gates; `WINDOWS_RUNTIME=NOT_RUN`, `GPU_PERFORMANCE=NOT_RUN`, `VISUAL_ACCEPTANCE=NOT_RUN` in emitted provenance. The requested 75 FPS remains an unmeasured target. The user must validate the downloaded candidate using legally installed game retail PK3s and the included launcher on a real Windows x64 GPU, with unchanged resolution/profile/camera and baseline comparison. Capture FPS p50/p95/p99 and 1% low after warmup and specifically check escape1 table/lamps, crypt1 torches, dam spotlight, assault sun-lit weapon/radar fence, forest sun movement, and gameplay effects. Do not call this a FINAL_ACCEPTED production release until those missing gates are satisfied.

See `RELEASE_ACCEPTANCE.md`, `REGRESSION_MATRIX.md`, `PERFORMANCE_AB.md` and the separate validation artifact for detailed machine-readable evidence.
