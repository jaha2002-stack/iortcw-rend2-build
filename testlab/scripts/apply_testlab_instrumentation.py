#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "source")
tr_init = root/"SP/code/rend2/tr_init.c"
tr_main = root/"SP/code/rend2/tr_main.c"
tr_scene = root/"SP/code/rend2/tr_scene.c"
g_cmds = root/"SP/code/game/g_cmds.c"

for p in (tr_init,tr_main,tr_scene,g_cmds):
    if not p.is_file():
        raise SystemExit(f"missing source file: {p}")

MARK="DARKWOLF_TESTLAB_V0_1"
if MARK in tr_init.read_text(errors="ignore"):
    raise SystemExit("TestLab patch already applied")

def one(path, old, new, label):
    s=path.read_text()
    n=s.count(old)
    if n != 1:
        raise SystemExit(f"{label}: expected one anchor, got {n}")
    path.write_text(s.replace(old,new,1))

# Production deliberately hard-wires these diagnostics OFF. TestLab makes them
# runtime CVars only in the isolated instrumented binary.
one(tr_init,
'''\tr_staticPromoteUnifiedDiag = &s_darkwolfProductionDiagOffCvar;
\tr_staticPromoteRootCauseDiag = &s_darkwolfProductionDiagOffCvar;
\tr_staticPromoteRootCauseCapture = &s_darkwolfProductionDiagOffCvar;
\tr_staticPromoteRootCauseFocus = &s_darkwolfProductionDiagNegOneCvar;
\tr_staticPromoteRootCauseSampleMs = &s_darkwolfProductionDiagOffCvar;''',
'''\t// DARKWOLF_TESTLAB_V0_1: isolated diagnostic build only; production stays hardwired OFF.
\tr_staticPromoteUnifiedDiag = ri.Cvar_Get( "r_staticPromoteUnifiedDiag", "0", 0 );
\tr_staticPromoteRootCauseDiag = ri.Cvar_Get( "r_staticPromoteRootCauseDiag", "0", 0 );
\tr_staticPromoteRootCauseCapture = ri.Cvar_Get( "r_staticPromoteRootCauseCapture", "0", 0 );
\tr_staticPromoteRootCauseFocus = ri.Cvar_Get( "r_staticPromoteRootCauseFocus", "-1", 0 );
\tr_staticPromoteRootCauseSampleMs = ri.Cvar_Get( "r_staticPromoteRootCauseSampleMs", "100", 0 );''',
"renderer root-cause cvars")

one(tr_main,
'''    s_rStaticPromotePhysicalGroupDiag = &s_uslrdMainProductionOffCvar;''',
'''    // DARKWOLF_TESTLAB_V0_1: expose existing physical shadow-group telemetry in TestLab only.
    s_rStaticPromotePhysicalGroupDiag = ri.Cvar_Get("r_staticPromotePhysicalGroupDiag", "0", 0);''',
"physical group diag")

one(tr_scene,
'''static void R_StaticPromotePhysicalResidencyFrameDiag(const refdef_t *fd,
	staticPromotePersistentLight_t **selected, int selectedCount)
{
	// DARKWOLF_USLRD_CLEAN_PRODUCTION_V1: retained call site, diagnostic body disabled.
	return;''',
'''static void R_StaticPromotePhysicalResidencyFrameDiag(const refdef_t *fd,
	staticPromotePersistentLight_t **selected, int selectedCount)
{
	// DARKWOLF_TESTLAB_V0_1: enable existing read-only production residency telemetry.''',
"enable residency frame diag body")

one(tr_scene,
'''	if (!fd || !tr.world || !0)
		return;''',
'''	if (!fd || !tr.world)
		return;''',
"enable residency frame diag guard")

# Emit stable fixture world origin for the external two-pass controller.
# Also add an independent TestLab-only discovery path that does not depend on
# historical root-cause diagnostic CVars.
diag_fn_anchor='''static void R_StaticPromoteRootCauseDiagFrame(const refdef_t *fd)
{'''
diag_fn_insert='''static void R_TestLabFixtureDiscovery(void)
{
    static int done = 0;
    int i;
    int found = 0;

    if (done || !tr.world || s_staticPromotePersistentCount <= 0)
        return;

    for (i = 0; i < s_staticPromotePersistentCount; ++i)
    {
        staticPromotePersistentLight_t *light = &s_staticPromotePersistentLights[i];
        const int fixture = light->candidate.entityOrdinal;
        if (fixture != 918 && fixture != 782)
            continue;

        ri.Printf(PRINT_ALL,
            "TESTLAB_FIXTURE_ORIGIN map=%s fixture=%d origin=%.3f,%.3f,%.3f\\n",
            tr.world->baseName, fixture,
            light->candidate.origin[0], light->candidate.origin[1], light->candidate.origin[2]);
        found++;
    }

    if (found >= 2)
        done = 1;
}

static void R_StaticPromoteRootCauseDiagFrame(const refdef_t *fd)
{'''
one(tr_scene,diag_fn_anchor,diag_fn_insert,"independent fixture discovery helper")

diag_guard='''    if (!r_staticPromoteRootCauseDiag || !r_staticPromoteRootCauseDiag->integer || !fd || !tr.world)
        return;'''
diag_guard_new='''    R_TestLabFixtureDiscovery();

    if (!r_staticPromoteRootCauseDiag || !r_staticPromoteRootCauseDiag->integer || !fd || !tr.world)
        return;'''
one(tr_scene,diag_guard,diag_guard_new,"fixture discovery call")

parse_anchor='''			parsedCandidate.style = style;
			Q_strncpyz(parsedCandidate.targetname, targetname, sizeof(parsedCandidate.targetname));'''
parse_insert='''			parsedCandidate.style = style;
			// DARKWOLF_TESTLAB_V0_1: deterministic BSP entity discovery before merge/residency policy.
			if (entityOrdinal == 918 || entityOrdinal == 782)
			{
				ri.Printf(PRINT_ALL,
					"TESTLAB_FIXTURE_ORIGIN map=%s fixture=%d origin=%.3f,%.3f,%.3f\\n",
					tr.world ? tr.world->baseName : "<none>", entityOrdinal,
					origin[0], origin[1], origin[2]);
			}
			Q_strncpyz(parsedCandidate.targetname, targetname, sizeof(parsedCandidate.targetname));'''
one(tr_scene,parse_anchor,parse_insert,"BSP fixture origin discovery")

registry_anchor='''	s_staticPromotePersistentBuildGeneration++;
	ri.Printf(PRINT_ALL,
		"STATIC_PROMOTE_V12_FIX_V5_1_REGISTRY map=%s generation=%d'''
registry_insert='''	s_staticPromotePersistentBuildGeneration++;
	// DARKWOLF_TESTLAB_V0_1: dump the final persistent registry once at build time.
	{
		int testlabIndex;
		for (testlabIndex = 0; testlabIndex < s_staticPromotePersistentCount; ++testlabIndex)
		{
			staticPromotePersistentLight_t *testlabLight = &s_staticPromotePersistentLights[testlabIndex];
			ri.Printf(PRINT_ALL,
				"TESTLAB_PERSISTENT_FIXTURE map=%s fixtureIndex=%d fixture=%d origin=%.3f,%.3f,%.3f rawMembers=%d synthetic=%d\\n",
				tr.world ? tr.world->baseName : "<none>", testlabIndex,
				testlabLight->candidate.entityOrdinal,
				testlabLight->candidate.origin[0], testlabLight->candidate.origin[1], testlabLight->candidate.origin[2],
				testlabLight->rawMembers, testlabLight->synthetic ? 1 : 0);
		}
	}
	ri.Printf(PRINT_ALL,
		"STATIC_PROMOTE_V12_FIX_V5_1_REGISTRY map=%s generation=%d'''
one(tr_scene,registry_anchor,registry_insert,"persistent registry dump")

anchor='''    ri.Printf(PRINT_ALL,
        "USLRD_RC_FRONT ms=%d map=%s fixture=%d'''
insert='''    // DARKWOLF_TESTLAB_V0_1: machine-readable discovery record.
    ri.Printf(PRINT_ALL, "TESTLAB_FIXTURE_ORIGIN map=%s fixture=%d origin=%.3f,%.3f,%.3f\\n",
        tr.world->baseName, focusId, light->candidate.origin[0], light->candidate.origin[1], light->candidate.origin[2]);

    ri.Printf(PRINT_ALL,
        "USLRD_RC_FRONT ms=%d map=%s fixture=%d'''
one(tr_scene,anchor,insert,"fixture origin telemetry")

# Full 6-DOF view placement, intentionally only present in TestLab qagame.
cmd_anchor='''/*
=================
Cmd_SetViewpos_f
=================
*/
void Cmd_SetViewpos_f( gentity_t *ent ) {'''
cmd_insert='''// DARKWOLF_TESTLAB_V0_1
static void Cmd_DWTestView_f( gentity_t *ent ) {
    vec3_t origin, angles;
    char buffer[MAX_TOKEN_CHARS];
    int i;

    if ( !g_cheats.integer ) {
        trap_SendServerCommand( ent-g_entities, "print \\"dw_testView requires cheats.\\n\\"" );
        return;
    }
    if ( trap_Argc() != 7 ) {
        trap_SendServerCommand( ent-g_entities, "print \\"usage: dw_testView x y z pitch yaw roll\\n\\"" );
        return;
    }
    for ( i = 0; i < 3; ++i ) {
        trap_Argv( i + 1, buffer, sizeof(buffer) );
        origin[i] = atof(buffer);
        trap_Argv( i + 4, buffer, sizeof(buffer) );
        angles[i] = atof(buffer);
    }
    TeleportPlayer( ent, origin, angles );
    trap_SendServerCommand( ent-g_entities, va("print \\"TESTLAB_VIEW %.3f %.3f %.3f %.3f %.3f %.3f\\n\\"",
        origin[0], origin[1], origin[2], angles[0], angles[1], angles[2]) );
}

/*
=================
Cmd_SetViewpos_f
=================
*/
void Cmd_SetViewpos_f( gentity_t *ent ) {'''
one(g_cmds,cmd_anchor,cmd_insert,"dw_testView implementation")

dispatch='''\t} else if ( Q_stricmp( cmd, "setviewpos" ) == 0 )  {
\t\tCmd_SetViewpos_f( ent );'''
dispatch_new='''\t} else if ( Q_stricmp( cmd, "dw_testView" ) == 0 )  { // DARKWOLF_TESTLAB_V0_1
\t\tCmd_DWTestView_f( ent );
\t} else if ( Q_stricmp( cmd, "setviewpos" ) == 0 )  {
\t\tCmd_SetViewpos_f( ent );'''
one(g_cmds,dispatch,dispatch_new,"dw_testView dispatch")

print("DARKWOLF_TESTLAB_V0_1 instrumentation applied")
