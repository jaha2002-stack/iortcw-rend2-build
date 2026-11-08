# DarkWolf PBR Studio V2

Windows authoring tool for ioRTCW Rend2 DarkWolf **r_pbr 3** materials.

V2 replaces the V1 one-size-fits-all luminance conversion with a material-aware, tile-safe PBR decomposition pipeline.

## V2 pipeline

1. Open a PK3 and choose a source texture.
2. Optional AI Restoration x4 with bundled Real-ESRGAN Vulkan.
3. Optional AI img2img variants with bundled stable-diffusion.cpp runtime and a user-selected local checkpoint.
4. Hybrid material classification from texture path + image statistics.
5. Material profile selection / manual override.
6. Tile-safe intrinsic decomposition:
   - removes broad baked/painted illumination from the relief signal;
   - suppresses saturated pigment changes from becoming false height;
   - separates fine and coarse material structure.
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

## Why V2 is more accurate than V1

V1 derived normal/AO/roughness mainly from source luminance.

V2 instead uses:
- sRGB-to-linear analysis;
- multi-scale local detail;
- large-scale illumination removal;
- chroma/pigment suppression;
- AO from reconstructed surface concavity rather than raw darkness;
- roughness from profile + micro-surface energy;
- material-specific metallic constraints;
- wrap-around filtering/gradients so tiled RTCW textures do not receive artificial edge seams.

This still cannot reconstruct ground-truth scanned material data from a single old diffuse texture, but it is substantially closer to the useful input range of DarkWolf PBR3.

## Rend2 compatibility

Main output:
- `<shader>_n.tga`
- `<shader>_orm.tga`

When the user explicitly enables parallax after validating the generated Height map:
- `<shader>_nh.tga` — RGB tangent-space normal, A height
- `<shader>_h.tga` — standalone authoring/debug height map

Explicit MTR export uses:
- `stage normalParallaxMap`
- `parallaxDepth <profile value>`
- `stage ormMap`
- existing BSP lightmap stage

Parallax is intentionally opt-in for diffuse-derived materials. It requires `r_parallaxMapping 1` in Rend2. The safe default exporter uses ordinary `stage normalMap`.

## V2 validation

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
