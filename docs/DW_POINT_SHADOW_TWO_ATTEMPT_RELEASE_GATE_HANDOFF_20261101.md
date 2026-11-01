# DarkWolf Point Shadow — Two-Attempt Cross-Map Release Gate (2026-11-01)

## Contract and immutable baseline

- **Accepted production base:** GitHub Actions [#41019985033](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/41019985033), commit `c653433e1b0a29b2f43f29a240b96a8192acb617`, original renderer SHA-256 `d7423e8648e2de556f79c7cddecf1a8df16b9f60a46c503d1440089876116b45`.
- User authorizes **two user-facing experimental releases only**: one fully automated diagnostic release (V4), then one generalization/proof release (V4-PROOF). **Third** user-facing build must be a fully checked Clean Production if the proof passes. Source/build CI retries before giving a test archive do **not** add a user-facing test round.
- Preserve accepted Sun HDR16F, CSM, Fire/Tesla, SSGI, Bloom, ToneMap, local volumetric, portal sky, Texture Fidelity, CAS/LUT/A2C, 32 StaticPromote lamps, **3 shadow slots**, full Stage11 Caster/Receiver coverage. Exclude only source-attached erroneous fixture self-shadows where proven, never global shader/material IDs.
- Explicitly **do not** globally suppress `world->surfaces[7232]` or `textures/metal_misc/ametal_m03dm`. Surface ID is map-build-dependent and material is shared.

## Verified GPU evidence before V4

- V3.2 [#41290226774](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/41290226774), visual A/B/A PASS on **Boss1**. The large solid silhouette is present in baseline, disappears when only source-local BSP `7232` is suppressed, and reappears after restoration. Correct holder/stand shadows remain. The experimental rule only matches capture `(-2764,-219,-24)`; physical cause not proven.
- V3.1 JSON report: Boss1 `rendererTotal=7791`, `mainWorld=7274`, selected drawlist count 424, `7232` metal with distance 10.359 to capture, `7234` emitter-like `textures/lights/light_m4` equally near. Removing **7234 alone does not** remove the big shadow. Removing **7229..7234** removes extra valid shadow geometry. Therefore choose individual source-attached casing, not groups.
- Factory: ladder/arch huge dark curve; Crypt1: hanging fire bowl huge dark polygon. V1 only established world/BSP caster family. Their exact responsible surfaces and source origins remain unknown; do not infer same material or geometry cause.

## RELEASE 1: V4 universal diagnostic (this branch)

- Source branch: `rend2-point-shadow-v4-universal-onepass-diagnostic-41019985033`.
- New code: `integration/point-shadow-v4-universal-diag/apply.py.gz` (read by `gzip -cd`, strict original source hash). This reconstructs accepted base by exact V1/V2/V3/V31/V32 CI gates and adds V4-only opt-in source/BSP audit and limited temporary suppression.
- `r_dwPointV4Scan 0` and `r_dwPointV4Mode 0` are safe defaults. No global material removal or geometry changes.
- For each currently rendered ordinary point-shadow capture: source XYZ, camera distance, nearby emissive-looking BSP, candidate BSP shader/material, AABB, distance, angular ratio/score, actual drawlist appearances and number of omissions are saved in per-map, per-mode JSON.
- Automatic selection of **one source** and up to **three candidate BSP surfaces**. The baseline automatically generates `DW_PS_V4_SELECTION.cfg` with map, source coordinates and ID tuple; subsequent phases load it internally. This is **heuristic source association**, not physical FixtureId proof or per-pixel GPU depth winner.
- One user action per map: `/exec DW_PS_V4_AUTOTEST.cfg`. Automated stages: A baseline, B emitter-linked candidate (if any), C one geometric candidate, D up to 3 geometry candidates, E restore, with 5 JPEGs, report JSONs and `condump`. After each map user runs `COLLECT_DW_PS_V4.cmd` (within full release ZIP) and sends one archive.
- Exactly three target scenes: **Boss1**, **Factory**, **Crypt1**. Capture identical camera/savepoint for each stage; camera/engine settings unchanged. If flame flickers in Crypt1, compare geometry area over multiple frames or use stable savepoint when interpreting.
- In report analysis distinguish: actual `DW_PS_V4_SOURCE_LOCAL_SKIP` logged vs no-op; selected map/source ID vs wrong source; matched cull info; whether unacceptable black silhouette disappears; whether legitimate stand/mesh/caster shadows remain; whether restoration matches baseline. Pixel changes alone do **not** prove physical correctness.
- If auto-selection gives no confidence, **do not** claim a fix; examine all captured source JSON and decide if second proof can reliably support the map. Do not request 10 further manual ID probes.

## RELEASE 2: V4 proof (only after all first-round telemetry)

- Code must be generalized from confirmed A/B effects: map-independent, source-local, conservative fixture detection and source geometry association. No special-case global material or hardcoded Boss1 ID.
- Guard fail-open on uncertain ownership and avoid clipping independent arch/walls, lamps not in capture, alpha cutouts, Fire/Tesla, sun CSM. Maintain complete Stage11 casters for every **other** source/receiver.
- Automated A/B/A on Boss1+Factory+Crypt1; confirm correct shadows, source stability, no large new light leaks, acceptable FPS and memory. No implicit physical claim without independent origin/projection evidence.
- If failures occur in proof, **stop** and document limitation rather than shipping unproven production or requesting arbitrary extra tests against the two-attempt constraint.

## RELEASE 3: Clean Production (only after proof accepted)

- A single clean renderer package based on the most recent user-accepted production requirements and explicit provenance (at minimum #41019985033; reconcile newer accepted texture branch only if properly verified). No diagnostic CVar/debug files in production; don't inadvertently carry V1/V2/V3/V31/V32/V4 test modes.
- Preserve exact accepted config packs (Performance/Balanced/Quality/High/Ultra), normal lighting defaults, 32 lamps/3 shadow slots. Only the confirmed generalized source-local shadow fix is carried into clean source.
- Audit original EXE/other DLL/assets untouched unless specifically justified, shader baseline unchanged, full ZIP per-file SHA-256, build CI, GPU visual regressions.
- If either Factory or Crypt1 has physically valid architectural shadow instead of an artifact, do not erase it to satisfy visual expectation; document and retain.
 
## Chat continuity

Read this file and `docs/DW_PS_V32_BOSS1_GPU_ACCEPTANCE_20261101.md` before working in a new conversation. No new diagnostic attempt beyond the current V4 user-facing build. New conclusions require uploaded ZIP/screenshots, not guesses.
