# DarkWolf IFLC V1.5 — Exact Body Self-Shadow

V1.5 is a narrow follow-up to V1.4. It does not change V1.4 native containment,
the accepted V1.3 electric worklamp correction, GLSL, PCF4x4, or shadow budgets.

The change affects only explicit manual own-body binding:
1. select the flame with `dw_fl_select`;
2. aim at one concrete body part and run `dw_fl_self_pick`;
3. verify `manualSeeds>=1` and `ownBodySurfaces>=1`;
4. use `dw_fl_set selfshadow 0`, then `dw_fl_save`.

Manual mode uses the picked surface as a seed for a bounded contact-only local
component. Large architectural planes, flame geometry, remote surfaces, and
oversized groups are rejected. AUTO behavior remains V1.4-compatible.
