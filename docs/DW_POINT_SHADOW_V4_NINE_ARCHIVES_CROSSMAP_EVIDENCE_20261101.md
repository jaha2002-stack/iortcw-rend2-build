# DarkWolf Point Shadow — V4 GPU field analysis across nine archives (2026-11-01)

## Provenance

Accepted baseline: #41019985033, original DLL SHA256 `d7423e8648e2de556f79c7cddecf1a8df16b9f60a46c503d1440089876116b45`.
V4 diagnostic CI: [#41292154221](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/41292154221), source commit `a37ab3308e65ac468acab4eff6c5d27ab21f1c1c`.
All nine uploaded ZIPs passed ZIP CRC checks and contained five 1280×768 screenshots, mode JSON, console data, selected-source CFG and collection status. Caution: collector recursively includes previous map JSONs; use only the JSON named after the current archive/map, especially in Escape1 and Rocket.

## Core A/B results (one initial diagnostic attempt, no new user testing yet)

| Map | Selected capture | Chosen source-local BSP surfaces | Actual removal | Visual result |
| --- | --- | --- | --- | --- |
| Boss1 | (-2764,-219,-24) | 7232, 7231, 7230; metal `ametal_m03dm`, emitter linked | mode1/2 1, mode3 3 | Known huge polygon disappears with 7232 alone; additional geometry shadow is lost with three. Baseline/restore agree exactly outside HUD. **PASS** for exact Boss1 |
| Factory | (-96,-952,-203) | 3580, 3576 `metal_m01_blood`, 6195 `ametal_m02` (none emitter-linked) | mode1 0, mode2 1, mode3 3 | Thick wall/ladder-crossbar shadows survive all modes; local small shading changes with 3. Cannot prove normal vs secondary overlap |
| Crypt1 | (-928,-64,256) | 3587,3592,3596 `metal_m04dg2` (none emitter-linked) | mode1 0, mode2 1, mode3 3 (console confirms) | Large black octagon remains; baseline was too dark from first renderer init and not equivalent to restored. **UNRESOLVED** |
| Crypt2 | (-896,-384,288) | 741,746,750 `metal_m04dg2` (none emitter-linked) | mode1 0, mode2 1, mode3 3 | Large black octagon remains. Around-floor area in phases 2/3/4 vs restored has **zero** pixels changed >15 RGB among multiple tested ROIs; baseline differs strongly due lighting warm-up. **UNRESOLVED** |

## Strong identical fixture fingerprint between Crypt1 and Crypt2

For the two selected capture origins the first **10/10** candidate AABBs are IDENTICAL after subtraction of their own source origin. All use material `textures/metal_misc/metal_m04dg2` and occupy four radial horizontal directions centered on the source, extending vertically from relative Z=-40 to +64 and horizontally up to ±16. This supports reuse of the **same source-centered lamp/cage geometry** across both maps; it does NOT prove which surface wins depth at the eight-sided black floor silhouette.

V4 has a hard `DWV4_MAX_CANDIDATES 10` truncation, with 10 near-source surfaces monopolizing the shortlist. Therefore its top-three omission cannot rule out an unexamined **horizontal dish/base surface or another BSP face** as the octagonal shadow source. Up to seven other candidates from the same centered cage remain even after mode3.

## Factory factual distinctions

Three candidate AABBs:
- 3580 `metal_m01_blood` x[-112,-108], y=-928, z[-256,-140], source distance26.833, linked=false, submitted;
- 3576 same material x[-148,-144], y=-928, z[-256,-140], distance53.666, linked=false, submitted;
- 6195 `ametal_m02` x=-98, y[-1007,-991], z[-175,-151], distance48.052, linked=false, submitted.
The wall crop x75..600,y80..560 has **0** pixels changed >15 RGB after one-surface mode2; three-surface mode3 changes 7603/252000 pixels (~3.02%) yet the thick diagonal/crossbar silhouette persists. Baseline vs restored has 0 pixels changed >15 in the same wall crop. This is consistent with an authentic magnified perspective shadow from ladder / other actual structural geometry, but **not conclusive** without true depth-owner attribution, vertices, and light-to-caster-to-wall ratios. No justified automatic ladder shadow suppression.

## Crypt exposure control invalidity

Crypt1 center ROI x480..820,y180..660 initial baseline vs restored changed in 39.77% of pixels (>15 RGB). Crypt2 center ROI x330..960,y150..680 initial baseline vs restored changed in 56.04%. These are large **lighting warm-up/exposure differences between restarts**; they cannot be interpreted as causality from selective shadow filtering. Later phases must be compared to restored and new proof needs a stabilized control (warm-up and second baseline). Octagon shape and location persist throughout.

V4 mode JSON is also **prematurely emitted** during the first point shadow capture: for Crypt1 modes1..3 it claims `selectedSourceIndex=-1` and `skippedDraws=0` even though the console later confirms source-local skips for the selected second capture. Mode JSON totals are incomplete; rely on the full console + visual A/B and fix reporting time in proof release.

## Control maps and false-positive risks

- Four Escape1 saves, Rocket: valid image/JSON. Escape1 some no candidates and no source skips; no reason for a global removal. Other Escape1/Rocket captures have source-near candidate metal/wood/stone but they are not proven defective; automatic suppression by material or just proximity would risk erasing proper lighting.
- Rocket source has emitter-linked nearby `metal_c06` panels and one candidate 9766 skipped; the shadow changes are not an accepted defect. This demonstrates that **emitter proximity alone is not sufficient for a general fix**.
- No performance inference from single FPS overlays due reload animation, lighting restart, warm-up differences.

## Decision gate (only two user-facing experimental releases)

1. First diagnostic V4 **finished**. New user tests with V4 are **not requested**.
2. The only remaining proof release must correct (a) mode-report timing; (b) stable pre/post controls; (c) full near-source geometry census beyond first 10 candidates; (d) source-local candidate grouping; (e) prove that any selected single/group exclusion eliminates **only a defective shadow** on Crypt1/Crypt2 and preserves the stand and architecture; (f) fail open on Factory if ownership remains unproven.
3. The third build may be Clean Production only if a single proof release passes strict cross-map regression and visual acceptance. If evidence remains insufficient, do not incorrectly claim a whole-game fix or silently remove a material class. User does not permit further diagnostic game releases.

Do NOT use the global material name `metal_m04dg2` or Boss1 `7232` as a generic exclusion key. Keep 32 StaticPromote lamps, 3 shadow slots, Sun/CSM, SSGI, Bloom, CAS/LUT/A2C and Fire/Tesla full parity. Production #41019985033 unchanged.
