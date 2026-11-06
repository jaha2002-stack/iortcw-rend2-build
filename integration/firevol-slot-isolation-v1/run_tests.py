#!/usr/bin/env python3
from pathlib import Path
import sys

root=Path(sys.argv[1])
b=(root/"tr_backend.c").read_text()
i=(root/"tr_init.c").read_text()

required_backend=[
    's_rDwFireVolSolo = ri.Cvar_Get("r_dwFireVolSolo", "-1", 0);',
    'if (soloSlot >= 0 && i != soloSlot)',
    'FIREVOL_SLOT_ISOLATION map=%s solo=%d selected=%d rendered=%d',
    'surface=%d primitive=%d entity=%d sourceClass=%d synthetic=%d iflcPriority=%d',
    'origin=%.1f,%.1f,%.1f geometryRadius=%.1f',
]
for x in required_backend:
    assert x in b, x

required_init=[
    'static void R_FireVolSolo_f( void )',
    'ri.Cmd_AddCommand( "dw_fv_solo", R_FireVolSolo_f );',
    'ri.Cmd_RemoveCommand( "dw_fv_solo" );',
    'ri.Cvar_Get( "r_dwFireVolSolo", "-1", 0 )',
    'slot < -1 || slot > 7',
    'FIREVOL_SLOT_ISOLATION_COMMAND',
]
for x in required_init:
    assert x in i, x

# Production selection/residency budget remains untouched.
assert '#define FIREVOL081_RENDER_CAP 8' in b
assert 'RB_FireVStableSelectResidents' in b
assert 'RB_FireVFixtureV3RefreshRegistry' in b
assert 'RB_FireV4WorldClusterDedup' in b
assert 'RB_FireV6StaticFireplaceDedup' in b

# The solo gate is strictly inside the final selected[] render loop.
loop=b.index('for (i = 0; i < selectedCount; ++i)')
gate=b.index('if (soloSlot >= 0 && i != soloSlot)',loop)
render=b.index('RB_LocalVolumetricRenderEx',gate)
post=b.index('FIREVOL_SLOT_ISOLATION map=%s',render)
assert loop < gate < render < post

# It must NOT rewrite selectedCount or maxActive based on solo slot.
window=b[gate-300:gate+400]
assert 'selectedCount =' not in window
assert 'maxActive =' not in window

print("PASS FireVol Slot Isolation V1 regression gates")
