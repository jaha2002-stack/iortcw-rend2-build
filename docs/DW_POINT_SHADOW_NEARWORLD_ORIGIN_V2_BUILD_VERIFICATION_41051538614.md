# DarkWolf Point Shadow NearWorld + Origin Diagnostic V2 — Release Verification

**GitHub Actions:** [#41051538614](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/41051538614), **SUCCESS** (2026-10-30).  
**Accepted immutable Clean Production baseline:** [#41019985033](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/41019985033).  
**Artifact ID:** 12975425465.

## Reproducible hashes

- Accepted renderer original SHA-256: `d7423e8648e2de556f79c7cddecf1a8df16b9f60a46c503d1440089876116b45`.
- Diagnostic V2 renderer SHA-256: `94e7a7a5ee206de877eedc6e39881f4ad806c3a287aa884d89efba57d06c0ae8`.
- Downloaded V2 full release ZIP SHA-256: `562ece701f0ec5ad488387cc9dc72c213e1d81e4ee5ed5c36e0d508fbdf0a854`.
- V2 source patch SHA-256: `5ef575d5698883c5f9649b1bf9c69915073ad51429fda70b588f0470a919ddff`.

## Inspection results

- 57 original Clean Production files compared byte-for-byte.
- Exactly two original paths differ: `renderer_sp_rend2_x64.dll` and `docs/SHA256SUMS.txt`.
- Exactly 10 extra files: eight mode CFGs, one Russian/English README, one new diagnostic manifest.
- All archive members pass ZIP integrity and every SHA256SUMS entry matches its content.
- New DLL contains all five diagnostic CVar names V1+V2 and accepted HDR16F marker `_dwSunHalfRGBA16F`.
- GLSL 1.20 and 1.30 compilation, all exact SHA source guards, and cross-compiled Windows x64 checks passed in GitHub Actions.
- Gameplay and graphics quality with any nonzero V2 diagnostic parameters remain **UNVALIDATED** until user GPU A/B testing.

## Full asset coverage contract

At zero defaults, all opaque/alpha-cutout/BSP/model casters and receivers accepted under Stage11 remain available. V2 modes intentionally alter ONLY the diagnostic point-shadow map; they are **not** production quality fixes. Any future integration into Clean Production requires the user's GPU test proving improved shape while preserving full asset coverage, avoiding wall leaks, preserving HDR16F/Sun/Local/Fire/SSGI and maintaining FPS.

See [GPU A-H test instructions](DW_POINT_SHADOW_NEARWORLD_ORIGIN_DIAG_V2_TEST_RU.md).
