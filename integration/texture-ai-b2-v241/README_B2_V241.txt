DarkWolf Local AI Texture Restoration B2 V2.4.1 — Door Picker Fix

BASE
  Successful B2 V2.4 Run #42930103256
  commit d6f24744f895e9c602b1b6606c6826f3c92595b9

FIX 1 — INLINE BSP DOORS
B2 V2.2 and V2.4 incorrectly rejected MOD_BRUSH surfaces whose surface index
was >= tr.world->numWorldSurfaces. Inline BSP models (func_door, rotating
doors, lifts, etc.) use the shared tr.world->surfaces array and commonly begin
after the world-only range.

V2.4.1 changes the upper bound to:
  tr.world->numsurfaces

FIX 2 — BJ HEAD / VIEWMODEL INTERCEPTION
Environment picking now ignores:
  RF_THIRD_PERSON
  RF_FIRST_PERSON
  RF_DEPTHHACK
and model prefixes:
  models/players/
  models/weapons2/
  models/weapons/

This prevents invisible BJ body/head and first-person weapon geometry from
winning the nearest ray hit over the intended door/wall texture.

UNCHANGED
- B2 V2.3 AI generation
- Real-ESRGAN x4plus
- FAITHFUL / BALANCED / STRONG
- A/B and next/prev
- cumulative zzzzzz_DW_TextureRestoration.pk3
- .pending startup promotion
- PBR/Owner/lighting/shadow renderer functionality
- sky and water remain unsupported
