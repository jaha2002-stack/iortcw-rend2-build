# Clean Production RC3: ten new corrective groups over exact RC2 Complete

Parent game ZIP SHA256: `094ceee1e80f89db2fa0c90d453d9378017269b32f3ba3f175602237cfbc5a06`.
Parent source tree: `c369e629136f8feef70d3ed91a121b3ad7ace151`.
Expected RC3 source tree: `921a3d2a339d3a670c098a777c4c7896d987efe8`.
The full cumulative RC1 -> RC2 -> Complete reconstruction is retained. Main and historical releases are not overwritten. Use the existing single production workflow and isolated branch; PR #4 remains a draft.

## Inspectable source and tests

Run `python3 integration/optimized-v4-4-6/rc3/bootstrap.py` after checkout.
It restores 23 regular source/test/document files from the six repository-owned chunks, after verifying archive SHA256 `7800fd97e7c3e748e44e96486a435d8b5c477636e4e632bdaf43038a320608b2` and safe member paths.
The restored `AUDIT_RC3.md`, `rc3.patch`, `rc3-lock.json`, `audit-coverage.json`, `test_rc3.py` and `tests/*.c` contain the detailed review, exact source delta and runnable tests. No historical Actions artifact is a required reconstruction dependency.

## Ten new groups (not repeated previous optimizations)

1. Bounded Q_stricmpn/Q_strncmp: do not read byte n for an equal n-byte non-NUL span.
2. COM_ParseExt: do not advance beyond NUL after an unterminated quoted token.
3. Command tokenizer/arguments: tokenize the bounded command copy; bounded linear argument assembly replaces repeated unbounded concatenation.
4. Screenshot command lifetime: every queued capture owns its filename, so same-frame captures do not overwrite each other's destination.
5. Polygon submission: safe null-world fog behavior and nonpositive/overflow-resistant input capacity checks.
6. GLSL source/log buffers: reserve source terminator; track log allocation capacity separately from the actual returned length and preserve correct ownership.
7. MDV/MDR tags: start at the requested index, reuse the found index for the second frame, guard negative frames, and replace null-based offset arithmetic with offsetof.
8. Savegame menu text: paint temporary text synchronously and restore the persistent item pointer, including early-return paths.
9. BMP loader: repair the 16-bit out-of-bounds path; bounded BI_RGB 8/16/24/32-bit decoding with row padding, palette, top-down orientation and header/offset validation.
10. Tesla effect: minimum positive hold/pulse intervals and current-bolt vector-component check, preserving ordinary positive-interval RNG use and geometry.

These are primarily correctness and robustness fixes, not ten measured FPS bottlenecks. All GLSL and production quality settings remain byte-identical to Complete. No new temporal shadow cache or gameplay balance/event scheduling redesign.

## Local evidence before CI

Full parent source tree reconstructed and verified. Broad static analyzer sweep: 217 first-party translation units completed, 76 warning records reviewed as candidates (not 76 confirmed bugs). Vendor code is not claimed exhaustively audited; this is not a proof that no defects remain.
Ten actual-source regression groups pass with ASan/UBSan and separately with inherited production flags. Seventeen targeted parent failures are reproducible and candidate probes pass. Parent-only legacy sanitizer exceptions are documented, not applied silently to RC3. Full changed C units pass syntax checks.

CI rechecks retained RC2/Complete tests, executes new tests, rebuilds both Windows SP variants with one toolchain/version, verifies all five PE components, runs fresh paired seven-scenario Mesa smoke and a real same-frame two-screenshot regression where protected assets are available. Source hashes, actual tests, screenshots and binary hashes are separate evidence; no generated picture is used as game proof.

## Release boundaries

Only one clean RC3 game ZIP is published after mandatory gates. No retail pak files, DWPERF/TestLab code, sanitizers or unit fixtures in production binaries. Source patch and provenance are included in docs. No real Windows FPS or 75-FPS claim.
High Quality and launcher are unchanged: forceSun=1, dlightMode=2, StaticPromote=32, persistent shadow slots=3, SSGI/local/sun/fire enabled, PBR=0. Inherited SSAO=0 and indirectLighting=0 remain explicit exceptions; do not call the preset all-effects-on.
The parent SWF white bottom band remains an unresolved visual issue, measured separately in fresh screenshots. Smoke success is not full visual acceptance. Final status stays CANDIDATE_FOR_LOCAL_VERIFICATION until the user's Windows gameplay/performance and visual checks.
