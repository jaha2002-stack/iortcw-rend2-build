# DarkWolf Hybrid Relight V2 — native Rend2 acceptance gates (2026-10-30)

## Immutable foundation

GitHub Actions **#41019985033**, commit `c653433e1b0a29b2f43f29a240b96a8192acb617`; accepted renderer SHA-256 `d7423e8648e2de556f79c7cddecf1a8df16b9f60a46c503d1440089876116b45`.

The new branch reconstructs the accepted September/October shader and renderer chain and modifies only `SP/code/rend2/tr_bsp.c`. No sun, shadow, GLSL, SSGI, bloom or game logic changes.

## Native behavior

- Native cvars: `r_dwHybridRelight` (default `0`) and `r_dwHybridRelightStrength` (default `1.0`; clamped `0..1`).
- On loading an IBSP v47 map, the renderer captures a **64-bit FNV-1a fingerprint** of the original BSP *before in-place header byte-order adjustment*.
- Only with `r_hdr=1`, a matching private `dwrl_v2.manifest`, non-deluxe map, and **all expected** `dwrl_XXXX.hdr` atlases present, does the loader select the overlay.
- Each 128×128 image is checked for the known Radiance-style *header + little-endian float32 RGB triples*. All values must be finite, not brighter than the original RGB8 value and not below **82%** of it. A single missing, corrupt or inconsistent input disables the overlay for the **whole map**, rather than allowing patchy mixed atlases.
- Overlay intensity is interpolated from original RGB8 to validated corrected RGB and uploaded through the already accepted GL_RGBA16 lightmap pathway. Runtime cvars are sampled at **map load**, not continuously.
- No new BAT installer is needed: optional derivative map PK3 assets remain in Main while the cvar selects stock/overlay. **Old** `zz_dw_hybrid_v2_*.pk3` assets must be removed; their `lm_XXXX.hdr` files bypass the new switch.
- No original `.bsp`, `.map`, or commercial PK3 may be uploaded into public GitHub artifacts.

## Private user-owned per-map data

The four verified derivative packs use distinct filenames `zz_dw_hybrid_native_v2_{norway,escape1,factory,assault}.pk3`, and exact map fingerprints:

| Map | BSP FNV64 | Native RGB atlases |
| --- | --- | ---: |
| norway | `cd89aad6ecf8826c` | 92 |
| escape1 | `2988a3066fa71294` | 42 |
| factory | `fb4164d87f634e95` | 20 |
| assault | `d7823e6f2f1472ed` | 69 |

Native C validation for all four original IBSP maps passes full valid input, wrong manifest, and missing-atlas negative tests. These are **offline** evidence; no screenshot or GPU field acceptance is claimed.

## The physical limitation that remains

Retail RTCW RGB lightmaps contain combined historical illumination. The new Stage 2 tagged CPU baker can separate direct/indirect light in *its own new solution*; this does not recover the exact historic lightmap. Therefore the current native importer uses **bounded, source-guided local correction**, one chosen BSP surface per map. It is not a 32-map relighting overhaul or a guaranteed one-to-one mapping to a dynamically lit StaticPromote fixture.

Future production acceptance additionally requires:
- Stable runtime fixture-id matching and do-not-remove-if-no-dynamic-replacement behavior
- Multi-surface/multi-source per-map tagged profiles with shared-atlas ownership checks
- Visual A/B on Escape1, Norway, Factory and Assault, with sun and Local shadow tests
- Water cubemap no-regression proof, fire/Tesla containment, ≥ maintained accepted FPS
- Optional clean-albedo restoration on materials proven to have directional lighting painted into the texture

**Never advertise the native library as user-GPU-approved until field A/B testing passes.**
