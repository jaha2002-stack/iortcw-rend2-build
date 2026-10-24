# DarkWolf Rend2 v4.4.6 RC4 — FourWeek Master SourceDefaultsON
## Permanent engineering handoff / build lineage (2026-10-24)

**Status:** Verified Windows x64 binary compile and ZIP integrity. Real Windows GPU FPS and visual acceptance remain pending. Never describe a passing CI build as proof of game-runtime behaviour.

**Privacy:** GitHub Release ID `422588491` was explicitly converted to an **unpublished Draft** at the owner's request. DO NOT publish, mark latest, or make it publicly visible. The repository and Actions runs themselves may still be public. Draft Release assets serve as durable private-to-repository-maintainers backup.

### Future AI entrypoint
- Canonical Git commit/tag (permanent): `2ef7ad6bd9dbe8e03b561b4be6279953e51ceee1`, tag `v4.4.6-rc4-fourweek-master-sourcedefaultson-20261024`.
- Full Windows x64 SP ZIP SHA256: `559d01d3815ef1d58b3f018d1c1f215cb37881d2756ad3508ae5cc891179b2e4` (5,672,784 bytes, 42 files).
- Renderer DLL SHA256: `4112890117f5fb16371ba8387ecd89203257eff361c22d83784db65c67eadd0a`.
- Full package run: https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40074980554 ; artifact `12553165220`, expires 2027-01-22.
- Renderer build run: https://github.com/jaha2002-stack/iortcw-rend2-build/actions/runs/40073883865 ; artifact `12552083888`, expires 2027-01-22.
- RC4 Bloom v2 base: run `38798189322`, artifact `12004010089`, SHA256 outer `6c6c2d2302e2f4f45bad9d7e3df7e2573fd79a72646bcf049596440cb62f7659`, expires **2027-01-13**.
- This base is the final cumulative four-week **Win64 SP** branch, NOT an Android build.

### Historical chain and source ownership
1. v4.4.6 original reconstructed engine and accumulated shaders, dynamic lighting, ignition, sun shadows and settings: `integration/optimized-v4-4-6/`. Historical decisions: `docs/optimization-v4-4-6/SOURCE_PROVENANCE.md`, `OPTIMIZATION_DECISIONS.md`, `REGRESSION_MATRIX.md`, and `FINAL_RELEASE_REPORT_RU.md`. Prefer the versioned source patch kits instead of historical Action downloads wherever possible.
2. RC4 optimization six bounded groups: `integration/optimized-v4-4-6/rc4/bootstrap.py`, `README.md` and six pinned `kit.part*.b64` blobs (checksums verified in bootstrap). Do not remove or blindly reapply.
3. Accepted Fire/Tesla wall occlusion: `integration/rc4-light-containment/bootstrap.py` and four pinned `kit.tar.xz.part0*` blobs. Approved patch SHA256 in final ZIP `docs/containment.patch`: `e3600847ed0d1def868439af0c94f5ce250e2e7afbb0584fbb151459ea009a2f`. Confirm `R_RenderDlightWorldOcclusion`, `DlightWorldVisibility`, and `DARKWOLF_REF_WORLD_OCCLUSION`. Do NOT overlay obsolete standalone Fire Direct V2.2 on top of this fix.
4. Quality and final Bloom v2 source tree: workflow `.github/workflows/RC4_BLOOM_V2_PRODUCTION_PORT.yml`, versioned `.github/bloom-port/part01.b64` through `part07.b64`; expected Bloom source tree `bb1432b459a4daf72a324f3fb477744bdb51fd4a`; its original build used run 38765428993, artifact 11989425549, and historical Bloom patchers. Original Bloom v1->v1.1->v2 HDR pyramid->production built-in must be retained.
5. `integration/rc4-final-csm/apply_csm_guard.py`: forceSun CSM reprime, retains staggered 1/2/4 optimization.
6. `integration/texture-material-fidelity/apply_fidelity.py`: Texture Fidelity, adaptive upsample, cutout mip, Material Fidelity.
7. `integration/cas-a2c-lut/feature.patch` SHA256 `6d143993ecd24537aa1b66e6649b43ba5281c3d5f21cee527192ef20c1336dec`, and `DARKWOLF_3FX_VISIBLE_V03.patch` SHA256 `b9f83421ebc55e5bc1d9ab3fc023eece71cc6e0a3203ab4e6eafd3d8ae83059a`. Their source gates protect existing A2C, lighting and CSM files.
8. `integration/cas-a2c-lut/ci_master_clean_4week.sh`: exact accepted source chain plus ONLY 10 default CVar changes in `tr_init.c`. Windows x64 DLL compiled in run 40073883865, SOURCEDEFAULTSON. The script currently downloads artifact 12004010089 — **not self-contained after expiration**. Use Draft Release **exact source snapshot** for future clean builds, once verified.
9. `integration/fourweek-master-release/package.py`: deterministic full Win64 packaging. It checks precise hashes for EXE, gameplay DLLs, original LightContainment, every patch and final renderer, then emits 42-file ZIP. Its old artifact download dependencies also expire, so future workflows must use archived snapshot and archived full ZIP.
10. Packaging run 40074980554 verified PE64, full ZIP and hashes. The originally published Release was made Draft in run 40075492227 at owner's request.
11. Source preservation workflow `.github/workflows/RC4_FOUR_WEEK_SOURCE_ESCROW_DRAFT.yml`, run 40076028945, should put final exact source `.tar.gz`, `.sha256`, `SOURCE_SNAPSHOT_PROVENANCE.json` into the **unpublished** Draft Release. Verify that workflow concludes SUCCESS and check asset digests before relying on it.

### Required instructions for later experiments
- Do not treat expiring Actions artifact URLs as canonical; use this Git handoff, immovable tag, source snapshot and SHA-256 files.
- Confirm available source snapshot reproduces the expected source tree and final renderer before making new patches.
- Never silently regress accepted RC4 LightContainment, Tesla, Bloom v2, CSM Guard, texture/material quality, CAS/A2C/LUT V03, shadows or frametime optimizations.
- Preserve the historical approved `r_dlightMode=2`, `r_forceSun=1`, Bloom v2 and all enabled effects. Do not enable historically excluded SSAO/indirect lighting without separate A/B acceptance.
- Make experimental branches from the pinned commit/tag, with new named workflows. Do not mutate the baseline commit/tag, compiled DLL, source kit or Draft Release ZIP.
- CI proves source/packaging integrity only. Required local acceptance: Escape1 exterior stove-wall light leak, Tesla boundaries, Factory lamps/SSGI, Assault volumetric weapon aliasing and MP40, Bloom and texture quality; check FPS/frametime and game startup with clean homepath.
- Original licensed RTCW `Main/pak*.pk3` is never bundled.

### SHA identification
Full inner Win64 ZIP `559d01d3815ef1d58b3f018d1c1f215cb37881d2756ad3508ae5cc891179b2e4` is **not** the GitHub Actions outer artifact ZIP SHA `6fae17e9acf4eb3c82b2c6b1d5a7e385787382234d5fb6f5d5df2b22502ae655`. The archived exact source is a third distinct asset with its own SHA.
