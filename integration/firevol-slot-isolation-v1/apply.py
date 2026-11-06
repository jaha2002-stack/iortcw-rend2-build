#!/usr/bin/env python3
from pathlib import Path
import re, sys

root=Path(sys.argv[1])
backend=root/"tr_backend.c"
init=root/"tr_init.c"

b=backend.read_text()
i=init.read_text()

# 1) Backend: diagnostic cvar is lazy/non-archived and affects render only.
old='''static void RB_VolumetricFireV07(FBO_t *srcFbo, ivec4_t srcBox)
{
	static int lastDiagMs = 0;
	static int lastResidencyDiagMs = 0;
	static int lastFixtureV3DiagMs = 0;
	static int lastContinuityV4DiagMs = 0;
	static int lastFlashFixDiagMs = 0;
'''
new='''static void RB_VolumetricFireV07(FBO_t *srcFbo, ivec4_t srcBox)
{
	static int lastDiagMs = 0;
	static int lastResidencyDiagMs = 0;
	static int lastFixtureV3DiagMs = 0;
	static int lastContinuityV4DiagMs = 0;
	static int lastFlashFixDiagMs = 0;
	static int lastSoloDiagMs = 0;
	static cvar_t *s_rDwFireVolSolo = NULL; // DARKWOLF_FIREVOL_SLOT_ISOLATION_V1, -1=production/all, 0..7=one selected slot
'''
if old not in b:
    raise SystemExit("backend function header anchor not found")
b=b.replace(old,new,1)

old='''	int renderedCount = 0, greenMarkers = 0;
	int flashFixNormalized = 0, flashFixCacheMissBlocked = 0, flashFixCacheFade = 0;
'''
new='''	int renderedCount = 0, greenMarkers = 0;
	int flashFixNormalized = 0, flashFixCacheMissBlocked = 0, flashFixCacheFade = 0;
	int soloSlot = -1;
'''
if old not in b:
    raise SystemExit("backend counter anchor not found")
b=b.replace(old,new,1)

old='''	qboolean captureFresh = s_fireV07CaptureValid &&
'''
new='''	if (!s_rDwFireVolSolo)
		s_rDwFireVolSolo = ri.Cvar_Get("r_dwFireVolSolo", "-1", 0);
	if (s_rDwFireVolSolo && s_rDwFireVolSolo->integer >= 0 && s_rDwFireVolSolo->integer < FIREVOL081_RENDER_CAP)
		soloSlot = s_rDwFireVolSolo->integer;

	qboolean captureFresh = s_fireV07CaptureValid &&
'''
if old not in b:
    raise SystemExit("backend captureFresh anchor not found")
b=b.replace(old,new,1)

old='''		float flashEnergyScale = 1.0f;
		float effectiveSourceWeight;
		if (!sel->latchValid)
'''
new='''		float flashEnergyScale = 1.0f;
		float effectiveSourceWeight;

		// DARKWOLF_FIREVOL_SLOT_ISOLATION_V1:
		// Render-only gate. The complete Production selected[] set, residency,
		// owner de-dup, cache and priority logic have already run unchanged.
		if (soloSlot >= 0 && i != soloSlot)
			continue;

		if (!sel->latchValid)
'''
if old not in b:
    raise SystemExit("backend render-loop gate anchor not found")
b=b.replace(old,new,1)

old='''	}

	if (r_dwFireVolFlashDiag && r_dwFireVolFlashDiag->integer &&
'''
new='''	}

	// DARKWOLF_FIREVOL_SLOT_ISOLATION_V1: compact owner proof for the selected index.
	if (soloSlot >= 0 && (lastSoloDiagMs == 0 || nowMs - lastSoloDiagMs >= 500))
	{
		if (soloSlot < selectedCount)
		{
			fireVolumetricV07Selection_t *sv = &selected[soloSlot];
			fireVolumetricV07PoolSlot_t *pp =
				(sv->poolSlot >= 0 && sv->poolSlot < FIREVOL07_MAX_POOL) ? &s_fireV07Pool[sv->poolSlot] : NULL;
			if (pp)
			{
				ri.Printf(PRINT_ALL,
					"FIREVOL_SLOT_ISOLATION map=%s solo=%d selected=%d rendered=%d pool=%d surface=%d primitive=%d entity=%d sourceClass=%d synthetic=%d iflcPriority=%d origin=%.1f,%.1f,%.1f geometryRadius=%.1f shadowSlot=%d dlightIndex=%d\\n",
					tr.world ? tr.world->baseName : "<none>", soloSlot, selectedCount, renderedCount,
					sv->poolSlot, pp->latchedFlameSurface, pp->latchedPrimitive, pp->latchedEntityNum,
					pp->sourceClass, sv->syntheticVolumeOnly ? 1 : 0, pp->fireV4IFLCPriority ? 1 : 0,
					pp->latchedFlameOrigin[0], pp->latchedFlameOrigin[1], pp->latchedFlameOrigin[2],
					pp->radiusStateValid ? pp->radiusStateValue : 0.0f, sv->shadowSlot, sv->dlightIndex);
			}
			else
			{
				ri.Printf(PRINT_ALL,
					"FIREVOL_SLOT_ISOLATION map=%s solo=%d selected=%d rendered=%d pool=INVALID\\n",
					tr.world ? tr.world->baseName : "<none>", soloSlot, selectedCount, renderedCount);
			}
		}
		else
		{
			ri.Printf(PRINT_ALL,
				"FIREVOL_SLOT_ISOLATION map=%s solo=%d selected=%d rendered=%d status=UNAVAILABLE\\n",
				tr.world ? tr.world->baseName : "<none>", soloSlot, selectedCount, renderedCount);
		}
		lastSoloDiagMs = nowMs;
	}

	if (r_dwFireVolFlashDiag && r_dwFireVolFlashDiag->integer &&
'''
if old not in b:
    raise SystemExit("backend post-render telemetry anchor not found")
b=b.replace(old,new,1)

backend.write_text(b)

# 2) Renderer console command. No archived state; -1 restores exact Production behavior.
handler=r'''
// DARKWOLF_FIREVOL_SLOT_ISOLATION_V1: diagnostic-only render isolation.
// -1 = normal Production (all selected FireVol); 0..7 = render only that selected index.
static void R_FireVolSolo_f( void )
{
	int slot;
	cvar_t *solo = ri.Cvar_Get( "r_dwFireVolSolo", "-1", 0 );

	if ( ri.Cmd_Argc() != 2 )
	{
		ri.Printf( PRINT_ALL,
			"dw_fv_solo: current=%d  usage: /dw_fv_solo -1|0..7  (-1 = normal Production)\n",
			solo ? solo->integer : -1 );
		return;
	}

	slot = atoi( ri.Cmd_Argv( 1 ) );
	if ( slot < -1 || slot > 7 )
	{
		ri.Printf( PRINT_ALL, "dw_fv_solo: invalid slot %d; expected -1..7\n", slot );
		return;
	}

	ri.Cvar_Set( "r_dwFireVolSolo", va( "%d", slot ) );
	if ( slot >= 0 )
	{
		// Metadata only. These diagnostics do not alter FireVol ownership or selection.
		ri.Cvar_Set( "r_dwFireVolContinuityDiag", "1" );
		ri.Cvar_Set( "r_dwFireVolFixtureDiag", "1" );
	}

	ri.Printf( PRINT_ALL,
		"FIREVOL_SLOT_ISOLATION_COMMAND solo=%d mode=%s\n",
		slot, slot < 0 ? "PRODUCTION_ALL" : "ONE_SELECTED_SLOT" );
}

'''
m=re.search(r'(?m)^(?:static\s+)?void\s+R_Register\s*\(\s*void\s*\)\s*\{',i)
if not m:
    raise SystemExit("R_Register function anchor not found")
i=i[:m.start()]+handler+i[m.start():]

old='''	ri.Cmd_AddCommand( "dw_fl_list", R_IFLC_List_f );
	ri.Cmd_AddCommand( "dw_el_select", R_ELSS_Select_f );
'''
new='''	ri.Cmd_AddCommand( "dw_fl_list", R_IFLC_List_f );
	// DARKWOLF_FIREVOL_SLOT_ISOLATION_V1 diagnostic command.
	ri.Cmd_AddCommand( "dw_fv_solo", R_FireVolSolo_f );
	ri.Cmd_AddCommand( "dw_el_select", R_ELSS_Select_f );
'''
if old not in i:
    raise SystemExit("command registration anchor not found")
i=i.replace(old,new,1)

old='''	ri.Cmd_RemoveCommand( "dw_fl_list" );
	ri.Cmd_RemoveCommand( "dw_el_select" );
'''
new='''	ri.Cmd_RemoveCommand( "dw_fl_list" );
	ri.Cmd_RemoveCommand( "dw_fv_solo" );
	ri.Cmd_RemoveCommand( "dw_el_select" );
'''
if old not in i:
    raise SystemExit("command removal anchor not found")
i=i.replace(old,new,1)

init.write_text(i)

print("PASS FireVol Slot Isolation V1 patch")
