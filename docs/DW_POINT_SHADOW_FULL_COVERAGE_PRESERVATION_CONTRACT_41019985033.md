# DarkWolf Point Shadow — full Caster/Receiver coverage preservation contract

**Accepted immutable production basis:** [#41019985033](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/41019985033), including Sun HDR16F Factory Visual PASS. **Target:** correct, naturally shaped and visually pleasing dynamic shadows without reducing the number of assets permitted to cast or receive them.

## Non-negotiable requirements
- Keep the entire Stage 11 **Unified Asset Shadow Coverage** eligibility for opaque, alpha-cutout, BSP, models, grates, doors, and other valid assets. Preserve all receiver paths, including legacy `ProjectDlightTexture`.
- Preserve `r_dlightMode 2`, `r_forceSun 1`, StaticPromote fixture stability, 32 promoted lamps, 3 regular shadow slots, CSM Sun, SSGI, Bloom, HDR16F, Local/Fire Volumetric, Tesla/Fire wall containment and previous leakage guards.
- Do not globally exclude categories of meshes or materials or disable the legacy receiver in production.
- The test-only `r_dwPointCasterScope` 1/2 and `r_dwPointReceiverPath` 1 exist **only to determine which pass generates incorrect shadow silhouettes**; values 0/0 reproduce the full accepted Stage 11 functionality. Diagnostic nonzero values must never enter a Clean Production default.
- Do not claim that near-source self-shadow is proven until same-view A/B across the three known scenes establishes the originating caster.

## Diagnostic interpretation
| Test | Scope | Receiver | Meaning |
|:--|:--|:--|:--|
| A | 0 | 0 | Unmodified all-casters + all-receivers output |
| B | 1 | 0 | World BSP static geometry contribution |
| C | 2 | 0 | Entity/model (including bmodel) contribution |
| D | 0 | 1 | All casters, but no selected cubemap in legacy ProjectDlightTexture |

Caster mode changes are latched and require `vid_restart` to avoid a stale cubemap history. Receiver path changes are runtime. Run each on identical savepoint/camera and exposure for the spotlight, Factory ladder/arch, and Crypt1 hanging fire.

## Intended post-diagnostic fixes (not yet implemented)
- Correct **shadow projection geometry**, capture origin and physically connected fixture self-shadow without removing the fixture as a caster for other lights.
- Correct **filtering, depth bias, contact hardness** only where shape diagnostics support them.
- Preserve every other eligible asset/receiver and wall/grate/door shadow, verify Escape1/Crypt1 leakage guards and fixed HDR16F sky.
- New quality fix must be tested separately on the player's GPU before acceptance or merging into any Clean Production release.

**Current status:** diagnostic-only branch. No production renderer changed.