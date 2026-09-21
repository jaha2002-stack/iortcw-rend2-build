# DarkWolf Rend2 Regression / Git History Audit

**Audit date:** 2026-09-21
**Scope:** repository history, retained/deleted workflow definitions, GitHub Actions metadata, and the production handoff
**Mode:** audit only; no renderer, game, configuration, or workflow changes
**Upstream source pinned by the audited workflows:** `jmarshall23/DarkWolf@438e7d413b5f7277187c35b032eb0ef9093ae778`

## Evidence vocabulary

This report uses the handoff's confidence vocabulary:

- **[CURRENT]** verified in a workflow present at audit HEAD.
- **[DIFF]** verified in a retained Git object, historical workflow, or Git commit/path history.
- **[API]** verified from the GitHub Actions run/artifact API on 2026-09-21.
- **[USER]** runtime outcome reported by the user and preserved in the handoff; it is not independently reproduced here.
- **[HYPOTHESIS]** a diagnostic interpretation not established as root cause.
- **[REJECTED]** an experiment explicitly rejected by runtime reporting or production policy.

The repository is principally a provenance/build-orchestration repository. Historical workflows reconstruct a pinned upstream tree, apply cumulative and delta patches, compile selected modules, and package contracts and hashes. Consequently, a green run proves reproducibility and compilation, not visual acceptance. Deleted workflow files remain inspectable in Git and are evidence; deletion alone does not mean the behavior was reverted from an already-produced artifact.

## Executive summary

1. **The strongest clean shadow baseline is Run `35150218437`.** It promoted the runtime-tested Stage 11 experiment `35117854581` into a telemetry-free clean package while preserving unified opaque/alpha-tested caster coverage, fallback receiver behavior, and dynamic fire/weapon/Tesla shadows. Boss2 Tesla/grate remained deferred. **[DIFF][USER]**
2. **The strongest lamp-behavior reference is Run `35361762179`, not an all-purpose rollback target.** Its exact artifact (`10555091293`) and Rend2 DLL hash are recorded below. It combined the Stage 11 lineage with the final USLRD synthetic capture work and clean packaging. The user specifically trusts its Escape1 lamp behavior. **[API][USER]**
3. **StaticPromote's historical regression is architectural coupling.** Physical identity, direct-light delivery, LocalVol relevance, and scarce cubemap ownership evolved through separate experiments but were repeatedly allowed to influence one another. A three-shadow selector could therefore alter perceived lamp brightness even though up to 32 direct lamps were intended to remain active. PCRB showed that runtime entity number, BSP corona identity, candidate identity, and physical fixture identity are not interchangeable. **[DIFF][USER]**
4. **The Escape1 table defect is selector churn, not baked lighting.** RC v0.1 identified alternating physical owner sets `{741,743,742}` and `{741,743,744}`. RC v0.2's persistent physical-set residency removed the duplicate shadow in the reported scene while retaining the first. Its behavior is accepted evidence, but its global selector consequences require re-evaluation. **[CURRENT][USER]**
5. **Tesla lifetime fixes after RC v0.2 were not accepted.** The diagnostic branch was useful, but the v0.4 approximately 650 ms renderer/server-side residency grace modeled the lifecycle incorrectly (`179 START`, `178 EXPIRE`, `0 RESUME`). Stationary Tesla cadence belongs to original gameplay/script unlink/relink semantics. Far-blue residual/fill also degraded grate-shadow quantity/quality and is rejected as the primary baseline. **[CURRENT][REJECTED][USER]**
6. **Recovery V1 (`35510117158`) is rejected as a global production base.** It attempted to restore the clean-run baseline plus only the table correction, but broadly changed shadow-owner behavior and altered other scene lighting. The subsequent Release V2 packages RC v0.2 behavior; it is a recovery artifact, not evidence that the global architecture is accepted. **[CURRENT][REJECTED][USER]**
7. **Configuration is part of the regression surface.** A saved configuration used `r_staticPromoteMaxLights 24`, while `FIREVOL_PRODUCTION_DEFAULT.cfg` could set `r_volumetricLocal 0`; source-equivalent packages could therefore render differently. The trusted policy remains approximately 32 active promoted lights, three expensive point-shadow owners, and LocalVol enabled. **[USER]**
8. **Performance remains unquantified and unresolved.** Earlier clean conditions were reported above roughly 90 FPS, Stage 11 with forced sun around 65–100 FPS, and later heavy scenes around 40–50 FPS. History contains caching, receiver-aware selection, fire-volume, and residency experiments, but no controlled same-scene median/percentile comparison establishes one regression commit. **[USER]**
9. **Crash behavior at shadow budgets 5–6 is real deferred debt.** It is correlated with raising `r_dlightShadowMaxLights`, but no audited run proves whether the cause is bounds, allocation, memory pressure, or another unsafe assumption. The production setting of 3 is a safety policy, not a root-cause fix. **[USER]**

## Chronological development timeline

| Period | Historical line | Evidence and outcome | Classification |
|---|---|---|---|
| 2026-07 | Early mode 3/cubemap prototypes, infrastructure diagnostics, Kits B–E | Established depth cubemap and shader comparison paths; explicitly diagnostic/prototype workflows. | **SUPERSEDED / DIAGNOSTIC ONLY** |
| 2026-08-08–11 | Dynamic-light shadow, flame, electroshock, frozen Tesla footprint, StaticPromote multilamp work | Added the foundations for object, fire, Tesla, and promoted-light shadows. Numerous narrow A/B workflows precede later production consolidation. | **KEEP BEHAVIOR; IMPLEMENTATION SUPERSEDED** |
| 2026-08-12–16 | Sun/player-shadow and material/reflection work | Preserved RTCW-oriented rendering while adding material-aware response; later material expansion retained normal/specular direction without adopting PBR. | **KEEP BEHAVIOR** |
| 2026-08-23–25 | LocalVol v0.1–v0.4 and LocalVol Production v1 | Separated local lamp volume from sun volume and investigated source/shadow matrices and performance. LocalVol became intended production behavior. | **PRESERVE; AUDIT COST/OWNERSHIP** |
| 2026-08-27 | Physical Corona Residency Bridge v0.1 | Began explicit server corona → cgame metadata → BSP/physical fixture bridge. Parent of PCRB v0.2 is Run `33078995146`, artifact `9649208281`. | **DIAGNOSTIC FOUNDATION** |
| 2026-08-27–28 | PCRB v0.2–v0.5 | v0.2 replaced ordinal identity assumptions with spatial binding; v0.3 traced LOS endpoints; v0.4 sampled multiple fixture points; v0.5 correlated PVS/portal/occluder surfaces. | **KEEP FINDINGS; REMOVE TELEMETRY** |
| 2026-08-28–29 | PCRB v0.6/v0.7 → Visible Surface Residency → LocalVol lamp stability → clean production r1/r2 | Converted identity/visibility findings into residency candidates and then clean packages. These are earlier clean baselines, not proof of later shadow correctness. | **MAJOR BASELINE LINEAGE** |
| 2026-08-30–09-07 | FireVol v0.1–v0.8.5, occlusion, stable residency, clean FireVol production | Iterated source ownership, shape, flame anchors, wall occlusion, synthetic shadow capture, and fixture registry. Clean promotions followed diagnostics. | **PRESERVE ACCEPTED FIRE/VOLUME BEHAVIOR; RE-EVALUATE COST** |
| 2026-09-07–10 | Dlight FX eligibility, Tesla/weapon endpoints, explosion and rocket receiver work | Restored/expanded transient shadow eligibility and investigated receiver duplication, including coplanar face deconfliction. | **PRESERVE ACCEPTED DYNAMIC SHADOWS** |
| 2026-09-10–15 | Shadow ownership/residency/cache/receiver-aware and classifier experiments | Explored stable identity, persistent cache, source separation, eight-shadow adaptive budget, PLR fixture association, Xlabs classifiers. Several were experiments and should not be inferred as accepted merely from successful builds. | **MIXED; RE-EVALUATE** |
| 2026-09-15 | Run `34962735592` | StaticPromote single-status-file cleanup; frozen diagnostic/base anchor. | **KNOWN REFERENCE** |
| 2026-09-16 | Runs `35071483766`, `35081824222`, `35098010299`, `35117854581` | Alpha-tested opaque caster experiment, unified diagnostics, then Stage 11 unified fix2. `35117854581` was runtime-tested. | **ACCEPTED DONOR LINE** |
| 2026-09-16/17 | Run `35150218437` | Clean Stage 11 production package over runtime-tested `35117854581`; removed experiment telemetry without changing accepted donor semantics. | **ACCEPTED CLEAN BASELINE** |
| 2026-09-17 | Runs `35228053515` and later far-fill v0.2 | Tesla residual/far-blue fill experiments. Greater distant blue presence traded away grate-shadow quality/quantity. | **REJECTED AS PRIMARY BASE** |
| 2026-09-18 | USLRD v0.1 through Final v2 | Investigated unstable synthetic lamp capture, persistent ownership, LocalVol continuity, physical groups, and world-stable synthetic capture. Final v2 CI repair built successfully as `35356962371`. | **MIXED; FINAL CAPTURE BEHAVIOR PRESERVE, COUPLING RE-EVALUATE** |
| 2026-09-18 | Run `35361762179` | Clean Production Release v1 over `35356962371`; critical Escape1 lamp-behavior reference. | **KNOWN-GOOD REFERENCE** |
| 2026-09-20 | Runs `35500825460`, `35503262322` | Table diagnostic v0.1, then persistent physical-set residency v0.2. Duplicate table shadow reportedly removed while first remained. | **DIAGNOSTIC; FIX BEHAVIOR TO PRESERVE/RE-EVALUATE** |
| 2026-09-20 | Run `35506107611` | Tesla delivery dropout trace over RC v0.2; transition-only telemetry, not production. | **DIAGNOSTIC ONLY** |
| 2026-09-20 | Run `35508522813` | Tesla light residency/grace RC v0.4. Lifecycle evidence disproved the short-gap model. | **REJECTED** |
| 2026-09-20 | Run `35510117158` | Table Shadow Only Recovery V1. Runtime report found broad lighting/owner changes. | **REJECTED** |
| 2026-09-20 | Clean Production Release V2 workflow | Packages persistent-shadow-set residency lineage after the failed recovery attempt. It is reproducible, but global runtime acceptance is not established. | **RECOVERY CANDIDATE; UNRESOLVED** |

## Major production baselines

### Early clean visual/performance baseline

- **Last known-good behavior:** original RTCW atmosphere, useful specular response, `r_pbr 0`, and historically greater than approximately 90 FPS in the user's reference conditions. **[USER]**
- **Missing capability:** robust unified shadows.
- **Status:** preserve its visual philosophy, not its missing-shadow implementation.

### LocalVol / visible-residency clean baseline (2026-08-29)

The chain from PCRB/Visible Surface Residency through LocalVol lamp stability produced `7build...final-clean-production-release-v1` and r2. Git commits `4807c0b6` and `27f960c6` preserve the workflow definitions. This is the first clearly named clean consolidation of physical-light residency plus local lamp volume. **[DIFF]**

### FireVol/HDR clean baselines (2026-09-01–07)

The FireVol v0.8.5 clean release (`a0fdc6a9`), HDR/MSAA integration clean release (`f22e8a12`), and FireVol final-architecture clean workflow (`4966b0b1`, with hygiene fix `ebafcddf`) establish that fire volume, occlusion, HDR/MSAA integrity, and production cleanup were promoted in stages rather than introduced by Stage 11. **[DIFF]**

### Stage 11 clean production — Run `35150218437`

- Parent/run-tested donor: `35117854581`, commit `780c1ee7`, artifact `10456195747`.
- Clean workflow commit: `7e457ac`; upstream remains pinned to `438e7d4`.
- Artifact: `10469110629`; artifact digest `sha256:059a3e7914ad5a8d25f56910bd238eb37ec274deae817178d35a8975b01d6d15`.
- Clean workflow explicitly reconstructs the 67-file cumulative source, preserves accepted donor semantic files, removes diagnostic code, and rebuilds Rend2 while retaining cgame hash provenance. **[DIFF][API]**
- Runtime acceptance recorded by the handoff: Factory fire shadow, weapon/Tesla/dynamic behavior, grate/metal and alpha-cutout coverage, fallback receivers, and no reported Escape1 degradation at that time. Boss2 remained deferred. **[USER]**
- **Status:** strongest shadow baseline; preserve behavior.

### USLRD clean production — Run `35361762179`

- Donor: Run `35356962371`, commit `c8b79541`, artifact `10552111977`, final synthetic-capture CI repair.
- Clean workflow commit: `79642f32`.
- Artifact: `10555091293`, artifact digest `sha256:6cd0e66d9e8e68ac4499a2e41b9ab0286b40942e14106b4b6ddc92ba38e3abb1`.
- Inner release ZIP SHA-256: `9b24185302c468b47b9c0125a31eb9b1edd9518e7cbd0084a80710c52d395a4b`.
- Rend2 DLL SHA-256: `84053287054333b89ffdc0d733e7231371098674fa75932f044598fa67df1701`.
- Intended policy: 32 promoted direct lights, default 3 persistent shadow owners, LocalVol independent of shadow sampling, synthetic capture separated from light delivery and offset toward camera free space with a bounded 0–32 control. **[DIFF][API]**
- **Status:** critical known-good Escape1 lamp reference; preserve the observed lamp behavior and provenance, not every internal coupling.

## Major experimental branches/workflows

### PCRB v0.1–v0.5

| Version | Historical question | Finding/status |
|---|---|---|
| v0.1 | Can a physical corona residency bridge carry server `ET_CORONA` identity to the rendered fixture? | Established metadata bridge. Diagnostic foundation. **[DIFF]** |
| v0.2 | Is `runtimeId == physicalCoronaOrdinal` valid? | No. Added deterministic spatial association; color/scale were secondary evidence. Modified cgame/Rend2 while freezing game/server. **[DIFF]** |
| v0.3 | Is one LOS endpoint/offset causing false fixture disappearance? | Instrumented obstruction and offsets 1/2/4/8; separated wall versus character blocking. Diagnostic only. **[DIFF]** |
| v0.4 | Does one point represent a fixture's visibility? | No reliable basis. Tested center, corona, vertical, and lateral points. Diagnostic only. **[DIFF]** |
| v0.5 | Are portal/PVS and occluder identities correlated with dropout? | Recorded camera/fixture leaf, cluster, area, 27 samples, rejection reason, brush/surface/shader, and mover `863/modelIndex=225`. Diagnostic only. **[DIFF]** |

**Durable finding:** identity, visibility evidence, direct delivery, LocalVol, and shadow ownership are distinct state. PCRB telemetry should not ship, but the rejected ordinal-identity assumption must not return.

### USLRD experiments

USLRD progressed from general unstable-light diagnostics to stable persistent shadow ownership, LocalVol continuity/relevance, physical shadow-group continuity, always-on direct shadow capture, and final stable synthetic capture. Commits `82065ddb`, `4b9cb031`, `ab37b25e`, `58c3ede7`, `2ef1e72c`, `1cb4cfdc`, `e930035b`, and `c8b79541` retain that order. **[DIFF]**

The accepted-looking final contract states: direct delivery remains up to 32; default persistent shadow budget remains 3; LocalVol shadow sampling is independent; only synthetic capture origin is offset and later made world-stable. This addresses a camera-following ceiling/wall shadow without intentionally changing brightness, materials, or post-processing. **[DIFF]**

The uncertainty is whether the cumulative implementation still makes shadow capture/owner status indirectly affect a lamp's apparent direct/LocalVol contribution. That coupling was observed at runtime but cannot be resolved from workflow contracts alone. **[USER]**

### Tesla diagnostics and fill branches

- Residual fill v0.1: Run `35228053515`, commit `09f51646`, artifact `10500260020`. **[API]**
- Distance-aware far-blue v0.2: historical workflow at commit `51505438`; improved distant blue but partially degraded grate-shadow quantity/quality. **[DIFF][USER]**
- Dropout trace RC v0.3: Run `35506107611`; instrumented server snapshot presence, PVS/area/link reasons, cgame receipt, Rend2 delivery, selector state, and `MAX_DLIGHTS` headroom only on transitions. **[CURRENT]**
- Residency decoupling RC v0.4: Run `35508522813`; added grace/lifetime behavior rather than restoring original game-script cadence. Runtime counters did not support the assumed short interruption. **[CURRENT][REJECTED][USER]**

### Escape1 table branch

- RC v0.1 (`35500825460`) added `r_dlightShadowSnapshot` and observation-only selector telemetry; source contracts assert no selection-score modification. **[CURRENT]**
- RC v0.2 (`35503262322`) consumes previous physical-group residents as a set before new score challengers, bounded by capture radius plus existing hysteresis. It claims to leave delivery, radii/color, budget, dynamic/Tesla/blast slots, materials, and post-processing untouched. **[CURRENT]**
- Runtime report: the table's second overlapping shadow disappeared while its first remained. **[USER]**
- Architectural caveat: RC v0.2 changes global persistent-owner selection; therefore the behavior is valuable but the scope/coupling is unresolved.

## Accepted improvements

| Improvement | Evidence | Current disposition |
|---|---|---|
| Opaque plus alpha-tested caster coverage, including grates/rails/metal doors | Stage 11 donor/clean workflows and runtime handoff | **PRESERVE** |
| Fallback receiver path and previously absent object shadows | Stage 11 runtime acceptance | **PRESERVE** |
| Dynamic weapon, Tesla, fire, explosion shadow eligibility | Dlight FX/Tesla/weapon/explosion clean lineage; Stage 11 | **PRESERVE** |
| Factory fire shadow and fire appearance | Stage 11 and FireVol clean line | **PRESERVE** |
| Stable world-space synthetic capture behavior | USLRD final v2 → Run `35361762179` | **PRESERVE BEHAVIOR** |
| Up to 32 accepted promoted direct lights independent of three expensive shadows | USLRD contracts and trusted runtime policy | **PRESERVE INVARIANT** |
| LocalVol as an intended independent visual effect | LocalVol production and USLRD contracts | **PRESERVE; AUDIT COST** |
| Normal/specular material enhancement with `r_pbr 0` | Stage 12 history/handoff | **PRESERVE** |
| Forest grass blend correction/removal of inappropriate maps | runtime-reported material correction | **PRESERVE** |
| Table single-shadow outcome from RC v0.2 | runtime report | **PRESERVE OUTCOME; RE-EVALUATE GLOBAL MECHANISM** |
| Exact provenance: pinned upstream, cumulative/delta replay, module and artifact hashes | Stage 11, USLRD, and RC workflows | **PRESERVE** |

## Rejected approaches

1. **Tesla residual/far fill as a substitute for original pulses.** It changes off-phase semantics and v0.2 reduced grate-shadow quality/quantity. **[REJECTED][USER]**
2. **Approximately 650 ms Tesla grace/lifetime persistence (Run `35508522813`).** Diagnostics show unlink/relink is not a brief renderer dropout. **[REJECTED][USER]**
3. **Global Table Shadow Only Recovery V1 (Run `35510117158`).** It altered unrelated lighting/shadow ownership and is not a production base. **[REJECTED][USER]**
4. **Increasing the point-shadow budget to 5–6 (and the earlier budget-8 candidate) as a residency fix.** Values 5–6 frequently crashed; a larger budget also conflates illumination capacity with cubemap cost. **[REJECTED][USER]**
5. **Synthetic duplicate deletion as the sole SWF fix.** Removing sample IDs `10/13/15` did not eliminate the defect. **[REJECTED][USER]**
6. **Candidate-level user block as equivalent to physical-fixture block.** One apparent lamp can have six or seven aliases; a reported `USER_BLOCKED` candidate could leave other delivery paths active. **[REJECTED AS SEMANTICS][USER]**
7. **`runtimeId == physicalCoronaOrdinal`.** PCRB evidence rejected this identity shortcut. **[REJECTED][DIFF]**
8. **Map/fixture hard-coding for the table (`741`–`744`) or other scenes.** IDs are diagnostic evidence, not a production identity policy.
9. **Post-processing changes to hide lighting overlap.** Bloom, tone map, and exposure are protected baselines.
10. **Treating build success as runtime acceptance.** Every listed failed approach compiled successfully.

## Known regressions

| Regression | Last known-good | First identifiable association | Compensating work | Coupling/status |
|---|---|---|---|---|
| Escape1 table gains a second, darker shadow by distance | Stage 11 acceptance did not report it; Run `35361762179` is the explicit parent where later diagnostic reproduces it | Present by `35361762179`; exact first commit not proven | RC v0.1 telemetry; RC v0.2 resident physical set | Global selector coupling; **UNRESOLVED ARCHITECTURE** |
| SWF lamps bright↔dim, sometimes dimmer near fixture | Earlier 32-light physical-residency intent; exact last artifact not established | USLRD-era symptom; exact workflow not proven | capture offset 32, then world-space capture | Capture/owner and apparent brightness coupled; **UNRESOLVED** |
| Moving ceiling/wall shadow follows camera | Before camera-directed capture offset; exact run unknown | Initial capture-offset compensation | USLRD final world-space direction | Final behavior should be preserved; **RE-VERIFY** |
| Stationary Tesla cadence differs from original | Original upstream gameplay/script behavior | Renderer-era persistence/fill attempts; exact initial regression unknown | far fill, dropout trace, v0.4 grace | Compensations redefine lifetime; **REMOVE/RESTORE ORIGINAL LIFECYCLE LATER** |
| Tesla far-fill reduces grate shadows | Stage 11 clean `35150218437` | far-fill v0.2 after residual Run `35228053515` | branch closed | **REJECTED** |
| StaticPromote block reports blocked but lamp remains | Earlier candidate block semantics never established physical veto | current cumulative lineage by user report; first run unknown | inspect/wide-inspect/all-delivery diagnostics | Alias/delivery bypass; **UNRESOLVED** |
| Configured light/LocalVol state differs between packages | tested environment for `35361762179` | saved `24` and FireVol default `LocalVol 0`; first package unknown | manual config corrections | Configuration/source coupling; **UNRESOLVED** |
| Heavy-scene FPS fell from historical >90 to 40–50 | early clean base | no controlled bisect; accumulated shadows/materials/volumes likely | caching and selector experiments | Cause not measured; **UNRESOLVED** |
| Shadow budget 5–6 crashes | budget 3 | higher-budget tests; first exact run unknown | revert to 3 | safety defect hidden by conservative default; **UNRESOLVED** |
| Forest grass blending/material error | pre-material grass | one Stage 12 material pass; exact run unknown | restored blend and removed maps | **FIX PRESERVE; RE-VERIFY ALPHA MATERIALS** |

## Deferred defects

- Boss2 Tesla/grate case was explicitly deferred at Stage 11 and has no later accepted closure. **[USER]**
- High `r_dlightShadowMaxLights` crash root cause remains unknown.
- `MAX_DLIGHTS=32` may collide with a 32-entry StaticPromote policy and transient Tesla/fire/weapon sources; Tesla RC v0.3 records this as a hypothesis, not proof.
- StaticPromote physical-block semantics remain inconsistent.
- Save/load and map-restart reset behavior for physical fixture registry, historical shadow owners, Tesla diagnostic state, and user overrides has no accepted test record.
- Xlabs classifier workflows exist, but no final cross-map runtime acceptance was located.
- Tram appears in the required heavy-scene matrix but lacks a scene-specific accepted workflow/result in the audited history.
- Directional shadows with `r_forceSun 1` were historically 65–100 FPS; no later controlled comparison explains current 40–50 FPS scenes.

## Run-by-run reference table

All listed runs returned `completed/success` from the Actions API. “Success” below means CI success only.

| Run | Commit | Artifact ID / digest | Purpose | Runtime disposition |
|---:|---|---|---|---|
| `34962735592` | `c1e98ec1` | `10393878434` / `fb1d730a…` | StaticPromote single-status cleanup; frozen Stage 11 base | Reference/diagnostic, not visual acceptance |
| `35071483766` | `d5a58d0a` | `10436283192` / `985616d2…` | Alpha-tested opaque caster experiment | Landmark; findings fed Stage 11 |
| `35117854581` | `780c1ee7` | `10456195747` / `6eaee2fd…` | Stage 11 unified asset shadow Fix2 | **Runtime-tested donor** |
| `35150218437` | `7e457aca` | `10469110629` / `059a3e79…` | Stage 11 clean production | **Accepted clean shadow baseline** |
| `35228053515` | `09f51646` | `10500260020` / `3c8d77f1…` | Tesla residual blue fill v0.1 | Experiment; subsequent direction rejected |
| `35356962371` | `c8b79541` | `10552111977` / `44b48660…` | USLRD stable synthetic capture Final v2 CI repair | Successful donor to clean release |
| `35361762179` | `79642f32` | `10555091293` / `6cd0e66d…` | Clean Production Release v1 | **Critical Escape1 lamp reference** |
| `35500825460` | `fa3dee77` | `10602266984` / `b118f021…` | Escape1 table selector diagnostic v0.1 | Diagnostic only |
| `35503262322` | `80fde84b` | `10603017159` / `51ef9cb5…` | Persistent physical shadow set RC v0.2 | Table outcome accepted; global mechanism unresolved |
| `35506107611` | `9a40b9bc` | `10603703946` / `f520517d…` | Tesla delivery dropout trace v0.3 | Diagnostic only; blackout not reliably reproduced |
| `35508522813` | `bfc84e0d` | `10604393513` / `26ada3f4…` | Tesla light residency decoupling/grace v0.4 | **Rejected** |
| `35510117158` | `c42493b2` | `10605030392` / `d51c8ee1…` | Run-35361762179 table-only Recovery V1 | **Rejected** |

Full digests and workflow paths are recoverable from the named commits and current workflow environment blocks. The Actions API also reported these artifacts unexpired on the audit date.

## Subsystem history

### Shadows

**Producer chain:** cgame/server dynamic source and StaticPromote submissions → `tr.refdef.dlights[]` → source/group classification → pending mask and persistent/dynamic budgets → cubemap faces → shader receiver path.

- Early prototypes proved cubemap/depth paths but were superseded.
- Stage 11 unified opaque and alpha-tested casters, added/retained fallback receivers, and explicitly reserved dynamic shadow capability alongside persistent owners.
- The workflow comments describe a persistent budget controlled by `r_dlightShadowMaxLights` and a fixed accepted transient reserve of 2. This must not be casually equated with a total “3+2” user setting without inspecting the reconstructed source.
- Historical surfaces `11561/11562`, shader `ladder_dark`, `alphaTest=3`, reached `RB_RenderShadowmap`; this proves caster participation, not final visible receiver correctness.
- Table RC v0.2 adds history-based physical-group residency before score challengers. It fixes one runtime symptom but creates a global owner-history dependency.
- Higher owner budgets are unsafe; the cause is not isolated.

**Last known-good:** Stage 11 for general dynamic/caster behavior; RC v0.2 only for the table single-shadow outcome.
**Status:** preserve caster/receiver and dynamic behaviors; re-evaluate ownership/residency; crash unresolved.

### StaticPromote

**Producer chain:** BSP corona/synthetic candidate/runtime corona metadata → grouping/canonical physical ID → active acceptance (target 32) → direct delivery and LocalVol → independent shadow eligibility/slot (target 3).

- Physical Light Residency and PCRB established that aliases and runtime IDs require deterministic binding.
- Visible Surface Residency and LocalVol stability attempted to prevent single-point visibility loss from removing fixture influence.
- Later PLR/classifier/Xlabs workflows expanded physical fixture coverage.
- USLRD separated synthetic capture parameters and made capture world-stable.
- The current defect—blocked candidate still visibly emits—strongly supports an alias or bypassed-delivery path, but neither is proven alone.

**Last known-good:** Run `35361762179` for specifically requested Escape1 lamp behavior; earlier clean residency line for the 32-light intent.
**First regression:** not uniquely identifiable.
**Status:** preserve stable illumination behavior; physical ownership/block semantics and budget separation unresolved.

### Tesla

**Producer chain:** original gameplay/script entity lifecycle and `ET_TESLA_EF` link/unlink → server snapshot/PVS → cgame environmental Tesla endpoint → dynamic-light submission → Rend2 source classification/selection → cubemap and receiver.

- Early electroshock/frozen-footprint and later Tesla endpoint workflows improved shadow eligibility.
- Stage 11 is the accepted rendering reference for Tesla and grate/metal interaction.
- Far-fill changed visual persistence and harmed grate shadows.
- RC v0.3 traced each lifecycle boundary and raised, but did not prove, dlight-capacity displacement.
- RC v0.4 treated absence as a short gap; runtime counters rejected that model.

**Last known-good:** original upstream for cadence; Stage 11/Run `35361762179` for improved rendering. These are two references that future integration must combine rather than choose between.
**Status:** rendering preserve; cadence unresolved; grace/fill rejected.

### LocalVol

- LocalVol v0.1–v0.4 isolated lamp/spot sources and performance; Production v1 promoted it.
- LocalVol lamp stability and multisource workflows integrated it with residency.
- USLRD explicitly declares LocalVol shadow sampling independent and all-active delivery.
- Packaging later allowed `FIREVOL_PRODUCTION_DEFAULT.cfg` to disable it, demonstrating configuration drift.
- No historical evidence justifies tying LocalVol presence to cubemap-slot ownership.

**Last known-good:** LocalVol production plus the Run `35361762179` intended configuration.
**Status:** preserve; verify config, blocking, residency, and cost.

### Materials

- Material provenance/reflection workflows began in mid-August; Stage 12 later generated map-aware MTR definitions (intermediate approximately 1181, later up to 2452) with `_n`, `_s`, and `_nh` assets.
- Intended production style is normal/specular mapping on, PBR off, conservative selective parallax.
- Forest grass regressed and was corrected by restoring blend semantics and removing unsuitable maps.
- Alpha materials overlap the shadow regression surface: foliage, fences, grates, and alpha-tested opaque surfaces need both material and shadow validation.

**Last known-good:** corrected grass plus accepted conservative normal/specular style; exact artifact not recorded in the handoff.
**Status:** preserve appearance; parallax/performance and exact provenance unresolved.

### Performance

- Historical early baseline: >~90 FPS in user reference conditions.
- Stage 11 with forced sun: ~65–100 FPS.
- Current heavy scenes: ~40–50 FPS.
- Likely cost centers identified by architecture, not proven as regression causes: six cubemap faces per selected point light, all-frame static recapture, directional shadows, repeated PVS/LOS/multipoint classification, fixture rebinding, LocalVol, parallax/material passes, receiver overdraw, and ownership churn.
- Persistent shadow cache and receiver-aware workflow families demonstrate prior attention to these costs, but were not established as accepted global production baselines.

**Status:** unresolved; no controlled benchmark or commit-level bisect exists.

## Full regression matrix

“Historical result” is deliberately not converted into a current PASS without a runtime run.

| Surface | Required invariant | Best historical reference | Known regression/debt | Historical status | Future verification dependency |
|---|---|---|---|---|---|
| Escape1 doctor's office | stable lamps; correct Tesla; grate/metal shadows; one table shadow; LocalVol | `35361762179` lamps + Stage 11 shadows + RC v0.2 table | references are split across artifacts | **UNRESOLVED INTEGRATION** | combine without selector/direct-light coupling |
| Stationary Tesla | original pulse cadence/lifetime | original upstream lifecycle | current cadence differs; grace/fill rejected | **FAIL/UNRESOLVED** | gameplay/script lifecycle plus improved renderer |
| Tesla grate shadows | retain improved cutout/metal projection | `35150218437`; `35361762179` | far-fill v0.2 degraded it | **KNOWN-GOOD REFERENCE EXISTS** | compare active pulse, same view/settings |
| Escape1 table | exactly one normal shadow | `35503262322` outcome | duplicate under distance in clean run; Recovery V1 altered other scenes | **LOCAL OUTCOME PASS; GLOBAL UNRESOLVED** | owner-set transitions and other maps |
| SWF lamp row | 32-light brightness stable; 3 shadows; no camera-following shadow | `35361762179` policy/final USLRD capture | near-distance dimming and prior moving shadow | **UNRESOLVED** | direct/LocalVol independent of slot; world-space capture |
| Factory | fire shadow/volume retained; lamps unaffected | Stage 11 + FireVol clean line | possible shared-budget interaction | **HISTORICALLY ACCEPTED; RE-VERIFY** | fire, nearby fixtures, transient pressure |
| Boss2 | Tesla/grate explicitly evaluated | none | deferred since Stage 11 | **DEFERRED/UNRESOLVED** | distinguish asset limitation from selection/caster defect |
| Xlabs | classifiers/lights stable in heavy rooms | Xlabs classifier experiment workflows `126`, `128`, `129` | no accepted final runtime matrix | **UNKNOWN** | fixture identity and performance |
| Tram | lighting/shadows/performance stable | no specific accepted run located | absent runtime evidence | **UNKNOWN** | full scene benchmark |
| Weapon shadows | muzzle/ordinary dynamic shadows retained | Stage 11 and player/NPC/weapon endpoint clean line | starvation possible if 32 promoted lights fill global array | **HISTORICALLY ACCEPTED; ARCHITECTURAL RISK** | dynamic headroom and preemption |
| Fire shadows | fire casts expected object shadow | Stage 11 / FireVol clean | shadow-budget interaction | **HISTORICALLY ACCEPTED; RE-VERIFY** | Factory and other fire scenes |
| StaticPromote brightness | close/far view does not dim/off direct light | `35361762179` Escape1 behavior | SWF/Escape1 switching | **UNRESOLVED** | separate active/direct/shadow state |
| StaticPromote user block | physical fixture vetoes direct, LocalVol, shadow | none | `USER_BLOCKED` can still emit; aliases remain | **FAIL/UNRESOLVED** | post-group physical veto and alias report |
| LocalVol | remains for accepted lights independent of shadow slot | LocalVol production / USLRD contract | config can disable; relevance coupled historically | **UNRESOLVED** | config order, blocking, shadow loss |
| Alpha grass/foliage | correct blend/no invalid material maps | corrected Stage 12 state | Forest grass regression occurred | **FIX REPORTED; RE-VERIFY** | Forest plus fences/grates |
| Save/load | identities, overrides, owners, Tesla reset safely | no accepted record | stale history/map-lifetime state possible | **UNKNOWN** | repeated save/load in key scenes |
| Map restart | clean registry/history/caches and correct defaults | no accepted record | old slots/aliases/config state possible | **UNKNOWN** | restart each representative map |
| Shadow budget 5–6 | no crash even if non-default | none | frequent crashes reported | **FAIL/UNRESOLVED** | bounds/resource safety investigation |
| Directional sun | retained quality at acceptable cost | Stage 11 ~65–100 FPS report | later 40–50 FPS aggregate slowdown | **UNRESOLVED** | isolated on/off frame-time comparison |
| Overall performance | improve worst scenes without removing effects | early clean and `35361762179` comparisons | no quantified current breakdown | **UNRESOLVED** | median/1% frame-time, pass counters |

## Known-good reference map

| Desired behavior | Reference | Use restriction |
|---|---|---|
| Original Tesla timing | pinned upstream game/script lifecycle | Reference cadence/lifetime only; lacks later rendering improvements |
| Unified shadows/caster coverage | Run `35150218437` | Preserve behavior; Boss2 was not solved |
| Runtime-tested Stage 11 semantics | Run `35117854581` | Donor experiment contains diagnostic-era context |
| Escape1 lamp behavior | Run `35361762179` | Do not discard later table fix; verify config equivalence |
| Table has one shadow | Run `35503262322` runtime outcome | Do not blindly carry global residency implementation |
| Tesla/grate quality before far fill | Run `35150218437`, then clean lineage | Test only during true active pulses |
| Factory fire shadows | Stage 11 plus FireVol clean lineage | Must retain fire volume and nearby direct lights |
| Dynamic weapon/Tesla endpoints | dlight FX clean production and Stage 11 | Ensure StaticPromote cannot starve them |
| Stable synthetic capture | Run `35356962371` → `35361762179` | Preserve world stability, audit camera-offset semantics |
| Original visual character/material policy | early clean baseline and corrected Stage 12 | `r_pbr 0`; do not use post-processing as compensation |

## Current unresolved technical debt

- No single artifact combines all trusted behaviors: original Tesla cadence, Stage 11 grate shadows, `35361762179` lamps, and RC v0.2 table result.
- The effective physical-fixture identity model is distributed across server, cgame, Rend2, synthetic files, and user overrides.
- Direct-light capacity and global `MAX_DLIGHTS=32` may share a hard ceiling, leaving transient headroom accidental.
- Shadow history uses compact slots and global arrays; higher budget safety is not demonstrated.
- Static world cubemaps may be redrawn every frame; cache correctness for moving casters is unresolved.
- PVS/LOS/multipoint work may repeat in hot paths and may participate in identity churn.
- User-block persistence and application order relative to grouping are not authoritative.
- Configuration layering can silently change active-light count and LocalVol.
- Diagnostic commands/CVars/markers exist in diagnostic artifacts and must not leak into a release.
- No authoritative same-hardware benchmark dataset or runtime screenshot set is stored here.
- Save/load/restart lifecycle coverage is absent.

## Changes that should probably be preserved

This is a historical classification, not a ranking of future solutions.

- Stage 11 unified opaque/alpha-cutout caster and fallback receiver behavior.
- Dynamic weapon, explosion, fire, and Tesla endpoint shadow functionality.
- Factory fire shadow and accepted FireVol appearance.
- Grate, metal door, rail, and other formerly missing caster behavior.
- Run `35361762179`'s verified Escape1 lamp behavior and world-stable synthetic capture result.
- The behavioral separation of 32 cheap active promoted lights from approximately 3 expensive shadow owners.
- LocalVol as an independent accepted effect.
- RC v0.2's visible table outcome: retain the first shadow, remove only the duplicate.
- Conservative material enhancement, corrected grass blending, and `r_pbr 0` visual direction.
- Exact upstream pinning, cumulative/delta replay, module allowlists, hashes, manifests, and unambiguous artifact names.

## Changes that require architectural re-evaluation

- RC v0.2's global “resident physical owner set first” policy and all later recovery packaging based on it.
- USLRD ownership/continuity changes wherever shadow status can alter direct light or LocalVol.
- Synthetic capture offsets that depend on camera position or direction, even if bounded.
- Multiple aliases/candidates independently delivering one apparent physical lamp.
- Candidate-level manual blocks and any accepted-delivery bypass.
- Use of a 32-entry global dlight container for both 32 promoted lights and transients.
- Every renderer/server grace, far-fill, or persistence mechanism that changes Tesla off phases.
- Persistent cubemap caches without explicit invalidation for dynamic casters and map lifecycle.
- Repeated multipoint PVS/LOS/classification scans without map-lifetime caching.
- Higher shadow budgets until fixed-array/resource safety is proven.
- Material/parallax breadth where performance and alpha blending were not runtime accepted.

## Evidence and Git references

### Primary documents

- `AGENTS.md` defines production invariants and audit discipline.
- `docs/PRODUCTION_AUDIT_HANDOFF.md` supplies runtime reports, acceptance/rejection decisions, and required scene matrix.

### Key Git objects

- PCRB: `32eb2fe5` (v0.1 bridge workflow), `0bcd0e07` (v0.2 fixed), `0538b94c` (v0.3), `427e8226`/`e51d028a` (v0.4), `84480149`/`601a7479` (v0.5), `2e0d31fa`/`0522feef` (v0.6), `8bb43aa1` (v0.7 audit).
- Earlier clean line: `4807c0b6`, `27f960c6`.
- LocalVol production/stability: `19ce342d`, `56b1bb02`, `8e0103f9`, `3b81acb6`.
- FireVol clean/final architecture: `a0fdc6a9`, `4966b0b1`, `cf16629e`, `ebafcddf`.
- Dynamic/Tesla/weapon shadows: `de50a522`, `cc6581eb`, `e3588f64`.
- Stage 11: `c1e98ec1`, `d5a58d0a`, `780c1ee7`, `7e457aca`.
- Tesla fill: `09f51646`, `51505438`.
- USLRD: `82065ddb`, `4b9cb031`, `ab37b25e`, `58c3ede7`, `2ef1e72c`, `1cb4cfdc`, `e930035b`, `c8b79541`, clean `79642f32`.
- Table/Tesla/recovery: `fa3dee77`, `80fde84b`, `9a40b9bc`, `bfc84e0d`, `c42493b2`, `6c1d60ad`.

### Current workflow evidence

The seven workflows present at audit HEAD preserve exact base/parent run IDs, artifact IDs/digests, cumulative patch hashes, module hashes, source contract markers, and package names for the table, Tesla diagnostic, recovery, and Release V2 line. In particular, the v0.2 workflow documents the physical-set algorithm and the v0.3 workflow documents the full Tesla snapshot/delivery trace boundary. **[CURRENT]**

### Commands used for this audit

```text
find .. -name AGENTS.md -print
cat AGENTS.md
cat docs/PRODUCTION_AUDIT_HANDOFF.md
git status --short --branch
git log --all --date=short --pretty=... --reverse
git log --all --name-status
git log --all --diff-filter=A --name-only
git show <commit>:<historical-workflow>
rg -i <history and workflow terms>
GitHub REST API: /repos/jaha2002-stack/iortcw-rend2-build/actions/runs/<id>
GitHub REST API: /repos/jaha2002-stack/iortcw-rend2-build/actions/runs/<id>/artifacts
```

## Uncertainties

1. Historical runtime judgments come from the handoff; this audit did not run the Windows game or visually reproduce scenes.
2. GitHub run metadata proves head SHA, workflow path, success, and artifact identity—not gameplay correctness.
3. The exact first commit/run that introduced the Escape1 table duplicate is not established; it is known present in the lineage diagnosed over `35361762179`.
4. The exact first build that changed stationary Tesla cadence is not established.
5. No source-level bisect ties the 40–50 FPS report to one subsystem or commit.
6. Boss2, Xlabs, and Tram lack complete accepted runtime records in the retained evidence.
7. The cause of high-shadow-budget crashes is unknown.
8. The current runnable source postimage is stored in historical cumulative patches/artifacts, not as a normal source tree at repository HEAD; a future source audit must reconstruct exact artifacts before making code claims.
9. Some historical workflows were uploaded, deleted, repaired, and re-uploaded under similar names. Commit SHA plus run ID, not filename alone, is the authoritative identifier.
10. “Accepted RC” in this report means a reported visible outcome was useful; it does not imply the RC's complete global implementation passed every regression surface.

## Audit conclusion

The history supports a composite production target rather than a rollback: original upstream Tesla cadence; Stage 11's accepted caster/receiver and dynamic shadow improvements; Run `35361762179`'s stable lamp behavior and provenance; RC v0.2's single-table-shadow result; LocalVol and conservative material improvements; and a strict separation between physical existence, direct delivery, volumetric delivery, and scarce shadow ownership. It also clearly marks far-fill, renderer grace, global Recovery V1, brute-force shadow budgets, ordinal identity, and candidate-only blocking semantics as rejected or unsafe.

No solution is selected or implemented by this audit.

**REGRESSION HISTORY AUDIT COMPLETE**
