# DarkWolf Rend2 v4.4.6 Fire Leak Rootfix RC1

Source-anchored, additive candidate over the verified \`rend2-v4-4-6-clean-optimization\` reconstruction. The baseline v4.4.6 pipeline, patches, Windows toolchain, game modules, anti-telemetry source gate, and binary/provenance checks are preserved.

**What RC1 changes**

* \`ProjectDlightTexture\` and \`ForwardDlight\`: if a persistent physical/fire source lacks a valid cubemap in shadow mode, suppress only its unoccluded Direct DLight pass. Transient muzzle/Tesla/explosion effects are unchanged.
* \`volumetriclocal_fp.glsl\`: modes 3/6/7 fail closed without a usable shadow map.
* Isolated high-quality launch profile: shadow strength \`1.0\` (instead of \`0.88\`); volumetric fire mode \`3\` (shaped shadow-aware shader mode 6); still retain FireVol V07 native/synthetic shadow cache mode 2 and all other settings.
* The fire sprite, baked lightmap, StaticPromote allocation, persistent 3 + transient 2 cubemap budget, sun CSM, MSAA, SSGI, Tesla, explosion coverage, and render order are unchanged.

**Unresolved parity risk**

With only three persistent dynamic cubemap slots, a valid fire/light without a shadow map loses its extra direct-light contribution; this is preferable to illuminating an exterior wall, but it is not a perfect visual-parity solution. A true production release also needs a larger safe persistent shadow cache or map/receiver-level LOS. The candidate is **not** declared visually accepted and requires escape1 GPU screenshots and performance data.

**Repro / CI**

Push this branch to trigger \`DARKWOLF_REND2_V446_FIRE_LEAK_ROOTFIX_RC1.yml\`. The workflow first verifies the original source-delta contract, then applies RC1 with exact source anchors and SHA pinning, checks six modified source files, builds both unchanged baseline and changed renderer on Win64, validates original packaging, then repackages the rootfix candidate and publishes artifacts. Retail assets are not bundled.
