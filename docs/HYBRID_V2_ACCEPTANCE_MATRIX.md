# Hybrid Relight V2 — validation matrix

| Area | Action | Reject if |
|---|---|---|
| Base | Verify exact run #41019985033 archived DLL and cfg packs | Any SHA256 mismatch; any effect disabled |
| BSP | Parse original RTCW SP IBSP v47 and lightmap layout | Non-v47, bad lump bounds, unknown atlas format |
| Provenance | Bind selected lamp/sun/emissive to `.map` or explicit shader source | Unmatched source or unverified shader |
| Light solve | Collect all direct tags and ALL indirect from one single solve | Different samples/bounce, non-linear transfer, missing direct tag |
| Decomposition | Compare I + kept D + selected D to full D+I | Any texel error outside tolerance |
| Masks | Select only opaque lightmapped surfaces; no water/fog/sky/glass/portal | Protected material, overlapping ownership, wrong layout hash |
| Artistic fallback | Match removed source with a persistent dynamic counterpart | Lamp absent, shadow budget overflow leaves area black |
| Norway | Validate original water material, cubemaps and observer movement | Sudden dark/light water boundaries; shimmering |
| Escape1 | Ceiling fixtures, doctor office, guard stove, adjacent rooms | Ambient disappearance, fire/Tesla leaks |
| Assault | Sun/CSM/rails and local volumetric | Volumetric edge regression, incorrect shadows |
| Factory | Tunnel lamps + SSGI | Halo return, source distance flips |
| Crypt1 | Grates, fire, Tesla and shadow slot budget | Object receiver/caster regression |
| Performance | A/B identical same-frame comparison vs production | Sustained FPS regression or shader compile errors |
| Production | Three shadow slots, <=32 promoted lamps, all five profiles | Hidden debug effects, PBR, new telemetry, changed defaults |

**Stage 0-2 synthetic tests:** complete; **stage 3 tagged compiler, 4 runtime, 5 real-map validation:** pending. Never mistake synthetic success for production visual acceptance.

## Stage 1 actual original-map evidence (2026-10-30)

| Gate | Expected | Observed | Result |
|---|---|---|---|
| Pinned base | Exact #41019985033 unchanged | Outer/nested release/renderer SHA256 verified | PASS |
| Original BSP archive | 32 IBSP47 maps | 32/32 accepted | PASS |
| RTCW `MST_FLARE` | 0x0 rectangles are not invalid lightmap | Correctly excluded; real maps no false errors | PASS |
| Norway protected water | No eligible `textures/liquids/water_norway` | 226 protected BSP surfaces | PASS |
| Reference-mask intersection | Protected owners win | Deterministic synthetic overlap test | PASS |
| Embedded light entity classification | Not equivalent to original editor-source lights | 7,632 candidates, all source-attribution unverified | PASS |
| Direct/indirect tagged compiler | Same-solve exported RGB linear irradiance | Not available: original retail ZIP has 0 `.map` sources | BLOCKED |
| Playable relit V2 map | Validated renderer importer | Not implemented | BLOCKED |
| Final visual acceptance | A/B in actual game | Not performed | BLOCKED |

No compiler, BSP or renderer binary has been changed. A *preflight* pass is not an in-game relighting pass.
