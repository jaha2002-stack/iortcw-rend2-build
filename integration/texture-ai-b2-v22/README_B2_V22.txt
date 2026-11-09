DarkWolf Local AI Texture Restoration B2 V2.2 — Win64 TEST

This release preserves all working B2 V2 features and fixes two user-reported workflow problems.

1. ONE PERSISTENT PK3 PER TEXTURE
The saved filename is deterministic from the normalized texture qpath:
  zzzzzz_dwtr_<texture-hash>.pk3

Saving the same texture again always targets the same filename and atomically replaces it.
After a successful save, V2.2 removes only legacy DarkWolf names with the same hash and
2..10 leading z characters. It does NOT remove packs belonging to other textures.

Result:
- same texture saved 1, 2, or 20 times -> one current persistent PK3
- different texture qpaths -> different PK3 files, by design

2. DOOR / BRUSH MODEL PICKING
The old /dw_tex_pick only ray-tested tr.world->surfaces.
RTCW func_door and many moving doors/lifts are inline BSP brush models rendered as
RT_MODEL / MOD_BRUSH entities. Aimed at a door, the old picker could select the wall behind it.

V2.2 tests both:
- static WORLD BSP surfaces
- visible MOD_BRUSH entity surfaces

The nearest real hit wins. Console now clearly prints:
  PICK source=WORLD ...
or
  PICK source=BRUSH entity=N model=*M ...

TEST ESCAPE1 DOOR
Aim at the door and run:
  /dw_tex_pick

Do not continue unless console says source=BRUSH and the texture name corresponds to the door.
Then:
  /dw_tex_ai_build
  /dw_tex_ab
  /dw_tex_next
  /dw_tex_prev

If the selected door texture is opaque, all B2 variants should apply normally.
Alpha/cutout textures remain intentionally refused in this test line.

PERSISTENCE TEST
Save the same chosen texture twice with different variants:
  /dw_tex_save
Then check the directory printed as physical PK3.
Only one zzzzzz_dwtr_<samehash>.pk3 should remain for that texture.

All prior B2 features remain:
Real-ESRGAN x4plus local ncnn/Vulkan, orientation fix,
FAITHFUL / BALANCED / STRONG, next/prev, A/B, offline runtime.
