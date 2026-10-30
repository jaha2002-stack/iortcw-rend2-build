# DarkWolf Hybrid Relight V2 — technical architecture (2026-10-30)

## Verified foundation

- Required accepted run: **41019985033**; branch `rend2-sun-hdr16f-v1-clean-production-20261030`, commit `c653433e1b0a29b2f43f29a240b96a8192acb617`.
- GitHub artifact **12960988233**: outer SHA256 `6385f719eb29bfa2c4edd172cadc9b95b6c5f3d107d7e0e088ed25769a8df57f`; nested clean production SHA256 `e61a38fec90fbdece43364232c0064e40825eb86db7c035df9a46cddcf2cc869`.
- Accepted renderer SHA256 `d7423e8648e2de556f79c7cddecf1a8df16b9f60a46c503d1440089876116b45`, all effects-on pack, volumetric Sun HDR16F. Nothing in this foundation has been modified by V2.
- RTCW single player map format: **IBSP 47**, **17 lumps**, shader index/flags, surfaces and lightmaps **128x128 RGB8**; see `SP/code/qcommon/qfiles.h` and `SP/code/qcommon/surfaceflags.h` in ioRTCW (`438e7d413b5f7277187c35b032eb0ef9093ae778`).

## Problem: existing MapLighting is an energy suppressor

Legacy per-surface `lightmapColor.rgb *= u_MapLightingBakedScale` multiplies **all** previously baked lighting, including ambient bounce, direct and older shadows. Halving this term may make corridors dark; three local shadow slots/32 promoted fixtures cannot replace all high-order light transport. Current `r_mapLightingProfileEnable`/`maplighting/*.maplight` remain untouched in this development stage.

## Actual V2 solution: tagged SINGLE bake, not inferred decomposition

For each linear HDR luxel (before tonemap/gamma/exposure, clamping or 8-bit conversion):

```
E_full(x) = E_indirect_all(x) + E_direct_unselected(x)
          + SUM(source in selected) E_direct_source(x)

E_relight(x) = E_full(x) - M_eligible(x)
             * SUM(source in selected) remove_fraction(source) * E_direct_source(x)
```

- **Indirect light includes all bounced light** even that originating from a removed direct source; this preserves established room ambience.
- Direct sources must be tagged **in the SAME light solve**, so every shade, bounce, area sample, sun sample, and lightstyle uses consistent geometry, albedo, sample seeds, and ray occlusion.
- `E_direct_unselected` includes all direct contributions not being replaced, including sky/sun/emissives if not selected. Do not subtract an unrelated source.
- `remove_fraction` may be less than 1 for artistic continuity; no magic 0.25/0.5 blanket attenuation applied to whole RGB lightmaps.
- **Before** subtraction, verify numeric parity of tagged reconstruction with `E_full` for every RGB channel at every luxel. The tool presently checks abs error <= `1e-4 + 1e-5*max(E_full,E_reconstructed)` in linear units. Threshold must be calibrated to exporter precision before production acceptance.
- Selected source has a stable provenance ID (source `.map` entity signature or explicitly named shader sun/emissive). Restrict source subtraction to lights that are truly reconstructed by real-time `r_forceSun`/StaticPromote/dlights; otherwise preserve their direct contribution.

### Output and precision

Source layer images are **RGB PFM 32-bit linear float** (bottom row first). Eligible mask is **binary PGM 8-bit** (top row first), created by parser from BSP surface/lightmap associations and selected surface IDs, not guessed from color. PFM and PGM row order are corrected during composition. Full output is PFM and a JSON proof record; it is **not** a playable RTCW lightmap package.

### Native BSP safety

Fail closed for shader surface flags `SURF_SKY|SURF_NODRAW|SURF_NOLIGHTMAP|SURF_NODLIGHT|SURF_GLASS` and contents `WATER|LAVA|SLIME|FOG|TRANSLUCENT`; additionally exclude water/liquid/fog/sky/portal/mirror/glass/ice/alpha and other ambiguous shader names. Protect all texels shared with any surface not explicitly selected (including cross-material atlas overlaps). Preserve shader index and original lightmap UV layout hash. Unknown/non-128x128 formats are rejected; future compiler adapters must implement explicit provenance, not silently reinterpret data.

### Runtime light-source stability

The source replacement stage must later use stable FixtureId per lamp and bind the tagged source ID to runtime light ID; never make the fallback depend on camera proximity. If a promoted source is not active, a fallback needs to preserve a reasonable amount of direct light, or the subtraction must be gated in a tested manner. Maximum active fixtures <=32; original three shadow slots, `r_dlightMode 2`, `r_forceSun 1`; PBR deferred. Current renderer is unmodified. Future runtime must avoid abrupt temporal toggles and should not use `r_cubeMapping` as a substitute for repairing local surface lighting.

## Exporter integration: must be built next

Implement an extension inside a known Q3Map2-compatible **single-pass** lighting build, with three accumulators per luxel: unselected direct, selected direct per stable light source, and indirect summed across all bounce origins. Capturing only a `-bounceonly` pass or subtracting independently rendered lightmaps is **not** exact: differences in preprocessing, sampling, global bounce and nonlinear output transfer will break parity.

Compiler must emit **one immutable source registry and exact BSP atlas-layout fingerprint**. For every targeted source: confirm source identity, mapped shader, lightstyle, cone/attenuation, shadow-casting class, direct energy, and runtime replacement coverage. If the game uses classic BSP entities stripped of light entities, the original `.map` or manual source manifest becomes mandatory.

Tools `bsp.py` and `relight.py` currently **consume** those tagged layers but do not generate them. See `TAGGED_BAKE_COMPILER_CONTRACT.md`.

## Planned implementation stages

| Stage | Artifact | Test gate | Status |
|---|---|---|---|
| 0 | Exact release identity, no renderer edits | SHA256, five packs effects ON | Implemented |
| 1 | PK3/BSP map inventory and material exclusions | Original 32/32 retail BSPs; surface type-aware water/flare protection | **Implemented and real-map tested** |
| 2 | Tagged bake full/indirect/direct parity and mask compositor | No dark ambient/water edits; atomically fail | Implemented on synthetic tests |
| 3 | Compiler instrumentation for `.map`/shader-driven light contributions, single solve | Source IDs; per-luxel parity on user maps | Not implemented |
| 4 | Runtime external relit lightmap loader with original UV layout and strict fallback | A/B parity against base, no FPS/visual regressions | Not implemented |
| 5 | Scene acceptance Escape1/Factory/Assault/Norway/Crypt1 | Water, reflection, CSM, sun, lights, fire, fog, SSGI, all cfgs | Not tested |

## Stage 1 real-map findings

The user supplied the complete original 32-BSP `maps(2).zip` archive. Stage 1 supports valid `MST_FLARE` surfaces (`lightmapNum=0`, 0x0 rectangle) that are present in 24 maps; the original Stage 0 parser rejected them. In the corrected run 32/32 maps pass with no format errors (300,097 surfaces, 1,086 atlases, 7,632 retained light entities). Norway water `textures/liquids/water_norway` includes 226 explicitly protected BSP surfaces. `policy.py` builds read-only per-atlas ownership/coverage without modifying source BSPs. Real-world `.map` source geometry and original tagged-bake direct/indirect light are **not** in the archive. Next actual V2 step is acquiring or reconstructing a verified editor source map and instrumenting the light compiler, not silently splitting the combined RGB lightmap. Details in `docs/HYBRID_RELIGHT_V2_RETAIL_BSP_STAGE1.md`.

## Map test plan using original BSP archive

- **Escape1**: ceiling lamp, doctor office, guard-room stove, adjacent ambient shadow continuity.
- **Norway**: water MUST be excluded; check cubemap stability `r_cubeMapping 1`, BSP fog/translucent exclusion, sun on snow.
- **Factory**: tunnel lamp ambient; preserve SSGI no halo.
- **Assault**: sun direction/shadows, volumetric edges, rails.
- **Crypt1**: fire/Tesla light paths and grate caster/receiver.

Use automated masked image diff and static lightmap parity before any production release. Do not introduce telemetry/debug CVARs or change renderer defaults. V2 is currently off-device, not part of the user's clean production distribution.
