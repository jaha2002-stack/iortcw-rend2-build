# DarkWolf AI Material Lab — implementation instruction

## Fixed base and non-regression contract

Accepted base: GitHub Actions run `36314079722`, artifact `10929902365`, `DarkWolf-ioRTCW-Rend2-Final-Native-v4.3-Deterministic-Profiles-Win64`.

Accepted renderer SHA-256 before Material Lab:

`92b1db33486ea2dd7d04ccda8f3030692578a13569440f100b677b63b7a6e6d2`

The Material Lab branch must preserve all non-renderer payload from that artifact byte-for-byte unless a later stage explicitly requires a change. Do not change StaticPromote residency, shadow selectors/budgets, Tesla timing, ignitable props, Bloom, ToneMap, Exposure, game logic, or native quality profiles while implementing the renderer-side authoring foundation.

Before applying any Material Lab delta, CI must reconstruct and compile the historical Unified Production V1 renderer source and prove that its output matches the accepted renderer SHA exactly. If not, stop.

## Product goal

Build an in-game renderer-native material authoring system for ioRTCW Rend2. The player points at a visible surface, selects the exact Rend2 shader/material under the crosshair, edits material response live, previews without map reload, and saves a per-map override profile without modifying original RTCW shader or texture files.

AI generation is a second contour of the same tool and must use this renderer-side picker/override/persistence foundation.

## Architecture principles

1. Original assets are immutable.
2. Runtime overrides are reversible and store original stage values.
3. v0.1 identity is shader-name based; all surfaces using that shader share the override.
4. Picking reuses the proven exact center-ray triangle probe already present in this Rend2 branch.
5. AI never runs on the render thread; it will be a sidecar/service.
6. Current Rend2 uses global latched `r_pbr`. In v0.1, `r_pbr=1` edits PBR roughness/metallic semantics, while `r_pbr=0` edits classic F0/gloss through the same conceptual roughness control.
7. CI fails closed on provenance/hash/replay/build drift.

## Stage 1 — renderer-native Material Lab v0.1

### Exact material picker

Command: `materiallab_pick`.

On the next main view, use the established center-ray triangle hits. Initial supported geometry:

- `SF_FACE`
- `SF_GRID`
- `SF_TRIANGLES`
- `SF_MDV`
- `SF_VAO_MDVMESH`

Skip sky, portal, fog, underwater/environment surfaces. Selection must not require shadow-caster eligibility.

### Live editable controls

- `r_materialLab 0/1`
- `r_materialLabAutoload 0/1`
- `r_materialLabRoughness 0.02..1.0`
- `r_materialLabMetallic 0..1`
- `r_materialLabSpecular 0..1`
- `r_materialLabNormalScale 0..4`
- `r_materialLabParallaxScale 0..4`

Changing any editable value after a selection applies the override live.

Implementation changes only in-memory shader stage values. It captures every original `normalScale` and `specularScale` before first edit. Normal strength multiplies `normalScale.xy`; parallax multiplies `normalScale.a`.

PBR mode:
- `specularScale.r` = encoded gloss derived from roughness according to `r_glossType`.
- `specularScale.g` = metallicness.

Classic mode:
- `specularScale.rgb` = F0/specular.
- `specularScale.a` = encoded gloss derived from roughness.

### Commands

- `materiallab_help`
- `materiallab_pick`
- `materiallab_status`
- `materiallab_apply`
- `materiallab_reset`
- `materiallab_save`
- `materiallab_load`
- `materiallab_list`
- `materiallab_reset_all confirm`

### Persistence

Per-map profiles:

`materiallab/<mapname>.materials`

Store conceptual values by shader name, not raw encoded Rend2 values. Save uses immediate read-back verification. Load rejects wrong version/map/format and must not partially apply malformed data.

## Stage 1.1 — native in-game panel

After backend validation, expose selected material and controls in the existing native DarkWolf Developer/Tools UI. No external .menu dependency.

## Stage 2 — generated map overrides and hot reload

Generated workspace:

`darkwolf/generated_materials/<map>/<sanitized-shader>/`

Optional maps:
- albedo/diffuse
- normal
- roughness/gloss
- metallic
- AO
- height/parallax
- emissive

Add renderer hot-load only for approved generated sets. Preserve alpha and shader state.

## Stage 3 — AI sidecar v0.1

The engine emits a bounded request:
- map
- shader
- source diffuse identity
- source content hash
- operation
- prompt/preset
- preserve-style
- preserve-palette
- seamless/tile-safe
- seed
- requested resolution

Operations:
- `enhance`
- `pbr_generate`
- `variants`
- `restyle`
- `inpaint`
- `tile_fix`

The sidecar writes only under the generated-material workspace and returns a manifest containing model/version, prompt, seed, source hash, output hashes and channel semantics. The game polls job state outside the render-critical path.

AI output always enters preview first; production apply/save is explicit.

## Stage 4 — AI authoring actions

1. Enhance — conservative RTCW-style cleanup/upscale.
2. Generate PBR — normal, roughness, AO, optional height/metallic.
3. Create Variants — deterministic seed variants.
4. Art Restyle — prompt-guided ageing/wetness/moss/burn/ice/etc.
5. Inpaint — local defect/detail editing.
6. Fix Tiling — seamless edge repair and repeat-aware generation.

Default constraints favor original RTCW palette, scale, readability and atmosphere over photorealistic replacement.

## Stage 5 — surface-only overrides

Material-wide remains default. Add stable surface identity only after the shader-wide workflow is proven. Use existing draw-surface identity if possible; introduce an ID pass only if necessary.

## AI safety/reproducibility

- Source assets remain read-only.
- Sanitize all generated paths/names.
- Store prompt, seed, model/version and hashes.
- Preserve alpha/channel semantics by default.
- Bound image size and job size.
- No network/model call on render thread.
- Preview before save.
- Exact rollback to original material.

## CI/release contract for v0.1

1. Verify run `36314079722` and artifact `10929902365`.
2. Restore historical Unified Production build inputs.
3. Reconstruct source from pinned ioRTCW SHA `438e7d413b5f7277187c35b032eb0ef9093ae778`.
4. Compile untouched reconstruction and require renderer SHA `92b1db33486ea2dd7d04ccda8f3030692578a13569440f100b677b63b7a6e6d2`.
5. Apply Material Lab patcher.
6. Require Rend2-only source changes.
7. Generate/replay delta and compare.
8. Compile new renderer.
9. Require new renderer hash to differ from base.
10. Copy exact run `36314079722` package and replace only `renderer_sp_rend2_x64.dll` plus docs.
11. Verify EXE, OpenGL1 renderer, UI, cgame and qagame remain byte-identical to run `36314079722`.
12. Upload one Windows x64 SP artifact.

## v0.1 acceptance test

1. Start a normal map and set `r_materialLab 1`.
2. Aim at stone/wood/metal and run `materiallab_pick`.
3. `materiallab_status` prints exact shader and mode.
4. Change roughness; response changes without map restart.
5. Change normal/parallax; only the chosen shader material changes.
6. `materiallab_reset` restores original stage values.
7. Apply and `materiallab_save`.
8. Restart map/game; autoload restores the profile.
9. `r_materialLab 0` restores original stage values in memory.
10. StaticPromote, shadows, Tesla, fire/ignitable props, Bloom/ToneMap/Exposure remain unchanged.

## Current implementation boundary

v0.1 is the foundation: exact material picking, reversible live parameter override and persistence. It intentionally does not yet generate AI textures, replace texture maps, provide surface-only identity, or add the final native UI. Those stages build on the validated v0.1 backend.