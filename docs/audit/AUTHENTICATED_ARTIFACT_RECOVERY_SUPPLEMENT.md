# Authenticated Artifact Recovery Supplement

**Date:** 2026-09-22  
**Scope:** evidence correction after Codex Task 7 authentication failure.  
**Production behavior changed:** NO.

## 1. Authentication blocker resolved outside Codex Cloud

The ChatGPT GitHub connection successfully downloaded all seven required historical GitHub Actions artifacts. Each outer artifact ZIP SHA-256 matches the artifact digest previously returned by the GitHub metadata API, and every inner release ZIP matches its own packaged `.sha256` sidecar.

Verified artifact IDs:

- 10456195747 — Stage 11 runtime-tested predecessor
- 10469110629 — Stage 11 clean
- 10552111977 — stable synthetic capture
- 10555091293 — Clean Production V1
- 10603017159 — Escape1 table RC v0.2
- 10604393513 — rejected Tesla grace v0.4
- 10605030392 — rejected Recovery V1

Therefore Task 7's `NOT READY` decision was caused by lack of Actions authentication inside Codex Cloud, not by missing/expired historical artifacts.

## 2. Exact cumulative patches now verified

- Stage 11 runtime: `762a413698f16208a65c2d36c9282dbaf317cda443c8e5f4c4658454bd0eff19`
- Stage 11 clean: `07df73bf297d22e044f59d3cd80e3c976b9f17517f0435b51be39931de7a4230`
- Stable capture: `d5695d4015fd74fedd9c6a0da95dbe35eef8779a2234c72a00c0eb863cf184f7`
- Clean V1: `7041376f9dccc1be3a2172ef5834c73bb270cc76d768ad1ad115b0567c1077a0`
- Table RC v0.2: `1b766221df31b483877cee2378e3696c7a992abc9cd61628e945b16c145bebe2`
- Tesla grace v0.4: `10cf3be9862225bc59b298e7b29fdc33fef3664a02bf6a25464feb465c07bc60`
- Recovery V1: `0d4f56d4a95a51d4793a04e03ca2b0e4de25decece66c2dcfdd1ad9df372bb8f`

Each cumulative patch contains 67 file sections. Clean V1 and Table RC cumulative patches differ in exactly three sections:

- `SP/code/rend2/tr_init.c`
- `SP/code/rend2/tr_local.h`
- `SP/code/rend2/tr_main.c`

This independently confirms that the accepted table RC is a narrow Rend2 selector/diagnostic delta over the Clean V1 source lineage.

## 3. USER_BLOCKED exact correction

Clean V1 source contract shows that `R_StaticPromoteUSLRDAllowed` consults the user override and rejects `STATIC_PROMOTE_CLASS_USER_BLOCKED` before setting `unifiedClassAccepted`.

Therefore the all-accepted delivery path does **not** directly bypass a correctly blocked candidate.

However, `r_staticPromoteBlockCandidate` routes through `R_StaticPromoteWideCandidateAction(-1, "WIDE_FORCE_OFF")`, and the override is keyed to a candidate `entityOrdinal`, not an authoritative physical lamp. Wide inspection/action also skips synthetic fixtures in the relevant path. Native/authored dlights can be independently present.

**Correct root cause class:** candidate/alias-level blocking allows sibling aliases/native sources belonging to the same visible physical lamp to survive. A future physical block must be applied after alias resolution and before Direct Light, LocalVol and shadow/history consumers.

## 4. 32 stationary lights vs dynamic transient correction

Earlier audit wording that 32 StaticPromote lights could necessarily consume all 32 entries before Tesla/muzzle/explosion was too strong.

Clean V1 computes StaticPromote budget from already used scene dlights:

```c
s_uslrdSceneNativeCount = MAX(0, r_numdlights - r_firstSceneDlight);
s_uslrdGlobalDlightsUsed = r_numdlights;
s_uslrdHeadroom = MAX(0, MAX_DLIGHTS - r_numdlights);
s_uslrdStaticBudget = MIN(requestedMaxLights, s_uslrdHeadroom);
```

`R_StaticPromoteFrame(fd)` is called from `RE_RenderScene` after cgame has already populated its scene dlights. StaticPromote fills only the residual headroom.

**Correct conclusion:** `MAX_DLIGHTS=32` remains a hard global capacity limit, but the Clean V1 StaticPromote ordering/headroom policy protects already-submitted normal cgame transient lights. Do not redesign light storage solely on the earlier unproven starvation claim.

## 5. Exact point-shadow capacity and budget

Clean V1 defines:

`MAX_DLIGHT_SHADOWS = 8`

and sizes compact cubemap/history resources accordingly.

Budget logic is:

```c
persistentShadowBudget = clamp(r_dlightShadowMaxLights, 0, MAX_DLIGHT_SHADOWS);
dynamicShadowBudget = 2;
dynamicShadowBudget = MIN(dynamicShadowBudget,
    MAX_DLIGHT_SHADOWS - persistentShadowBudget);
maxShadowLights = persistentShadowBudget + dynamicShadowBudget;
```

Production default:

- persistent budget = 3
- protected dynamic reserve = 2
- normal maximum cubemap owners = 5
- compiled compact capacity = 8

The selector explicitly preserves the dynamic slice when no persistent candidate fills a persistent position.

No exact modified-source array overflow was found merely by reaching owner 5 or 6. The user-reported 5–6 crash remains a runtime safety/performance investigation, not a proven `shadowCubemaps[5]` overflow.

## 6. Exact production PVS / LOS correction

### StaticPromote PVS

`R_StaticPromoteBuildUnifiedInfluenceMetadata` builds sphere-derived cluster/area pairs once per persistent registry generation, not every frame.

Per-frame unified visibility iterates those precomputed pairs and performs PVS bit plus area-mask checks until one pair is visible.

The historical PCRB 27-point audit is diagnostic evidence; it is not the production per-frame unified PVS algorithm.

### Corona LOS

The normal physical-corona bridge in cgame performs one `CG_Trace` from current camera origin to the qualifying corona origin per qualifying corona entity/frame using solid/body contents. Historical PCRB multi-point trace matrices are diagnostic paths and are not the normal Clean V1 per-frame cost.

## 7. Exact LocalVol production behavior

The older stable lamp pool has:

`LOCAL_VOLUMETRIC_MULTI_MAX = 4`

with `r_volumetricLocalLampMaxActive` default 4.

But Clean V1 freezes `s_rStaticPromoteLocalVolAllActive` ON. In production Mode 5 the four-source pool is reset and not used as the actual render limit.

`RB_LocalVolumetricRenderAllActiveUSLRD` scans up to `MAX_DLIGHTS`, forms canonical physical groups, and renders one unshadowed LocalVol volume per eligible canonical group with nonzero distance weight.

Therefore production StaticPromote LocalVol is **all-active by canonical group**, bounded indirectly by delivered dlights/groups (up to the scene dlight domain), not four volumes.

Default LocalVol samples = 24; normal lamp range = 4..32; spotlight range = 8..48. Mode-5 StaticPromote continuity calls the unshadowed path, so point-shadow slot churn cannot toggle its energy.

## 8. Exact FireVol production limits

Clean V1 defines:

- map-wide static flame catalog: up to `MAX_MAP_DRAW_SURFS`
- working registry: `FIREVOL07_MAX_POOL = 128`
- render residency cap: `FIREVOL081_RENDER_CAP = 8`
- synthetic FireVol shadow cache: 8
- volume-pair helper cap: 64
- `r_volumetricFireMaxActive` default = 1
- runtime max active is clamped to 8 in the multi-source variant
- default FireVol samples = 24, clamped 8..32 in the render path

This corrects the earlier historical estimate of a 64-entry CPU registry: Clean V1's working registry is 128, while 64 belongs to the volume-pair helper cap.

## 9. Point-shadow content caching

Clean V1 and Table RC retain a full `R_RenderDlightCubemaps` capture path and account six faces for each selected owner. Searches found FireVol-specific synthetic shadow caching, but no stationary point-dlight static-world dirty/age/reuse cache.

Thus the accepted StaticPromote point-shadow path stabilizes owner identity/capture but still recaptures selected point-light cubemap contents.

This remains the strongest future performance optimization target after diagnostic timing and invalidation design.

## 10. Integration-base decision

The strongest source/runtime combination remains:

**Clean Production V1 + the narrow Table RC v0.2 cumulative delta**

i.e. historical Run `35503262322`.

Reasons:

- inherits trusted Clean V1 lamp/LocalVol/stable-capture behavior;
- preserves Stage 11 caster/receiver lineage;
- table behavior was runtime accepted;
- its cumulative patch differs from Clean V1 only in three Rend2 sections;
- does not inherit later rejected Tesla grace;
- does not inherit rejected broad Recovery V1;
- failed Clean V2 is not needed as a runtime baseline.

This is the recommended historical source base for the single future unified integration implementation. No separate user-facing feature builds are implied.
