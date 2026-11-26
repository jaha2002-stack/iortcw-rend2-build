# Static source and build audit

Scope: reconstructed SP source, builder reconstruction, selected hot paths across renderer/game/system. This is not a measured whole-engine CPU/GPU profile or exhaustive proof of memory/thread safety.

| Subsystem | Source / ownership / finding | Decision |
|---|---|---|
| Frontend | tr_scene.c RE_RenderScene owns scene submission; tr_main.c R_RenderView expands main/shadow views | Preserve view/PVS semantics |
| BSP/PVS | tr_world.c R_MarkLeaves/R_RecursiveWorldNode; CCDF world-surface registry suppresses proven duplicate coplanar faces | Preserve table fix and registry |
| Sort/batching | tr_main.c R_SortDrawSurfs uses four-byte radix sort, already linear passes; backend batches compatible surfaces | No speculative sort rewrite |
| Shadow groups | tr_main.c CanonicalId runs BFS repeatedly inside canonical index/score/capture/residency loops | Invocation-scoped component labels |
| StaticPromote | tr_scene.c Frame/AddCandidate formats up to 65 strings for disabled report writer | Remove dead reporting only |
| Point shadows | R_RenderDlightCubemaps owns history, selection, six-face capture, group assignment | Preserve budget 3 persistent + existing transient reserve 2 |
| Sun CSM | RE_RenderScene and ShouldUpdateCascade own visible vs volumetric cadence; v4.4.4 already reuses cascades | Preserve; GPU cost and temporal behavior unmeasured |
| FBO/MSAA | tr_fbo.c selective per-sample shading; tr_backend.c MSAA resolve precedes post processing | Preserve; redundant resolve cannot be removed without captures |
| SSGI/SSAO | tr_backend.c entity depth pass, quarter-buffer SSGI, composite; tr_glsl.c uniforms have value caches | Preserve masks and filtering; no unsupported bind rewrite |
| VolSun | volumetricsun_fp.glsl samples CSM/PCF and exponential extinction per step | Shader max 32 despite requested preset 48; inherited cap documented, no quality change |
| Local/fire volumetric | per-light raymarch plus reconstruction, fire catalog/residency and synthetic shadow hints | Preserve selection/weights/dual origins; larger changes need GPU evidence |
| AA | v4.4.3 full-resolution coverage reconstruction after MSAA | Restored missing patch in reconstruction; shader byte identity required |
| Materials/GLSL | material class fallback, source-generated GLSL, cached program/uniform state | PBR remains off, preserve material semantics |
| cgame/game | explosion/spotlight fixes from v4.4.5/6, fixed local-entity pool and time-driven effects | Byte-identical source between A/B; no gameplay optimization claimed |
| Memory | command buffer and radix scratch preallocated; image/FBO lifetime tied to renderer init/shutdown | No leak/race proof; no new allocation introduced |
| System/config | common.c Com_ExecuteCfg skips wolfconfig and autoexec under +safe; files.c accepts fs_homepath startup variable | Isolated home launcher; do not delete saves |
| Synchronization | qglFinish in explicit r_finish, screenshots/debug/swap paths; DWPERF absent | Do not indiscriminately remove driver synchronization |

Frame order: game/cgame → scene lights/StaticPromote → light and sun shadow view submission → main BSP/entity view/sort → queued backend draws/depth/entity mask → MSAA resolve → SSAO/SSGI → volumetric composition → tone map/final presentation. Ownership and ordering preserved; no new threads, GPU state or temporal shadow cache.

Existing profiling collector was reviewed: probe frames use qglFinish and must be excluded from ordinary FPS. No such captures were supplied for this task. CPU-, GPU-, driver- and bandwidth-bound hypotheses cannot be distinguished from source inspection alone.

Compiler audit: upstream Win64 Makefile already uses -O3 -ffast-math. These inherited flags are preserved for baseline parity, not introduced or advertised as an optimization. Harness tests use UBSan separately from production.

Additional source review:
- `tr_cmds.c:R_GetCommandBufferReserved`: padded fixed command arena, reserved swap tail, rejects oversized commands and drops commands on exhaustion. `R_IssueRenderCommands` executes the backend synchronously; the new grouping labels are frontend-only. No worker-thread access or per-frame heap allocation was added.
- `tr_backend.c:GL_BindToTMU`, `tr_fbo.c:FBO_Bind` and `tr_glsl.c:GLSL_SetUniformFloat/Mat4`: existing image/FBO/uniform caches already suppress redundant GL state updates. An extra generic cache would require profiling and complete state ownership analysis.
- `cg_localents.c:CG_AllocLocalEntity/CG_AddLocalEntities`: fixed pool, oldest-entity reclamation, backwards traversal preserves effects spawned during iteration. `cg_event.c:CG_CheckEvents` tracks event sequence to avoid repeated emissions. Changing scheduling risks trails/explosion timing; no measured reason to change it.
- `tr_image.c`: temporary image resample/compression buffers belong to load/upload operations; skin/model material registration and GLSL permutation compilation remain possible load hitch sources, not measured frame bottlenecks.
- `common.c:Com_Frame`: configured frame caps use NET_Sleep, with optional busy wait. Do not alter timing or savegame behavior as a speculative renderer fix.
- `common.c:Com_Init/Com_SetRecommended`: +safe alone does not prevent queued first-run hardware recommendation CFG. Startup `com_recommendedSet=1` is necessary for an authoritative custom preset; captured actual cvars are now validated.

Warning review: initial production baseline emitted 60 compiler warnings, including upstream networking macros, codec diagnostics and const qualifiers in historical renderer code. Removing the dead report initially exposed 31 unused declarations/helpers; those are removed without suppression. Existing upstream warnings are not claimed fixed, and UBSan coverage is limited to the changed algorithm harness.
