# DarkWolf PCPS V5 — Fire Path Attribution — CI acceptance and handoff (2026-11-03)

**Final successful GitHub Actions:** [#41575510101](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/41575510101). Conclusion SUCCESS, 29 steps. Head SHA `91b7ddef0303711279a9e7fcde424fce222bebf3`. Artifact #13202754055, `DarkWolf-PCPS-V5-FIRE-PATH-ATTRIBUTION-Win64`.

## Independent downloaded-artifact verification

- Final standalone ZIP: `DarkWolf_PCPS_V5_FIRE_PATH_ATTRIBUTION_Win64.zip`; SHA-256 **`943f441f44e410a76be88c23fe3f25e519ed971b9f291c61ceb695fda42fdcc4`**, 6,732,697 bytes.
- Compiled `renderer_sp_rend2_x64.dll`: SHA-256 **`80202cf68d96a071d1f491a0159fc8351ac7961307eb6eacfb363aff524109bf`**, 3,094,010 bytes.
- Outer and inner ZIP CRC PASS. All **64** manifest SHA256SUMS entries PASS. Files: **65**.
- Exactly **61** files of original SAFE Clean [#41297344177](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/41297344177) byte-for-byte identical. Renderer DLL and SHA index replaced; README and V5 manifest added. All ten .cfg files preserved. Parent accepted Texture & Material Fidelity #41286257713.
- Old preliminary [#41575347925](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/41575347925) is OBSOLETE: one slow-path tess submission counter accidentally remained in a source comment; the final run fixes and SHA-verifies it.

## Source provenance

The patch is exactly SHA256 `3b802a6eb8007ecbd35a1271f06e354bdc37c66891ff45c816875135642ef4c3`, applied on exact accepted V4 source.
- `SP/code/rend2/tr_main.c`: V4 SHA `fe45d4079c28610a25efe50988258a1a318b96ef4049ce7d8f5352f2affdbbe9`, V5 SHA `83235e0c4e5096ea50d6ad7b0f4330894fd6f0b410aa9f75bda725511d1f7062`.
- `SP/code/rend2/tr_backend.c`: V4 SHA `9ebb4236ecd976325ce877d8ed7b7b76036624a7de8505819cf70a68c6712c87`, final V5 SHA `8a6cc862ac04431255eb81aa9a69d5fbd1f2d0f21f325b149945951be39ab498`.
- No graphics shader, accepted settings, new cvars, global caster blacklist, Fire/Tesla illumination algorithm, StaticPromote change, or shadow slot budget increase.

## User's seven failed Crypt1 torch tests are established negative evidence

PCPS V4 `dw_ps_light_off` affects only FireVol SYNTHETIC; real FireVol shadow can use a prioritized real DLight cubemap, and separate `R_RenderDlightWorldOcclusion()` creates architectural visibility for DLight. Neither was disabled by V4 synthetic. Crypt1 grate/brazier silhouettes can also be baked lightmap, which source-level counters cannot isolate without different evidence.

V5 addresses the three dynamic paths **independently** and reports actual source-linked backend tess drawSurf submissions/exclusions (NOT GPU per-pixel shadow owner). New audit commands: `dw_ps_fire_link N`, `dw_ps_fire_audit_start`, `dw_ps_fire_audit_save`; independent `dw_ps_fire_synthetic_off/on`, `dw_ps_fire_point_off/on`, `dw_ps_fire_world_off/on`, and corresponding `*_caster_off/on`. Existing V3 `Main/dw_pcps/` A/B journal remains. Baked lightmap is reported UNKNOWN rather than modified.

**A critical warning:** intentionally disabling DLight WORLD OCCLUSION may let direct light penetrate walls; this is a short-lived diagnostic option, not production correction.

**User GPU acceptance is still PENDING.** A successful CI compile and byte-verified ZIP do NOT establish correct Crypt1 visual behavior or zero regressions. Test ONE fire torch, report source link + path audit and compare only specific proven active channel. Do not repeat seven synthetic-only torch tests.

Manual: [integration/pcps-v5/README_RU.md](https://github.com/jaha2002-stack/iortcw-rend2-build/blob/rend2-pcps-v5-fire-shadow-attribution-20261103/integration/pcps-v5/README_RU.md).
