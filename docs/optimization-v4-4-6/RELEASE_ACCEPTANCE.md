# v4.4.6 Optimized Clean — release acceptance, 2026-10-14

**CI:** [run 38619534668](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/38619534668) COMPLETED / SUCCESS, run attempt 1, finished 2026-10-14 20:48:20 UTC.
**Built source/builder SHA:** `9df5ac17dd687437b4c2de39ea2d39b59fa8c179`. **Baseline source tree:** `a9afb5a60e26eb112bc5a6af4bb52f4ed08685f1`.
**Candidate artifact:** GitHub artifact `11928290259`; `DarkWolf-ioRTCW-Rend2-v4.4.6-Optimized-Clean-Candidate-Win64-SP.zip`, SHA256 `d005ca823debf7b5bfab025a11d360752ed1033c258fc9d22797e5291306014f`. The outer GitHub artifact digest is `08f6b189daa25a54ae18b91c84c5b4905204844b1766270b9a50e9369ab98342`.
**Evidence artifact:** GitHub artifact `11928055679`, SHA256 `9baa2ca7cfc3b4866f7136ca8356367284cf8076c0163cc0b9ecb24b9d17826a`.

| Gate | Verified result |
|---|---|
| G0 baseline provenance | PASS: SHA-pinned upstream, ordered patches, reconstructed source tree; baseline GitHub artifact known |
| G1 source/algorithm audit | PARTIAL: multi-subsystem static audit; real Windows GPU bottleneck profile unavailable |
| G2 constrained source delta | PASS for strict five-file inventory and C/math tests; complete graphics equivalence UNVERIFIED |
| G3 CI / Win64 SP / integrity | PASS: both Win64 variants compile; five PE AMD64 components, ZIP CRC, manifest SHA256, license/docs/deps checked |
| G4 available regression TestLab | PASS: 176 matched diagnostic capture sets on each variant (128 ring + 3 x 16 table); ring and table analyzers PASS |
| G5 runtime | PASS for seven Linux Mesa llvmpipe smoke scenarios on each variant; Windows runtime NOT_RUN |
| G6 performance | NOT_RUN: target Windows gaming-GPU FPS, frametime p95/p99, 1% low and 75 FPS target not measured |
| G7 visual acceptance | NOT_RUN for complete calibrated real Windows visual/GPU A/B; limited Mesa screenshots and analyzers PASS |
| G8 production candidate ZIP | PASS: one zipped candidate, 20 expected package members, no retail pak*.pk3, no forbidden DWPERF/TestLab binary markers |
| G9 CI publication | PASS: single authoritative workflow completed SUCCESS; clean candidate and separate evidence available |
| G10 report + review | PASS for this report and draft PR #4; `main` unmodified and no merge performed |

**Scope of limited image gate:** `regression-comparison.json` reports `capture_integrity=PASS`, `paired_image_count=176`, `baseline_failures=[]`, `candidate_failures=[]`, `semantic_acceptance=PASS`, `VISUAL_ACCEPTANCE=NOT_RUN`. This is diagnostic analyzer acceptance only, not proof of visual identity. Images can contain diagnostic overlays, and temporal animation/exposure are unsynchronized.

**Profile exception:** inherited `PRODUCTION_HIGH_QUALITY.cfg` intentionally retains `r_forceSun=1`, `r_dlightMode=2`, `r_staticPromoteMaxLights=32`, `r_dlightShadowMaxLights=3`, `r_ssgi=1`, `r_volumetricLocal=1`, `r_volumetricSun=1`, `r_volumetricFire=1`, `r_pbr=0`; however `r_ssao=0` and `r_indirectLighting=0`. The user requested preservation of these effects, so the candidate must not be called `all-effects-on` until the conflict with historical profile is resolved and tested. Do not silently change these defaults to manufacture acceptance.

**Decision:** `CANDIDATE_FOR_LOCAL_VERIFICATION`, **not `FINAL_ACCEPTED`**. Preserve draft PR; do not merge. The CI result proves build/source integrity plus bounded software-rasterizer regression, **not 75 FPS or real-Windows visual acceptance**.
