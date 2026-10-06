# DarkWolf ioRTCW Rend2 Android TestLab v0.1

## Provenance

- Requested base run: `37266797451`
- Base head SHA: `e410db87b5704fb1518740f1cfc760e9ea67d34f`
- Upstream ioRTCW SHA: `438e7d413b5f7277187c35b032eb0ef9093ae778`
- Base artifact: `DarkWolf-ioRTCW-Rend2-v4.4.6-Explosion-Coverage-Candidate-Win64`
- Base artifact id: `11326603946`
- SDL2 branch snapshot SHA: `4c2d9014afda49553c76f7045529207bb593f9b5`
- Target ABI: `arm64-v8a`
- Initial Android API: 29 (Android 10)
- Renderer target: Rend2 on OpenGL ES 3.x; no PBR rewrite and no visual reset of the DarkWolf v4.4.6 work.

## Goal

Produce a native Android single-player build of the exact DarkWolf ioRTCW Rend2 state represented by run 37266797451. The Android port must retain the v4.4.6 gameplay changes, the current Rend2 renderer behavior, force-sun work, volumetrics, dlight/shadow behavior, and the previously accumulated production patches unless a platform limitation is proven by TestLab.

Retail RTCW data is never committed or redistributed. The APK/native package must load legally owned RTCW data supplied by the user.

## Architecture

The first production-oriented route is:

1. SDL2 Android supplies Activity/lifecycle, window, touch/gamepad input, filesystem glue and audio.
2. ioRTCW SP engine is built for AArch64 as Android native code.
3. Rend2 is linked into the Android engine rather than loaded as a Windows-style renderer DLL.
4. OpenGL ES 3.x is the native GPU backend. Desktop-GL-only calls are isolated behind a small compatibility layer.
5. DarkWolf game code remains provenance-linked to v4.4.6.
6. Native game modules are built for AArch64 first; QVM fallback remains available as a portability escape hatch.
7. The final APK contains engine/runtime code only plus redistributable DarkWolf files; original retail PK3s stay external/user-supplied.

## Milestones and gates

### A0 - Exact-source reconstruction
Rebuild the exact source represented by run 37266797451 by cloning the pinned ioRTCW SHA and applying the four cumulative DarkWolf patches found inside that run's artifact. Gate: all provenance markers and reverse-apply checks pass.

### A1 - ARM64 NDK compile gate
Cross-compile the engine-facing and Rend2-critical source files with the Android NDK. Gate: no host-only Win32/Linux ABI leakage in selected critical files.

### A2 - Rend2 GLES3 bring-up
Create an ES 3.x context, load the shader/VBO/FBO/VAO path, add desktop-call shims only where required, and emit GLSL ES-compatible shader headers. Gate: the complete Rend2 object set compiles for arm64-v8a.

### A3 - Native engine link
Link the SP client + Rend2 into an Android shared entry module and build cgame/qagame/ui (or validated QVM fallback). Gate: all native ELF objects link without undefined engine/platform symbols.

### A4 - APK bootstrap
Build an installable debug APK using SDLActivity. Gate: APK installs and reaches ioRTCW initialization on an Android emulator/device without a native crash.

### A5 - Retail-data bootstrap
Add explicit user-data discovery/import path for `Main/` and DarkWolf redistributable files. Gate: menus render and a legal local RTCW data set is detected.

### A6 - First playable Rend2 frame
Load a retail map, render a stable frame with Rend2, receive touch/gamepad/keyboard input and audio. Gate: gameplay screenshot + log prove real Rend2, not OpenGL1 fallback.

### A7 - DarkWolf parity
Validate escape1/crypt1/open-map samples against the v4.4.6 Windows reference: dynamic lights, shadow slots, sun, volumetrics, explosions, materials, UI, saves. Unsupported effects are degraded explicitly, never silently replaced.

### A8 - Mobile optimization
GPU/CPU profiling, render scale, shadow quality tiers, memory pressure handling, lifecycle/suspend/resume, thermals and battery. Gate: stable 30/60 FPS profiles on representative Android GPUs.

## Non-negotiable rules

- Never modify the existing production branch while Android work is experimental.
- Never silently drop Rend2 and call an OpenGL1 build an Android Rend2 success.
- Every promoted Android artifact records base run, base SHA, upstream SHA, ABI, API level and renderer backend.
- Compilation success is not a visual pass.
- A final promotion requires a real-device screenshot/log proof and a matching artifact from the same source SHA.
