#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "source")
tr_init = root/"SP/code/rend2/tr_init.c"
tr_main = root/"SP/code/rend2/tr_main.c"
tr_scene = root/"SP/code/rend2/tr_scene.c"
g_cmds = root/"SP/code/game/g_cmds.c"
cg_info = root/"SP/code/cgame/cg_info.c"
cg_servercmds = root/"SP/code/cgame/cg_servercmds.c"

for p in (tr_init,tr_main,tr_scene,g_cmds,cg_info,cg_servercmds):
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
	return;
	static unsigned int lastSignature[STATIC_PROMOTE_PERSISTENT_MAX_FIXTURES];
	static int lastGeneration = -1;
	int i;
	int sceneDlights;
	int promotedCount = 0;
	int nativeCount;
	int headroom;
	int j;

	if (!fd || !tr.world || !0)
		return;''',
'''static void R_StaticPromotePhysicalResidencyFrameDiag(const refdef_t *fd,
	staticPromotePersistentLight_t **selected, int selectedCount)
{
	// DARKWOLF_TESTLAB_V0_1: enable existing read-only production residency telemetry.
	static unsigned int lastSignature[STATIC_PROMOTE_PERSISTENT_MAX_FIXTURES];
	static int lastGeneration = -1;
	int i;
	int sceneDlights;
	int promotedCount = 0;
	int nativeCount;
	int headroom;
	int j;

	if (!fd || !tr.world)
		return;''',
"enable residency frame diag")

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

# Trace only the early R_StaticPromoteFrame gates so TestLab can distinguish
# renderer invocation from registry readiness without changing production state.
frame_gate_anchor='''	// DARKWOLF_PCRB_E2E_V0_7_VISIBLE_SURFACE_INFLUENCE_AUDIT
	R_DarkWolfPCRBE2E07ResetFrame();
	if (!tr.world || (fd->rdflags & (RDF_NOWORLDMODEL | RDF_SKYBOXPORTAL)))
		return;
	R_StaticPromoteParseWorld();
	if (!R_StaticPromoteBuildPersistentRegistry())
		return;'''
frame_gate_insert='''	// DARKWOLF_TESTLAB_V0_1: read-only early-frame gate telemetry.
	{
		static int testlabLastFrameGateStage = -1;
		if (!tr.world || (fd->rdflags & (RDF_NOWORLDMODEL | RDF_SKYBOXPORTAL)))
		{
			if (testlabLastFrameGateStage != 0)
				ri.Printf(PRINT_ALL,
					"TESTLAB_FRAME_STATE stage=WORLD_GATE world=%d rdflags=%d\\n",
					tr.world ? 1 : 0, fd ? fd->rdflags : -1);
			testlabLastFrameGateStage = 0;
			return;
		}
		R_DarkWolfPCRBE2E07ResetFrame();
		R_StaticPromoteParseWorld();
		if (!R_StaticPromoteBuildPersistentRegistry())
		{
			if (testlabLastFrameGateStage != 1)
				ri.Printf(PRINT_ALL,
					"TESTLAB_FRAME_STATE stage=REGISTRY_NOT_READY map=%s entityString=%d parsedCandidates=%d persistentReady=%d persistentCount=%d\\n",
					tr.world->baseName, (tr.world->entityString && tr.world->entityString[0]) ? 1 : 0,
					s_staticPromoteCandidateCount, s_staticPromotePersistentReady ? 1 : 0,
					s_staticPromotePersistentCount);
			testlabLastFrameGateStage = 1;
			return;
		}
		if (testlabLastFrameGateStage != 2)
			ri.Printf(PRINT_ALL,
				"TESTLAB_FRAME_STATE stage=READY map=%s parsedCandidates=%d persistentCount=%d generation=%d\\n",
				tr.world->baseName, s_staticPromoteCandidateCount, s_staticPromotePersistentCount,
				s_staticPromotePersistentBuildGeneration);
		testlabLastFrameGateStage = 2;
	}'''
one(tr_scene,frame_gate_anchor,frame_gate_insert,"StaticPromote frame gate telemetry")

# Post-delivery frame proof: bypasses historical diagnostic guards and records
# only the two Escape1 fixtures after production selection/delivery has run.
runtime_probe_anchor='''	// DARKWOLF_USLRD_V0_1: compact transition/summary telemetry only when explicitly enabled.
	R_StaticPromoteUSLRDDiagFrame();'''
runtime_probe_insert='''	// DARKWOLF_TESTLAB_V0_1: renderer-authoritative camera proof.
	{
		static cvar_t *testlabCaptureIndexCvar = NULL;
		static int testlabLastCaptureIndex = -999999;
		int testlabCaptureIndex;
		if (!testlabCaptureIndexCvar)
			testlabCaptureIndexCvar = ri.Cvar_Get("r_testlabCaptureIndex", "-1", 0);
		testlabCaptureIndex = testlabCaptureIndexCvar ? testlabCaptureIndexCvar->integer : -1;
		if (fd && testlabCaptureIndex >= 0 && testlabCaptureIndex != testlabLastCaptureIndex)
		{
			ri.Printf(PRINT_ALL,
				"TESTLAB_RENDER_VIEW index=%d origin=%.3f,%.3f,%.3f forward=%.6f,%.6f,%.6f rdflags=%d\\n",
				testlabCaptureIndex,
				fd->vieworg[0], fd->vieworg[1], fd->vieworg[2],
				fd->viewaxis[0][0], fd->viewaxis[0][1], fd->viewaxis[0][2],
				fd->rdflags);
			testlabLastCaptureIndex = testlabCaptureIndex;
		}
	}

	// DARKWOLF_TESTLAB_V0_1: read-only post-delivery runtime proof.
	{
		static int testlabLastFramePrintMs = -1;
		int testlabNowMs = ri.Milliseconds();
		if (testlabLastFramePrintMs < 0 || testlabNowMs - testlabLastFramePrintMs >= 100)
		{
			int testlabFixtureIndex;
			for (testlabFixtureIndex = 0; testlabFixtureIndex < s_staticPromotePersistentCount; ++testlabFixtureIndex)
			{
				staticPromotePersistentLight_t *testlabLight = &s_staticPromotePersistentLights[testlabFixtureIndex];
				int testlabFixture = testlabLight->candidate.entityOrdinal;
				int testlabSelectedSlot = -1;
				int testlabAddedIndex;
				int testlabClass;
				int testlabSlot;
				if (testlabFixture != 918 && testlabFixture != 782)
					continue;
				for (testlabSlot = 0; testlabSlot < selectedCount; ++testlabSlot)
				{
					if (selected[testlabSlot] == testlabLight)
					{
						testlabSelectedSlot = testlabSlot;
						break;
					}
				}
				testlabAddedIndex = R_DarkWolfFindPromotedDlightIndex(testlabLight);
				testlabClass = R_StaticPromoteClassifyFixture(testlabLight);
				ri.Printf(PRINT_ALL,
					"TESTLAB_RUNTIME_FRAME map=%s fixture=%d enabled=%d maxLights=%d selectedCount=%d activeCount=%d physical=%d class=%d selectedSlot=%d addedDlightIndex=%d influenceVisible=%d held=%d unifiedResident=%d unifiedSlot=%d sourceRoute=%d nativeSuppressed=%d rawMembers=%d\\n",
					tr.world->baseName, testlabFixture, enable, maxLights, selectedCount, activeCount,
					testlabLight->physicalRecognitionAccepted ? 1 : 0, testlabClass,
					testlabSelectedSlot, testlabAddedIndex,
					testlabLight->influenceVisibleNow ? 1 : 0, testlabLight->heldResident ? 1 : 0,
					testlabLight->unifiedResident ? 1 : 0, testlabLight->unifiedSelectedSlot,
					testlabLight->physicalSourceRoute, testlabLight->nativeDuplicateSuppressed ? 1 : 0,
					testlabLight->rawMembers);
			}
			testlabLastFramePrintMs = testlabNowMs;
		}
	}

	// DARKWOLF_USLRD_V0_1: compact transition/summary telemetry only when explicitly enabled.
	R_StaticPromoteUSLRDDiagFrame();'''
one(tr_scene,runtime_probe_anchor,runtime_probe_insert,"post-delivery runtime probe")

# TestLab must enter actual gameplay rather than remain on the SP briefing UI.
# Mirror the stock UI "playerstart" action without opening menus or synthesizing input.
one(cg_info,
'''		trap_UI_Popup( "briefing" );

		//trap_UpdateScreen();''',
'''		{
			char testlabAutomation[16];
			trap_Cvar_VariableStringBuffer( "dw_testAutomation", testlabAutomation, sizeof(testlabAutomation) );
			if ( !atoi( testlabAutomation ) ) {
				trap_UI_Popup( "briefing" );
			} else {
				CG_Printf( "TESTLAB_BRIEFING_BYPASS active=1\\n" );
			}
		}

		//trap_UpdateScreen();''',
"briefing bypass")

one(cg_servercmds,
'''	if ( !strcmp( cmd, "rockandroll" ) ) {   // map loaded, game is ready to begin.
		CG_Fade( 0, 0, 0, 255, cg.time, 0 );      // go black
		trap_UI_Popup( "pregame" );                // start pregame menu
		trap_Cvar_Set( "cg_norender", "1" );    // don't render the world until the player clicks in and the 'playerstart' func has been called (g_main in G_UpdateCvars() ~ilne 949)

		trap_S_FadeAllSound( 1.0f, 1000 );    // fade sound up

		return;
	}''',
'''	if ( !strcmp( cmd, "rockandroll" ) ) {   // map loaded, game is ready to begin.
		char testlabAutomation[16];
		trap_Cvar_VariableStringBuffer( "dw_testAutomation", testlabAutomation, sizeof(testlabAutomation) );
		if ( atoi( testlabAutomation ) ) {
			// DARKWOLF_TESTLAB_V0_1: stock Continue action without UI/input emulation.
			CG_Fade( 0, 0, 0, 0, cg.time, 0 );
			trap_Cvar_Set( "g_playerstart", "1" );
			trap_S_FadeAllSound( 1.0f, 1000 );
			CG_Printf( "TESTLAB_GAMEPLAY_START requested=1\\n" );
			return;
		}
		CG_Fade( 0, 0, 0, 255, cg.time, 0 );      // go black
		trap_UI_Popup( "pregame" );                // start pregame menu
		trap_Cvar_Set( "cg_norender", "1" );    // don't render the world until the player clicks in and the 'playerstart' func has been called (g_main in G_UpdateCvars() ~ilne 949)

		trap_S_FadeAllSound( 1.0f, 1000 );    // fade sound up

		return;
	}''',
"automatic gameplay start")

# Escape1's stock map script can issue new startCam commands after a TestLab
# view has already called stopCam. In automation mode suppress those future
# client camera takeovers at the cgame boundary; normal production behavior is
# untouched because this source edit exists only in the isolated TestLab build.
one(cg_servercmds,
'''\tif ( !strcmp( cmd, "startCam" ) ) {
\t\tqboolean startBlack = atoi( CG_Argv( 2 ) );

\t\tCG_StartCamera( CG_Argv( 1 ), startBlack );
\t\treturn;
\t}''',
'''\tif ( !strcmp( cmd, "startCam" ) ) {
\t\tchar testlabAutomation[16];
\t\tqboolean startBlack;

\t\ttrap_Cvar_VariableStringBuffer( "dw_testAutomation", testlabAutomation, sizeof(testlabAutomation) );
\t\tif ( atoi( testlabAutomation ) ) {
\t\t\tCG_Printf( "TESTLAB_STARTCAM_SUPPRESSED name=%s black=%s\\n", CG_Argv( 1 ), CG_Argv( 2 ) );
\t\t\treturn;
\t\t}

\t\tstartBlack = atoi( CG_Argv( 2 ) );
\t\tCG_StartCamera( CG_Argv( 1 ), startBlack );
\t\treturn;
\t}''',
"scripted camera suppression")

# Full 6-DOF view placement, intentionally only present in TestLab qagame.
# Unlike normal gameplay teleport, keep the automation camera fixed in noclip
# with zero velocity so gravity/collision cannot collapse ring positions.
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

    // DARKWOLF_TESTLAB_V0_1: terminate any stock SP scripted camera through
    // the normal serverCommand -> CG_StopCamera -> stopCamera handshake before
    // placing the deterministic TestLab view.
    trap_SendServerCommand( ent-g_entities, "stopCam" );

    trap_UnlinkEntity( ent );
    ent->client->noclip = qtrue;
    ent->client->ps.pm_type = PM_NOCLIP;
    ent->client->ps.groundEntityNum = ENTITYNUM_NONE;
    VectorClear( ent->client->ps.velocity );
    ent->client->pers.cmd.forwardmove = 0;
    ent->client->pers.cmd.rightmove = 0;
    ent->client->pers.cmd.upmove = 0;
    VectorCopy( origin, ent->client->ps.origin );
    SetClientViewAngle( ent, angles );
    ent->client->ps.eFlags ^= EF_TELEPORT_BIT;
    BG_PlayerStateToEntityState( &ent->client->ps, &ent->s, qtrue );
    VectorCopy( ent->client->ps.origin, ent->r.currentOrigin );
    trap_LinkEntity( ent );

    trap_SendServerCommand( ent-g_entities, va("print \\"TESTLAB_VIEW %.3f %.3f %.3f %.3f %.3f %.3f\\n\\"",
        origin[0], origin[1], origin[2], angles[0], angles[1], angles[2]) );
}

static void Cmd_DWTestViewState_f( gentity_t *ent ) {
    char buffer[MAX_TOKEN_CHARS];
    int index;

    if ( trap_Argc() != 2 ) {
        trap_SendServerCommand( ent-g_entities, "print \\"usage: dw_testViewState index\\n\\"" );
        return;
    }
    trap_Argv( 1, buffer, sizeof(buffer) );
    index = atoi(buffer);
    trap_SendServerCommand( ent-g_entities, va(
        "print \\"TESTLAB_VIEW_STATE index=%d origin=%.3f,%.3f,%.3f angles=%.3f,%.3f,%.3f velocity=%.3f,%.3f,%.3f noclip=%d pmNoClip=%d\\n\\"",
        index,
        ent->client->ps.origin[0], ent->client->ps.origin[1], ent->client->ps.origin[2],
        ent->client->ps.viewangles[0], ent->client->ps.viewangles[1], ent->client->ps.viewangles[2],
        ent->client->ps.velocity[0], ent->client->ps.velocity[1], ent->client->ps.velocity[2],
        ent->client->noclip ? 1 : 0,
        ent->client->ps.pm_type == PM_NOCLIP ? 1 : 0) );
}

static void Cmd_DWTestEntityDump_f( gentity_t *ent ) {
    char buffer[MAX_TOKEN_CHARS];
    vec3_t center;
    float radius;
    float radiusSq;
    int i;

    if ( !g_cheats.integer ) {
        trap_SendServerCommand( ent-g_entities, "print \\"dw_testEntityDump requires cheats.\\n\\"" );
        return;
    }
    if ( trap_Argc() != 5 ) {
        trap_SendServerCommand( ent-g_entities, "print \\"usage: dw_testEntityDump x y z radius\\n\\"" );
        return;
    }
    for ( i = 0; i < 3; ++i ) {
        trap_Argv( i + 1, buffer, sizeof(buffer) );
        center[i] = atof(buffer);
    }
    trap_Argv( 4, buffer, sizeof(buffer) );
    radius = atof(buffer);
    if ( radius <= 0.0f )
        radius = 1024.0f;
    radiusSq = radius * radius;

    G_Printf( "TESTLAB_ENTITY_DUMP_BEGIN center=%.3f,%.3f,%.3f radius=%.3f numEntities=%d\\n",
        center[0], center[1], center[2], radius, level.num_entities );

    for ( i = 0; i < level.num_entities; ++i ) {
        gentity_t *e = &g_entities[i];
        vec3_t worldMins;
        vec3_t worldMaxs;
        float dx, dy, dz, pointDistSq;
        float aabbDistSq = 0.0f;
        const char *classname;
        const char *model;
        const char *model2;
        const char *targetname;
        int axis;

        if ( !e->inuse )
            continue;

        dx = e->r.currentOrigin[0] - center[0];
        dy = e->r.currentOrigin[1] - center[1];
        dz = e->r.currentOrigin[2] - center[2];
        pointDistSq = dx*dx + dy*dy + dz*dz;

        for ( axis = 0; axis < 3; ++axis ) {
            float d = 0.0f;
            worldMins[axis] = e->r.currentOrigin[axis] + e->r.mins[axis];
            worldMaxs[axis] = e->r.currentOrigin[axis] + e->r.maxs[axis];
            if ( worldMins[axis] > worldMaxs[axis] ) {
                float t = worldMins[axis];
                worldMins[axis] = worldMaxs[axis];
                worldMaxs[axis] = t;
            }
            if ( center[axis] < worldMins[axis] )
                d = worldMins[axis] - center[axis];
            else if ( center[axis] > worldMaxs[axis] )
                d = center[axis] - worldMaxs[axis];
            aabbDistSq += d * d;
        }
        if ( aabbDistSq > radiusSq )
            continue;

        classname = e->classname ? e->classname : "<null>";
        model = e->model ? e->model : "<null>";
        model2 = e->model2 ? e->model2 : "<null>";
        targetname = e->targetname ? e->targetname : "<null>";

        G_Printf(
            "TESTLAB_ENTITY entity=%d class=%s model=%s model2=%s target=%s origin=%.3f,%.3f,%.3f mins=%.3f,%.3f,%.3f maxs=%.3f,%.3f,%.3f worldmins=%.3f,%.3f,%.3f worldmaxs=%.3f,%.3f,%.3f isProp=%d physics=%d eType=%d modelindex=%d dist2=%.3f aabbDist2=%.3f\\n",
            i, classname, model, model2, targetname,
            e->r.currentOrigin[0], e->r.currentOrigin[1], e->r.currentOrigin[2],
            e->r.mins[0], e->r.mins[1], e->r.mins[2],
            e->r.maxs[0], e->r.maxs[1], e->r.maxs[2],
            worldMins[0], worldMins[1], worldMins[2],
            worldMaxs[0], worldMaxs[1], worldMaxs[2],
            e->isProp ? 1 : 0, e->physicsObject ? 1 : 0,
            e->s.eType, e->s.modelindex, pointDistSq, aabbDistSq );
    }

    G_Printf( "TESTLAB_ENTITY_DUMP_END\\n" );
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
\t} else if ( Q_stricmp( cmd, "dw_testViewState" ) == 0 )  { // DARKWOLF_TESTLAB_V0_1
\t\tCmd_DWTestViewState_f( ent );
\t} else if ( Q_stricmp( cmd, "dw_testEntityDump" ) == 0 )  { // DARKWOLF_TESTLAB_V0_1
\t\tCmd_DWTestEntityDump_f( ent );
\t} else if ( Q_stricmp( cmd, "setviewpos" ) == 0 )  {
\t\tCmd_SetViewpos_f( ent );'''
one(g_cmds,dispatch,dispatch_new,"dw_testView dispatch")

print("DARKWOLF_TESTLAB_V0_1 instrumentation applied")
