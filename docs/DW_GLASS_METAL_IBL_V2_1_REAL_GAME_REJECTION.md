# DarkWolf Glass Metal-Cubemap V2.1 — Visual acceptance rejected

**Accepted production source:** GitHub Actions #41297344177, unchanged.
**V2.1 build:** #41390832717, Windows x64 + GLSL 120/130/150 compilation SUCCESS.
**Real retail RTCW image proof:** #41390832769, native actual Xlabs and Chateau, three same-instance OFF/ON/OFF2 captures at the same camera. Recording/provenance succeeded, **visual acceptance FAILED**.

## Specific verified technical result

Rend2 metal material shader uses `u_CubeMap`, `EnvironmentBRDF`, and directional mip/parallax. Glass V1.1 used a separate weak additive overlay, not a physically convincing reflection. V2 reused the real metal environment function but incorrectly kept `reflect(-E,N)` despite Rend2 metal using `reflect(E,N)`; it overexposed the Xlabs `freeze_glass` pane to nearly white. V2.1 corrected the reflection sign to match metal and limited opacity via Fresnel alpha blending; it no longer whites out the pane but **still does not create visually recognizable surroundings in the glass**.

Actual native screenshot metrics at identical, temporally frozen camera (OFF/OFF2 MAE = 0):
- Xlabs `freeze_glass`: V2 OFF/ON whole-frame mean absolute difference 9.70514, ugly washout; V2.1 0.40934, primarily subtle shading.
- Xlabs `xwindow_c02`: V2.1 0.16170 whole-frame MAE; no convincing world reflection.
- Chateau `window_c03a_750`: V2.1 0.07416 whole-frame MAE; no convincing world reflection.
- Chateau `tramglass2`: V2.1 0.00099 whole-frame MAE.

**Do NOT call the feature finished. Do NOT merge or substitute this for Clean Production.** The real game proof gallery is from the private licensed RTCW TestLab artifact in run #41390832769; it is not a fabricated mockup. Compiler or pixel differences are not proof of recognizable reflections.

## Remaining engineering requirement (not implemented or validated)

Reuse the genuine static cubemap capture/path from existing metal **with glass-local probes on the correct visible side**, per-surface/texture segmentation separating panes from shared painted metal frames, conservative Fresnel/transmittance composition, and test scenes showing recognizable room geometry in the reflected image. Decorative windows with no pane polygon cannot be solved by reflection shading alone; synthesizing new geometry is a separate problem.

Preserve `r_cubeMapping=0` isolation for Norway water, original textures/shadows/volumetric/SSGI, the exact accepted binary baseline, and zero effect on metallic surfaces when glass is disabled.
