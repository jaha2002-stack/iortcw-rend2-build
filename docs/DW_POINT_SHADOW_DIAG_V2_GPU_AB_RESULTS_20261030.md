# DarkWolf Rend2 Point Shadow Diagnostic V2 — GPU A–H field findings (2026-10-30)

**Production base immutable:** [successful Clean Production #41019985033](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/41019985033).  
**Test build:** [Diagnostic V2 #41051538614](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/41051538614).  
**Evidence:** user-provided in-game screenshots, same approximate camera for Factory ladder/arch, spotlight, Crypt1 hanging flame. Frames are not pixel-registered and FPS overlays are not controlled benchmark results.  
**Status:** field **diagnosis only**, not production-quality approval.

## Meaning of modes

| Mode | Near BSP fragment clip radius | Origin shift |
|---|---:|---|
| A | 0 | 0 |
| B | 8 | 0 |
| C | 16 | 0 |
| D | 24 | 0 |
| E | 0 | world Z +4 |
| F | 0 | world Z −4 |
| G | 0 | world X +4 |
| H | 0 | world Y +4 |

All modes retain V1 `r_dwPointCasterScope=0`, `r_dwPointReceiverPath=0`: full original Stage11 Caster/Receiver eligibility. The different modes are destructive **only to the diagnostic shadow capture** and must never be merged into Clean Production.

## Spotlight interior

A: giant, nearly polygonal dark silhouette behind fixture. B and C: nearly unchanged. D (24 units): silhouette undergoes conspicuous shape changes with unnatural cut-outs/jagged pieces. E/G/H: projected shadow outline and position vary substantially with shifted origin; F (Z−4): tall upper part becomes larger. None is an acceptable beautiful, physically verified shadow. The strong origin sensitivity and D threshold indicate **at least some of the relevant BSP occluder geometry is near the shadow-capture origin**. This does not identify exact BSP surface ID or prove emitter identity.

## Factory ladder and stone arch

A–D: broad arched shadow and horizontal strip remain. E–H: broad arched shadow remains, although some changes in location/contour occur with X/Y shift (the camera also varies slightly). There is **no clear qualitative success** from clipping up to 24 units or shifting origin ±4 along tested axes. Plausibly the oversized arc arises from a larger architectural BSP caster beyond this narrow near region. Whether the arc's size is actually physically wrong remains unverified without the light/arch/receiver spatial geometry.

## Crypt1 hanging fire

A–D: broad near-black polygon on the floor remains present, despite world-fragment clipping up to 24; narrow stem shadow varies and its apparent attachment can change. E–H were supplied in a follow-up set of four images. They are part of this A–H field test, but any conclusion about a precise per-axis improvement must be based on visual alignment, source position and absence of light leaks. No broadly established full removal of the polygon can be claimed from the data currently available in this audit. The normal Fire/Tesla 256 cubemap world mask was NOT modified by V2, and previous tests already tied the major polygon to the main point-shadow channel.

## What V2 proves and does NOT prove

**Supported**:
1. Large shadows in spotlight and Factory are not fixed by a global near-radius clip of 8/16/24.
2. Spotlight silhouette responds to geometry close enough to be clipped by 24 units; origin offset influences it.
3. Factory appears dominated by another BSP scale/placement (or an area outside the tested radius), not the same single narrow near-region effect.
4. Any uniform near clip creates possible local wall leaks; merely shrinking a shadow with it does not mean improved correctness.
5. Existing Stage11 caster/receiver asset eligibility is intentionally unchanged in all test baseline modes 0/0.

**Not established**:
- Exact BSP surface/material/brush ID casting each objectionable silhouette.
- Whether any one global origin shift is physically appropriate or safe.
- Whether the broad Factory arch is a rendering bug rather than genuine point-source perspective.
- A production-ready cure applicable to spotlight, Factory and Crypt1.

## Next safe intervention

Do NOT ship nonzero `r_dwPointNearWorldClip` or arbitrary global `r_dwPointOriginAxis/Shift` in Clean Production. Instead, build a **shadow-source geometry attribution diagnostic**: identify source FixtureId / point-light origin and targeted BSP surface/brush, measure distance to relevant caster and receiver; for flashlight housing evaluate a **fixture-aware physical emissive lens center** shadow origin, with stable (not viewer-driven) placement and valid wall/grate/door occlusion. Distinguish self-occlusion from architectural arches. For physically appropriate large but harsh shadows, explore light-size-dependent, contact-hardening penumbra/PCSS or improved PCF filtering rather than removing caster coverage.

Preserve all assets capable of receiving and casting shadows, HDR16F, Local/Fire, CSM, SSGI, and the current 3-shadow-slot budget. Validate actual GPU screenshots and regression scenes before any future Clean Production integration.

**Safe restore:** `exec DW_PS_V2_A_ORIGINAL.cfg` and restore the original #41019985033 DLL after diagnostics.
