DarkWolf Original Texture Restoration V1

Base: GitHub Run #42198541106 (2026-11-06 Clean Production)

Goal
- Preserve the original RTCW artwork.
- Restore only the selected original diffuse texture.
- Produce a true 4x texture in memory.
- Switch A/B instantly while the game remains running.
- Persist an accepted B variant automatically as a PK3.

Commands
1. Aim at a world texture and run: /dw_tex_pick
2. Build and show restored B: /dw_tex_restore
3. Toggle original/restored instantly: /dw_tex_ab
4. Inspect state: /dw_tex_info
5. Accept B and create persistent PK3: /dw_tex_save
6. Discard the preview and return to A: /dw_tex_discard
7. /dw_tex_artistic is intentionally disabled in V1.

Persistence
/dw_tex_save writes zz_dwtr_<texture-path-hash>.pk3 through the engine filesystem.
The PK3 contains the replacement at the same logical texture path, so it is loaded
as a normal high-priority asset after restart. A text manifest is written under
texture_restoration/.

Restoration engine
This V1 core is fully local/offline. It reuses Rend2 FCBI edge-directed upscale in
YCoCg and applies a deliberately bounded high-frequency recovery (maximum +/-10 per
RGB channel). It is NOT a generative model and therefore cannot invent bricks,
cracks, symbols or colors.

AI
No network is used. The optional ARTISTIC/AI backend is not enabled in V1. A later
backend can be either a bundled local model or an explicitly configured Internet
service without changing the safe offline default.
