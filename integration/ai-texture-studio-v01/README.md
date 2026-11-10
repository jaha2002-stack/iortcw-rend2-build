# DarkWolf AI Texture Studio — Experimental V0.1 (NOT a release)

Parent: successful GitHub Actions **#41408153237**, SHA `6fd61c7bd4e6a1c23c549c93d237f2204c9d3d89`.

## What this branch contains
- Fail-closed, OFF-by-default renderer source experiment.
- BSP triangle ray pick using last renderer camera and UV barycentrics.
- Reports shader, source diffuse name and dimensions.
- Manual live preview of a PNG already installed at `Main/dwtex/name.png`.
- Original GL texture handle retained for runtime rollback.
- Request job emitted as `dwtex/request.json`; possible local AI worker integration point.
- Experimental polling for `dwtex/ready.txt` with `<request_id> dwtex/name.png`.
- Shared image overrides affect every surface referencing that same `image_t`.

## Commands planned (only after source integration, build and game verification)
```
set r_dwTexStudio 1
dw_tex_pick
dw_tex_status
dw_tex_generate original 2
dw_tex_generate art 4
dw_tex_preview dwtex/example.png
dw_tex_revert
dw_tex_revert_all
```

This branch does NOT include an image-generation service or a texture original exporter.
It does NOT produce new textures on its own. It is NOT a runnable AI editor.
No reliable screen UI, occlusion-aware ray selection, transparent surface handling,
AI output correctness proof or GPU/game acceptance has been established.

## Correct future architecture
1. Safe scene ray pick / visibility gate, resolving the full shader stage stack.
2. Source extraction from pk3 archive with stable asset identity, source image and alpha.
3. Local AI sidecar with original-preserving SR + art variants; tileable mode and masks.
4. Quality gate for ratio, alpha, seams, normal maps, mipmaps, aliasing, color and material fidelity.
5. GPU staging + single-frame swap with reversibility, memory budget and no resource leaks.
6. In-game menu with thumbnails, variant selection, compare and save as opt-in override pk3.

## Engineering caveats
- Code is a **prototype requiring compilation and review**, not a delivered binary.
- The original `R_CreateImageExt2` image registry has a finite size; V0.1 limits
  preview attempts per renderer lifetime, but does not implement full registry recycling.
- Future GPU preview must preserve alpha-test semantics and shader/texture coupling.
- FPS and graphics parity across existing Clean Production maps have NOT been tested.
- Never merge into Clean Production until QA succeeds; keep any executable build isolated.
