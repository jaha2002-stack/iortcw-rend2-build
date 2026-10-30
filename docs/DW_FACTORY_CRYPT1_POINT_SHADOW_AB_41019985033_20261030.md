# DarkWolf point-shadow A/B on Factory ladder and Crypt1 hanging fire — 2026-10-30

**Immutable current production baseline:** [#41019985033](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/41019985033); renderer DLL SHA-256 `d7423e8648e2de556f79c7cddecf1a8df16b9f60a46c503d1440089876116b45`.

**Exact shadow source recovery:** [#41030449949](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/41030449949), approved historic #408787 shadow code. Final release did not alter this shadow source (only Sun HDR16F). No modifications have been made to the accepted production DLL.

## 1. Evidence from user-supplied screenshots B / C / D

The user explicitly identified image order for **both maps** as B, C, D:

- **B:** `r_dlightShadowStrength 0` (main point-shadow visibility contribution disabled).
- **C:** `r_dlightShadowStrength 0.88; r_dlightWorldContainment 0` (normal point shadow enabled, separate Fire/Tesla architecture mask disabled).
- **D:** `r_dlightWorldContainment 2; r_dlightShadowSoftness 0.80` (main point shadow and architectural mask enabled; smaller sample offset).

| Scene | B | C | D | FPS B/C/D (screen overlays) |
| --- | --- | --- | --- | --- |
| Factory tunnel ladder/arch | Broad curved silhouette behind ladder **not present** | Strong curved and broad horizontal shadow **present** | Same shadow **present** | 114 / 108 / 90 |
| Crypt1 hanging fire | Distinct giant hard-edged polygon under brazier **not clearly present** | Giant near-black polygon on floor **present** | Giant near-black polygon on floor **present** | 83 / 72 / 75 |

**Interpretation:** all three user-tested scenes, including the previous spotlight, respond to main point-shadow strength, while disabling `r_dlightWorldContainment` does **not** remove the offending broad shadow. The screenshot evidence therefore prioritizes **regular point cubemap caster/receiver/origin logic** over separate 256-face Fire/Tesla world-mask for THESE silhouettes. The 256-mask can still have independent problems elsewhere.

**Caution:** views differ slightly; the fire source varies in intensity, so do not infer exact light strength from the screenshot RGB values or treat FPS counters as controlled benchmarks. In Crypt1 B overall surroundings remain dark for other reasons; the supported claim is disappearance of the distinct giant polygon, not complete removal of darkness.

## 2. Historical correction: Stage 11 is a candidate, NOT proof of regression

[Pre-Stage11 #34962735592](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/34962735592) already admitted common `SS_OPAQUE` casters in the generic depth fill. Its logic was broadly:

`if (depthFill && shader && shader->sort != SS_OPAQUE && shader->sort != SS_PORTAL) continue;`

[Stage11 #35150218437](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/35150218437) adds `R_DarkWolfClassifyShadowMaterial`, alpha-cutout eligibility and material-aware depth fill. Therefore **a solid opaque light housing was potentially already a caster before Stage 11**; we must not claim the solid fixture began casting only due to this classifier.

A separate Stage11 change is more relevant as a candidate: **receiver expansion**. In `tr_shade.c` Stage11 extends the legacy `ProjectDlightTexture` path to consume the shadow cubemap via `UNIFORM_DLIGHTSHADOWPARAMS`, `UNIFORM_LIGHTORIGIN` and the appropriate world/entity model matrix; earlier this legacy receiver path did not apply the selected cubemap. `ForwardDlight` also uses shadow visibility, but it already had a main point-shadow path before this Stage11 experiment. Hence giant shadows could become visible on additional world surfaces even when the underlying caster existed in older builds.

These are code-level hypotheses. Only a same-camera pre-/post-Stage11 visual A/B can establish first bad release. The two test sets B/C/D confirm **which current shader mechanism**, not precisely **which September commit** introduced the issue.

## 3. Plausible geometric mechanisms, kept separate

- **Factory:** the curved shadow matches the geometry of a nearby stone arch/structural element, not necessarily the thin rungs of the ladder. A point light located close to a large architectural caster can generate a huge projection onto a farther wall. Do not automatically exclude the entire ladder or BSP arches; first identify the source and actual caster.
- **Crypt1:** the huge polygon is consistent with the hanging basket/stand or adjacent near-source geometry casting through the main cubemap; specific geometry/owner ID not yet established. Its being a fire emitter does NOT mean the separate 256-face containment mask is the dominant cause in this capture.
- **Previously tested spotlight:** solid fixture body/self-shadow is plausible; exact rendered entity or BSP surface still unproven.

The likely common class is **point-source projection from overly close or incorrectly attributed caster/receiver geometry**, potentially exacerbated by the expanded Stage11 legacy receiver. Do not claim identical individual caster on all maps.

## 4. Safe next diagnostic design (no production change yet)

Rebuild diagnostic DLL **on the exact accepted clean source and HDR16F Sun**, with two test-only, shadow-pass-local switches:

1. `r_dwPointCasterScope`: 0 original, 1 world/BSP-only casters, 2 entity/model-only casters. Apply only inside ordinary `VPF_SHADOWMAP` point-shadow capture, explicitly NOT synthetic FireVol and architectural world-mask views. Maintain all light selection, shading, receiver and slot logic unchanged. This isolates whether shadow comes from world/BSP or refEntity/bmodel geometry.
2. Optional *receiver-path* A/B: original both, forward-only, legacy `ProjectDlightTexture` cubemap disabled. Implement only at the receiver's `useShadow` decision, without reducing light intensity or affecting `DlightWorldVisibility()`. If broad shadows appear only on legacy receivers, this points more sharply to Stage11 expansion.

Do not ship these diagnostics. Only after both domains are known implement source-identity-aware fixture self-caster exclusion or a narrow receiver fix. Never blanket-skip nearby BSP polygons: doing so risks light leaks through walls, broken grates/doors and prior Escape1/Crypt1 shadow regressions.

## 5. Validation gate

Compare same fixed view and exposure across spotlight, Factory ladder/arch and Crypt1 hanging fire, plus checks on door/grate transparency and wall occlusion. Restore `r_dlightShadowStrength 0.88`, `r_dlightWorldContainment 2`, `r_dlightShadowSoftness 1.70` after these tests. Preserve Sun HDR16F, SSGI, Bloom, StaticPromote identity, fire/tesla and standard three shadow slots.

**Status:** scene-level A/B PASS for routing to main point-shadow; exact owner and historical first-bad commit still UNPROVEN.