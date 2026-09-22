# DarkWolf/ioRTCW Rend2 Unified Production V1

This is the single integrated Windows x64 SP validation package. Copy the files over
a legally installed Return to Castle Wolfenstein/ioRTCW SP installation and run
`exec UNIFIED_PRODUCTION.cfg`. Do not combine it with earlier Tesla, table, recovery,
or diagnostic packages. User-generated `wolfconfig.cfg` files are intentionally not
included.

## One-pass runtime test matrix

### Escape1 doctor's office
Confirm original intermittent stationary-Tesla timing, a genuinely dark authored
off phase, two independently lit ceiling fixtures, correct active Tesla illumination,
grids/grates casting shadows, and a separate Tesla-weapon light.

### Escape1 table
At near, medium, and far distances and while crossing the former transition point,
confirm one normal table shadow, no overlapping darker second shadow, and no loss of
the first shadow.

### SWF three-lamp row
Approach, retreat, turn, and stand under the lamps. Base Direct Light and LocalVol
must remain stable while scarce shadow ownership may change.

### Physical USER_BLOCKED
Block one promoted lamp. Its promoted Direct Light, LocalVol and shadow must all
disappear, with no sibling alias still emitting. Unblock it and confirm all three
outputs return consistently.

### Dynamic sources under many lamps
Check muzzle flashes, explosions, Tesla weapon and fire. Dynamic effects must remain
visible and stationary lamps must not disappear incorrectly.

### Factory / Boss2 / Xlabs / Tram
Check Factory fire Direct Light, shadow, FireVol and nearby lamps; Boss2 Tesla/grate;
and Xlabs/Tram cutout/grate shadows, receivers and performance.

### Lifecycle
Test save/load and map restart. Confirm physical blocks and identities remain valid
and no stale point shadows survive.

## Performance record

Report FPS in the same Escape1, SWF, Factory and Boss2 locations used previously.
Note any 40–50 FPS scene and whether the value is stable or follows Tesla, fire, or
point-shadow activity. No second package is required.

Compilation and static replay are not visual runtime acceptance; please return the
results of this complete matrix.
