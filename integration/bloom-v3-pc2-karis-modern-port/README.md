# Bloom V3 PC2 + Karis modern forward port

Target: renderer source lineage that produces the accepted renderer used by Run #43189244002.
Historical reference: Run #32847437364.

The integration deliberately does not copy an old renderer or old LightAll shader. It reuses the exact historical Bloom V3 and V3.1 transforms on the unchanged Bloom V2 foundation, then adds a minimal production-only PC2 final RGB non-finite firewall to the modern PBR/GGX/POM LightAll shader and the exact candidate-v2 Karis 3x3 anti-firefly algorithm.

Hard changed-file allowlist:
- SP/code/rend2/glsl/bloom_fp.glsl
- SP/code/rend2/glsl/lightall_fp.glsl
- SP/code/rend2/tr_backend.c
- SP/code/rend2/tr_init.c
- SP/code/rend2/tr_local.h

Mode 2 remains the current three-level Bloom V2 fallback. Mode 3 is the five-level HDR Scatter + V3.1 safety + PC2 + Karis test path.
