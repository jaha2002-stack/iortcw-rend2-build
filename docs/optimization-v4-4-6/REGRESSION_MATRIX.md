# Regression matrix

| Check | Evidence / status before CI |
|---|---|
| Group labels, changing lights/eligibility/scene epochs | PASS: 850000 extracted-C differential checks; UBSan |
| Light emission values/full pool/null | PASS: 10000 extracted-C cases, bitwise equality |
| Shader/gameplay/PVS/AA code preservation | PASS: only tr_main.c and tr_scene.c differ |
| Windows full SP compile and PE hashes | PENDING CI |
| Linux Mesa six-map spawn smoke | PENDING CI protected assets; identical 640x480 High Quality + forceSun 1 |
| Escape1 calibrated guard table movement | NOT_RUN; spawn smoke is insufficient |
| SWF lamp distance traversal | NOT_RUN; spawn smoke is insufficient |
| Dam spotlight shutdown | NOT_RUN |
| Crypt1 fire temporal behavior | NOT_RUN |
| Assault close radar railing / weapon sun beam | NOT_RUN; no calibrated camera supplied |
| Forest CSM/PVS traversal | NOT_RUN |
| Shot/explosion/Tesla sequences | NOT_RUN |
| Windows clean launcher, Cyrillic paths, save/load | NOT_RUN |
| Windows GPU low/high profiles and performance A/B | NOT_RUN |

The existing TestLab instrumentation is reused only in separate native diagnostic builds, after packaging Windows binaries. No retail files are uploaded; runtime trees stay outside evidence. Coarse black/white screenshot checks cannot prove UV/depth correctness or eliminate local artifacts.
