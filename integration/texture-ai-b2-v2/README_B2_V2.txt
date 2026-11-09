DarkWolf Local AI Texture Restoration B2 V2 — Win64 TEST

This release combines both requested stages.

STAGE 1 — B2 V1.1 HOTFIX
1. /dw_tex_save no longer asks the ioRTCW filesystem to open a .pk3.
   The renderer writes a standards-compatible stored ZIP/PK3 through physical
   Win32 file I/O, first as .pk3.tmp and then atomically renames it to .pk3.
   This specifically removes the fatal:
   FS_FOpenFileWrite: Not allowed to manipulate ... due to pk3 extension

2. Orientation fix for asymmetric textures.
   ioRTCW RE_SaveJPG internally writes RGB rows bottom-to-top. B2 V1 supplied
   the renderer-order pixels directly, so a window/wood texture could reach
   Real-ESRGAN vertically inverted. B2 V2 pre-flips the RGB input before the
   renderer JPEG writer; the two flips cancel and Real-ESRGAN receives the
   canonical orientation.

STAGE 2 — MULTI-VARIANT
One local Real-ESRGAN x4plus inference is used to create three bounded variants.
The original 4x structural reference stays dominant; AI contributes controlled
detail and substantially less chroma change than luma change.

Variant 1 FAITHFUL
  luma AI 35%, chroma AI 10%, max luma delta 36

Variant 2 BALANCED — DEFAULT FOR RTCW
  luma AI 55%, chroma AI 20%, max luma delta 56

Variant 3 STRONG
  luma AI 80%, chroma AI 35%, max luma delta 88

COMMANDS
/dw_tex_ai_info
/dw_tex_pick
/dw_tex_ai_build     -> builds all 3 variants, shows BALANCED
/dw_tex_next         -> Faithful/Balanced/Strong cycle forward
/dw_tex_prev         -> cycle backward
/dw_tex_ab           -> ORIGINAL <-> current variant
/dw_tex_info         -> current variant and output information
/dw_tex_save         -> save exactly the current variant to zz_dwtr_<hash>.pk3
/dw_tex_discard      -> return to original and clear candidate CPU buffers

FIRST TEST
Use escape1 and first retest:
A. the same castle wall from B2 V1;
B. the asymmetric wood/window texture that was upside-down in B2 V1.

For the window, verify orientation before judging AI quality.
For the wall, compare all three variants using next/prev.

Runtime AI remains completely local:
Real-ESRGAN realesrgan-x4plus + ncnn/Vulkan, network OFF, telemetry OFF.
