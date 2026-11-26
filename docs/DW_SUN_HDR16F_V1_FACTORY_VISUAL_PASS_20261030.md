# DarkWolf Volumetric Sun HDR16F Precision V1 — Factory Visual PASS

**Date:** 2026-10-30  
**Accepted base:** GitHub Actions [#40878732886](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40878732886), commit \`4e4bcdfa8c1d7bf45191ab8bd0b1d260b0b95595\`.  
**Accepted test build:** GitHub Actions [#41013202896](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/41013202896), commit \`7b3786f9ad0aefb4abe8512315120834db7decda\`.  
**Accepted Win64 DLL SHA-256:** \`d7423e8648e2de556f79c7cddecf1a8df16b9f60a46c503d1440089876116b45\`.  
**Original baseline DLL SHA-256:** \`8f1d482011200e8aa5d254450c360b753a2e514b9e9cf3f34c35bbc6e3fe18b5\`.

## User hardware test acceptance
- **Factory Visual PASS**: broad color banding / sky arcs are no longer visible on the tested Factory scene.
- The user tested the new DLL on additional maps and reported no arcs, with a visually excellent sky.
- The user reported FPS above 100 on all tested maps; this is user-reported gameplay experience, not a universal benchmark.
- Very small residual fine grain remains and was explicitly accepted as visually minor.

## Clean production freeze
- Integrate **the exact accepted renderer binary**, without further reworking or adding dithering.
- Preserve all other executables, DLLs, original cfg files, Portal Sky Single-Sample Fix, Sun V3 CSM visibility, 32 raymarch steps, Local and Fire Volumetric, SSGI, Bloom V2 HDR, ToneMap, StaticPromote, CAS/LUT/A2C.
- Keep \`r_dlightMode 2\`, \`r_forceSun 1\`, up to 32 promoted static lamps, and 3 dynamic shadow slots.
- Five additional selectable quality profiles may be added; none may disable existing major effects, and none replaces the accepted default.
- Exclude experimental PK3/GLSL overrides, diagnostic telemetry, debug cvars and new rendering algorithms.
- Package on top of immutable baseline artifact #12899612623 from run #40878732886, with the exact user-tested renderer from artifact #12958870751 from run #41013202896.
- Original historical manifests stay available, with a new authoritative Clean Production manifest for the merged release.

## Scope caveat
Game-side tests on the user's actual GPU support the accepted result. Other hardware and optional performance profiles have not been independently validated.