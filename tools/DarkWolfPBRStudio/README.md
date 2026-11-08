# DarkWolf PBR Studio V1

Windows desktop tool for preparing ioRTCW Rend2 DarkWolf r_pbr 3 materials.

## V1 goals

- Open an RTCW .pk3 archive directly.
- Browse/search JPG/TGA/PNG texture entries.
- Preview the selected original texture.
- Create local AI Restoration x4 with Real-ESRGAN.
- Create multiple local AI img2img variants with stable-diffusion.cpp.
- Press AI Next repeatedly to generate a new variant with a new seed while retaining previous candidates.
- Select any candidate from history before PBR generation.
- Generate *_n.tga tangent-space Normal and *_orm.tga with R=AO, G=Roughness, B=Metallic.
- A/B preview original vs selected variant, plus Normal and ORM previews.
- Export a new override PK3. The source PK3 is always read-only.
- Optional explicit BSP .mtr for implicit textures.
- Detect scripted material names in sibling PK3 files and warn before overriding them.

## Local AI

### Restoration

The packaged Windows build includes the portable Real-ESRGAN NCNN/Vulkan runtime and its standard models.
The application uses realesrgan-x4plus for general RTCW texture restoration/upscale.

### AI Variants / Next

The packaged Windows build also includes a pinned stable-diffusion.cpp Win64 Vulkan runtime.
A diffusion checkpoint is intentionally not embedded because checkpoints are multi-gigabyte and have their own licenses.
Choose a local .safetensors, .gguf, or .ckpt once in the UI. The path is remembered in
%LOCALAPPDATA%/DarkWolfPBRStudio/settings.json.

Each AI Next operation uses img2img, a new random seed, the configured strength and the user prompt.
Generated variants remain in session history and can be reviewed before PBR maps are generated.
Recommended texture-preserving img2img strength: 0.18-0.35.

## PBR3 material convention

For source textures/snow/s_cathedrale_c06.jpg the application exports:
- textures/snow/s_cathedrale_c06_n.tga
- textures/snow/s_cathedrale_c06_orm.tga

ORM convention: R = Ambient Occlusion, G = Roughness, B = Metallic.
Stone/wood/plaster should normally remain metallic 0.

## Export modes

### Safe map-only mode

Recommended when an existing scripted material is detected. The exported PK3 contains BaseColor (when selected),
Normal, ORM and a manifest. Rend2 PBR3 can use the maps without replacing the original shader definition.

### Explicit BSP PBR MTR

Recommended for an implicit lightmapped BSP texture. PBR Studio writes a small .mtr containing
Diffuse + Normal + ORM + lightmap stages. This is the same structure validated by the Escape1 PBR TestLab.
Do not force this mode over complex animated/blended shaders without reviewing the result.

## V1 scope

V1 is optimized for RTCW BSP/lightmapped world textures, because that is the path validated by
DarkWolf PBR BSP Relight V4.2. Model/character material tooling can be expanded after the BSP workflow is stable.

## Build

dotnet publish tools/DarkWolfPBRStudio/DarkWolfPBRStudio.csproj -c Release -r win-x64 --self-contained true

GitHub Actions workflow: .github/workflows/DW_PBR_STUDIO_WINDOWS.yml
The CI package downloads and bundles pinned local AI runtimes before creating the Win64 ZIP.
