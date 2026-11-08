# DarkWolf PBR Studio V2.04

Windows authoring tool for ioRTCW Rend2 DarkWolf **r_pbr 3** materials.

V2.03 contains two first-class relief modes. **ReferenceHandGenerated** reproduces the first successful Escape1 hand-generated PBR recipe as a selectable option. **MacroReliefEnhanced** keeps that reference Height/AO/Roughness unchanged and increases only broad, coherent structural normal gradients, so extra macro relief cannot create new interior pits from JPEG specks.

## V2.03 relief modes

- **ReferenceHandGenerated** — direct compatibility/reference mode: 74% fine Gaussian structure + 26% coarse structure, no high-pass, no percentile normalization, no groove detector.
- **MacroReliefEnhanced** — default: the exact same height and ORM response as ReferenceHandGenerated, with a multi-scale coherence mask that increases normal slope only on broad stone/block boundaries.
- **StructurePreservingV202** — retained as a compatibility option for comparing earlier V2.02 behavior.

## V2.03 pipeline

1. Open a PK3 and choose a source texture.
2. Optional AI Restoration x4 with bundled Real-ESRGAN Vulkan.
3. Optional AI img2img variants with bundled stable-diffusion.cpp runtime and a user-selected local checkpoint.
4. Hybrid material classification from texture path + image statistics.
5. Material profile selection / manual override.
6. Structure-preserving geometry decomposition:
   - uses perceptual/sRGB structure for geometry, matching the successful hand-generated reference;
   - edge-preserving denoise suppresses JPEG ringing and pixel chatter;
   - broad stone/block shape is preserved instead of being removed as low-frequency illumination;
   - fine and coarse absolute structure are blended without percentile normalization;
   - local dark valleys are treated as restrained mortar/crack depressions;
   - saturated pigment changes are suppressed from becoming false height.
7. Generate:
   - Height authoring map;
   - tangent-space Normal;
   - Rend2 NormalHeight `*_nh.tga` with height in alpha;
   - ORM `*_orm.tga` with R=AO, G=Roughness, B=Metallic.
8. Validate normal slope, AO, roughness, metallic, height range and texture seams.
9. Export a new override PK3. The source PK3 is never modified.

## Material profiles

- Generic dielectric
- Stone
- Snowy stone
- Brick
- Concrete
- Plaster
- Wood
- Bare metal
- Painted metal
- Rusted metal
- Ceramic
- Fabric
- Leather
- Snow / ice
- Soil / ground

Profiles control physically meaningful defaults such as normal strength, height contrast, AO, roughness, metallic and parallax depth.

The automatic classifier is deliberately conservative. It uses strong path semantics when available and falls back to image statistics. The user can always override the detected material type.

## Why V2.03 fixes the V2.01 failure mode

V2.01 over-emphasized high-pass residuals. On old JPEG diffuse textures this could turn compression noise and tiny color variations into embossed micro-relief even when the individual maps looked technically valid.

V2.03 instead uses:
- edge-preserving denoise before geometry extraction;
- perceptual/sRGB geometry luminance rather than linear-dark-region amplification;
- absolute multi-scale structure, not high-pass-only relief;
- no percentile normalization of the height signal;
- a small gradient noise floor and a 50-degree normal-angle safety cap;
- AO/roughness response tuned back toward the visually successful Escape1 reference;
- chroma/pigment suppression and tile-safe wrap filtering.

This still cannot reconstruct ground-truth scanned material data from a single old diffuse texture, but it is substantially closer to the useful input range of DarkWolf PBR3.

## Rend2 compatibility

Main output:
- `<shader>_n.tga`
- `<shader>_orm.tga`

When the selected material profile recommends parallax and the user enables it:
- `<shader>_nh.tga` — RGB tangent-space normal, A height
- `<shader>_h.tga` — standalone authoring/debug height map

Explicit MTR export uses:
- `stage normalParallaxMap`
- `parallaxDepth <profile value>`
- `stage ormMap`
- existing BSP lightmap stage

Parallax requires `r_parallaxMapping 1` in Rend2. If parallax is disabled, the exporter uses ordinary `stage normalMap`.

## V2.03 validation

The Windows CI executes a real self-test before packaging. It verifies:
- SnowyStone and BareMetal classification;
- Normal/ORM dimensions;
- normal slope safety;
- dielectric/metal metallic rules;
- AO/roughness bounds;
- meaningful Height range;
- `_nh` alpha height;
- PK3 export;
- `normalParallaxMap`, `parallaxDepth` and `ormMap` output.

## Local AI

Real-ESRGAN runtime is bundled.

stable-diffusion.cpp Vulkan runtime is bundled. Model weights are not redistributed; select a local compatible `.safetensors`, `.gguf` or `.ckpt` model once in the UI.

The **AI Next** workflow remains intentionally separate from deterministic PBR decomposition: AI may improve/restore the BaseColor candidate, while the final PBR maps are generated under physical material constraints.

## Build

```powershell
dotnet run --project tools\DarkWolfPBRStudio.SelfTest\DarkWolfPBRStudio.SelfTest.csproj -c Release
dotnet publish tools\DarkWolfPBRStudio\DarkWolfPBRStudio.csproj -c Release -r win-x64 --self-contained true
```

CI: `.github/workflows/DW_PBR_STUDIO_WINDOWS.yml`


## V2.03 anti-pit invariant

The self-test verifies that ReferenceHandGenerated and MacroReliefEnhanced produce byte-identical Height maps. MacroReliefEnhanced may only alter tangent-space normal slopes at coherent macro boundaries; it is not allowed to invent new height depressions. AO and roughness remain the hand-reference response.


## V2.04 Batch Material Set

V2.04 keeps the validated V2.03 ReferenceHandGenerated and MacroReliefEnhanced material quality and adds bulk authoring:

- Ctrl/Shift multi-select many textures from one source PK3.
- Generate the selected set with one shared profile/mode configuration.
- Review every generated material in the Batch Review list before export.
- Remove rejected items without discarding the rest of the batch.
- Export all accepted materials into one PK3.
- Export one combined `scripts/dw_pbrstudio_v204_batch.mtr` containing every material block.
- Implicit textures automatically receive a complete diffuse/Normal/ORM/lightmap material definition.
- Existing scripted materials are preserved and only their Normal/ORM stages are replaced or inserted; unrelated stages and surface properties stay intact.
- Batch manifest records source shader, generated maps, validation, settings, and scripted-material provenance for every item.

For a batch made from original retail BaseColor textures, the override PK3 contains the generated PBR maps and combined MTR without redundantly copying the source BaseColor images.
