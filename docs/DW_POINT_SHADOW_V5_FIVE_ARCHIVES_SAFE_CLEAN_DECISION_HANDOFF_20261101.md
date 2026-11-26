# Point Shadow V5 after two attempts — decision for SAFE final Clean (2026-11-01)

## Test inputs and evidence

Five valid user V5 ZIPs: `DW_PS_V5_boss1_20261101_150636.zip`, `DW_PS_V5_factory_20261101_150800.zip`, `DW_PS_V5_crypt1_20261101_150922.zip`, `DW_PS_V5_crypt1_20261101_151050.zip`, `DW_PS_V5_crypt2_20261101_151156.zip`. All ZIP CRC and 29 supplied JPEG SHA-256 entries PASS. Boss1 phase 02 JPEG is absent, but screenshot write logged. Every other phase JPEG exists. All sources and caster group counts below are taken from these ZIPs. 

### Boss1 (GPU PASS)

Selected capture `(-2764,-219,-24)`. V5 mode1 and mode3 skip exactly **one** map-local world surface `7232` (`textures/metal_misc/ametal_m03dm`), three shadow draw calls. Mode2 skips none. Large solid polygon behind spotlight disappears in mode1/mode3 and returns in 01/04/06; legitimate stand and bracket shadows remain. The 01 vs 06 and 04 vs 06 images have **zero pixels differing >15 RGB** outside HUD; 03 vs 06 has **23,005 pixels** differing in x549..772, y122..356, and zero in stand region. V3.2 had already confirmed independent A/B/A. Map-local source+unique AABB+material fingerprint is acceptable. A global material ban or numeric BSP-ID ban is not.

### Factory (NO PROVEN EXCESS-SHADOW FIX)

Capture `(-96,-952,-203)`; matching ladder rails world surface IDs `3576,3580`, material `metal_m01_blood`; mode1 skip=0, mode2/3 skip=8 draw calls. The thick horizontal/diagonal wall shadow survives rail filtering. Some legitimate narrow lines change. Cannot certify the broad shadow artificial OR fully natural; preserve source geometry. No production source-local rail suppression.

### Crypt1 — TWO DISTINCT fixtures

- `150922`, selected capture `(384,512,160)`: dish=18, radialCage=16, mode1/2/3 skips **60/72/132**. Four of the supposedly dish candidates are `textures/props/torch_ember` surfaces, revealing a false-positive risk. Mode1 produces a large brighter floor region with harsh cage-like sharp shadows. Initial warmup vs restore differs 0.34% pixels >15, but second labelled “stable” baseline differs 14.04%. The purported baseline is NOT stable.
- `151050`, selected capture `(-928,-64,256)`: dish=10, radialCage=16, mode1/2/3 skips **54/72/126**. The mode1 image differs from restored at just 0.22% of pixels outside HUD; no visible robust octagon correction. Other variations mostly flame animation.

### Crypt2 (NO RELIABLE PHYSICAL FIX)

Selected capture V5 `(320,-384,288)`, different fixture from V4 prior `(-896,-384,288)`. dish=10, radialCage=16, mode1/2/3 skips **54/72/126**. Mode1 alters the octagonal shadow but darkens broad surroundings; mode3 can remove it, but removes all cage panels as well, risking genuine shadows. V5 nominal stable baseline vs restored differs **676,039 pixels >15 (68.77% of whole image)** outside HUD; warmup vs restored differs 26.28%. Not physically validated; production must **not** suppress dish/cage globally.

## Hard two-attempt stop and Clean decision

The two user-facing experimental releases V4 #41292154221 and V5 #41294915333 have been consumed. **No further diagnostic builds are authorized**. Full-game universal shadow correctness was NOT established.

Next and third release is **Conservative SAFE Clean Production**, not a falsely named universal shadow fix:
- Accepted immutable original #41019985033, newest accepted Texture & Material V2 FINAL #41286257713.
- Preserve all five accepted quality CFG profiles, game EXE, qagame/cgame/ui DLLs and trusted assets from texture final byte-for-byte.
- Rebuild only renderer from exact accepted Texture V2 source plus **one** Boss1 source-local AABB-confirmed caster exception. No baked-in map-independent material ban, no global numeric Surface ID, no new diagnostic CVar, telemetry or test CFGs.
- This exception matches: `boss1`, `maps/boss1.bsp`, point-shadow capture `(-2764,-219,-24)` ±0.25, numWorldSurfaces 7274, total surfaces 7791, `textures/metal_misc/ametal_m03dm`, unique AABB `(-2799.02,-229.78,-40.53)-(-2774.36,-210.73,-16.56)` ±0.25. Any mismatch => fail-open.
- Other lights and receivers, Fire/Tesla shadows, Sun/CSM, SSGI, Bloom/volumetrics, Texture Fidelity, CAS/LUT/A2C, 32 StaticPromote lamps and **3 shadow slots** stay at accepted behavior.
- Factory/Crypt1/Crypt2 remain **unmodified**, unresolved. Do not erase physically plausible shadow geometry.

## CI build and acceptance rule

Source patch: `integration/point-shadow-safe-final-clean/apply.py`. Exact expected V2 backend SHA-256: `ee22de02f024fccbad22c69d5b6c1ede5c56b2f4f3bd6d307c6880ad5d950be3`. 

Packager: `integration/point-shadow-safe-final-clean/package.py` uses accepted final texture artifact #13074798665, SHA-256 `2fa5947c2562db208ab586c450afbb93420423a0dbb67a4352d6ed06af720837`, accepted DLL `83e492871751cc4c37baf9909350a71ce0c90f3c21b895c2e8d572aa21b40acc`.

Release must PASS original binary/ZIP proof, 5 preserved CFG profiles, all 59 unrelated accepted production files preserved byte-for-byte, PE check, absence of V3/V4/V5 diagnostic CVar strings and SHA256SUMS check. CI compilation does not replace user GPU visual acceptance of the *new* clean DLL; do not overstate it.

For extended Russian forensic report, see the conversation-generated `DarkWolf_V5_FINAL_GPU_FORENSIC_REPORT_RU.md`.
