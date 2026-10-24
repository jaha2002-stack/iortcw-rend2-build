# DarkWolf Rend2 v4.4.6 RC4 LUT V05 — Direct-EXE Clean Win64, 24.10.2026

## Final build identity

**Full 12-file ZIP packaged locally (NO BAT / NO CFG shipped):**
- Filename: `DarkWolf_Rend2_v4.4.6_RC4_LUT_V05_DirectEXE_Clean_FINAL_Win64.zip`
- ZIP SHA256: `c3bd6c4ae8a5ca680c0f026df78f4e99547a71fa33a063607753296dc44fd99b`, 5,600,750 bytes, 12 files; ZIP entries validated and no .bat or .cfg.
- User-requested exact parent archive: `DarkWolf_Rend2_v4.4.6_RC4_FourWeek_Master_LUT_V05_Clean_Production_Win64.zip`, verified SHA256 `48516fcd936a019e0a5f824ebbdc19ea9634d753e73e802d4d3db41439fe4bb2`.
- New `ioWolfSP.x64.exe` SHA256 `8c4199d52c29d3a67846c6873d9c3f76229be2bf8846e175ee6fd21ee63f49a4`, 3,718,402 bytes, Windows PE32+ x64.
- New `renderer_sp_rend2_x64.dll` SHA256 `e2a0e49d36de4979c846946245b9e37d5cb16dddcd4262c95d1d01b06f9afd13`, 3,007,809 bytes, Windows PE32+ x64.
- Game DLLs `cgame_sp_x64.dll`, `qagame_sp_x64.dll`, `ui_sp_x64.dll`, SDL/OpenAL DLLs and `darkwolf_ignition_rc_v0_6.pk3` verified unchanged against the requested parent archive.
- Final code compilation and SHA validation: GitHub Actions [run 40105928068](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40105928068), SUCCESS, commit `8582a184d55a2df093ded4eab01aec7e15c0b892`, binaries/evidence artifact ID `12564453721`.
- No GitHub Release was published or modified in this change. No original FourWeek Master tag changed.

## Source changes from verified LUT V05

1. `integration/direct-exe-clean/patch_source.py` alters only `SP/code/rend2/tr_init.c`, `SP/code/rend2/tr_backend.c`, `SP/code/client/cl_main.c`. Renderer 20 quality defaults now explicit, original user-verified procedural GLSL LUT V05 unchanged. Removes forced `r_dlightShadowMaxLights=3` reset from renderer reinitialization. SSGI remains enabled but skips its additive pass when world fog or underwater fog is detected.
2. `integration/direct-exe-clean/patch_native_defaults.py` alters only `SP/code/qcommon/common.c`. Adds `Com_DarkWolfNativeFirstRunDefaults` with **51** baked defaults (no delivered CFG), applied **after retail default.cfg, before user wolfconfig.cfg**. Prevents automatic legacy highVid*/lowVid* recommendations after user video choices. Persistent user settings still use engine's own CVAR_ARCHIVE mechanisms and take precedence when later loaded.
3. `integration/direct-exe-clean/ci_direct_exe_clean.sh` reconstructs canonical source Bloom V2 + CSM + Texture + CAS/A2C/LUT V03 + user-verified V05 fix and compiles both Win64 binaries using pinned MinGW, with fail-closed original source SHAs. `.github/workflows/RC4_V05_DIRECT_EXE_CLEAN_WIN64.yml` is only a Win64 build/evidence workflow; not a public Release workflow.
4. Original accepted effects remain: Bloom v2, dynamic light Fire/Tesla containment, CSM Guard, sun/local/fire volumetrics, CAS 0.55, LUT V05 0.80, SSGI 1, A2C, Texture/Material Fidelity, shadow budgets and optimizations.

## Acceptance

- User-confirmed on RTX 3060 Ti: V05 fixes red speckle/color crush from V03 original master. 
- User-confirmed on Tram: turning SSGI off removed fog image artifacts. The new world-fog SSGI guard is a **source-level candidate**, not yet verified by user with this new EXE/DLL.
- CI verifies compilation and source gates. **Direct EXE cold-start settings persistence, menu behavior, Tram GPU fog visuals and FPS remain UNTESTED on user's PC**. Do not mark fully runtime accepted until the user verifies.
- The resulting ZIP contains no .bat or .cfg. It still requires legally owned RTCW game data (Main/pak*.pk3). Runtime-generated `wolfconfig.cfg` is legitimate and necessary to save user changes; existing external `autoexec.cfg` / older `wolfconfig.cfg` may override new defaults. Back up older configs before first-run testing.
- **DO NOT PUBLISH** a GitHub Release without explicit permission, and **DO NOT** overwrite the original four-week master artifact.
