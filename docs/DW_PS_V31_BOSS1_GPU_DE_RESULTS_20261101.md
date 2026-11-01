# DarkWolf Point Shadow V3.1 — Boss1 D/E GPU field findings (2026-11-01)

**Accepted Clean Production remains immutable:** #41019985033. **Test DLL:** V3 #41194882539. **New experimental branch:** `rend2-point-shadow-v31-one-shot-audit-41019985033`.

## Submitted evidence

User provided two same-scene Boss1 screenshots in order:
- D: `DW_PS_V3_BOSS1_D_EXCLUDE_0000_3636.cfg`, 108 FPS overlay. The huge dark sharp-edged shadow behind the spotlight **persists**.
- E: `DW_PS_V3_BOSS1_E_EXCLUDE_3637_7273.cfg`, 125 FPS overlay. The huge dark shadow **disappears**; spotlight and walls remain visible.
- Previous A/B/C: A huge shadow present; exclude capture (-2428,68,20): huge shadow persists; exclude capture (-2764,-219,-24): huge shadow disappears.
- The V3 backend logged `map=maps/boss1.bsp totalWorldSurfaces=7791 mapped=7791`; independent maplighting/census logs `worldSurfaces=7274`. V3 includes more indices than main-world count, so 0..7273 is deliberately used in this targeted experiment.

## Supported causal envelope

1. The **ordinary point-shadow world/BSP caster contribution** within msurface IDs **3637..7273** affects the huge spotlight silhouette in capture **(-2764,-219,-24)**.
2. Removing 0..3636 alone does not clear it; removing 3637..7273 does.
3. This is a **group intervention**, not proof that a single surface is faulty, that the lamp origin is physically wrong, or that a given surface wins one pixel's depth test.
4. Side-by-side screenshot FPS overlays are **not** controlled performance benchmarks.

## Mandatory next approach (no manual multi-step binary search)

Use one experimental `/exec DW_PS_V31_BOSS1_AUTO.cfg`, with one-shot compiled renderer report:
- No new caster/receiver exclusions, no point origin shift, no global depth clipping.
- Automatically export `dw_ps_v31_boss1_auto.json` with source origin, suspect-range indexes, surface material, bounds, estimated angular extent and presence in shadow drawlist.
- Rank candidates by explicit *heuristics*, **never** imply actual GPU depth owner.
- Final pixel-level proof, if needed, requires a separate verified GPU-ID/debug depth ownership pass; no production fix solely from heuristic ranking.

## Release rules

Preserve exact accepted #41019985033 EXE / other DLLs / CFG / shader output at V3.1 defaults; keep Sun HDR16F, CSM, SSGI, Fire/Tesla guards, Local/Fire volumetric, Bloom, ToneMap, Stage11 full coverage and 3-shadow-slot budget. No Clean Production release prior to user GPU visual pass.
