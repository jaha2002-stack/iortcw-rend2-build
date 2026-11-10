# DarkWolf PBR Studio V2.06.1 — Physical Relief Coupled Normal

V2.06.1 keeps the V2.06 AI Material Authoring pipeline and fixes the PhysicalReliefPOM normal/height mismatch:

- `_nh.RGB` remains tangent-space Normal.
- `_nh.A` remains the Physical Height field consumed by Rend2 POM.
- Physical Height structural gradients are now coupled into Normal RGB, so recessed mortar, cracks, bevels and stone edges are visible even near front-facing views where UV parallax displacement is subtle.
- The validated V2.06 micro/macro normal detail is retained and combined with the physical structural gradient.
- New UI control: **Physical height to normal coupling**, range `0.00..2.00`, masonry default `1.25`.
- Coupling changes Normal only; the authored Physical Height/POM field remains unchanged.
- Export contract remains: ordinary `_n.tga` and `_orm.tga` are 24-bit; `_nh.tga` is 32-bit because alpha carries Height.

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


## V2.05.1 Safe Material Export

V2.05.1 fixes Rend2 material registration and scripted-material replacement semantics without changing the validated V2.05 PhysicalReliefPOM map generation.

Rend2 discovers only `scripts/*.shader`. For each discovered basename it prefers a same-basename `.mtr`, and that `.mtr` replaces the complete `.shader` source for Rend2 parsing.

Export rules:

- **Implicit texture:** Studio owns one unique pair. The `.shader` is a real legacy fallback containing only ordinary diffuse/lightmap syntax. The same-basename `.mtr` contains diffuse + normal/normalParallax + ORM + lightmap.
- **Existing scripted material:** Studio preserves the complete original discovery `.shader` file and exports a complete same-basename `.mtr` based on the effective original script. Only selected material blocks are upgraded. Unselected neighboring definitions, surfaceParm, cull and unrelated stages remain present.
- Existing Normal/NormalParallax/Specular/ORM response stages are removed from the selected material before inserting the generated Normal + ORM response immediately after its primary diffuse stage and before the lightmap.
- One PK3 may contain more than one script pair when selected materials originate from different original shader files. This is intentional and avoids ambiguous duplicate shader definitions in a new unrelated script namespace.
- `*_nh.tga` remains RGB tangent-space Normal + A Height for Rend2 POM.


## V2.05.2 Stone Height Reconstruction

V2.05.2 keeps the V2.05.1 Safe Material Export rules and the accepted V2.03 Normal/ORM response. It changes only `PhysicalReliefPOM` Height reconstruction for `Stone`, `SnowyStone`, and `Brick`.

The rejected V2.05.1 game test exposed a specific failure mode: high-frequency grooves from the diffuse texture were being interpreted as displacement and produced visible wavy/accordion-like POM.

The V2.05.2 masonry path therefore:
- suppresses micro-frequency texture detail before Height classification;
- detects coherent dark mortar/cracks as seam recesses;
- suppresses broad dark stains with a neighborhood-occupancy guard;
- keeps stone faces on low-frequency plateaus with only restrained block-to-block variation;
- keeps micro-surface grain exclusively in the tangent-space Normal map;
- preserves V2.05.1 Safe Material Export and `*_nh` RGB Normal + A Height packing;
- leaves non-masonry PhysicalReliefPOM generation unchanged.

The self-test includes a deliberately wavy stone fixture and requires the reconstructed Height to suppress high-frequency embossing while retaining measurable mortar depth below stone faces.


## V2.06 AI Material Authoring

V2.06 keeps the validated V2.05.2 Stone Height Reconstruction and V2.05.1 Safe Material Export, then adds renderer-aware AI authoring for the exact PBR V3.2 contract.

Authoring modes:
- **Original Restore 4×** — Real-ESRGAN restoration while preserving the original RTCW composition.
- **Artistic Rebuild** — local stable-diffusion.cpp img2img generation of new BaseColor candidates that preserve the UV layout and RTCW visual identity.

Surface finishes:
- **Dry**
- **Wet**
- **Snowy**
- **WetSnow**
- **Mossy**

The AI stage authors/restores **BaseColor only**. Normal, Height, NormalHeight and ORM remain deterministic Studio outputs so they stay compatible with Rend2 PBR V3.2.

PBR V3.2 compatibility rules:
- `*_n.tga` and `*_orm.tga` remain 24-bit RGB.
- `*_nh.tga` remains 32-bit RGBA with RGB=Normal and A=Height.
- `ormMap` remains R=AO, G=Roughness, B=Metallic.
- Wet stone remains dielectric (Metallic=0); wetness is represented mainly by lower roughness.
- Snow remains dielectric and relatively rough.
- Finish authoring does not modify the validated POM Height geometry.
- PhysicalReliefPOM defaults to a safer masonry `parallaxDepth` near **0.010** instead of forcing 0.030.

Artistic prompts explicitly forbid baked directional shadows and painted specular highlights. This is important because real highlights must come from Rend2's GGX direct lighting / IBL, not from the BaseColor image.
