# MASTER AUDIT SYNTHESIS — DarkWolfRTCW / ioRTCW Rend2 Production Audit

**Date:** 2026-09-21  
**Branch:** `rend2-production-audit-base`  
**Purpose:** Integration-stage normalization of the five independent Codex audits:
- Tesla Original Behavior
- StaticPromote Architecture
- Shadow Pipeline
- Performance
- Regression / Git History

This document is a synthesis. It does not replace `docs/PRODUCTION_AUDIT_HANDOFF.md` or `AGENTS.md`.

## 1. Cross-audit consensus

All five audits converge on the same high-level architecture problem:

1. StaticPromote, LocalVol, point-shadow selection, environmental Tesla, PVS/visibility residency, and alias/corona binding evolved as partially independent systems.
2. The renderer does not yet have one authoritative map-lifetime physical fixture identity that owns all aliases and all outputs.
3. Direct illumination, LocalVol, and shadow ownership must be independent state machines.
4. A shadow-slot transition must never extinguish or dim the underlying stationary direct light.
5. A physical user block must be applied after alias grouping and before all promoted outputs.
6. Dynamic/transient sources must retain explicit headroom and must not be starved by a fully populated stationary-light set.
7. Shadow ownership stability and cubemap content reuse are different problems. Stable ownership does not mean cubemap faces are reused.
8. Production performance is dominated by multiplicative render work rather than by one proven scalar bottleneck.
9. The stationary Tesla temporal source of truth is gameplay/map/cgame lifecycle, not renderer persistence.
10. The Escape1 table defect is best supported as a physical shadow-owner residency/selection defect, not a material or baked-light defect.

## 2. Normalized immutable reference map

### Original gameplay / Tesla timing authority
Use upstream ioRTCW:

`438e7d413b5f7277187c35b032eb0ef9093ae778`

plus the original Escape1 map/script target graph.

This is the authority for:
- `shooter_tesla` link/unlink semantics;
- server entity lifetime;
- snapshot disappearance when unlinked;
- cgame `ET_TESLA_EF` dispatch;
- the original frame-local attached-dlight submission predicate.

No later DarkWolf renderer workaround overrides this temporal authority.

### Stage 11 shadow behavior reference
Run:

`35150218437`

runtime-tested predecessor:

`35117854581`

Preserve behavior from this line for:
- opaque and alpha-tested/cutout point-shadow casters;
- grate/metal/rail shadow coverage;
- fallback receiver coverage;
- weapon/Tesla/fire dynamic shadow behavior;
- Factory fire shadow.

Boss2 remained deferred and must not be inferred as accepted.

### Clean Production lamp reference
Run:

`35361762179`

Recipe commit:

`79642f3242ce270e946ef0a13d2863f421b228b5`

Artifact:

`10555091293`

Recorded Rend2 SHA-256:

`84053287054333b89ffdc0d733e7231371098674fa75932f044598fa67df1701`

Use this as the principal behavioral reference for:
- stable Escape1/SWF-style stationary lighting;
- stable world-space synthetic capture inherited from Run 35356962371;
- LocalVol-enabled clean-production behavior;
- safe persistent shadow default.

It is NOT the original Tesla timing authority and it still predates the accepted table-shadow correction.

### Escape1 table single-shadow reference
Run:

`35503262322`

Recipe:

`80fde84b6e91febd5ab5a8c10e37ed0d6dd01476`

Artifact:

`10603017159`

This is runtime evidence that persistent physical owner-set residency removed the second/darker table shadow in isolation.

Preserve the result. Re-evaluate/generalize the mechanism carefully.

### Negative references

- Tesla far-fill lineage: `35228053515` / `35233369524` — rejected as production restoration strategy.
- Tesla grace: `35508522813` — rejected. Approximately 179 START / 178 EXPIRE / 0 RESUME showed the assumed short-gap model was wrong.
- Recovery V1: `35510117158` — rejected globally because broader owner behavior changed unrelated scene lighting.
- Shadow budgets 5–6 — rejected as a normal operating solution because of frequent crashes and extreme cost.

## 3. Critical normalization: Clean Production V2

A major cross-audit wording conflict must be resolved explicitly.

The current repository contains a Clean Production V2 workflow implementing persistent physical-set residency. That workflow is useful as a **source/design contract**.

However, the historical run:

`35510769201`

failed and does not establish a successful production artifact or runtime acceptance.

Therefore:

- Do not call Clean Production V2 a runtime baseline.
- Do not treat it as stronger evidence than Run 35503262322 for table behavior.
- Its code delta may be studied and reused after reconstruction/validation.
- Runtime baselines remain Run 35361762179 for lamp behavior and Run 35503262322 for the table fix.

## 4. Stationary Tesla — agreed technical conclusion

The original environmental Tesla is not a persistent renderer lamp.

Authoritative chain:

`Escape1 script -> target/delay/timer graph -> shooter_tesla.use -> LinkEntity/UnlinkEntity -> snapshot presence -> CG_Efx -> frame-local AddLightToScene -> Rend2`

### Original lifecycle

- Unlinking removes the entity from normal snapshot delivery.
- When the entity is absent, both discharge rendering and attached light stop.
- There is no original renderer grace timer or independent dlight expiry object.

### Escape1 authored cadence

The audits found:
- two broad environmental shooters are enabled through the 0.5-second path and disabled through the 3.5-second path, giving a nominal 3.0-second treatment window;
- the timer fires immediately and then at approximately 2.2 +/- 0.4 seconds;
- left/right narrow shooters are toggled through 0.5/1.0-second delays, yielding nominal 0.5-second linked pulses.

### DarkWolf temporal deviation

The inherited enhanced Tesla path replaced the stock intermittent frame predicate with a continuously submitted enhanced linked-phase light modulated by a sine:

`0.90 + 0.10 * sin(0.019 * time + 0.73 * entityNum)`

This is approximately a 330.7 ms / 3.024 Hz intensity ripple while linked.

The restoration target is:

- original gameplay/map link/unlink ownership;
- original cgame submission eligibility/predicate;
- NO light replay across actual unlink/off periods;
- preserve enhanced active-pulse origin, source identity, accepted color/radius tuning, and Stage 11 grate/caster/receiver behavior.

Do not restore timing in Rend2 shadow selection.

## 5. StaticPromote — agreed architectural defect

The current system has multiple overlapping identities:
- classifier candidate;
- BSP/native source;
- BSP corona ordinal;
- runtime corona entity;
- PLR/fixture identity;
- synthetic FixtureId;
- current-frame dlight index;
- derived physical shadow group;
- historical shadow slot/group identity.

No single demonstrated map-lifetime object owns all of them.

### Required future invariant

One physical fixture must own:
- all source aliases;
- acceptance/block state;
- Direct Light state;
- LocalVol state;
- Shadow eligibility/state;
- stable capture identity.

### USER_BLOCKED

Runtime evidence proves that a candidate can report USER_BLOCKED while the physical lamp remains visibly promoted.

The exact source-level cause is not yet proven, but the strongest supported failure paths are:
- another alias remains active;
- the final all-accepted delivery boolean bypasses the older candidate veto;
- downstream state/history still references another identity.

Future semantics must be:

`physicalFixture.userBlocked => no promoted Direct Light + no LocalVol + no promoted shadow candidate/history`

Baked lightmaps/emissive/corona visuals must be reported separately.

## 6. Direct Light / LocalVol / Shadow separation

All audits agree these are separate concepts.

### Direct Light
Target behavior:
- approximately 32 accepted stationary physical fixtures may remain illuminated;
- distance/view/PVS transitions must not create bright/dim switching merely by changing shadow eligibility.

### LocalVol
Must be owned by the same physical fixture but independently scheduled/cost-culled.

It must not gain or lose energy just because the fixture gains or loses a point-shadow slot.

### Shadow
Expensive opportunistic ownership only.

Camera score, transient priority, hysteresis, capture cost, and slot residency may affect the shadow, but not the existence of the base light or its LocalVol source.

## 7. Global dlight-capacity hazard

A structural contradiction exists in the intended limits:

- StaticPromote target can reach 32 active stationary lights.
- Historical/current renderer contracts use `MAX_DLIGHTS=32`.
- Dynamic Tesla, muzzle flashes, explosions, and fire also need dlight submission.

Therefore a full 32 stationary set has no explicit guaranteed transient headroom if all classes share the same array.

The earlier Tesla blackout was not proven to be caused by this, but the capacity collision is real by construction.

Preferred future design:
- separate persistent-fixture and transient stores and compose later;

or, if ABI constraints force one container:
- explicit deterministic reserved transient headroom and overflow policy.

Do not reduce the user's intended stationary illumination merely to create accidental headroom.

## 8. Shadow pipeline — agreed findings

### Preserved behavior
Keep:
- compact selected shadow slots rather than one cubemap per every direct light;
- semantic source classes;
- alpha-tested/cutout caster support;
- forward/lightall receiver;
- legitimate fallback receiver;
- environmental/player Tesla source separation;
- stable world-space synthetic capture behavior;
- physical owner-set residency intent from the table RC.

### Escape1 table defect
Strongest evidence supports:

`camera-distance score transition -> false compact-slot/physical-owner vacancy -> challenger physical owner admitted -> second darker point-shadow contribution`

The successful RC v0.2 changed selection/residency only and removed the visual defect.

There is insufficient evidence to state that the defect was definitively:
- one specific duplicate synthetic ID;
- a double receiver pass;
- stale cubemap contents;
- baked lighting.

Those remain weaker hypotheses.

### 5–6 shadow-light crash
Root cause remains unproven.

Do not claim a simple `shadowCubemaps[5]` overflow: historical arrays are commonly sized to 8 and the relevant selector performs bounds checks.

Most plausible unproven classes:
- command/draw-surface/resource pressure from 30–48 shadow views;
- latent fixed-capacity overflow elsewhere;
- selector/history corruption at higher occupancy;
- driver/watchdog/FBO/backend failure.

A symbolized crash/diagnostic matrix is required before changing capacity.

## 9. Shadow budget semantics — do not collapse counters

A key integration requirement is to determine the exact postimage semantics of:

- `r_dlightShadowMaxLights`;
- persistent StaticPromote owner count;
- protected dynamic reserve;
- `MAX_DLIGHT_SHADOWS`;
- total simultaneously rendered cubemap owners.

Stage 11 evidence supports a historical architecture of approximately:
- 3 persistent owners;
- plus a dynamic reserve of 2;
- up to 5 total selected owners in some configurations.

The user's production intent is a small expensive shadow budget while dynamic sources remain functional.

Do not assume that a displayed/configured value of 3 means exactly three total cubemap owners until the reconstructed postimage is inspected.

## 10. Performance — agreed dominant cost model

No new runtime timing was produced, but the source architecture demonstrates multiplicative work.

### Point shadows
Each selected owner renders six cubemap views.

Examples:
- 3 owners = 18 shadow views/frame;
- 5 owners = 30 shadow views/frame;
- 6 owners = 36 shadow views/frame;
- 8 owners = 48 shadow views/frame.

Selection stability does not mean texture reuse.

No accepted production lineage demonstrates a static-world cubemap cache.

### Additional multipliers
Potentially concurrent:
- sun/directional cascade rendering;
- volumetric sun producer;
- LocalVol quarter-resolution raymarchs;
- FireVol residents;
- alpha-cutout caster texture sampling in every relevant shadow view;
- up to 32 direct-light receiver interactions;
- normal/specular/parallax permutations;
- repeated PVS/LOS/alias work.

The most important future performance work is not to disable effects.

Required order:
1. measure;
2. classify pass costs;
3. reuse stable stationary shadow content;
4. cull unnecessary cubemap faces;
5. deduplicate physical fixture work;
6. bound volumetric work;
7. share sun/volumetric shadow data where valid;
8. tune materials only after measured attribution.

## 11. Performance instrumentation requirements

Future diagnostic build should provide, with no hot-loop string logging:

### CPU
- main `R_RenderView` time;
- point-shadow selector/grouping time;
- each cubemap face front-end time;
- draw-surface generation/sorting time;
- StaticPromote classifier/PVS/LOS/binding/delivery time;
- LocalVol/FireVol selection time;
- front-end/back-end waits.

### GPU
- total point-shadow capture and per owner/face;
- sun cascades;
- volumetric-only cascades;
- main opaque/alpha;
- forward dlight receiver;
- fallback receiver;
- LocalVol per physical fixture;
- FireVol per resident;
- volumetric sun;
- composites/post.

### Counters
At minimum:
- submitted dlights;
- physical fixtures;
- aliases;
- accepted/delivered stationary fixtures;
- transient lights;
- persistent shadow owners;
- dynamic shadow owners;
- cubemap faces requested/rendered/reused/culled;
- shadow owner churn;
- opaque/alpha caster draws;
- receiver interactions;
- LocalVol and FireVol source/pass/pixel/sample counts;
- PVS queries;
- LOS traces;
- draw calls/program switches/FBO binds;
- allocation/free high-water;
- any `qglFinish`, `glReadPixels`, or blocking `glGet*`.

## 12. World-space synthetic capture

The pre-final synthetic shadow offset fixed one symptom but initially derived capture direction from the current camera, causing a moving ceiling/wall shadow.

Run `35356962371` made the direction world-stable and is accepted behavior.

Preserve world-space stability.

However, first-view initialization still may not be the ideal long-term physical model. The preferred end state is an authored or deterministic geometry-derived capture transform stored in the physical fixture registry.

## 13. PVS / LOS role

PCRB demonstrated that:
- runtime corona ID is not BSP ordinal;
- spatial binding plus color/scale is a better alias relation;
- a single corona point can fail PVS even when the finite-radius influence is relevant;
- multi-point/surface/PVS/portal evidence is useful for visibility diagnosis.

Future rule:

`physical identity -> enabled/block state -> independent output policies`

PVS/frustum/portal/LOS should be used as conservative work/relevance culling, not as identity generation and not as a reason for a stationary fixture to cease existing.

Map-lifetime associations should be cached.

## 14. Material/caster conclusions

Preserve:
- opaque solids;
- non-blended alpha-tested cutout casters;
- grate/fence/rail/door cutout behavior;
- world/BMODEL/model/actor participation where intended;
- normal/specular visual improvements;
- corrected grass blending;
- `r_pbr 0`.

Do not globally add blended translucent surfaces as point-shadow casters.

Do not change Bloom/ToneMap/Exposure as part of this work.

Parallax is a measured/selective performance question, not a blanket removal target.

## 15. Accepted / rejected / unresolved matrix

### Preserve behavior
- Stage 11 alpha/grate caster coverage.
- Stage 11 forward/fallback receiver coverage.
- weapon/fire/explosion/Tesla dynamic shadows.
- Factory fire shadow.
- active environmental Tesla enhanced origin/source identity and grate-shadow quality.
- Run 35356962371 world-stable synthetic capture.
- Run 35361762179 clean lamp/LocalVol behavior.
- Escape1 table single-shadow result from 35503262322.
- normal/specular material character with PBR disabled.
- exact artifact/run/hash provenance process.

### Reject as production mechanisms
- Tesla far/residual fill as lifecycle restoration.
- 650 ms Tesla light grace.
- global broad Recovery V1 ownership behavior.
- camera-relative shadow capture.
- raising shadow budget to 5–6 to hide selector defects.
- map-name or fixture-ID hacks.
- candidate-level block as the final physical block semantics.

### Unresolved and must be proven
- exact current production postimage after cumulative artifact reconstruction;
- exact 3 vs 3+2 shadow-budget semantics;
- user-block bypass site;
- complete physical alias map;
- transient starvation at `MAX_DLIGHTS=32`;
- 5–6 crash cause;
- Boss2 Tesla/grate;
- Xlabs/Tram regressions;
- save/load/map restart invalidation;
- actual CPU/GPU cost distribution;
- exact current PVS/LOS cadence;
- whether ordinary sun and volumetric sun duplicate cascade production;
- final package CVar precedence.

## 16. Required next phase: integration evidence, not implementation

Do not start the final renderer rewrite/fix yet.

The next task must materialize and compare exact source postimages for the important reference states.

Minimum source states:

1. Stage 11 clean / runtime-tested line:
   - Run 35150218437
   - predecessor 35117854581 as needed

2. Clean Production lamp baseline:
   - Run 35361762179

3. Table fixed state:
   - Run 35503262322

4. Rejected negative controls for diff only:
   - Run 35508522813
   - Run 35510117158

5. Current Clean V2 workflow delta:
   - inspect as source/design intent only;
   - do not treat failed Run 35510769201 as runtime baseline.

For each state, reconstruct/hash the actual source or exact cumulative patch and compare:

### Game/cgame Tesla
- `SP_shooter_tesla`
- `use_shooter_tesla`
- snapshot inclusion/residency code
- `CG_Efx`
- environmental effect-light submission
- source identity transport

### StaticPromote
- candidate creation/classification
- acceptance and user overrides
- runtime-corona/BSP/synthetic alias binding
- `R_StaticPromoteSelectProduction`
- direct-light submission
- LocalVol enumeration
- physical grouping

### Shadow
- source classification
- selector budgets
- dynamic reserve
- physical grouping
- history/residency
- capture origin/radius
- cubemap allocation
- six-face render loop
- caster classifier
- forward/fallback receivers
- bias/filter settings
- all array/resource declarations

### Performance/safety
- `MAX_DLIGHTS`
- `MAX_DLIGHT_SHADOWS`
- masks and shifts
- history arrays
- cubemap/FBO resources
- command/draw-surface capacities
- volume registries
- sun/volumetric cascade producers
- allocation/readback/sync points

The output of the next phase should be an exact evidence matrix and integration design, still with no gameplay/renderer behavior changes.

## 17. Integration principles

The eventual implementation should proceed in this order unless postimage evidence disproves it:

1. Establish authoritative physical fixture registry.
2. Move alias grouping and user-block ownership into that registry.
3. Separate persistent stationary Direct Light storage from transient dynamic capacity.
4. Route LocalVol through physical identity, independent of shadow slot.
5. Route shadow grouping/history through the same physical identity.
6. Restore stationary Tesla original temporal predicate/lifecycle while preserving enhanced active-pulse spatial/shadow behavior.
7. Preserve table owner-set behavior using stable physical identities and narrowly defined release conditions.
8. Add diagnostic-only performance/safety instrumentation.
9. Implement static-world point-shadow reuse/dirty tracking.
10. Add face-level capture rejection and other measured optimizations.
11. Validate full regression matrix.
12. Remove diagnostics/test CVars and produce a reproducible clean artifact.

## 18. Runtime acceptance matrix

At minimum:
- Escape1 doctor's office stationary Tesla on/off cadence;
- Escape1 grate/metal shadow;
- Escape1 table near/far path, exactly one intended shadow;
- SWF aligned lamps, near/far/turn/inside radius;
- Factory fire light/shadow/volume;
- Boss2 Tesla/grate;
- Xlabs;
- Tram;
- weapon muzzle and Tesla weapon;
- explosion/transient lights under full stationary load;
- user block/unblock one physical lamp;
- save/load;
- map restart;
- portal/door transitions;
- high stationary count;
- default shadow policy;
- 4/5/6 shadow-slot stress for diagnostics only;
- heavy performance scenes with identical resolution/MSAA/config.

No runtime PASS may be inferred from successful compilation.
