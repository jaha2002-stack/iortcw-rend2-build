# DarkWolf point-shadow spotlight A/B — confirmed by user (2026-10-30)

## Immutable accepted base

[Clean Production #41019985033](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/41019985033). Accepted renderer SHA-256: `d7423e8648e2de556f79c7cddecf1a8df16b9f60a46c503d1440089876116b45`. Base must remain unmodified during investigation.

Exact-point-shadow code was reconstructed and verified in [forensic workflow #41030449949](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/41030449949).

## User A/B photographic observation

Four screenshots of the **same spotlight in a small stone room**, with visually comparable camera position (not pixel-identically registered):

| Case | Test CVar(s) | FPS on snapshot | Extra-large dark silhouette behind spotlight |
| --- | --- | ---: | --- |
| A (baseline) | `r_dlightShadowStrength=0.88`, `r_dlightWorldContainment=2`, `r_dlightShadowSoftness=1.70` | 133 | PRESENT |
| B | `r_dlightShadowStrength=0` | 129 | **ABSENT** |
| C | restored strength 0.88, `r_dlightWorldContainment=0` | 121 | PRESENT |
| D | restored containment 2, `r_dlightShadowSoftness=0.80` | 83 | PRESENT |

The physical spotlight model remains visible in B, proving that the extra-large polygonal silhouette seen in A/C/D is a **shadowing result** rather than a disappeared visible model.

**Conclusions for this spotlight only:**
- The defect is controlled by the **main point-light shadow visibility/mix**, not by the separate Fire/Tesla architectural world containment.
- Changing point-shadow PCF footprint from 1.70 to 0.80 does not remove the large silhouette; this does not mean the width of its boundary never changes.
- `r_dlightShadowStrength=0` also eliminates valid point shadows globally; it is a **diagnostic negative control**, not a fix.
- FPS values are one-frame overlays from different captures, not controlled benchmarks; do not infer impact of individual CVars or regressions.
- The silhouette is consistent with near-source casing geometry casting onto a more distant receiver, but **the identity of the caster is not yet established**. It might be the spotlight housing itself, a fixture-associated BSP surface, or another nearby opaque model.

## Exact code branches and actionable gaps

- `SP/code/rend2/tr_main.c` `R_RenderDlightCubemaps()` sets capture origin to the light/group origin and renders all six cube faces with `VPF_SHADOWMAP | VPF_DEPTHSHADOW | VPF_NOVIEWMODEL`.
- `SP/code/rend2/tr_backend.c` `RB_DarkWolfRejectDepthFillShader()` admits world/models using `R_DarkWolfSupportedShadowCasterMaterial(shader)`. The classifier checks material/shader only, not ownership relation to the active emitter.
- `SP/code/rend2/tr_shade.c` `RB_StageIteratorGeneric()` uses `R_DarkWolfClassifyShadowMaterial` and draws `SS_OPAQUE` / alpha-tested casters into the point cubemap.
- `r_dlightShadowStrength` is applied in receiver shaders using visibility blend; `r_dlightWorldContainment` gates a **separate** world-mask path, so their A/B outcomes are consistent with the source.
- The broader caster eligibility was integrated into production at [Stage 11 #35150218437 (2026-09-16)](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/35150218437). This is a strong **historical candidate**, not a GPU-bisected first-bad commit.

## Do not commit an untargeted workaround

Never disable all model casters or skip every surface within a generic radius of any light. Doing so would reintroduce light leaks and remove legitimate nearby wall/grate/door shadows, including previously fixed Escape1/Crypt1 scenes. Never remove the Stage11 material classifier wholesale.

**Proposed next isolate:** diagnostic capture that tags actual owner/entity, shader/surface and distance to active light for the geometry responsible for the dark silhouette (without shipping logs). Then test a per-source **owner-aware** shadow-caster exclusion, only when a provable fixture-body link exists. The fixture may be BSP world geometry; entityNum alone is insufficient if so. Keep all other casters, all receivers, Sun HDR16F, static-promoted stable identities and 3-slot budget untouched. Compile a TEST-only DLL and validate on spotlight, flame, tunnel, grates and doors before merging anything into #41019985033.

## Safe cleanup

```cfg
seta r_dlightShadowStrength "0.88"
seta r_dlightWorldContainment "2"
seta r_dlightShadowSoftness "1.70"
vid_restart
```

No production DLL or CFG was changed by this audit.
