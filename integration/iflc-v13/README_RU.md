# IFLC V1.3: electric self-shadow and fire containment work

Accepted baseline is exactly Run #41772470237. This branch is isolated; it does not replace the accepted IFLC V1.2.

Current implementation adds a geometry-qualified electric aperture housing classifier. Connected triangle components, not whole BSP meshes, are selected. Classification is shared by ordinary and architectural captures, with a distinct world-cache key. Fire/IFLC, CSM, main-view geometry, rods/tripod and other lights are excluded. Downward-facing shades are deliberately not classified as defective just because they produce a large ceiling shadow.

The native harness contains test-only controls to distinguish electric point/world shadow ownership and fire direct/volumetric/SSGI/bloom contributions. Fire hard-visibility, two-sided synthetic-capture and near-plane controls are diagnostic hypotheses, NOT production fixes. No deployable build is published by the initial causal workflow.

Any correction requires actual rendered evidence; source classification and successful CI alone are not visual acceptance. User lamp profiles and original global settings remain untouched. Licensed map data are never included in artifacts.
