DarkWolf Local AI Texture Restoration B2 V2.4 — Universal Texture Picker

BASE
  Unified Clean Production Run #42736840967
  commit 2cca3afcbe908b3f07d99afa6fd1085bc223d883

GOAL
Expand only texture selection coverage while preserving the proven B2 V2.3
AI pipeline and single cumulative PK3 persistence.

NEW PICKER COVERAGE
- WORLD BSP surfaces
- inline MOD_BRUSH entities (doors, rotating doors, lifts)
- scaled/non-normalized MOD_BRUSH entities via correct inverse axis transform
- MOD_MESH MD3/MDC runtime entities, including animated frame interpolation
- model customShader
- model customSkin surface shader resolution

INTENTIONALLY NOT ADDED
- sky
- water
- slime/lava
- portals
- skeletal MDS/MDR/IQM models

SAFETY
- excluded sky/water/liquid/portal surfaces block selection behind them
- unsupported/special images continue to be rejected by the existing B2 V2.3 AI guards
- alpha/cutout safety rules are unchanged
- Real-ESRGAN model and FAITHFUL/BALANCED/STRONG are unchanged
- /dw_tex_save is still B2 V2.3
- zzzzzz_DW_TextureRestoration.pk3 and .pending startup promotion are unchanged
- no Internet and no telemetry at runtime

COMMANDS
  /dw_tex_pick
  /dw_tex_info
  /dw_tex_ai_build
  /dw_tex_next
  /dw_tex_prev
  /dw_tex_ab
  /dw_tex_save

The expected practical improvement is that doors implemented as model entities,
plus scaled brush doors that V2.2 skipped, can now be selected by the same crosshair workflow.

BUILD TARGET
  GitHub Actions workflow: DW Texture B2 V2.4 Universal Picker Win64 TEST
