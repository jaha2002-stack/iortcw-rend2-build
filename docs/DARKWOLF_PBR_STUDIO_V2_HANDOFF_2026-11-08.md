# DarkWolf PBR Studio V2 — Implementation / Test Handoff

Date: 2026-11-08
Target renderer: ioRTCW Rend2 DarkWolf r_pbr 3, including BSP Relight V4.2.
Source branch: feature/darkwolf-pbr-studio-v2

## Purpose

PBR Studio V2 upgrades material authoring quality while intentionally leaving the renderer unchanged.
The goal is to determine how much of the current r_pbr 3 potential can be reached with better material inputs
before changing environment BRDF / IBL architecture.

## V2 material pipeline

1. PK3 remains read-only.
2. Select original texture.
3. Optional local Real-ESRGAN x4 restoration.
4. Optional stable-diffusion.cpp img2img variants / Next history.
5. Hybrid material classification:
   - semantic shader/path keywords;
   - image luminance, saturation, variance and detail statistics;
   - manual material profile override remains available.
6. Profile-constrained intrinsic decomposition:
   - sRGB -> linear analysis;
   - broad illumination removal;
   - fine/coarse structure separation;
   - chroma/pigment suppression so color/stains are less likely to become false geometry;
   - tile-safe wrapped filtering and gradients.
7. Height reconstruction.
8. Tangent-space Normal from reconstructed Height with maximum slope safety.
9. AO from local Height concavity, not raw BaseColor darkness.
10. Roughness from material profile + micro-surface energy.
11. Metallic constrained by material type.
12. Optional Rend2 native NormalHeight (_nh):
    - RGB = Normal XYZ
    - A = Height
13. Validation.
14. Export to a new override PK3.

## Material profiles

GenericDielectric, Stone, SnowyStone, Brick, Concrete, Plaster, Wood,
BareMetal, PaintedMetal, RustedMetal, Ceramic, Fabric, Leather, SnowIce, Soil.

Each profile specifies:
- normal strength;
- height contrast;
- fine/coarse contribution;
- pigment suppression;
- AO strength/floor;
- roughness range and base;
- micro-roughness response;
- metallic;
- parallax recommendation and depth;
- AI prompt hint.

## Renderer-compatible output

Always:
- <shader>_n.tga
- <shader>_orm.tga (R=AO, G=Roughness, B=Metallic)

When parallax is enabled:
- <shader>_nh.tga (RGB normal, A height)
- <shader>_h.tga (authoring/debug height)

Explicit implicit-BSP MTR:
- stage diffuseMap
- stage normalParallaxMap + parallaxDepth, or normalMap when parallax is disabled
- stage ormMap
- original lightmap stage

The source PK3 is never overwritten.

## Physical safety / QA

V2 self-test validates:
- SnowyStone classifier;
- BareMetal classifier;
- height dimensions;
- normal/ORM dimensions;
- non-flat normal response;
- maximum normal slope safety;
- dielectric stone metallic = 0;
- bare metal metallic = 1;
- roughness bounds;
- AO bounds;
- meaningful _nh alpha height;
- PK3 output contains _n/_nh/_h/_orm;
- explicit MTR uses normalParallaxMap, parallaxDepth and ormMap.

The normal generator caps extreme slopes rather than letting painted high-contrast edges create unstable,
near-horizontal normals.

## V2 test procedure on PC

Recommended first material:
textures/snow/s_cathedrale_c06.jpg

1. Open pak0.pk3.
2. Search for s_cathedrale_c06.
3. Confirm automatic profile SnowyStone.
4. Generate PBR3 material without AI first.
5. Review Height, Normal and ORM previews and Validation.
6. Export override PK3.
7. Run r_pbr 3.
8. Compare the same outdoor Escape1 wall close-up used by TestLab.
9. Optionally enable r_parallaxMapping 1 for _nh validation.
10. Then repeat after AI Restore x4.
11. Then compare one or more low-strength AI Next variants.

Do not judge AI img2img and deterministic PBR decomposition in one step. First validate the deterministic
V2 maps from the original BaseColor; then separately evaluate AI-restored or artistic BaseColor variants.

## Renderer work intentionally deferred

Do not change PBR3 renderer until Studio V2 material tests are accepted.

Next renderer milestone:
- true GGX prefiltered environment cubemap;
- proper specular convolution mip chain;
- 2D BRDF integration LUT;
- split-sum IBL integration;
- regression isolation against current BSP Relight V4.2.

This will be implemented as a separate renderer stage after V2 material acceptance.
