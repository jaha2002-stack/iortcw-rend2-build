# Bottleneck ranking / optimization backlog

| Priority | Finding | Evidence | Cost | Risk / disposition |
|---|---|---|---|---|
| P0 correctness | Reconstruction drops AA and UI patches | Historical workflows vs telemetry chain and shipped patch files | Not an FPS metric | Correct chain before rebuilding |
| P1 CPU | Repeated connected-component BFS in shadow grouping | Actual C differential harness: 44,110,275 → 899,957 companion comparisons across synthetic invocations | 97.96% fewer comparisons in harness; game milliseconds unknown | Implement with per-invocation lifetime |
| P1 CPU | Discarded report formatting/scans | ReportIfChanged unconditionally returns; Frame constructs header + 2 lines per selected lamp | Up to 65 format calls/frame at 32 lights, plus map override scans; game milliseconds unknown | Remove producers; retain light calls |
| P2 GPU hypothesis | Sun/point six-face shadow views, volumetric PCF/raymarch | Source pass/sample structure | UNMEASURED | Deferred; no cadence/sample reduction |
| P2 GPU hypothesis | Repeated per-light fullscreen local/fire reconstruction | Source loop and FBO calls | UNMEASURED | Deferred scissor/bounds until edge/depth A/B |
| P3 driver hypothesis | SSGI filter resets and FBO binds | Source state transitions; some state caches already exist | UNMEASURED | Deferred; avoid leaking sampling state |
| P3 load hypothesis | Shader compilation/permutation startup | GLSL builder structure | UNMEASURED | No prewarm/cache change without actual hitch trace |

No whole-frame speedup estimate is made. More expensive GPU changes are postponed until comparable Windows captures exist.
