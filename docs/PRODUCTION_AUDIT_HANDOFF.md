# DARKWOLF / ioRTCW Rend2 — FULL PRODUCTION AUDIT & PUBLIC-READY RELEASE HANDOFF

**Prepared:** 2026-09-21  
**Target model / execution window:** Pro model available to the user on/after **2026-10-14**  
**Project:** DarkWolfRTCW / ioRTCW Rend2 Single Player  
**Primary GitHub working repository:** `https://github.com/jaha2002-stack/iortcw-rend2-build`  
**User source fork / related source:** `https://github.com/jaha2002-stack/DarkWolfRTCW`  
**Historical upstream:** `https://github.com/jmarshall23/DarkWolf`  
**Related source lineage / upstream context:** DarkWolf / ioRTCW Rend2 SP  
**Purpose of this document:** transfer the accumulated technical context from months of renderer/gameplay work to an AI that must perform a **full-scale source/history/runtime/performance audit**, stabilize the integrated feature set, restore selected original behavior, eliminate known regressions, optimize performance, and produce a **public-presentable downloadable build artifact**.

---

## 0. Read this first — this is not a request for another local patch

The project has reached a point where isolated fixes can no longer be treated as independent. During previous work, a change that solved one visible defect sometimes changed light ownership, shadow selection, Tesla lifetime, StaticPromote delivery, Local Volumetric behavior, or scene brightness elsewhere.

The core problem is now **system coupling**.

The final task is therefore **not**:

- "fix one lamp";
- "remove one shadow";
- "increase one budget";
- "add another CVar";
- "hide an issue by lowering quality";
- "apply a map-specific exception";
- "keep stacking experiments on top of experiments".

The final task **is** to reconstruct the effective architecture of the modified game, understand every major interaction, identify redundant or conflicting mechanisms, measure cost, simplify where safe, preserve the visual achievements that were already won, restore original gameplay behavior where requested, and then produce a clean optimized release.

The AI receiving this handoff is explicitly authorized to reorganize internal implementations such as StaticPromote selection/residency, PVS use, shadow ownership, fixture grouping, light delivery and related mechanisms **if the new architecture preserves or improves the required visible behavior and stability**.

However, it must not make broad changes before it understands the dependency graph and builds a regression matrix.

---

# 1. Final user goal

Produce one **clean, optimized, stable, public-ready DarkWolf/ioRTCW Rend2 SP build** that represents the best result of the months of work already invested.

The final release should:

1. Preserve the original RTCW visual identity.
2. Preserve the shadow improvements already achieved for ordinary dynamic lights, Tesla, fire, grates, metal doors and other alpha-cutout/opaque objects.
3. Preserve the ability to run many promoted stationary lamps as actual Direct Lights without distance-driven bright/dim instability.
4. Preserve Local Volumetric where it is part of the accepted visual design.
5. Keep the safe production point-shadow budget rather than solving instability by brute-force budget increases.
6. Eliminate duplicate/distance-dependent shadow artifacts such as the Escape1 table second shadow.
7. Eliminate architectural regressions where a fixture is marked blocked but continues to emit light.
8. Restore the **original stationary Tesla behavior and pulse cadence** from the game, while retaining the improved Tesla light/shadow rendering.
9. Prevent the Tesla restoration from degrading the grate/metal shadowing and the Doctor's Office lighting.
10. Audit all accumulated changes for code duplication, stale telemetry, experimental code, override conflicts, unsafe assumptions and unnecessary runtime cost.
11. Profile and optimize the current heavy scenes where FPS can now fall to approximately **40–50 FPS**.
12. Produce a release artifact that the user can download and run without manually reconstructing hidden test settings.
13. Include a technical release report explaining what changed, what was removed, what was retained, what was optimized, and which behaviors were explicitly verified.

---

# 2. One-question-round rule

After reading this handoff, the AI gets **one opportunity only** to ask the user clarification questions.

Rules for that clarification round:

- Ask all genuinely necessary questions in a single grouped message.
- Do not ask questions whose answers are already contained here or recoverable from Git history, Actions artifacts, workflow YAMLs, source diffs or previous release configs.
- Do not use questions as a reason to postpone investigation.
- If the user does not answer one or more questions, choose the conservative interpretation that best preserves the trusted baselines in this document.
- After that one clarification round, proceed autonomously through source audit, history reconstruction, experiments, workflow creation, builds, verification and final packaging.

The final result must be a **downloadable artifact**, not merely a plan or patch suggestion.

---

# 3. Scope boundaries

## 3.1 Primary scope

The primary target is the **ioRTCW Rend2 Single Player** line, not the separate idTech4 renderer POC repository.

The user has a separate `DarkWolfRTCW-idTech4` POC project. Do not merge that experimental renderer takeover into this production audit unless the user explicitly changes scope.

## 3.2 Rendering philosophy

The desired visual direction is still **enhanced original RTCW**, not a conversion into a different-looking PBR game.

Historical production intent:

- `r_pbr 0`;
- normal/specular mapping enabled where appropriate;
- conservative material enhancement;
- preserve original atmosphere and brightness relationships;
- avoid using post-processing changes as a shortcut to disguise lighting/shadow defects.

Bloom/ToneMap/Exposure were intentionally protected during many shadow branches. Treat them as a **protected visual baseline** unless profiling proves a genuine need to change implementation. Do not alter them merely to compensate for lighting regressions or to manufacture FPS gains.

---

# 4. Historical development map — important anchors

This section is a compressed reconstruction of the work history. Every run ID or implementation statement below must be verified against GitHub history before being treated as current source truth. These are investigation anchors.

## 4.1 Early clean visual/performance base

The earlier trusted direction was a clean visual base with:

- original RTCW look;
- working specular response;
- strong FPS, historically above ~90 FPS in the user's reference conditions;
- no PBR requirement;
- the major missing feature at that stage was robust shadows.

This became the foundation for the later shadow work rather than a reason to replace the rendering style.

## 4.2 Stage 11 — unified shadow work

A major historical milestone was the Stage 11 shadow line.

Important anchors:

- frozen diagnostic/base run: **34962735592**;
- later accepted clean-production baseline: **35150218437**;
- a runtime-tested predecessor was **35117854581**.

Important achievements accumulated in this line:

- unified treatment of opaque and alpha-cutout casters;
- alpha-aware shadow handling;
- restored/expanded shadow casting from objects that previously failed to cast correctly;
- fallback receiver shadow path;
- dynamic light shadow behavior for weapons/Tesla/fire sources;
- Factory fire shadow restored;
- grate/metal-object shadowing materially improved;
- Escape1 was accepted without visible degradation at the time;
- diagnostic/experimental telemetry was removed from the clean production package.

The Stage 11 implementation was described historically as a combination of a persistent-light shadow allocation plus dynamic slots. Later production operation centered on the safe runtime policy `r_dlightShadowMaxLights = 3`. **Do not assume the labels "3 persistent + 2 dynamic" and `r_dlightShadowMaxLights 3` refer to the same exact counter in the current code. Verify the implementation.**

### Alpha-cutout / grate diagnostics

A diagnostic line identified surfaces such as `ladder_dark` as `SS_OPAQUE` with alpha test behavior. Historical telemetry included surfaces **11561/11562**, `alphaTest=3`, reaching `RB_RenderShadowmap`.

One important lesson: shader sort/classification alone was not sufficient to explain every missing visible shadow. Later receiver/ownership/light-selection behavior also mattered.

### Known Stage 11 deferred issue

**Boss2 grate vs Tesla shadow behavior** was explicitly deferred. The baseline was accepted without solving every Boss2 Tesla/grate case.

That issue belongs in the final regression audit.

## 4.3 Directional / sun shadows

When testing with:

```text
r_forceSun 1
```

historical performance was reported around approximately **65–100 FPS** in the accepted Stage 11 era.

This was already recognized as a future optimization target.

The current user now sees some scenes falling to **40–50 FPS**, so directional shadow cost must be profiled together with point shadows, materials and volumetrics rather than optimized in isolation.

## 4.4 Stage 12 material work

The project later added a map-aware material layer using prepared texture assets such as:

- `_n` normal maps;
- `_s` specular maps;
- `_nh` height/normal-height variants;
- conservative parallax/relief candidates.

Historical intermediate statistics included:

- a pass with ~1181 unique MTR definitions and duplicate cleanup;
- a later broader map-aware package with up to ~2452 unique definitions;
- hundreds of normal/specular maps and parallax candidates;
- a conservative relief target around +15–20% rather than extreme displacement.

A useful accepted style was:

```text
r_pbr 0
r_normalMapping 1
r_specularMapping 1
```

with parallax used conservatively and separately evaluated for cost.

### Important material regression already encountered

Forest grass was visually regressed during one material pass. The correction was to restore its blend behavior and remove inappropriate grass material maps.

The final audit must therefore include **alpha foliage / grass / fences / grates** in material regression testing, not only solid stone/metal surfaces.

## 4.5 Tesla far-fill experiments

A separate Tesla visual experiment attempted a distance-aware blue residual/far fill. One v0.2 variant made distant blue light more visible but **partially degraded grate-shadow quality/quantity**.

The user explicitly closed that experimental direction as the primary baseline.

Therefore:

- do not reintroduce a residual fill as the main solution;
- do not restore Tesla behavior by keeping a fake light permanently alive;
- do not trade correct grate shadows for prettier far-blue fill.

## 4.6 StaticPromote / lamp instability era

This became one of the most difficult architectural areas.

### User's desired simple behavior

The user repeatedly defined the desired policy in plain terms:

- up to **32** accepted StaticPromote lamps should remain visually active/bright;
- these lamps may have Direct Light and Local Volumetric;
- only a small opportunistic subset needs expensive point-shadow cubemaps;
- production-safe shadow budget: **3**;
- shots, explosions, Tesla and other dynamic sources must continue using their dynamic behavior;
- approaching or looking at a lamp must not cause the lamp to switch bright↔dim;
- one physical lamp should behave like one stable fixture/light identity.

Historically accepted runtime values:

```text
r_staticPromoteMaxLights 32
r_volumetricLocal 1
r_dlightShadowMaxLights 3
```

Testing with `r_dlightShadowMaxLights 5` or `6` restored some older visual behavior but caused **frequent crashes**, so increasing the shadow budget is **not** an acceptable production fix.

### SWF symptom

In SWF, three ceiling lamps in a row could change bright↔dim with player distance, including becoming dimmer at close range.

A major clue:

```text
r_staticPromoteShadowCaptureOffset 32
```

stabilized the visible bright/dim behavior of those three synthetic lamps in one test, but initially created a moving ceiling/wall shadow artifact because capture orientation/location was effectively coupled to the camera. A later world-space capture direction design was intended to stabilize this.

### Synthetic duplicate test

A deduplicated synthetic-light file was tested, including deletion of synthetic duplicates such as IDs `10/13/15`, but the core SWF defect did not disappear.

Conclusion: simple synthetic duplication was **not** the sole root cause.

### Escape1 symptom

Escape1 also had a lamp that could switch by distance. Later, a moving ceiling/wall shadow could follow the player even though it was not the player's own shadow.

This strongly implicated shadow capture/ownership behavior rather than only Direct Light activation.

## 4.7 PCRB / corona → fixture identity investigation

A long diagnostic chain investigated whether unstable lamp behavior was caused by incorrect identity binding between runtime coronas, BSP markers, promoted fixtures and visibility state.

The conceptual chain became:

```text
SERVER ET_CORONA
    -> CGAME metadata
       (runtimeId, origin, color, scale, LOS)
    -> spatial binding
    -> BSP corona marker
    -> PLR / physical fixture
    -> residency / Direct Light / LocalVol / shadow eligibility
```

Historical identity examples included:

- Factory fixture `300` / runtimeId `352`;
- Escape1 fixture `918` / runtimeId `628`;
- mover `863`, `modelIndex=225`.

A prior assumption `runtimeId == physicalCoronaOrdinal` was rejected.

The design direction became deterministic spatial binding with tolerance, using color/scale only as secondary evidence.

### PCRB v0.2

Spatial binding experiment.

### PCRB v0.3

LOS obstruction/endpoints experiment, including offset tests around `1/2/4/8` and separation of wall-only vs wall+character blocking.

### PCRB v0.4

Fixture multi-point visibility:

- center;
- corona point;
- vertical points;
- side points.

### PCRB v0.5

PVS/portal/occluder correlation:

- camera BSP leaf/cluster/area;
- multiple fixture PVS sample points (historically 27 points);
- exact PVS rejection reason;
- blocking brush/surface/shader;
- debug markers for corona/light center/body/hit point;
- mover identity (`863/modelIndex=225`).

Important architectural lesson: visibility, identity and delivery must not be casually conflated. A fixture can be a valid physical light even when one sample point fails LOS/PVS.

## 4.8 Clean Production Run 35361762179 — critical visual behavior anchor

A later important production anchor was:

- **Run 35361762179**;
- artifact ID historically recorded as **10555091293**;
- renderer DLL SHA-256 historically recorded as `84053287054333b89ffdc0d733e7231371098674fa75932f044598fa67df1701`.

This run is especially important because the user later explicitly requested that **Escape1 lamp behavior be restored to the behavior of this run** while keeping later specific fixes such as removal of the table's second shadow.

The intended architecture around this anchor was described as:

- Direct StaticPromote capacity up to 32;
- default expensive shadow capacity 3;
- stable synthetic capture offset around 32;
- Local Volumetric active for the accepted lights.

### Packaging/config divergence discovered later

A clean package could behave differently from the tested environment because saved/default configs were not identical:

- one saved config still had `r_staticPromoteMaxLights = 24`;
- `FIREVOL_PRODUCTION_DEFAULT.cfg` could reset `r_volumetricLocal = 0`.

This is a major production lesson:

> Source correctness is not enough. Release config ordering and defaults are part of the rendering architecture.

The final audit must inspect every CFG/BAT/launcher/default-CVar source that can override runtime behavior.

## 4.9 Escape1 table double-shadow defect

Visible symptom:

- under one table, one normal acceptable shadow exists;
- depending on player distance, a second shadow appears and overlaps the first;
- the combined result becomes too dark;
- the requirement was to remove **only the second shadow**, preserving the first.

A diagnostic RC identified shadow-selector churn involving fixtures historically reported as:

```text
A: {741, 743, 742}
B: {741, 743, 744}
```

The important finding was that the second shadow was not simply baked lighting. With point shadows disabled, both dynamic shadows disappeared.

The defect was associated with score/distance-driven point-shadow owner replacement.

A subsequent physical-shadow-set residency/hysteresis idea successfully removed the second shadow in one test. Historical data included fixture `742`, radius about `249.6`, residency limit about `312.0`, distance about `209.429`.

### Critical caution

A later global "Recovery V1" style change that broadly altered shadow-owner residency was rejected because it changed scene lighting/ownership behavior elsewhere.

Rejected run anchor:

- **35510117158** — do not treat this as a production base.

Therefore the final solution must preserve the **behavioral intent** of the successful table fix without globally destabilizing light/shadow ownership.

## 4.10 Tesla transient-darkness diagnostic branch

A separate branch investigated temporary darkness around the stationary Tesla/Doctor's Office.

One diagnostic suggested:

- `MAX_DLIGHTS=32` headroom might be tight in some transitions;
- a transient Tesla endpoint could appear/disappear;
- a local Direct Light might be displaced at the edge of capacity.

However the user later could not reliably reproduce the blackout, so it was **not accepted as a proven root cause**.

Do not hard-code a fix for this hypothesis without reproducing it.

## 4.11 Rejected Tesla grace/lifetime patch

A later Tesla RC tried to solve perceived dark gaps with a lifetime grace period.

Important rejected run:

- **35508522813** (RC v0.4).

Runtime evidence included approximately:

- `179 START`;
- `178 EXPIRE`;
- `0 RESUME`.

The experiment demonstrated that a simple ~650 ms grace was based on the wrong lifecycle model. The Tesla unlink/relink behavior was script-controlled and not merely a short ~500 ms renderer interruption.

This branch was rejected because it changed the behavior the user wanted to preserve.

**Do not restore the stationary Tesla by adding arbitrary renderer-side grace, persistent fill, or fake lifetime extension.**

## 4.12 StaticPromote manual blocking regression

The user needs a reliable per-fixture way to disable an automatically accepted StaticPromote lamp so that it produces:

- no Direct dlight;
- no Local Volumetric;
- no promoted shadow.

Baked/emissive map appearance may remain.

Commands involved historically included:

```text
r_staticPromoteInspect
r_staticPromoteWideInspect
r_staticPromoteBlockCandidate
r_staticPromoteAllAcceptedDelivery
```

User overrides were associated with:

```text
Main/static_promote_user_overrides.txt
```

Observed regression:

- `r_staticPromoteInspect` could report `USER_BLOCKED`;
- the lamp could still visibly emit light;
- even testing `r_staticPromoteAllAcceptedDelivery 0` did not always make interpretation simple;
- wide inspect could show 6–7 fixture/candidate records associated with what visually looked like one physical lamp.

Possible historical explanations included:

- accepted-delivery path bypassing an older user-block veto;
- another candidate for the same physical lamp still being active;
- BSP + synthetic duplication;
- block applied to candidate identity rather than final physical fixture identity.

This remains an architectural cleanup target.

The final semantics should be simple:

> A persistent user block on a physical StaticPromote fixture is a hard veto for promoted Direct Light delivery, LocalVol delivery and promoted shadow eligibility for that physical fixture, regardless of automatic classifier acceptance.

The implementation should preserve a deterministic way to inspect which logical candidates map to the same physical fixture.

## 4.13 Enhanced locomotion — separate cgame feature to preserve

A separate non-renderer feature added optional enhanced Soldier/Zombie locomotion blending.

Historical v0.2 anchor:

- Run **34965634119**;
- only `cgame_sp_x64.dll` was changed in that experiment;
- phase-aware Walk↔Run;
- start/stop behavior;
- `animSpeedScale` smoothing;
- cvars such as `cg_enhancedAnimBlend 0/1/2` and a debug control.

This is not the cause of the current renderer coupling problem, but a "full game modifications audit" must make sure renderer cleanup does not accidentally remove or regress accepted cgame-side improvements.

---

# 5. Required final behavior for the stationary Tesla

This is a **non-negotiable special requirement**.

The user wants the stationary Tesla to behave again like the original game in terms of its **pulse frequency, cadence and on/off timing**.

At the same time, the final build must **retain the improved rendering work**:

- Tesla light should still illuminate the Doctor's Office appropriately while the original Tesla is in its active phase;
- grate/metal shadows produced by the Tesla must not regress;
- alpha-cutout/opaque caster improvements must remain;
- the improved shadow response through grates/metal structures must remain;
- the surrounding room must not become incorrectly black merely because a Tesla pulse ends if independent ceiling lamps are supposed to remain active;
- no distance-aware fake far fill should replace the original Tesla lifecycle;
- no arbitrary grace timer should redefine the gameplay/script timing.

## 5.1 Correct restoration method

The AI must trace the original stationary Tesla lifecycle end-to-end:

```text
map/script/entity activation
    -> server entity state / use function
    -> network snapshot/event/state
    -> CGAME effect/light submission
    -> Rend2 dlight/shadow submission
    -> visual bolt/light/shadow
```

Known historical code clue: Tesla work touched/observed behavior around `use_shooter_tesla()` and script-controlled unlink/relink.

The AI must compare:

1. upstream/original ioRTCW behavior;
2. the last trusted DarkWolf baseline before Tesla lifecycle experiments;
3. Run 35150218437;
4. Run 35361762179;
5. rejected RC v0.4 / 35508522813;
6. current repository HEAD.

The goal is to determine **where the cadence was actually changed**. Restore cadence at the authoritative gameplay/script/entity layer, not by fabricating a renderer workaround.

## 5.2 Tesla acceptance criteria

A final Tesla test must prove all of the following:

- pulse cadence visually matches the original/validated reference;
- active pulse has the enhanced light interaction;
- inactive interval matches original behavior rather than a new continuous fill;
- grate shadow remains present and correctly shaped when expected;
- ordinary nearby StaticPromote ceiling lamps remain stable and independent;
- no light ownership cascade from Tesla causes unrelated lamp bright/dim switching;
- no crash or shadow-slot overflow;
- muzzle/weapon Tesla behavior is not accidentally changed by the stationary Tesla fix unless a common verified bug is being corrected.

---

# 6. Known unresolved or deferred items to include in the audit

Do not silently drop these because they were once postponed.

1. **Boss2 Tesla/grate shadow behavior** — explicitly deferred in the Stage 11 era.
2. **Residual StaticPromote bright/dim behavior** in difficult scenes, especially where shadow ownership changes with distance.
3. **Per-fixture USER_BLOCKED semantics** — blocked lamp may still emit via another delivery path/candidate.
4. **Physical-lamp identity explosion** — one visual lamp can appear as many inspect candidates; physical grouping must become deterministic and inspectable.
5. **Shadow capture stability** — capture position/orientation must be world-stable and not produce camera-following ceiling/wall shadows.
6. **Escape1 table double shadow** — the successful behavioral fix must survive the final architecture without broad residency regressions.
7. **Potential dlight capacity/headroom coupling** — audit `MAX_DLIGHTS`/submission counts, but do not declare the earlier transient blackout hypothesis proven unless reproduced.
8. **Directional/sun shadow cost** — historically already expensive and now part of a broader 40–50 FPS problem.
9. **Material cost / parallax candidates** — must be profiled rather than globally enabled because scene cost can multiply with lights/shadows.
10. **Forest/foliage blend regressions** — preserve correct alpha/blend behavior.
11. **Config/package default divergence** — ensure release defaults reproduce the tested runtime.
12. **Experimental telemetry/test CVars** — remove from final release unless they serve a deliberate user-facing feature.
13. **Dead or superseded branches** — remove or isolate old logic so multiple selectors/residency systems cannot both influence the same light.
14. **Crashes when shadow budget was raised to 5–6** — identify the actual reason even though final production target remains 3. A crashable path indicates a robustness defect worth understanding.

---

# 7. Architecture audit required before modifying production behavior

The AI must build a written dependency map from the current code.

At minimum trace these subsystems:

## 7.1 Light creation sources

Classify every dlight/light-like source:

- map/native dynamic lights;
- weapon muzzle flashes;
- Tesla weapon;
- stationary Tesla;
- fire/explosion sources;
- coronas;
- StaticPromote BSP fixtures;
- StaticPromote synthetic fixtures;
- any FireVol synthetic/helper lights;
- temporary FX endpoint lights;
- any fallback/legacy Rend2 dlight path.

For each source record:

- creation function;
- lifetime owner;
- identity key;
- origin/radius/color/intensity;
- whether it consumes a dlight array entry;
- whether it receives Local Volumetric;
- whether it is eligible for point-shadow cubemap allocation;
- whether it can displace another source;
- whether it is culled by PVS, frustum, distance, LOS or score;
- whether a second path can submit the same physical source again.

## 7.2 StaticPromote pipeline

Document the exact current chain from candidate discovery to rendered light:

```text
candidate discovery
 -> classification
 -> physical-fixture grouping
 -> user override
 -> visibility/PVS/LOS
 -> residency
 -> Direct Light delivery
 -> LocalVol delivery
 -> shadow eligibility
 -> shadow owner selection
 -> shadow cubemap capture
 -> receiver application
```

If the current source mixes these phases, consider refactoring them into explicit stages with a stable `PhysicalFixtureId` or equivalent.

A user block must occur **after identity resolution but before every delivery path**, so that one block cannot be bypassed by another alias/candidate.

## 7.3 Shadow generation vs shadow application

Audit separately:

1. light selected for shadow;
2. cubemap allocated;
3. caster list built;
4. shadowmap rendered;
5. receiver path samples the shadow;
6. any fallback/forward receiver path also samples/applies it.

The table defect taught that "two dark shadows" may arise from owner churn or duplicate application, not only duplicate physical lights.

Search for multiple receiver paths, including forward and fallback logic, and verify that one light/one receiver interaction is not applied twice under certain material/surface categories.

## 7.4 Dynamic vs promoted shadow ownership

Document exact priority rules among:

- StaticPromote persistent candidates;
- Tesla;
- muzzle flashes;
- explosions/fire;
- other dynamic effects.

The user wants:

- many lights active;
- few shadow cubemaps;
- dynamic effects retained;
- no lamp intensity changes just because shadow ownership changes.

Therefore **Direct Light delivery and shadow residency must be decoupled**. A lamp losing a shadow slot must not lose or materially change its Direct Light.

## 7.5 PVS / visibility

PVS should reduce work, not redefine physical identity.

Audit:

- cluster/area checks;
- portal state;
- multi-point fixture sampling;
- LOS use;
- camera-dependent capture code;
- any behavior that destroys/recreates fixture identity when a visibility sample changes.

A stable fixture may temporarily become non-visible, but that should not create an unrelated new identity when it becomes visible again.

---

# 8. Full performance audit — required methodology

The current visible symptom is no longer just correctness. Some scenes now fall to roughly **40–50 FPS**.

Do not optimize by guessing.

## 8.1 Establish reproducible benchmark scenes

At minimum create a benchmark matrix containing:

### Escape1 — Doctor's Office

Test:

- stationary Tesla active/inactive cycles;
- grate/metal shadows;
- table double-shadow location;
- multiple promoted lamps;
- Local Volumetric;
- player moving near/far from table and lamps.

### SWF — three ceiling lamps

Test:

- near/medium/far camera distances;
- bright/dim stability;
- stable capture orientation;
- LocalVol;
- point-shadow owner changes.

### Factory

Test:

- fire shadow;
- fire/local volumetric cost;
- promoted lamps if present;
- alpha/opaque shadow casters.

### Boss2

Test:

- Tesla/grate deferred case;
- shadow quality;
- dynamic source priority.

### Xlabs / Tram

Use as cross-map caster/material regressions because earlier alpha-caster work was checked across these maps.

### At least one material-heavy / foliage scene

Verify grass/alpha foliage blending and cost.

### At least one directional-light-heavy scene

Test `r_forceSun 0/1` or equivalent supported production states.

## 8.2 Capture per-scene metrics

If the engine does not already expose these, add **temporary diagnostic instrumentation only**, then remove it from final release.

Measure:

- CPU frame time;
- GPU frame time if available;
- draw calls;
- surface count;
- triangles;
- visible dlights submitted;
- StaticPromote candidate count;
- grouped physical fixture count;
- active Direct Lights;
- LocalVol light count;
- point-shadow owner count;
- cubemap faces rendered per frame;
- shadow caster surfaces per light;
- alpha-cutout caster count;
- receiver sampling count;
- dynamic-light interaction count;
- volumetric pass cost;
- normal/specular/parallax material counts;
- directional shadow cascades / resolution / redraw policy;
- PVS-cull ratios;
- overdraw-sensitive passes if measurable;
- CPU time in light selection/residency/sorting;
- memory allocations in hot paths;
- crash/assert bounds around light/shadow arrays.

## 8.3 Profile update frequency

A likely optimization opportunity is to stop recomputing expensive stable information every frame.

Investigate caching for:

- physical fixture grouping;
- static map-space light metadata;
- stable PVS association where valid;
- static caster lists where geometry and light are stationary;
- shadow cubemap reuse for stationary light/static geometry when nothing relevant changed;
- material classification;
- synthetic/native dedup information.

Do not cache dynamic character occlusion incorrectly. Separate static and dynamic invalidation.

## 8.4 Shadow cubemap optimization

Point-light shadows are potentially six-face renders per light.

Audit:

- whether all six faces are redrawn every frame for stationary promoted lamps;
- whether face-level visibility can skip unused faces;
- whether static world caster results can be cached;
- whether dynamic entities can be layered/updated independently;
- resolution selection;
- PCF/sample count;
- bias and normal-bias;
- redundant clear/setup/state changes;
- duplicate capture caused by aliases of the same physical fixture.

The optimization goal is **same or better visual result with less work**, not simply lower resolution everywhere.

## 8.5 Volumetric optimization

Local Volumetric is part of the accepted visual design, but it must not force every promoted light through an expensive identical path.

Profile:

- number of volumetric lights visible;
- bounds/step count;
- screen coverage;
- empty-space work;
- occlusion/PVS rejection;
- whether blocked/hidden physical fixtures still generate volumetric work;
- whether aliases duplicate the same effect.

## 8.6 Material optimization

Profile the cost of:

- normal mapping;
- specular mapping;
- parallax/relief;
- alpha-tested foliage/grates;
- shader permutations;
- texture bandwidth.

Keep parallax selective. It must not be enabled blindly on every `_nh` asset if it materially damages FPS in light-heavy scenes.

## 8.7 Directional shadow optimization

Profile separately from point lights.

Investigate:

- redraw frequency;
- cascade count/resolution;
- caster culling;
- stable cascade caching if applicable;
- alpha-caster cost;
- unnecessary off-screen/behind-camera casters;
- interaction with `r_forceSun`.

---

# 9. Stability / safety audit

The final public release must not simply be faster; it must be robust.

## 9.1 Explain the 5–6 shadow-slot crash

Even though production should remain at 3, identify why `r_dlightShadowMaxLights 5–6` caused frequent crashes.

Check:

- fixed-size arrays;
- cubemap/FBO pool size;
- texture unit assumptions;
- descriptor/state arrays;
- indexing between persistent and dynamic slots;
- stale pointer/owner arrays;
- stack allocations;
- renderer synchronization/state reuse.

Do not raise the production budget as the fix. Fix unsafe bounds if they exist, then keep the conservative default unless profiling proves more is safe and valuable.

## 9.2 Remove debug-only runtime cost

Search for:

- per-frame `Com_Printf`/logging in hot loops;
- debug scans;
- shadow telemetry always running;
- candidate string formatting;
- repeated file parsing;
- test visual markers;
- stale experimental CVars with code branches executed every frame.

Diagnostics may be used during the audit but must be removed or compiled/gated out in the final production artifact.

## 9.3 Determinism

Given a fixed camera and scene, physical fixture identity and Direct Light state should not oscillate because of unstable sorting ties or uninitialized values.

Make tie-breaks explicit and deterministic.

---

# 10. Configuration audit — mandatory

The project previously had source-correct builds behave differently because packaged CFGs changed values.

Audit all of the following:

- engine CVar defaults;
- renderer CVar registration defaults;
- `wolfconfig`/saved user config behavior;
- production CFGs;
- FireVol CFGs;
- launcher BAT files;
- map autoexecs if any;
- workflow packaging scripts;
- files copied from older artifacts;
- order of `exec` calls.

Create a final **single documented production-default layer**.

The final artifact must not require the user to remember that one config needs 32 while another silently resets to 24.

At minimum, the shipped configuration must intentionally and visibly resolve the historically important production values around:

```text
r_staticPromoteMaxLights 32
r_dlightShadowMaxLights 3
r_volumetricLocal 1
```

If the final architecture no longer needs one of these exact controls, document the replacement and preserve the same user-visible behavior.

---

# 11. Git/history reconstruction procedure

Before coding, reconstruct the lineage.

## 11.1 Create a run/commit matrix

For each important GitHub Actions run, capture:

- run ID;
- commit SHA;
- parent/base SHA;
- workflow filename;
- files changed;
- DLLs rebuilt;
- artifact ID/name;
- runtime result reported by the user;
- whether accepted/rejected/deferred.

Minimum anchors to investigate:

- `34962735592` — frozen shadow base/diagnostic anchor;
- `35071483766` — alpha-tested caster experiment landmark;
- `35117854581` — runtime-tested predecessor to clean production;
- `35150218437` — accepted Stage 11 clean baseline;
- `35228053515` — Tesla residual/fill-related branch anchor; verify exact content before use;
- `35356962371` — successful build feeding later clean production;
- `35361762179` — critical lamp-behavior clean production anchor;
- `35500825460` — table shadow selector diagnostic RC v0.1;
- `35503262322` — table/renderer RC v0.2 lineage anchor; verify exact patch;
- `35506107611` — Tesla/transient diagnostic branch;
- `35508522813` — rejected Tesla grace/lifetime RC v0.4;
- `35510117158` — rejected global Recovery V1 shadow-owner behavior.

Do not blindly cherry-pick based on run number. Read diffs and runtime outcomes.

## 11.2 Classify each historical change

Use categories:

- KEEP AS-IS;
- KEEP BEHAVIOR, REIMPLEMENT CLEANLY;
- DEFERRED BUT MUST NOW AUDIT;
- DIAGNOSTIC ONLY;
- REJECTED;
- SUPERSEDED;
- UNKNOWN — VERIFY.

This classification should become an appendix in the final release report.

---

# 12. Recommended architectural end state

This section defines the **behavioral shape**, not mandatory exact code.

## 12.1 Stable physical fixture registry

For promoted stationary lights, prefer one stable map-lifetime registry entry per physical fixture.

A physical fixture should own:

- stable identity;
- origin/orientation;
- color/radius/base intensity;
- source aliases (BSP corona, synthetic candidate, runtime corona metadata, etc.);
- user override state;
- classifier state;
- current visibility state;
- Direct Light residency state;
- LocalVol state;
- shadow eligibility state;
- optional shadow-owner state.

Aliases should not independently emit after they are grouped into one physical fixture.

## 12.2 Separate three concepts

Never let these be the same switch:

1. **physical light exists / is enabled**;
2. **Direct Light is delivered**;
3. **expensive shadow cubemap is assigned**.

The user's 32-lights/3-shadows requirement fundamentally depends on this separation.

### Global dlight capacity is not the same thing as the StaticPromote policy

Audit whether `r_staticPromoteMaxLights 32` can fill a global array whose hard capacity is also `MAX_DLIGHTS=32`. If so, this creates an architectural collision with Tesla, muzzle flashes, fire, explosions and other transient sources. The final design must make dynamic headroom explicit rather than relying on accidental eviction order. Acceptable designs may reserve headroom, prioritize insertion deterministically, or separate persistent/promoted storage from transient dynamic submissions before composing the renderer-visible set.

The required invariant is:

> A transient dynamic source may temporarily gain its required rendering resources without causing an unrelated accepted stationary lamp to disappear, dim, lose LocalVol, or change physical identity.

This is separate from point-shadow preemption: a dynamic source may preempt a **shadow slot** according to policy, but it should not evict the stationary lamp's base Direct Light merely because both share an undersized submission container.
## 12.3 User block semantics

After physical grouping:

```text
if physicalFixture.userBlocked:
    no promoted direct light
    no promoted local volumetric
    no promoted point shadow eligibility
```

The inspect command should show the physical fixture ID and all aliases that were suppressed.

## 12.4 Shadow-owner hysteresis

A point-shadow owner should not be replaced for tiny score/distance changes.

Use a physically meaningful hysteresis/residency rule, but do not make it global in a way that starves more important dynamic lights or freezes obviously wrong owners.

Possible policy shape:

- preserve current owner while within an expanded release threshold;
- introduce a challenger only if it exceeds the incumbent by a meaningful margin;
- dynamic high-priority effects may preempt according to explicit policy;
- preemption changes shadow only, never base Direct Light.

Tune with the Escape1 table regression scene.

## 12.5 Static shadow reuse

If a promoted fixture and world geometry are stationary, consider caching static world shadow data and updating only dynamic casters where feasible.

This is likely one of the highest-value optimization directions if the current code redraws all six cubemap faces for every shadowed stationary lamp every frame.

Any such optimization must preserve moving character/object shadows.

---

# 13. Regression matrix — visual invariants that must survive

The AI must create an explicit PASS/FAIL matrix.

## 13.1 Escape1 / Doctor's Office

PASS only if:

- stationary Tesla pulse cadence matches original reference;
- Tesla's improved active light remains;
- grate/metal shadows remain;
- table has only the intended single shadow, not distance-triggered doubling;
- promoted ceiling lamps stay stable;
- no room-wide unexpected blackouts;
- LocalVol behaves as intended;
- user-blocked fixtures truly stop promoted effects.

## 13.2 SWF lamp row

PASS only if:

- all intended promoted lamps remain bright/active within the 32-light policy;
- approaching a lamp does not make it dimmer;
- shadow owner changes do not change base lamp brightness;
- no camera-following ceiling/wall shadow;
- capture orientation is world-stable;
- shadow budget remains 3 by default.

## 13.3 Factory

PASS only if:

- fire shadow remains;
- fire effect/volumetric appearance does not regress;
- no shadow budget interaction destroys nearby static lamp light.

## 13.4 Boss2

PASS only if:

- deferred Tesla/grate case is explicitly evaluated;
- if fixed, it does not regress Escape1/Factory;
- if a map asset limitation remains, document it precisely rather than hiding it.

## 13.5 Weapons / ordinary dynamic lights

PASS only if:

- weapon/muzzle dynamic shadow behavior remains;
- ordinary dlights continue to cast expected object/grate shadows;
- dynamic priority is not starved by persistent promoted lights.

## 13.6 Materials

PASS only if:

- normal/specular appearance remains;
- no widespread white/incorrect highlights;
- alpha foliage and Forest grass remain correctly blended;
- parallax is selective and stable;
- original RTCW atmosphere is preserved.

## 13.7 Performance

PASS only if:

- the known 40–50 FPS heavy scenes improve materially on the same hardware/settings, or the audit demonstrates a hard bottleneck with quantified evidence;
- optimization does not come from globally disabling the accepted effects;
- frame pacing is stable and no new periodic spikes appear from cache invalidation/shadow-owner churn.

---

# 14. Public-release performance targets

Do not invent an absolute universal FPS promise because hardware and map scenes differ.

Instead use the user's own current build as baseline and define targets per benchmark scene:

- capture median FPS and 1% low (or equivalent frame-time percentile) for current HEAD;
- capture the same for the final candidate;
- aim for a clear measurable improvement in the worst 40–50 FPS scenes;
- do not accept a "performance improvement" that is actually caused by missing lights, missing shadows, disabled LocalVol, disabled materials or lower visual correctness.

If possible, also compare against Run 35361762179 in the same scenes to detect when newer features added cost.

---

# 15. YML / GitHub Actions operating procedure

The AI is authorized to create and iterate GitHub Actions workflows autonomously.

## 15.1 Work in phases

Recommended workflow series:

### Phase A — audit / reproducibility

Create a workflow that:

- checks out exact baseline/current revisions;
- records source SHAs;
- produces file-diff manifests against important anchors;
- builds unmodified current HEAD;
- packages a reproducible baseline artifact;
- records DLL hashes.

### Phase B — diagnostics

Temporary diagnostic builds may add instrumentation for:

- light source counts;
- physical fixture grouping;
- shadow owners;
- shadow churn;
- Tesla lifecycle;
- cubemap redraw counts;
- per-pass timings.

These artifacts must be clearly labeled `DIAGNOSTIC`, never confused with production.

### Phase C — isolated fixes/refactors

Each architectural change must have:

- narrow intent;
- source diff summary;
- predicted affected subsystems;
- regression checks;
- build artifact.

### Phase D — integration candidate

Merge only changes that passed the regression matrix.

### Phase E — clean production release

Remove:

- temporary telemetry;
- debug CVars not intended for users;
- test files;
- temporary markers;
- unused experiment code.

Then rebuild from a clean checkout.

## 15.2 Every successful workflow must record

- workflow name;
- run ID;
- commit SHA;
- artifact name/ID;
- SHA-256 of produced DLLs/ZIP where practical;
- exact configuration/default files packaged;
- source files changed relative to the selected base.

## 15.3 Never validate only "workflow green"

A successful compile is not proof of correct behavior.

Source-level invariants, automated checks and runtime evidence must be combined.

If the execution environment supports launching the game and collecting screenshots/logs automatically, use it. If not, build robust self-diagnostics and validate logic through traces, assertions, deterministic tests and cross-checks against known accepted code paths.

---

# 16. Required code-quality cleanup

The final pass should reduce accumulated complexity.

Look for:

- multiple versions of the same selector left in source;
- duplicated fixture grouping;
- renderer logic that belongs in server/cgame lifecycle;
- hard-coded map/fixture IDs from diagnostics;
- magic timeouts;
- global state introduced only for one experiment;
- user block logic applied before grouping in one path and after grouping in another;
- hidden CVar overrides;
- dead branches guarded by abandoned experiment CVars;
- debug code inside hot loops;
- repeated world scans per frame;
- unsafe fixed-array assumptions;
- string/hash work repeated every frame when map-lifetime caching is sufficient.

Prefer a smaller, explicit architecture over preserving every historical experimental path.

---

# 17. Prohibited shortcuts

The final solution must **not** do any of the following unless the user explicitly approves a changed requirement:

- increase `r_dlightShadowMaxLights` to 5–6 as the main fix;
- globally disable StaticPromote shadows;
- globally disable Local Volumetric;
- lower all light intensity to hide overlap;
- lower global shadow strength to hide the table defect;
- change Bloom/ToneMap/Exposure to disguise lighting bugs;
- add a map-specific `if (escape1)` table hack;
- hard-code fixture IDs `741/742/743/744` as the production solution;
- keep a fake Tesla light alive during original off phases;
- add arbitrary grace timers to approximate Tesla cadence;
- permanently enable Tesla far-fill that degrades grate shadows;
- solve performance by disabling the very effects that define the project;
- claim success based only on compilation;
- leave temporary diagnostic telemetry in the final public release;
- create a release whose behavior depends on undocumented user console commands.

---

# 18. Final release packaging requirements

The AI must provide a downloadable artifact suitable for direct user testing/presentation.

The final ZIP/package should include:

1. production binaries;
2. all required renderer/cgame/game DLLs produced from the final source;
3. the exact production config/default files;
4. required material/MTR files and texture-side definitions already part of the project;
5. launcher BAT/config if the project currently uses one;
6. a concise `README_RELEASE.md` with install/run instructions;
7. `AUDIT_AND_OPTIMIZATION_REPORT.md`;
8. `REGRESSION_MATRIX.md`;
9. `BUILD_PROVENANCE.md` with run ID, commit SHA, artifact hash and key parent baselines;
10. optional `KNOWN_LIMITATIONS.md` only if a verified issue remains that cannot be safely solved without changing the user's requested behavior.

Do not include obsolete diagnostic configs/logging in the production package.

---

# 19. Required final technical report structure

The final `AUDIT_AND_OPTIMIZATION_REPORT.md` should contain:

## 19.1 Executive summary

What was wrong, what was changed, measured result.

## 19.2 Historical reconstruction

Which old changes were retained, reimplemented, rejected or removed.

## 19.3 Root-cause map

For each major defect:

- symptom;
- actual root cause;
- why previous local fixes caused regressions;
- final architecture.

## 19.4 Tesla restoration

- exact original cadence source;
- changed files/functions;
- proof that renderer-side fake lifetime is absent;
- grate shadow verification.

## 19.5 StaticPromote redesign/cleanup

- physical identity model;
- Direct Light residency;
- user block semantics;
- shadow ownership;
- PVS/LOS use;
- LocalVol relationship.

## 19.6 Shadow system

- persistent vs dynamic policy;
- cubemap allocation;
- caster path;
- receiver path;
- table double-shadow prevention;
- cache/reuse strategy.

## 19.7 Performance

Per-scene before/after frame-time/FPS metrics and major cost reductions.

## 19.8 Stability

- crash/bounds fixes;
- shadow budget behavior;
- deterministic ownership.

## 19.9 Configuration

How final defaults are guaranteed.

## 19.10 Remaining limitations

Only verified remaining issues, not speculation.

---

# 20. Suggested one-time clarification questions

The AI may ask the user one grouped clarification message after reading this file. It should ask only if Git/history cannot answer these.

Examples of legitimate questions:

1. Which exact current repository branch/HEAD should be treated as the starting integration branch on 2026-10-14?
2. Does the user still want the optional Enhanced Locomotion v0.2 feature included in the final public package, or only preserved if already merged into the chosen HEAD?
3. Which two or three scenes currently show the reproducible worst 40–50 FPS on the user's hardware, if different from Escape1/SWF/Factory/Boss2?
4. Does the user want parallax enabled by default in the public release, or available but conservative/off by default if profiling shows significant cost?

Do **not** ask again about already fixed constraints:

- StaticPromote target capacity 32;
- production-safe shadow budget 3;
- Local Volumetric is an intended effect;
- Tesla must recover original stationary cadence;
- Tesla/grate shadow improvements must be preserved;
- the user wants a final downloadable artifact.

---

# 21. Final execution directive to the AI

You are not being asked to propose what someone else should do.

You are being asked to **perform the work**.

After the single clarification round:

1. Inspect the repository and Actions history.
2. Reconstruct the modification lineage.
3. Build the current baseline reproducibly.
4. Produce a subsystem dependency map.
5. Instrument and profile where necessary.
6. Reproduce the known regression scenes.
7. Restore original stationary Tesla cadence at the correct gameplay/script layer.
8. Preserve Tesla/grate/metal shadow improvements.
9. Stabilize StaticPromote physical identity, Direct Light delivery, user block semantics, LocalVol and point-shadow ownership.
10. Preserve the Escape1 table single-shadow behavior without global lighting regressions.
11. Audit the Boss2 deferred Tesla/grate case.
12. Optimize shadow rendering, PVS/culling, stationary-light work, volumetrics, materials and directional shadows using measured evidence.
13. Fix unsafe bounds/array behavior uncovered by the 5–6 shadow-slot crash investigation, while keeping production defaults conservative.
14. Remove obsolete diagnostic/experimental code.
15. Normalize production configs so the artifact starts with intended behavior.
16. Run/build iteratively through GitHub Actions until the integrated candidate is internally consistent and all obtainable automated/runtime checks pass.
17. Produce a clean final workflow and final release artifact.
18. Deliver the artifact plus the audit, regression, provenance and performance reports.

The quality bar is **public presentation**, not "good enough for the next experiment".

---

# Appendix A — trusted behavioral invariants

These invariants are more important than preserving any specific historical implementation:

- one physical lamp = one stable physical identity;
- many accepted lamps may emit Direct Light simultaneously;
- only a few of them need expensive shadow cubemaps;
- losing a shadow slot must not make a lamp dim/off;
- promoted light blocking must block the whole promoted physical effect, not one alias;
- dynamic Tesla/fire/weapon effects must still function;
- Tesla stationary pulse cadence belongs to original gameplay/script behavior;
- renderer improvements should enhance an active Tesla pulse, not redefine its lifetime;
- grate/metal/alpha-cutout shadows must remain;
- table shadow must not double when player distance changes;
- world-space shadow capture must not follow the camera;
- PVS/LOS are culling inputs, not unstable identity generators;
- release configs are part of the product and must match tested values;
- `r_dlightShadowMaxLights=3` is the safe production target unless the final audited architecture proves another value safe and necessary;
- original RTCW atmosphere is preserved; PBR is not the production goal.

---

# Appendix B — historical CVar/reference values to verify

These are historical anchors, **not permission to blindly force them** without checking current code:

```text
r_staticPromoteMaxLights 32
r_volumetricLocal 1
r_dlightShadowMaxLights 3
r_dlightShadowStrength 0.88
r_staticPromoteShadowCaptureOffset 32
r_pbr 0
r_normalMapping 1
r_specularMapping 1
```

Stage 11/Tesla-era references also included settings such as:

```text
cg_dlightFxShadowPolicy 1
r_dlightIntensity 1.10
```

and historical radius/intensity scale experiments. Verify exact current semantics before carrying them into final defaults.

---

# Appendix C — important rejected/unsafe ideas

Keep these visible so the same mistakes are not repeated:

- raising point-shadow budget to 5–6 to hide residency defects;
- global shadow-owner residency rewrite that altered unrelated scene behavior;
- Tesla 650 ms grace/lifetime patch;
- Tesla far-fill as replacement for original pulse behavior;
- synthetic dedup assumed as sole lamp root cause;
- candidate-level block assumed to equal physical-lamp block;
- source-only validation without config audit;
- compilation success treated as runtime correctness.

---

# Appendix D — status confidence labels

Because this handoff is reconstructed from a long development history, every factual item in the audit should be tagged internally as one of:

- **VERIFIED IN CURRENT SOURCE**;
- **VERIFIED BY HISTORICAL DIFF**;
- **RUNTIME-REPORTED BY USER**;
- **DIAGNOSTIC HYPOTHESIS**;
- **REJECTED HISTORICAL EXPERIMENT**.

Do not allow a historical hypothesis to silently become a production assumption.

---

**End of handoff.**