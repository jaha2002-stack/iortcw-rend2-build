DarkWolf Local AI Texture Restoration B2 V2.3 — Win64 TEST

NEW PERSISTENCE MODEL: ONE CUMULATIVE PK3

The tool no longer creates one PK3 for every accepted texture.

FIRST ACCEPTED TEXTURE
  /dw_tex_save
creates:
  zzzzzz_DW_TextureRestoration.pk3

SECOND / THIRD / 100TH TEXTURE
They are added to that same cumulative archive. No new per-texture PK3 is created.

RE-SAVING THE SAME TEXTURE
The exact texture qpath is the key.
Saving the same texture again replaces its existing entry and per-texture manifest inside
the cumulative archive. It does not create a duplicate entry or another PK3.

WHY A .pending FILE MAY APPEAR DURING A RUN
ioRTCW keeps every loaded PK3 open as an unzFile handle until filesystem shutdown/restart.
Therefore replacing an already-mounted cumulative PK3 in place is unsafe on Windows.

V2.3 behavior:
- if no cumulative PK3 exists yet: first save creates it directly;
- if it is already present/mounted: save rebuilds ONE
  zzzzzz_DW_TextureRestoration.pk3.pending
  archive;
- additional saves in the same session update that same pending file;
- on next game startup, qcommon promotes .pending to the real cumulative PK3 BEFORE
  scanning/loading PK3 files;
- a backup/restore path protects the previous pack if promotion fails.

After startup there is one active cumulative .pk3, not one PK3 per texture.

LEGACY MIGRATION
Existing B2 V2/V2.1/V2.2 files named with 2..10 leading z characters and
_dwtr_<hash>.pk3 are merged into the cumulative archive during save.
They are removed only after a cumulative archive has been created successfully.
At startup qcommon also removes already-migrated legacy packs before loading search paths.

ALL PREVIOUS WORKING FEATURES REMAIN
- local Real-ESRGAN x4plus, ncnn/Vulkan, no Internet at runtime
- FAITHFUL / BALANCED / STRONG
- /dw_tex_next /dw_tex_prev
- in-game A/B
- orientation fix
- WORLD + MOD_BRUSH picker for doors/lifts from B2 V2.2

TEST
1. Start with no zzzzzz_DW_TextureRestoration.pk3.
2. Pick texture A, build, choose variant, /dw_tex_save.
   Verify one cumulative PK3 exists.
3. Pick texture B, build, choose variant, /dw_tex_save.
   The tool must not create a second PK3. Depending on whether the cumulative pack
   was already mounted, one .pending staging file may exist until restart.
4. Save texture A again using a different variant.
   It must replace texture A inside the same cumulative pack/pending archive.
5. Restart game.
   qcommon promotes pending before PK3 scanning.
6. Verify texture A and texture B are both restored automatically.
7. Verify old per-texture *_dwtr_<hash>.pk3 files are gone after successful migration.
