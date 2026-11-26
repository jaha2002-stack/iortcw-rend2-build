# Clean Production RC4: final bounded optimization round

Cumulative parent: published RC3 game ZIP SHA256
`fc45bbeb642cc07692ad10ee6758343712bcb155fca282557cbdb6c5d2932814`.
Parent source tree: `921a3d2a339d3a670c098a777c4c7896d987efe8`.
RC4 source tree: `74049eab929ec9271459634e143dda9fd7d700c1`.
Patch SHA256: `b29fe9ad1eeea913dfd14acd52991de3806705481b3217e28fba6152bb8d3174`.

Run `python3 integration/optimized-v4-4-6/rc4/bootstrap.py` to verify and unpack
11 pinned kit files. The complete audit, exact engine patch, file-hash lock,
actual-source tests, build/packaging scripts and runtime scenarios are in the kit.
The existing authoritative production YAML is the sole release entrypoint.
No merge to main or historical artifact replacement is implied.

Six groups over exact RC3:

1. Build local-volumetric connected-component labels once per view/invocation,
   retaining the same companion predicate, canonical fixture IDs and draw order.
   This is not the earlier shadow-group optimization and is not a temporal cache.
2. Skip synchronous depth readback for coronas already marked invisible by cgame,
   preserving the same fade updates and same-frame occlusion for visible coronas.
3. Bound texture resampling dimensions and offset arithmetic; replace the 2048-wide
   temporary-array limit with a balanced temporary allocation when needed.
4. Correct the 1xN/Nx1 normal/height mip tail, including swizzle and cancelling
   vectors. Preserve the ordinary 2D filtering kernel and height maximum.
5. Validate FBO attachment indices and release owned renderbuffer slots safely on
   shutdown, clearing actual/cache bindings and registry ownership.
6. Validate DDS 2D/cubemap mip payload lengths and supported layouts before upload.
   Preserve the bytes of accepted compressed and uncompressed images.

Five source files change. All 35 GLSL files, production quality/BAT/owned assets,
light counts and shadow limits remain unchanged. No retail assets, TestLab or
sanitizer code enter the game package. The separate remaining user-reported
issue is not imported into this round.

Local actual-source tests passed six groups in ASan/UBSan and separately with
inherited production flags; eleven parent negative probes reproduce errors or
invalid acceptance and pass on RC4. A fresh 217-unit static sweep is advisory,
not proof of universal correctness. CI repeats source/test/build checks and,
when protected assets are available, fresh paired six-map captures, screenshot
queue and vid_restart scenarios. SWF uses the previously verified dock view;
this does not claim to fix the old position-dependent white band.

A successful build may produce CANDIDATE_FOR_LOCAL_VERIFICATION, not measured
Windows gaming-GPU FPS or full temporal visual acceptance. Final run IDs,
artifact hashes and actual gate results must be read after CI completion.
