#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "source")
p = root / "SP/code/rend2/tr_scene.c"
g = root / "SP/code/game/g_cmds.c"
for q in (p, g):
    if not q.is_file():
        raise SystemExit(f"missing {q}")
s = p.read_text(encoding="utf-8")
gs = g.read_text(encoding="utf-8")
mark = "DARKWOLF_ASSAULT_PROOF_SUN_PROBE_V1"
aim_mark = "DARKWOLF_ASSAULT_PROOF_AIM_V1"
state_mark = "DARKWOLF_ASSAULT_PROOF_STATE_V1"
weapon_mark = "DARKWOLF_ASSAULT_PROOF_MP40_V1"
runtime_mark = "DARKWOLF_ASSAULT_PROOF_STATICPROMOTE_V1"
if mark in s and aim_mark in gs and state_mark in gs and weapon_mark in gs and runtime_mark in s:
    print("assault proof probes already applied")
    raise SystemExit(0)

old = '''\tVectorCopy(tr.sunDirection, tr.refdef.sunDir);\n'''
new = '''\t// DARKWOLF_ASSAULT_PROOF_SUN_PROBE_V1: isolated TestLab telemetry only.\n\t{\n\t\tstatic int assaultProofSunPrinted = 0;\n\t\tif (!assaultProofSunPrinted && tr.world)\n\t\t{\n\t\t\tri.Printf(PRINT_ALL,\n\t\t\t\t"ASSAULT_PROOF_SUN map=%s dir=%.7f,%.7f,%.7f light=%.3f,%.3f,%.3f\\n",\n\t\t\t\ttr.world->baseName,\n\t\t\t\ttr.sunDirection[0], tr.sunDirection[1], tr.sunDirection[2],\n\t\t\t\ttr.sunLight[0], tr.sunLight[1], tr.sunLight[2]);\n\t\t\tassaultProofSunPrinted = 1;\n\t\t}\n\t}\n\n\tVectorCopy(tr.sunDirection, tr.refdef.sunDir);\n'''
n = s.count(old)
if n != 1:
    raise SystemExit(f"sun probe anchor count={n}")
if mark not in s:
    s = s.replace(old,new,1)

aim_anchor = '''static void Cmd_DWTestViewState_f( gentity_t *ent ) {
'''
if aim_mark not in gs:
    if gs.count(aim_anchor) != 1:
        raise SystemExit(f"aim helper anchor count={gs.count(aim_anchor)}")
    aim_impl = '''// DARKWOLF_ASSAULT_PROOF_AIM_V1: TestLab-only deterministic view rotation.
static void Cmd_DWAssaultAim_f( gentity_t *ent ) {
    vec3_t angles;
    char buffer[MAX_TOKEN_CHARS];
    int i;

    if ( !g_cheats.integer ) {
        trap_SendServerCommand( ent-g_entities, "print \\"dw_assaultAim requires cheats.\\n\\"" );
        return;
    }
    if ( trap_Argc() != 4 ) {
        trap_SendServerCommand( ent-g_entities, "print \\"usage: dw_assaultAim pitch yaw roll\\n\\"" );
        return;
    }
    for ( i = 0; i < 3; ++i ) {
        trap_Argv( i + 1, buffer, sizeof(buffer) );
        angles[i] = atof(buffer);
    }

    ent->client->noclip = qtrue;
    ent->client->ps.pm_type = PM_NOCLIP;
    ent->client->ps.groundEntityNum = ENTITYNUM_NONE;
    VectorClear( ent->client->ps.velocity );
    ent->client->pers.cmd.forwardmove = 0;
    ent->client->pers.cmd.rightmove = 0;
    ent->client->pers.cmd.upmove = 0;
    SetClientViewAngle( ent, angles );

    trap_SendServerCommand( ent-g_entities, va(
        "print \\"ASSAULT_PROOF_AIM origin=%.3f,%.3f,%.3f angles=%.3f,%.3f,%.3f\\n\\"",
        ent->client->ps.origin[0], ent->client->ps.origin[1], ent->client->ps.origin[2],
        angles[0], angles[1], angles[2]) );
}

'''
    gs = gs.replace(aim_anchor, aim_impl + aim_anchor, 1)

# DARKWOLF_ASSAULT_PROOF_MP40_V1: force a deterministic first-person MP40 for proof screenshots.
weapon_anchor = '''static void Cmd_DWTestViewState_f( gentity_t *ent ) {
'''
if weapon_mark not in gs:
    if gs.count(weapon_anchor) != 1:
        raise SystemExit(f"MP40 helper anchor count={gs.count(weapon_anchor)}")
    weapon_impl = '''// DARKWOLF_ASSAULT_PROOF_MP40_V1
static void Cmd_DWAssaultMP40_f( gentity_t *ent ) {
    if ( !ent || !ent->client )
        return;
    COM_BitSet( ent->client->ps.weapons, WP_MP40 );
    Add_Ammo( ent, WP_MP40, 999, qtrue );
    ent->client->ps.weapon = WP_MP40;
    ent->client->ps.weaponstate = WEAPON_READY;
    ent->client->ps.weaponTime = 0;
    trap_SendServerCommand( ent-g_entities, va(
        "print \\"ASSAULT_PROOF_MP40 weapon=%d ammo=%d clip=%d\\n\\"",
        ent->client->ps.weapon,
        ent->client->ps.ammo[BG_FindAmmoForWeapon(WP_MP40)],
        ent->client->ps.ammoclip[BG_FindClipForWeapon(WP_MP40)]) );
}

'''
    gs = gs.replace(weapon_anchor, weapon_impl + weapon_anchor, 1)

# DARKWOLF_ASSAULT_PROOF_STATE_V1: TestLab-only weapon/player state proof.
state_anchor = '''static void Cmd_DWTestViewState_f( gentity_t *ent ) {
'''
if state_mark not in gs:
    if gs.count(state_anchor) != 1:
        raise SystemExit(f"state helper anchor count={gs.count(state_anchor)}")
    state_impl = '''// DARKWOLF_ASSAULT_PROOF_STATE_V1
static void Cmd_DWAssaultState_f( gentity_t *ent ) {
    int weapon = ent->client ? ent->client->ps.weapon : -1;
    int pmType = ent->client ? ent->client->ps.pm_type : -1;
    int weaponState = ent->client ? ent->client->ps.weaponstate : -1;
    trap_SendServerCommand( ent-g_entities, va(
        "print \\"ASSAULT_PROOF_STATE weapon=%d pmType=%d weaponState=%d origin=%.3f,%.3f,%.3f angles=%.3f,%.3f,%.3f\\n\\"",
        weapon, pmType, weaponState,
        ent->client->ps.origin[0], ent->client->ps.origin[1], ent->client->ps.origin[2],
        ent->client->ps.viewangles[0], ent->client->ps.viewangles[1], ent->client->ps.viewangles[2]) );
}

'''
    gs = gs.replace(state_anchor, state_impl + state_anchor, 1)

# Extend the existing TestLab post-delivery telemetry to the observation-tower lamp.
runtime_old = '''\t\t\t\tif (testlabFixture != 918 && testlabFixture != 782 &&
\t\t\t\t\ttestlabFixture != 741 && testlabFixture != 742 &&
\t\t\t\t\ttestlabFixture != 743 && testlabFixture != 744)
\t\t\t\t\tcontinue;
'''
runtime_new = '''\t\t\t\t// DARKWOLF_ASSAULT_PROOF_STATICPROMOTE_V1
\t\t\t\tif (!Q_stricmp(tr.world->baseName, "assault"))
\t\t\t\t{
\t\t\t\t\tif (testlabFixture != 209)
\t\t\t\t\t\tcontinue;
\t\t\t\t}
\t\t\t\telse if (testlabFixture != 918 && testlabFixture != 782 &&
\t\t\t\t\ttestlabFixture != 741 && testlabFixture != 742 &&
\t\t\t\t\ttestlabFixture != 743 && testlabFixture != 744)
\t\t\t\t\tcontinue;
'''
if runtime_mark not in s:
    if s.count(runtime_old) != 1:
        raise SystemExit(f"StaticPromote runtime anchor count={s.count(runtime_old)}")
    s = s.replace(runtime_old, runtime_new, 1)

dispatch_anchor = '''\t} else if ( Q_stricmp( cmd, "dw_testViewState" ) == 0 )  { // DARKWOLF_TESTLAB_V0_1
\t\tCmd_DWTestViewState_f( ent );
'''
dispatch_new = '''\t} else if ( Q_stricmp( cmd, "dw_testViewState" ) == 0 )  { // DARKWOLF_TESTLAB_V0_1
\t\tCmd_DWTestViewState_f( ent );
\t} else if ( Q_stricmp( cmd, "dw_assaultAim" ) == 0 )  { // DARKWOLF_ASSAULT_PROOF_AIM_V1
\t\tCmd_DWAssaultAim_f( ent );
\t} else if ( Q_stricmp( cmd, "dw_assaultState" ) == 0 )  { // DARKWOLF_ASSAULT_PROOF_STATE_V1
\t\tCmd_DWAssaultState_f( ent );
\t} else if ( Q_stricmp( cmd, "dw_assaultMP40" ) == 0 )  { // DARKWOLF_ASSAULT_PROOF_MP40_V1
\t\tCmd_DWAssaultMP40_f( ent );
'''
if aim_mark not in gs[gs.find(dispatch_anchor):]:
    if gs.count(dispatch_anchor) != 1:
        raise SystemExit(f"aim dispatch anchor count={gs.count(dispatch_anchor)}")
    gs = gs.replace(dispatch_anchor, dispatch_new, 1)

p.write_text(s,encoding="utf-8",newline="\n")
g.write_text(gs,encoding="utf-8",newline="\n")
print("DARKWOLF_ASSAULT_PROOF_SUN_PROBE_V1 applied")
print("DARKWOLF_ASSAULT_PROOF_AIM_V1 applied")
print("DARKWOLF_ASSAULT_PROOF_STATE_V1 applied")
print("DARKWOLF_ASSAULT_PROOF_MP40_V1 applied")
print("DARKWOLF_ASSAULT_PROOF_STATICPROMOTE_V1 applied")
