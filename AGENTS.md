# AGENTS.md — DarkWolfRTCW / ioRTCW Rend2 Production Audit

This file defines persistent repository-level instructions for every Codex task working on the DarkWolfRTCW / ioRTCW Rend2 Single Player production audit.

## Primary authority

Before substantial work, read:

`docs/PRODUCTION_AUDIT_HANDOFF.md`

That handoff is the authoritative technical history, scope, regression record, acceptance criteria, known-good runs, known defects, and production goals.

Do not replace its requirements with assumptions derived from only the latest workflow or latest commit.

## Project objective

The end goal is a public-ready, optimized ioRTCW Rend2 SP build that preserves the visual improvements accumulated during development while eliminating regressions, instability, accidental coupling between subsystems, and major performance losses.

The work is not a request for isolated local fixes. Treat the renderer, lighting, shadow, StaticPromote, Tesla, volumetric, material, PVS, residency, and runtime-selection systems as an interacting architecture.

## Mandatory engineering method

Before changing behavior, trace the complete chain:

`symptom -> producer -> identity/ownership -> lifetime/residency -> selectors/budgets -> consumers -> shared resources -> regression surface`

Do not patch the final visible symptom until the upstream ownership and lifecycle are understood.

For any nontrivial fix:
1. Identify the exact producer of the state.
2. Identify all consumers of that state.
3. Identify shared budgets, masks, indices, residency sets, caches, and global arrays involved.
4. Identify which historical behavior is intentional and which is a regression.
5. Check the affected regression matrix from the handoff.
6. Prefer architectural separation over compensating timers, grace periods, or duplicated delivery paths.

Compilation success is not proof of correctness.

## Production invariants

These are hard constraints unless the handoff explicitly authorizes a change.

### Stationary Tesla
- Restore the original temporal behavior of the stationary Tesla as implemented by the original game/gameplay/script/entity lifecycle.
- Preserve the original pulse frequency, timing, activation pattern, and lifetime semantics.
- Do not fake the original timing with renderer-only grace periods, forced persistence, or arbitrary millisecond extensions.
- Preserve the improved Tesla lighting and shadow behavior already achieved in Escape1.
- Preserve shadows projected through the grate / metal grid in the doctor's office.
- Do not regress stationary Tesla visibility or its interaction with nearby geometry.

### StaticPromote / stationary fixtures
- Direct-light residency, Local Volumetric residency, and shadow-slot residency are separate concepts.
- Losing a shadow slot must not turn off or dim the corresponding stationary direct light.
- Up to the configured StaticPromote active-light budget may remain illuminated independently of the much smaller shadow budget.
- The intended production policy is approximately:
  - up to 32 active accepted stationary fixtures;
  - approximately 3 expensive shadow slots by default;
  - dynamic/transient sources remain independently functional.
- Do not assume that 32 active StaticPromote fixtures should consume all global dynamic-light shadow resources.
- Blocking a fixture must eventually mean no delivered direct light, no LocalVol contribution, and no shadow contribution from that fixture.
- Avoid multiple logical fixtures controlling one physical lamp unless explicitly justified and deterministic.

### Dynamic lights
- Weapon flashes, explosions, fire, Tesla transients, and other dynamic sources must remain functional.
- Dynamic selection and transient behavior must not be starved by StaticPromote residency.
- Preserve existing useful dynamic shadow behavior.

### Shadows
- Preserve improved caster/receiver behavior for grates, metal doors, rails, and other previously missing casters.
- Do not reintroduce the Escape1 table double-shadow / distance-dependent darkening defect.
- Keep the normal first table shadow while removing only the duplicate/darker contribution.
- Treat crashes observed with higher `r_dlightShadowMaxLights` values as a real safety/performance defect to investigate, not as a reason to hide the problem.

### Visual fidelity
- Preserve the original RTCW visual character.
- Do not introduce PBR unless explicitly authorized by the handoff.
- Do not change Bloom, ToneMap, or Exposure as part of unrelated renderer/shadow fixes.
- Preserve working specular/material improvements unless a proven regression requires a targeted change.

## Performance rules

The audit must explain scenes where frame rate falls to roughly 40–50 FPS.

Do not optimize blindly.

Measure or statically account for, where possible:
- CPU frame cost;
- GPU/pass cost;
- shadow cubemap face rendering;
- number of shadowed lights;
- redundant PVS/LOS/classifier work;
- repeated per-frame fixture binding;
- Local Volumetric cost;
- material/parallax/specular cost;
- overdraw;
- duplicated renderer submissions;
- allocations and transient buffers;
- unnecessary shadow recapture;
- unnecessary state churn.

Prefer caching, stable identities, bounded budgets, and separation of expensive work from cheap persistent illumination.

An optimization is rejected if it silently removes required visual behavior.

## Historical evidence

Use Git history aggressively.

The repository intentionally preserves historical workflows and commits. Important run IDs, artifact IDs, hashes, and known-good references are listed in `docs/PRODUCTION_AUDIT_HANDOFF.md`.

When a behavior regressed:
- find the last known-good implementation;
- compare the exact code path;
- distinguish gameplay-side changes from renderer-side changes;
- avoid rebuilding a historical bug merely because it appears in an old run.

Run `35361762179` is an important behavioral reference for earlier lamp behavior, but it is not an instruction to discard all later improvements.

## GitHub Actions / provenance

Production workflows are part of the system design.

When modifying or creating workflows:
- pin exact upstream source revisions where appropriate;
- preserve reproducible provenance;
- verify hashes for inherited artifacts/patches when used;
- keep diagnostic workflows separate from clean production workflows;
- remove temporary diagnostics, test-only Cvars, debug commands, and periodic telemetry from final production artifacts;
- produce explicit validation records;
- keep artifact naming and lineage unambiguous.

Do not treat a successful CI compile as runtime acceptance.

## Audit phase versus implementation phase

If a task is explicitly marked DIAGNOSTIC/AUDIT ONLY:
- do not change production source;
- do not create speculative fixes;
- produce evidence and a technical report only.

If a task explicitly authorizes implementation:
- make the smallest architecture-consistent change that resolves the proven root cause;
- update relevant validation/report files;
- explain regression risk;
- run all available static/build checks;
- never claim visual runtime acceptance without actual runtime evidence.

## Required regression surfaces

At minimum, consider the scenes and behaviors documented in the handoff, including:
- Escape1 doctor's office;
- Escape1 table double-shadow case;
- stationary Tesla;
- Tesla through grate / metal grid;
- SWF multi-lamp rooms;
- Factory lighting/fire cases;
- Boss2 Tesla/grate case;
- Xlabs / Tram / other heavy scenes;
- weapon and transient light shadows;
- StaticPromote stability near/inside fixture radius;
- save/load and map restart where relevant.

Do not close a global renderer change after testing only one scene.

## Reporting standard

Every substantial task should end with:
- root cause or strongest supported hypothesis;
- files/functions examined;
- evidence from Git history or source;
- affected subsystems;
- regression risks;
- tests/checks performed;
- unresolved uncertainties;
- next recommended action.

Separate facts from hypotheses.

## Change discipline

Do not:
- add map-specific hacks unless explicitly approved as a last resort;
- key production behavior to one hard-coded entity number when a stable identity mechanism exists;
- create hidden coupling between shadow selection and direct-light delivery;
- preserve an experimental workaround only because it appears to fix one scene;
- alter unrelated post-processing;
- leave abandoned telemetry/debug Cvars in clean production;
- rewrite major renderer subsystems without first proving why smaller architectural corrections are insufficient.

## Final release acceptance

The final production candidate must satisfy the handoff's acceptance criteria, including:
- restored original stationary Tesla timing;
- preserved Tesla/grate shadow quality;
- stable stationary lighting;
- independent active-light and shadow budgets;
- no Escape1 table duplicate shadow;
- preserved dynamic lighting/shadows;
- no known crash regression from shadow selection;
- materially improved performance in previously slow scenes;
- clean production configuration;
- no experimental telemetry/debug residue;
- reproducible GitHub Actions artifact;
- explicit regression and performance reports.

When in doubt, prefer preserving verified working behavior and gather more evidence before changing code.
