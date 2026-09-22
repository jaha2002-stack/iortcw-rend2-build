# Unified Production Integration Report

**Status:** SOURCE, REPLAY, COMPILE, AND LOCAL PACKAGE COMPLETE
**Date:** 2026-09-22
**Branch:** `rend2-production-unified-integration`

## 1. Exact base reconstruction

The authenticated local base descriptor and cumulative patch were verified before
editing. The base is pinned upstream `438e7d413b5f7277187c35b032eb0ef9093ae778`,
Run `35503262322`, artifact `10603017159`, recipe `80fde84b6e91febd5ab5a8c10e37ed0d6dd01476`,
and SHA-256 `1b766221df31b483877cee2378e3696c7a992abc9cd61628e945b16c145bebe2`.
`git apply --check` and exact application both passed. The baseline source manifest
is stored at `integration/base/TABLE_RC_V0_2_BASELINE_SOURCE_SHA256.txt`.

## 2. Changed files

Production postimage changes are restricted to:

- `SP/code/cgame/cg_ents.c`;
- `SP/code/rend2/tr_scene.c`;
- `SP/code/rend2/tr_main.c`;
- `SP/code/rend2/tr_init.c`;
- `SP/code/rend2/tr_local.h`.

The exact list and changed-function inventory are packaged as `CHANGED_FILES.txt`
and `CHANGED_FUNCTIONS.txt`. Repository additions provide the reproducible patches,
manifests, production configuration, runtime README, packaging script, workflow, and
this report.

## 3. Tesla temporal restoration

`CG_Efx` once again gates the enhanced Tesla submission with the exact original
attached-dlight timing expression. The enhanced endpoint-aware
`electricLightOrigin`, radius/color pulse, and `CG_EFFECTLIGHT_ENVIRONMENTAL_TESLA`
classification remain inside that predicate. No renderer lifetime or replay was
added. Map/script link/unlink and snapshot presence therefore remain temporal
authority.

## 4. Physical StaticPromote block architecture

The existing map-lifetime PLR association is now the override owner. A deterministic
alias set comprises the persistent candidate plus associated light-junior, corona,
native dlight, and fire-speaker ordinals. Any negative legacy or migrated alias
override vetoes the physical owner; block/unblock commands persist the state across
all known aliases without map names or hard-coded fixture IDs.

The veto occurs before unified delivery. A matching already-submitted native alias
is made inert without shifting the fixed scene array: radius and color are cleared,
shadow eligibility is disabled, LocalVol tagging is cleared, and its promoted
fixture identity is removed. Promoted aliases are never submitted. Consequently no
blocked group reaches Direct Light, all-active LocalVol, or point-shadow eligibility;
old shadow history fails normal owner revalidation in the same frame.

## 5. Direct/LocalVol/shadow independence verification

The integration does not change the three policies. Direct delivery still uses
classifier acceptance and actual scene headroom, Mode-5 LocalVol still enumerates
all delivered canonical groups without consulting compact shadow slots, and the
point-shadow selector remains separately budgeted. Physical blocking is an upstream
veto, not a shadow-slot coupling.

## 6. Table RC productionization

The resident physical-owner selector is preserved: previous-owner reconstruction,
duplicate suppression, eligibility revalidation, capture-radius/hysteresis release,
old-slot affinity, resident compaction, and residents-before-challengers remain
unchanged, including the accepted `!r_dlightDiagForceSelect->integer` behavior.

Only the RC snapshot command, camera cache, snapshot formatters, registration,
unregistration, and declaration were removed. RC provenance markers were renamed to
the production policy name. Recovery V1 was not imported.

## 7. Dynamic-light headroom verification

The source still computes native scene use first, then `MAX_DLIGHTS - r_numdlights`
headroom, then caps StaticPromote by that headroom. Existing cgame muzzle, explosion,
fire, and Tesla sources therefore retain ordering priority over promoted additions.

## 8. LocalVol verification

Clean V1 all-active Mode 5 remains fixed on. It scans delivered dlights, canonicalizes
physical groups, and renders unshadowed LocalVol independently of compact point-shadow
ownership. The package enables `r_volumetricLocal 1` and Mode 5.

## 9. Shadow budget verification

`MAX_DLIGHT_SHADOWS` remains 8. The persistent default remains 3 and the protected
dynamic reserve remains 2, for up to five normal selected owners. No shadow cache,
throttle, face skipping, resolution reduction, or budget increase was introduced.
The reported high-budget crash remains unresolved and is not claimed fixed.

## 10. Rejected mechanism absence

Static scans confirm no Tesla 650 ms grace, light replay/cache, START/RESUME/EXPIRE
residency telemetry, residual/far-fill Tesla, Recovery V1, table snapshot command, or
map/fixture-specific integration condition was introduced. The authenticated Clean
V1 base retains internally compiled diagnostic implementation names whose public
CVar/command surface is frozen to production-off aliases; the integration adds no
new diagnostic surface and removes the Table RC snapshot surface.

## 11. Configuration cleanup

`UNIFIED_PRODUCTION.cfg` selects Rend2, sets StaticPromote to 32, the persistent
shadow budget to 3, LocalVol on/Mode 5, and PBR off. The source default for `r_pbr`
is also restored to 0. Bloom, ToneMap, and Exposure are not set or changed. No saved
user configuration is packaged.

## 12. Compile results

The canonical MinGW Windows x64 SP build succeeded. The rebuilt changed modules are:

- `renderer_sp_rend2_x64.dll` — `c96d1e93f903a51db31ab39e4846f8b39158cd36755516090779abdfb249b42f`;
- `Main/cgame_sp_x64.dll` — `f7705ba005c5a9442ca8eaeb5e0874739c2e717c81353bce36964b08cd5798db`.

The packaging build also supplies the required SP executable, baseline renderer,
runtime libraries, qagame, and UI DLL so the single package is self-contained.
Compiler warnings are inherited; there were no compilation or link errors.

## 13. Replay/reproducibility verification

The final cumulative patch was applied with `git apply --check` and verbose exact
application to a second clean pinned-upstream clone. Every hunk reported `cleanly`;
there were no offsets or fuzzy hunks. The integration and replay SHA-256 source
manifests are byte-identical.

- integration delta SHA-256: `23f859e06c984b5d66af3cc1fb5d4163fec1223f98b7d8de86b2e0fe9ce38e8e`;
- final cumulative patch SHA-256: `3710fcdca411ea4873a3a710edf6efa84aeff1344e4bae1752fb6273170a2ebf`.

## 14. Final binary hashes

The complete binary manifest is generated inside the package at
`docs/SHA256SUMS.txt`. The two behavior-changing DLL hashes are listed in section 12.

## 15. Final artifact provenance

Local package name:
`DarkWolf-ioRTCW-Rend2-Unified-Production-V1-Win64.zip`.

Local package SHA-256:
`f12191d4d089ea2d15868e9ea12dbc1ee742e3416fbe2079ebd527c9da4245e5`.

The workflow uploads exactly one Actions artifact with the corresponding concise
name and records its run ID, artifact ID, Actions digest, and DLL hashes in the job
summary. The provenance document inside the ZIP records the pinned/base lineage,
commit, patch hashes, workflow run, and binary hashes; Actions assigns the artifact
ID after upload, so that post-upload value is recorded in the workflow summary.

## 16. Runtime test matrix

The single package README requests one integrated pass covering Escape1 doctor's
office Tesla timing/grate, Escape1 table near/medium/far motion, SWF lamp rows,
physical block/unblock, dynamic sources under lamp load, Factory, Boss2, Xlabs,
Tram, save/load, and map restart. It also requests comparable FPS for Escape1, SWF,
Factory, and Boss2 and correlation with Tesla/fire/shadow activity.

No visual runtime PASS is inferred from compilation.

## 17. Remaining known risks

1. Visual runtime acceptance still requires the user's full matrix.
2. The 5–6 persistent-budget crash remains unproven; production remains at 3.
3. Selected point owners still recapture six cubemap faces; caching is deliberately
   deferred pending measured runtime results and a proven invalidation model.
4. A native alias is suppressed by clearing its already-submitted dlight in place;
   runtime block/unblock testing must confirm every historical native source refreshes
   normally on the next frame.
5. Clean V1's frozen internal historical diagnostic implementations remain in the
   authenticated base, although no production diagnostic command/CVar is exposed by
   this integration. Future source-only cleanup should be separately proven rather
   than mixed into this behavior release.
