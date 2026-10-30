# DarkWolf Hybrid Relight V2 — Stage 1 retail-BSP preflight + tagged-bake compositor

**Pinned production foundation**: [GitHub Actions #41019985033](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/41019985033); `c653433e1b0a29b2f43f29a240b96a8192acb617`.

This is a **read-only offline prototype**, not a new renderer build, PK3, nor a finished lighting solver. Its purpose is to obtain the *exact* separation of direct and indirect light from a future instrumented one-pass lighting compiler, **not** estimate it from existing 8-bit lightmap RGB.

## Implemented

- `bsp.py`: reads original RTCW SP **IBSP v47**, audits entity/classname light sources, shader flags, BSP surface -> 128x128 lightmap geometry; scans `maps/*.bsp` inside original game PK3 **without modifying the archive**.
- `bsp.py make-mask`: creates a fail-closed **per-lightmap texel mask** for explicitly selected BSP surfaces. Rejects water, sky, fog, glass, lava, translucent, decals and lightmap-free materials; disables any texel overlapping an unselected BSP surface. No automatic light removal.
- `relight.py audit-map`: reads original editable `.map` source light entities and deterministic source IDs.
- `relight.py compose`: requires **same-solution, source-tagged, linear HDR** irradiance from an instrumented compiler, checks SHA256 provenance and full-bake additive parity, then removes only the direct contribution of selected sources on eligible texels. Preserves *all indirect*, unselected direct and protected materials; atomically publishes outputs only after all checks pass.
- `baseline.py`: verifies the **exact accepted** downloaded artifact and nested clean-production Win64 renderer, without altering either.
- `policy.py`: **all-32-maps read-only preflight**. Produces one derived metadata file per map, including BSP-aware water exclusion, per-atlas texel ownership and a *non-authoritative* registry of embedded light-entity candidates. No game BSPs or lightmap RGB pixels are copied into outputs.
- RTCW `MST_FLARE=4` with zero lightmap rectangle is correctly accepted and protected (original Stage 0 bug fixed), while malformed genuine lightmapped faces are still rejected.
- **19 tests**, including optional execution against the user's original retail 32-map archive. CI works without proprietary assets.
- All retained game-light entities are **unverified candidates**, not valid targets for direct-light subtraction. Tagged compiler exporter, source `.map` provenance and an ingame runtime importer are still required for actual V2 replacement.

## Quick start (Python 3.10+, standard library only)

From repo root:

```bash
python integration/hybrid-relight-v2/baseline.py /path/to/base_41019985033.zip
python integration/hybrid-relight-v2/bsp.py audit-pk3 /path/to/sp_pak1.pk3 --only norway
python integration/hybrid-relight-v2/bsp.py audit-bsp /path/to/norway.bsp --surfaces
python integration/hybrid-relight-v2/relight.py audit-map /path/to/norway.map
python -m unittest discover -s integration/hybrid-relight-v2/tests -v
python integration/hybrid-relight-v2/policy.py /path/to/maps.zip --out /new/report/folder
# Optional original-game integration tests, on YOUR machine only:
DW_RTCW_ORIGINAL_MAPS_ZIP=/path/to/maps.zip python -m unittest discover -s integration/hybrid-relight-v2/tests -v
```

Build a protection mask **only after auditing `surface.id`, `lightmap_id`, and material**:

```bash
python integration/hybrid-relight-v2/bsp.py make-mask /path/to/norway.bsp --atlas 0 --surface 0 --out /path/to/eligible.pgm
```

`0` values above are **syntax examples**, not known safe Norway indices. The tool will reject protected/mismatched selections. The compiler must emit the full, indirect, unselected-direct and chosen per-source direct layers in **one** solve. After generating and SHA256-pinning a conforming manifest:

```bash
python integration/hybrid-relight-v2/relight.py compose /path/to/tagged-bake/manifest.json --check-only --out /new/output/folder
python integration/hybrid-relight-v2/relight.py compose /path/to/tagged-bake/manifest.json --out /new/output/folder
```

The `--out` folder must not exist and must not be inside the immutable bake-input directory. Input `.map`, `.bsp`, source shader files, PK3s and original renderer are NEVER edited.

## Verified on original RTCW BSPs (Stage 1)

The locally supplied original `maps(2).zip` was tested without modifying it:
32/32 RTCW IBSP v47 BSPs accepted, 300,097 BSP surfaces, 1,086 native lightmap atlases, and 7,632 embedded light-class entities identified. Norway: 8,972 surfaces, 92 atlases, 79 light entities; all **226** BSP surfaces using `textures/liquids/water_norway` are **protected**. 55 RTCW flare surfaces are separately excluded. See `docs/HYBRID_RELIGHT_V2_RETAIL_BSP_STAGE1.md`.

The large audit report with 32 per-map JSON files is distributed separately with the local stage package, **not committed as game data** to GitHub. This Stage 1 is still read-only and never edits the renderer or any lightmap.

## Essential limitations

**Retail `.pk3` files normally contain only compiled `.bsp` maps.** `.bsp` provides geometry, entities and combined low dynamic range lightmaps, **not** separately baked direct and indirect irradiance. Having 32 retail BSP maps is enough to audit material exclusions and surface layout, but is **not** enough to obtain mathematically exact source separation. The user must supply the editable original `.map` *and* compile assets, or an audited compiler/reconstruction workflow must be developed. BSP->MAP decompilation is generally lossy and cannot be described as the original source.

**Tagged light-bake exporter and compatible production runtime lightmap importer are not implemented in this stage.** There is no in-game change, no relit Norway runtime, and no production claim. Existing `maplighting/*.maplight` profiles should not be silently migrated into V2. See `docs/HYBRID_RELIGHT_V2_ARCHITECTURE.md` and `docs/TAGGED_BAKE_COMPILER_CONTRACT.md` for next implementation steps.

Do not upload or redistribute commercial RTCW map assets to a public GitHub repository. Audit outputs and user-owned source data should be kept private.
