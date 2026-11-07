DarkWolf Local AI Texture Restoration B2 V1 — Win64 TEST

BASE
Clean Production Run #42198541106 (2026-11-06).
The accepted renderer lineage is restored first. B1 infrastructure is reused only
for surface picking, A/B pointer switching and persistent PK3 writing.

B2 AI
Model: Real-ESRGAN realesrgan-x4plus
Runtime: portable ncnn/Vulkan Win64 backend
Scale: x4
Internet at game runtime: NO
Telemetry: NO
Python/CUDA required on test PC: NO
A Vulkan-capable Intel/AMD/NVIDIA GPU and current Vulkan driver are required.

TEST SCOPE
BSP world diffuse textures only.
Opaque textures only. Alpha/cutout textures are rejected by design in B2 V1.
Do not use this first test on grates, foliage, UI, sky, lightmaps or model skins.

COMMANDS
1. Aim at a normal opaque wall/stone/wood texture:
   /dw_tex_pick
2. Verify local backend:
   /dw_tex_ai_info
3. Generate the real neural B2 candidate:
   /dw_tex_ai_build
4. Toggle instantly in the running game:
   /dw_tex_ab
   A = ORIGINAL
   B2 = LOCAL AI 4X
5. If B2 is good:
   /dw_tex_save
   The game creates zz_dwtr_<hash>.pk3 for persistent use after restart.
6. Reject current preview:
   /dw_tex_discard

IMPORTANT
/dw_tex_ai_build is synchronous in B2 V1: the game may pause while the selected
texture is processed, then resumes with B2 visible. No map reload and no
vid_restart are required for A/B preview.

The old conservative /dw_tex_restore builder is intentionally NOT registered
in B2 V1. We are testing and developing the neural path directly.

THIRD PARTY
Real-ESRGAN: https://github.com/xinntao/Real-ESRGAN
Portable ncnn/Vulkan backend release:
https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0
Real-ESRGAN is distributed under its BSD-3-Clause license. The release package
also contains the licenses/notices shipped by its upstream project.
