# IFLC V1.5U — VOLUME_ONLY manual own-body validation

Requested validation target: a selected fire owner reported as `VOLUME_ONLY` with `ownBodySurfaces=0` and `manualSeeds=0`.

Required behavior:
- `/dw_fl_select` selects one unambiguous stable fire owner.
- `/dw_fl_self_pick` binds the exact visible opaque body surface without requiring flame bounds.
- `/dw_fl_set selfshadow 0` removes only the selected source's own-body shadow.
- Fire/volume lighting and unrelated scene shadows remain enabled.

Run the existing `DW IFLC V1.5 Universal manual self-shadow` workflow, including its `volume-only` job with flame-bounds discovery deliberately disabled. This file is a validation trigger/documentation only; it does not alter renderer source or production assets.
