# Clean Production RC2 Complete

This package preserves every change in released RC2 (ZIP SHA256
125c456bbfe5490a05c3d85c0d30aebab19f2a57f69d4d55e2a40200f570a9b5)
and integrates the pending R2 source-kit work. It does not replace RC2 with the
alternative RC1-based source-kit. The requested ten R2 items include one overlap:
R2-01 stable adaptive radix sorting already exists as RC2-01. That implementation
is retained unchanged, not counted twice. Nine further items are integrated.

| Requested item | Actual complete package |
|---|---|
| R2-01 radix sorting | Existing RC2 sorter preserved; no duplicate new claim |
| R2-02 CCDF grouping | Hash exact plane/fog/cubemap/culling compatibility; retain all exact geometry tests |
| R2-03 fire shader classification | Reuse last shader classification within one call; no interframe cache |
| R2-04 local/fire uniforms | Set final DlightInfo once before the first draw |
| R2-05 SSGI receiver reuse | Share center depth/mask and postpone unused edge-stability work |
| R2-06 empty SSGI entity mask | Skip work only at the original exact zero-factor cutoff |
| R2-07 visible solar shadowmask | Compute additional cascade projections only when selected or blended |
| R2-08 fire setup | Hoist ray-invariant shape/tint setup without removing spatial noise |
| R2-09 local/fire extinction | Two initial exponentials plus per-step recurrence, including rejected samples |
| R2-10 volumetric coverage AA | Skip unused directional taps only for exactly zero blend |

The released RC2 early fire lateral guard, SSGI saturated-mask exits, viewport /
scissor and matrix caches, BSP, filesystem fix, particles, trails and far-plane
cache remain. During integration, the SSGI center-mask conflict was resolved by
using the shared center while retaining the existing saturation test. Only six
renderer files differ from the released RC2 source tree. Game/cgame/UI/system
source and production settings remain byte-identical to released RC2.

## Verification

Full RC1 source was obtained from artifact 11940791672, SHA256
5eb349b9a874cf20cf374092f4c834fcb67a381afdb687b1e617add450002f01.
Its Git tree ec4caf9f5543c535e1b019894dab52565e691b4c was checked. Released RC2
was reconstructed and its tree a5434fd5d8d139b6622f90c48b46639988828fc0 verified.
The production pipeline independently reconstructs from pinned upstream and
versioned patches; this historical artifact is not a build dependency.

Actual functions, helper functions and GLSL are extracted from both full trees
for each new test run, not taken from stale source snippets. The CCDF fixture now
uses the real 1024-bucket constant (the earlier source-kit fixture used 4096).
Local C tests: 1200 sorting sets; 128 worlds/32768 surfaces; 256 fire-classification
scenes; 3000 uniform cases, under UBSan and inherited -O3/-ffast-math separately.
Observed CCDF pair visits on synthetic inputs: 941830 to 29173. These are not FPS.
Software GLSL: 28 program links, 1188 synthetic FBO comparisons, GLSL120/150.
Observed local maximum error: zero for SSGI/shadowmask/coverage, 9.8348e-7 for
local/fire volumetric. Recurrence is numerically close, not bitwise exact.

Sampler review: affected render targets are non-mipmapped, depth uses nearest,
color uses linear, anisotropy is 1 for non-mipmapped images. Required derivatives
remain before divergent returns. Native and GLSL harness inputs are synthetic;
no harness image is gameplay evidence.

Baseline RC2 and Complete Win64 SP are both rebuilt using the same pinned toolchain
and explicit identical PRODUCT_VERSION. Normalizing this build identity avoids
unrelated EXE differences caused only by different reconstruction Git commits.
The final manifest identifies actual source trees and builder SHA separately.
Unchanged EXE/cgame/qagame/UI must compare byte-identical; renderer must differ.
Historical RC2 binary identity is not claimed for this newly versioned build.

Retail smoke: seven scenarios per variant (six maps High, escape1 Quality), actual
engine PNG/TGA validation. This is not a full motion, weapons/Tesla/explosion,
spotlight-lifetime or Windows GPU test. Previous lamp-ring screenshots are not
reused. Missing assets yield NOT_RUN rather than fabricated PASS.

## Install / status

Install into a separate legal RTCW SP copy, preserving its retail Main/pak*.pk3.
Use RUN_DARKWOLF_OPTIMIZED_CLEAN.bat; the original profile is untouched and an
isolated DWOptimizedHome is used. Retail files, telemetry and test code are not
included. The high-quality preset and BAT are identical to RC1/released RC2.
forceSun=1, dlightMode=2, StaticPromote=32, persistent shadow slots=3, SSGI and
local/sun/fire volumetric remain. SSAO=0 and indirectLighting=0 are inherited
exceptions: this is not described as an all-effects-on preset.

Clean Production describes package hygiene, NOT final hardware acceptance.
CANDIDATE_FOR_LOCAL_VERIFICATION: Windows gameplay, real gaming-GPU FPS, HDR and
full temporal visual acceptance remain for the user's actual-PC test. No 75-FPS
claim. Consult BUILD_PROVENANCE.json for this specific run's actual test statuses.
One workflow and the existing isolated branch are used; no merge to main.
