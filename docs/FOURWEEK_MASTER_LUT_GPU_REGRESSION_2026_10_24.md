# FourWeek Master visual regression: RTX 3060 Ti LUT / red pixels (2026-10-24)

## User-verified facts, not CI inferences

- Historical visually good baseline: RC4 Bloom v2 run 38798189322 plus CSM Guard DLL run 39152821574.
- Full SourceDefaultsON Master from run 40074980554 causes black-crushed scenes and red speckle/pixel artifacts on game maps (screenshot initial room, further runtime on `baseout`).
- GPU reported: NVIDIA RTX 3060 Ti, NVIDIA driver 581.95, desktop OpenGL 3.2, HDR=1, MSAA actualSamples=4.
- Runtime experiment on original Master: `r_dwLutStrength 0` plus `r_dwCasStrength 0` restores correct image.
- Controlled single-variable tests: **LUT 0.80 + CAS 0 => RED/BLACK regression**; **LUT 0 + CAS 0.55 => normal**. Therefore LUT-enabled final processing is implicated; CAS-alone is **not** the cause.
- LUT V04 from run **40096338943** changed only CPU LUT table generation, passed C/native matrix and Win64 compilation, **FAILED real GPU visual acceptance**: user still observed red image after replacing candidate DLL. New user `rtcw1.txt` shows repeated renderer init and explicit `vid_restart` but does NOT provide a DLL checksum/version marker, so binary replacement is not cryptographically proven by that log alone.
- The original atlas LUT shader `SP/code/rend2/glsl/dwfinal_fp.glsl` samples `u_LevelsMap` / 16x16x16 packed 256x16 atlas; `tr_backend.c` binds table on `TB_LEVELSMAP`; source can be externally overridden if `r_externalGLSL 1`. LUT V04 did **not** change the shader sampler, so it could not disprove atlas-path or external shader faults.
- The V03 contrast curve causes dark shadow crush in isolation, but LUT V04's strictly bounded, luminance-preserving table **still produced a red image on the user's GPU**. Therefore the earlier confident claim that contrast was the complete root cause was incorrect.

## Scoped V05 diagnostic candidate (not production)

- Branch `rend2-lut-v05-atlas-bypass-20261024`, exact master base commit `2ef7ad6bd9dbe8e03b561b4be6279953e51ceee1`.
- Patch `integration/lut-v05/LUT_V05_ATLAS_BYPASS_ONLY.patch` changes ONLY:
  - `SP/code/rend2/glsl/dwfinal_fp.glsl`: analytically evaluate 3 color grade modes from RGB instead of sampling `u_LevelsMap`; mode0 is exact identity; modes1/2 preserve luminance and bound channel adjustments.
  - `SP/code/rend2/tr_backend.c`: convey selected LUT mode in `u_Color.z`; do not bind LUT atlas sampler.
  - `SP/code/rend2/tr_glsl.c`: force internal `dwfinal` GLSL rather than potentially stale external PK3 file, leave all other GLSL source selection unchanged; log `DARKWOLF_LUT_V05_PROCEDURAL_ACTIVE`.
- Keeps CAS 0.55 and LUT 0.80 enable controls, CSM Guard, Fire/Tesla LightContainment, Bloom v2, Texture/Material Fidelity, SSGI, A2C, volumetrics, shadows, material pipeline and EXE as in master. It is **not the original 3D atlas LUT implementation**; it is a controlled substitution to identify the GPU lookup problem before deciding how to repair the atlas production implementation.
- Static source checker `integration/lut-v05/test_lut_v05.py` checks 29,101 RGB values, all modes, no channel introduced from black, bounded changes, exact three-file hashes, identity and renderer GLSL markers.
- Previous diagnostic run `40097905973` successfully built Win64 DLL and ran source tests; it failed a standalone `glslangValidator` call because the tool defaulted to ES 100 without a desktop shader header. This is a CI syntax-check harness mismatch, not a reported runtime GL shader compilation failure.
- Final corrected desktop GLSL validation and Win64 candidate run: `40098098000`. Verify SUCCESS and artifact DLL hash after completion; do NOT claim production success before user GPU test.

## User hardware acceptance steps

1. Back up the original `renderer_sp_rend2_x64.dll`. Change ONLY that DLL in the FourWeek Master folder.
2. Verify DLL `Get-FileHash` matches the specific V05 artifact's published `LUT_V05_RENDERER.sha256` (GitHub Actions ZIP SHA is a separate value).
3. Start game with original high quality mode; on console `r_dwLut 1`, `r_dwLutStrength 0.80`, `r_dwCas 1`, `r_dwCasStrength 0.55`, `r_dwLutMode 1`, `vid_restart`.
4. **REQUIRED:** console log contains `DARKWOLF_LUT_V05_PROCEDURAL_ACTIVE atlasSampling=0 builtinDwfinal=1`. If absent, do not conclude whether V05 works: verify DLL load path, SHA and GL shader initialization.
5. Re-test matching game positions and maps; compare red noise and shadow detail to RC4 Bloom v2 + CSM Guard and original Master. If clean, treat old GPU LUT atlas/external GLSL path as implicated and propose repair of real LUT texture backend separately, not blanket rollback of accepted improvements.
6. If still red despite marker, narrow to `r_dwLutMode 0` (identity analytic) and cross-check `r_dwLutStrength 0`. Do not claim root without evidence.

## Restrictions

- No changes to permanent clean Draft Release, baseline tag or historic Git backup.
- A successful CI build does NOT mean graphical correctness or FPS parity.
- The external shader packs and unrelated user model PK3 files are not confirmed to contain conflicting `dwfinal` GLSL; treat that as a hypothesis, not a conclusion.
- Remove diagnostic mode/log code and restore a fully verified LUT backend only **after** visual GPU acceptance.
