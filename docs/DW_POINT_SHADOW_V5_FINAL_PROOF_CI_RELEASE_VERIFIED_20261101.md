# DarkWolf Point Shadow V5 — FINAL user-facing proof release, CI verification (2026-11-01)

**User constraint:** V4 diagnostic (first experimental release, tested on 9 archives) and V5 proof (SECOND AND LAST experimental release). Third release is CLEAN PRODUCTION ONLY if GPU proof passes; otherwise stop and report blockers.

## CI and artifact

- Latest fixed-source GitHub Actions run: **#41294915333**, URL https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/41294915333, head commit `2d1b833b26f5d339910f498cf5cfb5c24270e288`. Completed SUCCESS, all 29 workflow steps pass.
- A prior V5 run #41294784788 also compiled but **must not be distributed**, because final build fixes a first-pass candidate classification dependency on premature `seenDraws`.
- Published release ZIP: `DarkWolf_PointShadow_V5_CrossMap_SourceLocal_PROOF_FINAL_ATTEMPT_41019985033_Win64.zip`.
- Outer GHA artifact id **13078948259**; outer GHA zip CRC PASS, nested release ZIP CRC PASS; 63 file entries, 62 SHA-256 table entries ALL MATCH.
- Release ZIP SHA256 `44e3b2bae10ec7b6372a5ad6855799650d716c3dd4f81282aa4c5ff38fdd113f`.
- Win64 experimental renderer DLL SHA256 `b7b8ad1ee237dad4cff60e89238cbcba538d9b6ef8d20ab52ec3411bcdf910bb`, PE MZ, 3,069,088 bytes. All debug marker strings V4/V5 + Sun HDR16F included.
- Original accepted #41019985033 renderer `d7423e8648e2de556f79c7cddecf1a8df16b9f60a46c503d1440089876116b45`. All 55 unrelated original files kept byte-for-byte unchanged (except renderer and SHA list).
- Pack contains `Main/DW_PS_V5_PROOF_AUTOTEST.cfg`, `Main/DW_PS_V5_RESET.cfg`, `COLLECT_DW_PS_V5.cmd`, `COLLECT_DW_PS_V5.ps1`, complete Russian test instructions and manifest.

## One automated proof procedure per map

Test Boss1, Factory, Crypt1, Crypt2 only, each on original saved camera, no user moving it:
1. `/exec DW_PS_V5_PROOF_AUTOTEST.cfg`.
2. Test auto-captures **six phases**: 01 warmup, 02 stable baseline, 03 source-local conservative candidate FIX, 04 construction-shadow diagnostic CONTROL (radial cages or factory ladder rails), 05 combined CONTROL, 06 restored. Each stage has condump and screenshots. Mode2 and Mode3 must never be production defaults.
3. After finished text appears run `COLLECT_DW_PS_V5.cmd` from release package. It searches Windows user/game screenshot paths, bundles 6 JPGs, logs, per-map JSON reports, selection cfg and SHA hashes. Send one ZIP per map. Collector MUST be run after each map to prevent screenshot filename overwrites.
4. If needed `/exec DW_PS_V5_RESET.cfg` and restore accepted renderer after test.
5. Acceptance: actual source-correct skip logs, reliable warmed A/restored controls, Boss1 preserves right stand shadows, Crypt1/2 octagon removed if and only if verified nonphysical, Factory rail shadow only suppressed as diagnostic control and decide physical correctness rather than blindly erasing it. Protected effects and static-promote 32/3 preserved.

## Current scope

The proof DLL may find zero confident candidates on Crypt1/2 or Factory; this is a NO-OP not a fix. The 'source-local' label is an algorithm scope, not pixel-depth-winner verification. Do not assert universal fix until user's actual four-map GPU files have been inspected. Do not create further user-facing diagnostic releases under the two-attempt constraint.

See `docs/DW_POINT_SHADOW_V4_NINE_ARCHIVES_CROSSMAP_EVIDENCE_20261101.md`, `docs/DW_POINT_SHADOW_V5_FINAL_PROOF_HANDOFF_20261101.md`, `docs/DW_PS_V5_PRE_GPU_RULE_SPECIFICITY_NINE_ARCHIVES_20261101.md`.
