# DarkWolf PBR V2 — Architecture Audit & Implementation Handoff

Date: 2026-11-07  
Production baseline: GitHub Actions Run #42217883095  
Baseline commit: `0ef4fc401daff30c230ccb8226a8029fb0a3519f`  
Accepted inherited base: Run #42198541106  
Upstream renderer ancestry: `iortcw/iortcw@438e7d413b5f7277187c35b032eb0ef9093ae778`

## 1. Scope and non-regression contract

PBR V2 is implemented as an opt-in renderer path. The existing paths must remain byte/logic equivalent where possible:

- `r_pbr 0`: legacy non-PBR Rend2 behavior.
- `r_pbr 1`: existing Rend2 PBR behavior.
- `r_pbr 2`: DarkWolf PBR V2 path.

The production defaults remain unchanged. PBR V2 must not alter FireVol, IFLC, ELSS, dynamic-light budgets, shadow-slot policy, CSM, SSGI, volumetric, texture/material fidelity, Bloom, ToneMap, CAS or LUT defaults.

The current production TestLab contract remains:
- `r_staticPromoteMaxLights = 32`
- `r_dlightShadowMaxLights = 3`
- production `r_pbr = 0`

## 2. Exact architectural audit

### 2.1 Current PBR path

The inherited Rend2 already contains a first-generation PBR path in `glsl/lightall_fp.glsl`.

Current material interpretation in `USE_PBR`:
- diffuse RGB = base color
- specular R = gloss/smoothness source
- specular G = metallic
- dielectric F0 = 0.04
- cubemap reflection uses `textureCubeLod()`
- roughness chooses an ordinary cubemap mip
- input/output transfer is approximated with square/sqrt instead of precise sRGB
- current environment BRDF is a compact approximation
- cubemap mips are generated with `qglGenerateTextureMipmapEXT`, not GGX convolution

### 2.2 File responsibilities

#### `SP/code/rend2/tr_shader.c`
Current role:
- parses `normalMap`, `normalParallaxMap`, `specularMap`
- parses scalar `gloss`, `roughness`, `specularScale`
- collapses diffuse/normal/specular/lightmap stages into `lightall`
- auto-discovers `_nh`, `_n`, `_s`

PBR V2 changes:
- preserve all existing shader syntax
- add opt-in `stage ormMap`
- for `r_pbr >= 2`, auto-discover `_orm` before legacy `_s`
- mark ORM layout without adding another texture unit
- keep `_s` as compatibility fallback

#### `SP/code/rend2/tr_shade.c`
Current role:
- binds diffuse/lightmap/normal/deluxe/specular/cubemap
- passes `u_NormalScale`, `u_SpecularScale`, `u_EnableTextures`
- `u_EnableTextures.z` already indicates whether a real specular texture is bound

PBR V2 changes:
- preserve texture-unit layout
- reuse `TB_SPECULARMAP` for either legacy spec/gloss or packed ORM
- use a sentinel in `u_SpecularScale.z` for packed ORM, avoiding a new uniform and avoiding texture-unit growth
- no default changes

#### `SP/code/rend2/tr_glsl.c`
Current role:
- injects `USE_PBR`
- injects roughness mip count
- compiles `lightall`
- binds all current samplers

PBR V2 changes:
- keep `USE_PBR` for all nonzero legacy-compatible modes
- inject `USE_PBR2` only for `r_pbr >= 2`
- V3 adds a conservative IBL/cubemap quality define
- no new sampler needed for V1/V2

#### `SP/code/rend2/tr_image.c`
Current role:
- chooses internal texture format
- creates mipmaps
- normal-map special handling
- color mip filtering uses an sRGB-aware path

PBR V2 changes:
- V2 adds a dedicated linear data-map image type for ORM
- ORM must not receive color/light scaling
- ORM mip generation must be linear channel averaging, not color-space filtering
- normal-map path remains unchanged

#### `SP/code/rend2/glsl/lightall_fp.glsl`
Current role:
- direct lighting
- normal/parallax
- legacy PBR material interpretation
- environment reflection

PBR V2 changes:
- V1: precise sRGB transfer helpers, GGX NDF, Smith correlated visibility, Schlick Fresnel
- V1: keep legacy `USE_PBR` branch untouched when `USE_PBR2` is absent
- V2: decode packed ORM as AO/Roughness/Metallic
- V2: material AO affects indirect/ambient contribution only
- V3: improved split-sum-style environment BRDF approximation and roughness-to-mip calibration

#### Cubemap generation (`tr_backend.c`, `tr_bsp.c`)
Current role:
- renders cubemap faces
- calls ordinary `qglGenerateTextureMipmapEXT`
- loads exported DDS cubemaps with mipmaps

PBR V2 changes:
- V1/V2: no cubemap-generation mutation
- V3: keep existing cubemap capture and DDS compatibility, but calibrate roughness sampling to the available mip pyramid
- true GGX offline/runtime convolution is explicitly deferred to V3.1 because it requires a new prefilter shader/FBO pass and materially increases regression surface

This V3 choice is intentional: it gives a measurable IBL improvement without rewriting cubemap capture in the first production candidate.

## 3. Staged implementation

### V1 — PBR2 Core, legacy-safe

Goal: modern direct BRDF while preserving all old rendering paths.

Changes:
1. Add `USE_PBR2` for `r_pbr >= 2`.
2. Add exact sRGB transfer functions.
3. Add GGX/Trowbridge-Reitz distribution.
4. Add Smith GGX correlated visibility.
5. Add Schlick Fresnel.
6. Clamp roughness to a safe floor.
7. Continue consuming existing Rend2 specular layout for compatibility.
8. Keep `r_pbr 0/1` source path unchanged.

Acceptance:
- GLSL compiler PASS.
- Win64 renderer compile PASS.
- Linux native renderer compile PASS.
- production default still `r_pbr 0`.
- protected FireVol/IFLC/ELSS markers remain present.
- TestLab source contracts pass.
- package includes A/B cfg: PBR legacy vs PBR2 core.

### V2 — Modern material input

Goal: allow modern packed metallic-roughness materials without increasing the sampler budget.

Material convention:
- BaseColor: normal diffuse/base texture
- Normal: `_n`
- Normal+Height: `_nh`
- ORM: `_orm`
  - R = ambient occlusion
  - G = roughness
  - B = metallic

Changes:
1. Add `IMGTYPE_PBRDATA`.
2. Add linear mip generation for PBR data.
3. Add `stage ormMap` parser support.
4. Auto-discover `_orm` when `r_pbr >= 2`.
5. Reuse `TB_SPECULARMAP`; do not add texture units.
6. Fall back to legacy `_s` if ORM is missing.
7. AO applies to ambient/IBL only.
8. Existing `specularMap` remains supported.

Acceptance:
- V1 regression suite remains green.
- ORM path is independently source-tested.
- legacy `_s` fallback remains active.
- no change to non-PBR materials.
- Win64 candidate package produced.

### V3 — Conservative IBL upgrade

Goal: improve environment response without destabilizing cubemap capture.

Changes:
1. Add Epic-style environment BRDF approximation for `r_pbr 2`.
2. Use perceptual roughness -> alpha conversion consistently.
3. Use squared/perceptual roughness calibration for cubemap LOD.
4. Apply Fresnel-aware energy split to environment contribution.
5. Keep current cubemap capture/export/load format and ordinary mip generation for this first stable V3.
6. Document V3.1 as the later true GGX prefilter pass.

Acceptance:
- cubemap on/off shader variants compile.
- no changes to cubemap loading/export format.
- no changes to `r_cubeMapping` default.
- no production behavior change while `r_pbr 0`.
- final Win64 test candidate produced with V1/V2/V3 switchable cfgs.

## 4. TestLab strategy

The PBR workflow reconstructs exact production source using the same accepted chain as #42217883095:
1. `integration/elss-v1/prepare.py`
2. ELSS V1/V1.0.1
3. FireVol production chain
4. ELSS V1.1 Component Pick REFINED
5. PBR V2 stage patches

Automated gates:
- source lineage hashes/proof
- changed-path allowlist
- `git diff --check`
- GLSL compile where supported
- Linux native compile
- Win64 cross-compile
- production marker preservation
- default-CVar preservation
- package integrity/SHA256

Runtime TestLab:
- use `escape1` only for automated gameplay capture
- PBR off / legacy PBR / PBR2 comparisons
- runtime is only declared PASS when protected retail assets are available
- missing private assets is BLOCKED, never converted into PASS

## 5. Packaging

Candidate name:
`DarkWolf_PBR_V2_V3_From_42217883095_Win64.zip`

Test cfgs:
- `DW_PBR_LEGACY_OFF.cfg`
- `DW_PBR_LEGACY_V1.cfg`
- `DW_PBR2_CORE.cfg`
- `DW_PBR2_MODERN_ORM.cfg`
- `DW_PBR2_V3_IBL.cfg`

The package must inherit the accepted #42217883095 payload and replace only `renderer_sp_rend2_x64.dll`, checksum/proof files, and additive PBR test cfg/readme files.

## 6. Stop conditions

Do not promote to Clean Production if any of the following occurs:
- default `r_pbr` changes from 0
- any legacy `r_pbr 0/1` shader branch is accidentally replaced
- FireVol/IFLC/ELSS protected markers disappear
- shadow budgets/defaults change
- ORM changes affect ordinary color textures
- cubemap export/load compatibility changes in V3
- TestLab reports a visual/runtime regression

## 7. Future V3.1

True GGX cubemap prefilter is deliberately separated from this first V3:
- new prefilter shader
- per-mip convolution
- importance sampling
- BRDF integration LUT or equivalent
- deterministic export path

It should be attempted only after V1/V2/V3 receive visual acceptance on PC, because it changes the cubemap generation path rather than only the material-lighting interpretation.


## 8. V3.2 / BSP Lightmap Relight V4 — 2026-11-08

### TestLab finding

The real Escape1 A/B test on `textures/castle_wall/castle_c46_on_grid` proved that
loading a valid Normal + ORM pair is not sufficient to create a strong material response
on legacy lightmapped BSP surfaces.

The relevant inherited code path is:

- `R_CalcVertexLightDirs()` computes one dominant direction per BSP vertex.
- `R_LightDirForPoint()` samples the world lightgrid.
- if `dot(lightDir, surfaceNormal) <= 0.2`, the function replaces the sampled direction
  with the macro geometric surface normal.
- `lightall_fp.glsl` then reconstructs the baked lightmap as 75% directional and 25% ambient.

On old RTCW maps this frequently makes a material normal look nearly front-lit, so normal
detail is visually suppressed even when the normal texture is correctly loaded.

### V4 implementation

For `r_pbr >= 3` only:

- inject `USE_PBR2_BSP_RELIGHT_V4`;
- only activate the new logic on `USE_LIGHTMAP` shader variants;
- preserve the baked lightmap as total irradiance;
- split it into a confidence-weighted directional and indirect component;
- reproject only the directional component onto the material normal;
- apply ORM AO only to the indirect component;
- when an ORM/specular data texture is bound, add a conservative GGX response from the
  same dominant baked-light direction;
- with a flat normal, the relight resolves to the original baked irradiance, avoiding a
  baseline brightness shift;
- legacy `r_pbr 0/1` and PBR2 core paths remain source-preserved.

### Acceptance

The same Escape1 camera and the same material packages are reused:

A:
- explicit MTR BaseColor + lightmap only.

B:
- identical MTR layout;
- BaseColor + generated Normal + generated ORM.

The test must compile first, then capture both variants in clean processes and preserve
the exact camera coordinates.  Visual acceptance requires a material-local difference
without a global exposure/color shift or geometry change.
