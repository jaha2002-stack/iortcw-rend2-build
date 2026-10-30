# DarkWolf Hybrid Relight V2 — Stage 1: validated retail BSP maps

Date: 2026-10-30. Exact production base: GitHub Actions **#41019985033**, commit `c653433e1b0a29b2f43f29a240b96a8192acb617`.

## Actual provided input (user-owned; NOT embedded in public source kit)

- Original archive: `maps(2).zip`
- Archive SHA-256: `94ebda268adf81f4a775bf954a8fdbb4e6098be99510831487626465dca7f6c6`
- **32 maps (`maps/*.bsp`)**, all RTCW IBSP version 47, **no editable `maps/*.map`**.
- Total: **300,097 surfaces**, **1,086 128x128 RGB8 lightmap atlases**, **7,632** retained `light*` entities.
- These are statistics from original BSPs. Light entities are candidates, **not proven 1:1 direct-light sources used during old BSP baking**.

## Critical real-map parser fix

The Stage 0 validator rejected most original RTCW maps when it encountered surfaces with `surfaceType=MST_FLARE=4`, `lightmapNum=0` and a **0x0** rectangle. Such flare records are normal RTCW BSP data and do not own lightmap texels.

Stage 1 accepts them, marks them `protected-flare`, never includes them in masks or reinterpret them as lightmapped faces. Zero-sized lightmap rectangles on *actual* planar/patch/trianglesoup surfaces still fail closed. Without this fix, 24 out of 32 retail maps (including Norway, Factory and Escape1) were incorrectly rejected. **All 32 pass after the fix.**

## Map-specific proof

| Original map | Surfaces | Atlases | Embedded `light*` | Flare surfaces | Protected water |
|---|---:|---:|---:|---:|---:|
| Norway | 8,972 | 92 | 79 | 55 | 226 `textures/liquids/water_norway` |
| Escape1 | 15,321 | 42 | 665 | 7 | 40 water-stain decal surfaces |
| Factory | 9,077 | 20 | 240 | 208 | 2 `textures/liquids/water_calm2` |
| Assault | 9,554 | 69 | 417 | 257 | 4 water-stain decal surfaces |
| Crypt1 | 14,103 | 18 | 468 | 0 | 0 matching water material names |

Norway BSP SHA-256: `413f9c9c91bff2350dea20fe7bf8ac23a3f55a755dcf2c120c5b63fd6a966dd6`.
Norway atlas layout SHA-256: `c4627c9d2effcb124e7f21fa4bb5dc9e48258ad3c5ee90ae377e430cd3db44f1`.

The actual 226 Norway water surfaces are excluded by `CONTENTS_WATER`, in addition to protective shader-name matching. Some water texels occupy native atlases 72–89; Stage 1 atlas ownership treats water as blocked, not a candidate for relighting. No claim is made that the old `norway.maplight` actually selected these surfaces; that is a separate investigation requiring the specific saved profile.

## Delivered new code

- `integration/hybrid-relight-v2/bsp.py`: repaired native `MST_FLARE` handling; lightmapped surface validity still enforced.
- `integration/hybrid-relight-v2/policy.py`: new **read-only** `audit-retail` companion. Produces one JSON policy per BSP, SHA provenance, candidate/blocked texel ownership per atlas, real water material surface count and a registry of embedded light candidates. Candidate registry has `source_bake_identity_verified=false` and `eligible_for_direct_light_subtraction=false` for every entity.
- `integration/hybrid-relight-v2/tests/test_real_bsp_safety.py`: added synthetic tests for flare/protected-water/overlap/parity. Optional tests use the user-provided 32-map archive without including it in GitHub.
- `relight.py`: unchanged Stage 0 compositor; still refuses to claim exact direct/indirect decomposition until a tagged single-solve compiler is supplied.

## Reproduce (Python 3.10+, standard library)

```sh
python integration/hybrid-relight-v2/policy.py /path/to/maps.zip --out /new/audit-folder
python -m unittest discover -s integration/hybrid-relight-v2/tests -v
# Local-only, optional:
DW_RTCW_ORIGINAL_MAPS_ZIP=/path/to/maps.zip python -m unittest discover -s integration/hybrid-relight-v2/tests -v
```

The preflight output cannot be installed into a game, because it does **not** contain altered lightmaps.

## Actual V2 implementation gate

A true replacement of baked **direct** light while preserving **all indirect** requires an audited source-tagged lighting solution from a capable compiler. `maps/*.bsp` and their existing 8-bit lightmaps do not carry a source-tagged decomposition. Original `.map` geometry was not provided inside these retail assets. Any BSP->MAP reconstruction will have to be separately validated and cannot be asserted bit-identical to id Software's editor source. Do not generate subtractive runtime lightmap patches or change production until this gate is passed.
