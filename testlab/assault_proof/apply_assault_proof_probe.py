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
if mark in s and aim_mark in gs:
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

dispatch_anchor = '''\t} else if ( Q_stricmp( cmd, "dw_testViewState" ) == 0 )  { // DARKWOLF_TESTLAB_V0_1
\t\tCmd_DWTestViewState_f( ent );
'''
dispatch_new = '''\t} else if ( Q_stricmp( cmd, "dw_testViewState" ) == 0 )  { // DARKWOLF_TESTLAB_V0_1
\t\tCmd_DWTestViewState_f( ent );
\t} else if ( Q_stricmp( cmd, "dw_assaultAim" ) == 0 )  { // DARKWOLF_ASSAULT_PROOF_AIM_V1
\t\tCmd_DWAssaultAim_f( ent );
'''
if aim_mark not in gs[gs.find(dispatch_anchor):]:
    if gs.count(dispatch_anchor) != 1:
        raise SystemExit(f"aim dispatch anchor count={gs.count(dispatch_anchor)}")
    gs = gs.replace(dispatch_anchor, dispatch_new, 1)

p.write_text(s,encoding="utf-8",newline="\n")
g.write_text(gs,encoding="utf-8",newline="\n")
print("DARKWOLF_ASSAULT_PROOF_SUN_PROBE_V1 applied")
print("DARKWOLF_ASSAULT_PROOF_AIM_V1 applied")
