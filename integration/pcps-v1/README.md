# DarkWolf PCPS V1: opt-in shadow controls

Source baseline: SAFE Clean Actions #41297344177, preserving accepted Texture & Material Fidelity V2.

This first increment is **not** a universal physically-correct shadow solver. It provides reversible, source-local point-shadow interventions and a real source-eligibility filter that frees a shadow-map allocation for other eligible lights.

## Commands
- \`dw_ps_help\`: command reference
- \`dw_ps_lights\`: enumerate live dynamic lights and slot allocations
- \`dw_ps_picklight\`: choose source roughly in crosshair direction (angular nearest); \`dw_ps_select N\` for exact numbered light
- \`dw_ps_pickcaster\`: raycast BSP triangles under the crosshair; reports map-local surface and shader
- \`dw_ps_caster_off\` / \`dw_ps_caster_on\`: change only selected source's ordinary point-shadow caster submission
- \`dw_ps_light_off\` / \`dw_ps_light_on\`: remove/restore selected source from **shadow-source selection** (direct lighting untouched)
- \`dw_ps_info\`, \`dw_ps_reset\`: status and immediate reset

Rules are session-local and tied to loaded BSP world identity. All edits reset on map change or restart. Do not rely on surface number across maps.

Not implemented in V1: exact per-pixel depth-owner selection, UI overlay, per-source soft penumbra, shadow capture origin shift, permanent profile export, and changes to existing receivers/emitters.

Safety: 3 persistent shadow slots and 2 accepted dynamic reserved slots remain untouched; no global material suppression or changed game executables; Boss1 local guard remains active; no shader edits.

### Correct slot semantics
Disabling a **caster** does *not* free a slot because slots belong to shadow-producing **lights**. \`dw_ps_light_off\` filters that light before the canonical priority/residency selection. The fixed slot budget is not raised, and any remaining light may acquire the freed allocation under the production selection rules.

### Known limitations
- Light selection from the player view is angular and may select an obscured lamp. Inspect results before editing.
- The BSP ray picker can select a nearby receiver surface (wall/floor) rather than the source of the distant shadow; aim at the actual object you want to exclude.
- Model entities and bmodels are not included in V1 caster selection; BSP world geometry only.
- Source matching relies on origin/class/radius tolerance and can be ambiguous when multiple dlights overlap. Ambiguous matching must be audited before GPU acceptance.
- A successful CI compile does not establish physical accuracy or visual safety. Compare same-camera screenshots on Factory, Crypt1/2, Boss1 and negative controls.
