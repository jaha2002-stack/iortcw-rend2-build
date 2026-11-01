# Boss1 V3.1 automatic fixture test — collector failure (2026-11-01)

Received user archive `DW_PS_V31_BOSS1_FIXTURE_RESULTS_20261101_133439_803bee.zip`. CRC passed; it contains only the 44,117-byte console log (840 lines) and 511-byte collection status, **no JPEGs**.

Factually confirmed in the console log:
- `Wrote screenshots/DW_PS_V31_BOSS1_03_EXCL_7234_EMISSIVE.jpg`, `DW_PS_V31_PHASE_03_DONE excludedID=7234..7234` (lines 181–182).
- `Wrote screenshots/DW_PS_V31_BOSS1_04_EXCL_7229_7234_FIXTURE.jpg`, `DW_PS_V31_PHASE_04_DONE excludedID=7229..7234` (lines 508–509).
- `Wrote screenshots/DW_PS_V31_BOSS1_05_RESTORED.jpg`, `DW_PS_V31_FIXTURE_AUTOTEST_END renderer_restored_to_no_filter`, `Dumped console text` (lines 837–839).

Phases 01/02 are outside the last console buffer segment and cannot be verified from this truncated condump. `FILE_COLLECTION_STATUS.txt` reports MISSING for all five JPEGs, but FOUND for the console log under `C:\\Return to Castle WolfensteinPBR\\main\\`.

**Failure class:** collection-path discovery failure, not demonstrated graphics failure. iortcw multi-user screenshots often reside under a user homepath separate from the game installation directory; Windows redirected Documents/OneDrive and VirtualStore must be searched. A console `Wrote` message confirms issuance, not independently a valid file on disk.

A revised standalone `RECOVER_DW_PS_V31_BOSS1.cmd` + PowerShell collector has been prepared for the user. It searches Windows KnownFolder Documents, redirected OneDrive, appdata, virtualstore, profile, game root, and additional game-library roots; validates JPEG magic and SHA-256, archives screenshots and provenance. **No rerun of the game is required while existing shots are recoverable.**

No per-surface causal attribution can be established without images. Current prior evidence only: group 3637..7273 affects unwanted Boss1 spotlight shadow for capture (-2764,-219,-24); ID7232 and ID7234 are candidates, not confirmed owners. Clean #41019985033 remains unchanged.