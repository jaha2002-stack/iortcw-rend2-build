DarkWolf Local AI Texture Restoration B2 V2.1 — Win64 TEST

This is B2 V2 from successful Run #42574596120 plus one persistence/autoload fix.

ROOT CAUSE
ioRTCW SP filesystem has a historical sorting kludge:
- filenames beginning with sp_ are temporarily changed to zz_ for sorting;
- later ANY name beginning with zz_ is changed back to sp_ before loading.

B2 V2 created accepted overrides as:
  zz_dwtr_<hash>.pk3

Therefore on restart the engine could turn that real filename into:
  sp_dwtr_<hash>.pk3

That file does not exist, so the saved override is skipped.

FIX
B2 V2.1 writes:
  zzz_dwtr_<hash>.pk3

"zzz_" does not match the exact "zz_" rewrite, while still sorting very late and
therefore keeping high override priority.

SAVE LOCATION
The renderer intentionally writes to:
  fs_homepath/<game>/

That is a valid ioRTCW search-path directory and normally has higher priority
than fs_basepath/<game>. The command now prints the exact physical PK3 path after
save so the user can verify it directly.

OLD FILES
Old zz_dwtr_*.pk3 files from B2 V2 are not useful for autoload and may be deleted.
B2 V2.1 creates new zzz_dwtr_*.pk3 files.

TEST
1. /dw_tex_pick
2. /dw_tex_ai_build
3. choose variant with /dw_tex_next or /dw_tex_prev
4. /dw_tex_save
5. confirm console prints:
     DWTR AI B2 V2.1: physical PK3=...
   and filename begins zzz_dwtr_
6. quit game completely and start again
7. check the accepted texture is already active before running any DW texture command
8. optionally run /path and verify zzz_dwtr_*.pk3 appears in Current search path.

All B2 V2 features are preserved:
FAITHFUL / BALANCED / STRONG, next/prev, orientation fix, Real-ESRGAN x4plus,
local ncnn/Vulkan, network OFF, telemetry OFF.
