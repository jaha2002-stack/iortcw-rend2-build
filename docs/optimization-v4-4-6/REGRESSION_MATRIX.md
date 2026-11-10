# v4.4.6 Regression matrix — observed final run

Source: [run 38619534668](https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/38619534668), builder `9df5ac17dd687437b4c2de39ea2d39b59fa8c179` and evidence artifact `11928055679`.

| Scenario / invariant | Actual result | Limitation |
|---|---|---|
| Five-file SP/code delta | PASS: only `tr_main.c`, `tr_scene.c`, `ssgi_fp.glsl`, `volumetriclocal_fp.glsl`, `volumetricsun_fp.glsl`; no added/deleted source files | Actual three changed GLSL shaders are *not* byte-identical |
| C shadow-component cache vs baseline | PASS: 850,000 synthetic extracted-C label checks under UBSan; comparison counts 44,110,275 baseline vs 899,957 optimized | Comparison counts are algorithmic, not FPS |
| StaticPromote light emission | PASS: 10,000 extracted-C cases; same output, 9,411 ignored report formatting calls removed | Synthetic; no target gaming-GPU timing |
| Fire/Sun shader arithmetic | PASS: 20,000 fire samples + 3,000 sun rays; maximal float32 absolute errors 1.192e-7 fire, 1.550e-6 sun | Does not replace HDR GPU imagery |
| Windows x64 SP compile | PASS: rebuilt baseline, optimized engine and packaged candidate; EXE/cgame/qagame/UI A/B SHA equal, Rend2 renderer SHA differs as expected | Target Windows program execution NOT_RUN |
| Linux Mesa runtime high profile | PASS: escape1, swf, dam, crypt1, assault, forest on both variants | Only 640x480 software rasterizer smoke, not complete movements/events |
| Linux Mesa runtime lower profile | PASS: escape1 native Quality on both variants | Not a performance comparison; not all requested release profiles |
| Escape1 calibrated fixture 918 ring | PASS: 128 real captures per variant, 128 verified view/render camera indices and no direct/residency drops | Not proof of every table-shadow angle |
| Escape1 table exclusion experiment | PASS: three scenarios of 16 captures per variant (baseline/exclude742/exclude744), analyzer exit 0 | No complete video/motion-based visual sign-off |
| A/B captured PNG/TGA integrity | PASS: 176 matched PNG+TGA pairs, baseline/candidate matching 640x480 settings and hardware; actual engine frame files present | Debug text and unsynchronized effects; no pixel-exact acceptance claim |
| SWF lamp distance traversal | NOT_RUN as calibrated route; only targeted lamp-cluster static smoke passed | Requires mapped motion route |
| Dam spotlight lifetime / shutdown | NOT_RUN as sequence; spawn smoke PASS | Sequence required |
| Crypt1 torch flicker / fire shadows | NOT_RUN as sequence; spawn smoke PASS | Temporal fire test required |
| Assault close radar railing and sun-lit weapon | NOT_RUN as calibrated A/B; spawn smoke PASS | User-described close camera not captured |
| Forest moving outdoor sun CSM/PVS | NOT_RUN as route; spawn smoke PASS | Moving camera/shadow tests required |
| Muzzle/explosion/Tesla gameplay sequences | NOT_RUN | No captured event sequences |
| Win64 launcher, Cyrillic path and save/load | NOT_RUN on Windows | BAT/source static gate passed only |
| Real Windows gaming-GPU frametime p50/p95/p99, 1% low | NOT_RUN | No Windows gaming GPU measurements; no 75-FPS claim |

Analyzer status must not be marketed as full visual acceptance. The diagnostic screenshots are genuine Mesa game output and may have diagnostic overlays; they are not synthetic unit fixtures.
