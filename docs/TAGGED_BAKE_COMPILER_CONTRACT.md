# Strict compiler/exporter contract: `darkwolf.hybrid-relight.v2.tagged-bake.v1`

The offline assembler is **not** a global illumination solver. This contract describes outputs an audited **modified single-solution compiler** must produce to reach physical separation of legacy lightmap lighting.

## Inputs required

1. Original editable `maps/<map>.map` (geometry/entity keys for source identity), matching `.bsp` with RTCW v47 surface and 128x128 lightmap layout.
2. Complete shader source files referenced by emitting, sky, translucent and solid materials; compile settings/raytracer version; lightstyle information.
3. Stable source ID for every replaced source: map entity IDs derived from exact entity keys, or explicitly provenance-backed `shader-sun`/`shader-emissive` names.
4. Compilation with identical geometry, bounce count, shading, random seeds, sky/emissive properties and correct linear color transfer for all layers.

## Hook points (design for q3map2 or other RTCW-compatible compiler)

During each sample's direct-light accumulation:

- Determine which *physical source* produced that energy sample, before it is mixed into the lightmap buffer.
- If source has an explicit dynamic counterpart selected for removal, add irradiance RGB to `selected_direct[source_id][luxel]`.
- Otherwise add to `unselected_direct[luxel]`.
- Indirect/bounce samples must accumulate to `indirect_all[luxel]` regardless of the ancestor source; **never delete bounce just because a direct source will be replaced**.
- The complete physical solution must accumulate to `full[luxel]` using the same sample normalization, surface response and shadowing as the components. Re-summing component buffers must match `full` before any sRGB/gamma/tonemap, overbright, scaling, clamp, dithering or texture packing.
- Store `compiler.build_id`, source registry, deterministic `atlas_layout_sha256`, input hashes, samples/bounce and version metadata. Any missing source class becomes unselected direct (fail closed).

## Manifest shape

All relative files below must reside under the same input directory as `manifest.json`, and `file_sha256` must contain the actual SHA256 for each one. Placeholder text is illustrative only.

```json
{
  "schema": "darkwolf.hybrid-relight.v2.tagged-bake.v1",
  "base_run": 41019985033,
  "base_commit": "c653433e1b0a29b2f43f29a240b96a8192acb617",
  "map_name": "norway",
  "source_map": "norway.map",
  "source_bsp": "norway.bsp",
  "atlas_layout_sha256": "<sha256-from-bsp.py-audit>",
  "compiler": {
    "build_id": "<audited-tagged-q3map2-build>",
    "tagged_direct_indirect": true,
    "same_radiosity_solution": true,
    "color_space": "linear-rgb",
    "output_units": "irradiance"
  },
  "source_registry": [
    {"id": "<audit-map-generated-ID>", "kind": "map-light"}
  ],
  "file_sha256": {
    "norway.map": "<sha256>", "norway.bsp": "<sha256>",
    "full.pfm": "<sha256>", "indirect.pfm": "<sha256>",
    "unselected_direct.pfm": "<sha256>", "lamp_direct.pfm": "<sha256>",
    "eligible.pgm": "<sha256>"
  },
  "atlases": [
    {
      "id": "atlas0000",
      "lightmap_index": 0,
      "selected_surface_ids": [0],
      "eligible_mask": "eligible.pgm",
      "full": "full.pfm",
      "indirect": "indirect.pfm",
      "unselected_direct": "unselected_direct.pfm",
      "selected_direct": [
        {"source_id": "<audit-map-generated-ID>", "file": "lamp_direct.pfm", "remove_fraction": 1.0}
      ]
    }
  ]
}
```

These **are placeholders**, not a bake ready for the tool. `source_bsp` atlas layout hash must agree with existing surface UV/rect assignments. `selected_surface_ids` must be actual BSP surfaces for that specific atlas and may not include water, fog, sky or materials not definitively opaque. Mask content must match the fail-closed `bsp.py make-mask` result exactly.

## Critical non-goals

- This contract does not claim to recover lighting from stock 8-bit RGB lightmaps.
- It does not use independently baked `-bounceonly` as proof of indirect separation, or subtract two gamma-encoded LDR images.
- It does not guarantee current dynamic lights cover all removed direct sources. Runtime matching and fallback are separate acceptance gates.
- It does not add any renderer change, user map asset, or proprietary texture to GitHub.

## Proofs emitted by assembler

- Full tagged sum per component matches `full` for all RGB luxels, absolute and relative error in JSON.
- PGM mask is byte-for-byte equivalent to BSP-validated selected surface mask.
- Untouched base renderer is pinned by separate `baseline.py`.
- Output only after *all* atlases pass, written atomically into a new target folder; no mutation of bake input, PK3 or production files.
