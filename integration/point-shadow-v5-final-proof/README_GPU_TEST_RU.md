# DarkWolf V5 — SECOND and FINAL proof attempt (TEST ONLY)
Date: 2026-11-01. Base accepted Clean #41019985033 unchanged.

This is NOT a finished production fix. It is the user's **last allowed test release**. The next user-facing release must be Clean Production ONLY after full visual acceptance. No additional diagnostic rounds.

## Why this candidate design
- Boss1 V3.2 and V4 fixed the oversized polygon by removing ONE source-local housing surface, preserving stand shadows. V5 tries the same **spatial link and high angular size rule** without hardcoded Boss1 ID or shader.
- Crypt1/Crypt2 have 10/10 identical relative AABBs for source-centered `metal_m04dg2` cage radial panels (Z=-40..+64, XY +/-16). V4 selected 3 of many: removing 3 did not remove the octagonal blot. V5 independently groups ALL symmetric radial panels of the **current** source; tries a separate small horizontal plate/dish beneath fire, and their union. No shader name is used as a universal exclusion.
- Factory V4 found nearest two physical ladder-like rails; partial selection did not remove the very thick wall silhouette. V5 **does not** remove a Factory caster as the candidate fix; its mode2 only removes a selected paired rail group as a control to distinguish normal ladder shadow from another overlapping caster. Loss of physical ladder shadows in control MUST NOT be shipped.
- Rocket/Escape1 controls have near-emitter geometry which is not proven wrong. Strict geometry and source matching prevent bulk/global material removal.

## One command and automatic evidence per map
1. Separate test installation; backup DLL. Copy V5 renderer and CFGs to proper game directories.
2. Start from a fixed SAVE and camera on Boss1, Factory, Crypt1, then Crypt2.
3. Run `/exec DW_PS_V5_PROOF_AUTOTEST.cfg` once per map and do not move camera.
4. Wait for `DW_PS_V5_PROOF_FINISHED`.
5. Double click `COLLECT_DW_PS_V5.cmd` *after each map* to produce ZIP of six screenshots, six condump logs, three mode JSON, source selection and hashes.
6. Send four ZIPs to ChatGPT. No further user commands or manual surface numbers.
7. After testing `/exec DW_PS_V5_RESET.cfg` or restore original Clean #41019985033 DLL.

## What each screenshot proves
1. WARMUP_CONTROL — allow shadows, exposure and fire to settle after vid_restart.
2. STABLE_BASELINE — real baseline control for A/B, compare to phase 06.
3. SOURCE_LOCAL_FIX — **the only candidate repair rule**: dominant emitter-linked opaque housing OR small horizontal source bowl beneath validated symmetric cage. If no confident geometry, no caster is skipped.
4. CONSTRUCTION_CONTROL — temporarily excludes all verified radial cage faces around source OR paired ladder rails near source. This is diagnostic attribution only; it can remove legitimate physical shadows.
5. COMBINED_CONTROL — temporary union of all source-attached groups for attribution only; NEVER a default production rule.
6. RESTORED — all proof and V4 filters off; expected to reproduce stabilized baseline apart from fire animation.

Proof logs `DW_PS_V5_CLASSIFIED`, `DW_PS_V5_SOURCE_LOCAL_SKIP`, `DW_PS_V5_PROOF_REPORT_OK` must match the intended source. If a mode has zero skips, it is a NO-OP and not evidence of a successful correction.

## Acceptance criteria
Boss1: huge solid polygon removed by source-local fix; holder/stand shadows remain; restore returns baseline.
Crypt1/Crypt2: undesired octagon disappears only if actual surface(s) excluded from this lamp's ordinary point cubemap; acceptable bowl/pole/architecture shadows retained. Fire flicker and exposure differences must be identified by stabilized A/RESTORE pair.
Factory: classify whether thick ladder shadow is physically cast by visible rails/rungs, from a different BSP surface, or inconclusive; NEVER erase legitimate ladder shadows by broad global material exclusion.
Protected: CSM/Sun, Fire/Tesla worldmask, 32 StaticPromote and 3 slots, Volumetric, SSGI, Bloom, Texture Fidelity, LUT/CAS/A2C; no global shader or texture exclusions.

If any map remains unproven, record it honestly and do NOT claim the next release is a universal Clean Production. User allows no additional diagnostic game releases.
