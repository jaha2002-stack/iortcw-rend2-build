# V5 pre-GPU classifier specificity test against all nine V4 archives (2026-11-01)

Tested source-link criterion (emitter-linked BSP candidate, AABB boxDistance<=16 from capture, AABB halfDiagonal>=12, AABB halfDiagonal/max(centerDistance,8)>=0.70) against the **actual V4 mode0 JSON** from:

- Boss1 20261101_142544: **only surface 7232**, source (-2764,-219,-24), material ametal_m03dm, angular proxy 0.85, AABB distance10.359, halfDiagonal19.655.
- Factory 20261101_142745: none.
- Crypt2 20261101_143001: none.
- Crypt1 20261101_143159: none.
- Escape1 143330, 143422, 143533, 143618: none in any four scene archives.
- Rocket 20261101_143740: none.

This is a **static replay over the V4 shortlist**, not proof across unseen RTCW maps or a GPU test. Importantly, a generic rule based just on a nearby shader/material or source proximity would falsely target Rocket/Escape1; the stricter geometric rule did not in this sample.

Crypt1/2 require independent structurally symmetric radial cage grouping; their first 10 relative AABBs were identical exactly. No material name is blacklisted globally and no fixed numeric Boss1 ID appears in V5 generalized matching logic.

Next: final V5 proof release GPU one-exec A/B/attribution/restore on Boss1, Factory, Crypt1, Crypt2. A skipped draw, by itself, is NOT proof that a caster won the shadow map depth buffer. Clean Production #41019985033 remains immutable until GPU accepted.
