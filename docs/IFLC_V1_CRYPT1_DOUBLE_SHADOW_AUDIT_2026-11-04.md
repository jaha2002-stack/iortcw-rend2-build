# IFLC V1: Crypt1 double-shadow causal audit

Date: 2026-11-04 (Asia/Dushanbe). Reference: screenshot `iflc_flame_1_surface_2992_direct_3.png` from [IFLC V1 Run #41691075610](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/41691075610).

## Reproducible evidence

- [Diagnostic Run #41700133238 — success](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/41700133238)
- [Artifact: 17 real Crypt1 screenshots, console and verification report](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/41700133238/artifacts/13263372309)
- Native Linux/Mesa llvmpipe, renderer V1 exact source, isolated instrumentation only. Captured 17/17, `faults=[]`, verified same camera and frozen client time. The `direct=3` reference and final restored image are pixel-identical.
- Chosen opt-in source: `surface:2992:711b28d1:6de6bac8` at `(-224.5,1544.5,552)`, `VOLUME_ONLY`, `enabled=1`, one real IFLC DLight, radius 205, RGB `(3,1.56,0.48)`.
- Another distinct authored source was rendered: native DLight ordinal `291` at `(-152,1668,636)`, radius 311.667, color `(1,0.686275,0.454902)`. Origins are ~166.03 world units apart. Nearness does not prove both belong to the same physical torch.

## Causal findings (verified on original images)

1. **Large angular wall silhouette** is caused by the selected opt-in IFLC DLight's shadow visibility, **not** by drawing a duplicate IFLC DLight. With `direct=3, volume=0, baked=.2`, bypassing *only* its world visibility (frame 04) or *only* its ordinary shadow cubemap (frame 05) preserves the large silhouette. Bypassing **both** for this source (frame 06) removes the large angular silhouette while the same direct light continues to illuminate the wall. Full-frame comparison with frame 03: bypass world MAE 0.7658, bypass ordinary 0.3665, bypass both 5.8699 RGB levels. In the large-below ROI, ordinary-only bypass changed **0 pixels**, whereas both bypass changed 3200 pixels, MAE 15.81.
2. **Smaller patch beneath the bowl** is associated with the separate existing native291 shadow. When the opt-in DLight's receiver contribution is zero (frame 08), the small patch remains. With the opt-in still zero and both native291 visibility paths bypassed (frame 10), the small shadow disappears: small-fixture ROI MAE **11.702**, 7585 changed pixels. Thus these are two distinct shadow contributions from two different physical DLight positions. Do **not** claim that native291 is definitely the authored owner of the selected flame without a fixture ownership test.
3. Changing MapLighting baked scale `0.20 -> 0` with fixed direct receivers does not reproduce removal of the small patch; it remains when native291 shadows stay active. This is not a demonstrated lightmap artifact. The `baked=0` controls change surface ambient brightness, as expected.
4. The original renderer's PCF, source positions, DLight structure, shadow selection, capture, FireVol shader, and GLSL are unchanged by this diagnostic. Only *receiver-side* visibility/color controls were injected into a disposable native diagnostic build. Diagnostic toggles are **not a safe production workaround**.

## Limits of conclusion

- These controls isolate the two visible shadow **paths and lights**, but do not identify the exact BSP caster polygons, self-shadow bias, or geometric reason for the unnatural *shape* of the opt-in shadow. In particular, the IFLC light is positioned at the BSP flame-surface center; that may intersect/interact with the lamp geometry and must be explicitly tested rather than presumed the root defect.
- Since two visibility paths are combined, disabling either alone is not a valid test for complete suppression; suppressing both is a causal diagnostic, not a correction.
- No corrected Win64 release has been built or GPU-validated as part of this audit; the existing IFLC V1 package remains unchanged.

## Engineering direction

For a V1.1 fix, address only **opt-in VOLUME_ONLY** shadow geometry and self-occlusion. Investigate the fixture's actual caster triangles, source depth/bias relative to the mounting geometry, and a fixture-local caster exclusion or stable origin correction if geometry supports it. Preserve world containment outside the selected fixture, native291's small shadow, FireVol, accepted V1.4 PCF4x4 and global shadow budgets. Reproduce Crypt1 frames 03/06/08/10 after the correction; add a 4–6-fire room test, other maps and Windows GPU before marking visual PASS.

Artifact files: `runtime/iflc_shadow_03.png`, `04.png`, `05.png`, `06.png`, `08.png`, `10.png`, `IFLC_SHADOW_AUDIT_VERIFICATION.json`. The test-only mask is documented in `integration/iflc-shadow-audit/README_RU.md`.
