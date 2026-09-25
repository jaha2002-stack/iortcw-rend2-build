# DarkWolfRTCW Renderer TestLab v0.1

Renderer TestLab is an isolated regression harness for the current DarkWolf ioRTCW Rend2 SP production postimage.

## Safety model

- The exact production source is reconstructed from pinned GitHub Actions provenance.
- Production source contracts are checked before any TestLab change.
- TestLab instrumentation is applied only to a separate CI source tree.
- The instrumentation allowlist is exactly:
  - `SP/code/game/g_cmds.c`
  - `SP/code/rend2/tr_init.c`
  - `SP/code/rend2/tr_main.c`
- No TestLab instrumentation is shipped as a production fix.
- Missing runtime evidence is reported as a gate, never as PASS.

## v0.1 runtime capabilities

When protected RTCW retail game data is available, the Linux CI runner builds native ioRTCW SP + Rend2 and runs it under Xvfb + Mesa software OpenGL. The harness loads `escape1`, enables TestLab-only root-cause telemetry, resolves historical fixtures 918/runtime 628 and 782/runtime 609, reads fixture origins from real renderer state, generates deterministic camera rings, places the camera with `dw_testView x y z pitch yaw roll`, captures lossless screenshots, and verifies direct-light/residency/shadow-slot evidence.

The regression registry also tracks the table double-shadow, Tesla-room lighting, dynamic grate shadow, and SWF three-lamp distance stability tests. Those visual cases remain explicitly uncalibrated until their first real retail-data runtime is captured.

## Retail asset gate

The public repository intentionally contains no RTCW retail `pak*.pk3` files. Full map-specific runtime needs one protected source configured once:

- GitHub Actions secret `DARKWOLF_RTCW_ASSETS_URL`: a private/expiring URL to a ZIP containing the user's legitimate RTCW game data.
- Optional secret `DARKWOLF_RTCW_ASSETS_SHA256`: SHA-256 of that ZIP.

Without the secret, TestLab still reconstructs the exact production source, validates the 32-light / 3-shadow contract, applies isolated instrumentation, and compiles a native Rend2 TestLab binary. The evidence artifact records runtime status as `BLOCKED_MISSING_RETAIL_ASSETS`; it does not claim gameplay tests passed.

## Current production contract

- `r_staticPromoteMaxLights = 32`
- `r_dlightShadowMaxLights = 3`
- `r_volumetricLocal = 1`
- PBR remains disabled in the current production profile.

The baseline is pinned in `testlab/baseline/current.json`.
