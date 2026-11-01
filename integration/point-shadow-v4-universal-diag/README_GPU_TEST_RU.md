# DarkWolf Point Shadow V4 — Universal Source/Fixture Attribution (DIAGNOSTIC 1 of 2)

**Accepted immutable Clean Production:** GitHub Actions #41019985033. **Prior proven one-source test:** V3.2 #41290226774, world surface 7232 in Boss1 only. V4 is NOT a finished fix.

## What this one binary does

- Enumerates all *ordinary point-shadow captures actually rendered* in the current scene. Logs source capture XYZ, material names, surface IDs, AABBs, camera distance, near-light geometry and ranking.
- Determines probable fixture-attached BSP surfaces through **source-local spatial proximity plus adjacency to emitter-like BSP material**, never global material name suppression.
- Automatically creates `DW_PS_V4_SELECTION.cfg` in the active writable game directory selecting **one** capture origin and up to 3 BSP Surface IDs observed in its drawlist. Selection is based on a **heuristic**, not a physical FixtureId mapping or GPU per-pixel depth owner.
- Within the SAME test DLL, source-local diagnostic filters compare (1) linked candidate, (2) top geometric candidate, (3) top three candidates. The rest of the scene, other shadow-map sources, Fire/Tesla masks and sunlight are never filtered by V4.
- Exports `dw_ps_v4_<map>_mode0.json`, `...mode1.json`, `...mode2.json`, `...mode3.json` from the renderer. Empty/low-confidence selections remain fail-open.
- No per-map hardcoded Surface IDs, no globally excluded material, no change to CSM, Fire/Tesla, GL shaders, StaticPromote 32/3 budget, HDR16F, LUT/CAS/A2C or other accepted production options.

## One execution per map

1. Install the TEST DLL in a separate game copy; retain original production DLL.
2. Put `DW_PS_V4_AUTOTEST.cfg` and `DW_PS_V4_RESET.cfg` in `Main`.
3. Load the same saved view on **Boss1**, **Factory**, or **Crypt1**.
4. Without moving the camera: `/exec DW_PS_V4_AUTOTEST.cfg`.
5. Wait until `DW_PS_V4_AUTOTEST_FINISHED`; five JPEG files are automatically created.
6. Double click `COLLECT_DW_PS_V4.cmd`. It collects the five images, all matching JSON telemetry, generated selection.cfg and console log. Attach the ZIP to ChatGPT.
7. Repeat only for the other two maps, collecting each map's ZIP before the next run because JPEG filenames are reused.

### Exact phases

A `01_BASELINE`: no filters; source/material/coordinates auto-inventoried.
B `02_LINKED_ONE`: suppress one candidate **only if** near its presumed emitter surface.
C `03_NEAREST_ONE`: suppress one top candidate regardless of emitter adjacency (DIAGNOSTIC only).
D `04_TOP_THREE`: suppress up to three top candidates for selected source (DIAGNOSTIC only; may lose correct stand/architecture shadows).
E `05_RESTORED`: resets all V4 filters, must look like A.

Success markers: `DW_PS_V4_SELECTION`, `DW_PS_V4_REPORT_OK`, and `DW_PS_V4_SOURCE_LOCAL_SKIP` (the last is expected only where a filter actually applies). Absence of SKIP means **NO automatic exclusion**, NOT proof of success. For Crypt1 fire/flicker, changes must be interpreted with temporal differences in mind.

### Strict two-attempt acceptance gate

- First diagnostic release V4: user tests all three scenes once. Do not create another diagnostic game release.
- Second **proof release** only after interpreting all three report sets. It must have a generalized, guarded source-local classifier and automated A/B/A, with **zero hardcoded Boss1 IDs in general policy**.
- Only third shipped build may be new Clean Production and only after Boss1+Factory+Crypt1 visual PASS and protected-effect regression checks. If evidence is insufficient, say so; DO NOT falsely claim full-game fix.

To reset /exec DW_PS_V4_RESET.cfg. Completely return to Clean by restoring original #41019985033 DLL.
