#!/usr/bin/env python3
from pathlib import Path
import argparse

ap=argparse.ArgumentParser()
ap.add_argument("source")
args=ap.parse_args()
p=Path(args.source)/"SP/code/cgame/cg_servercmds.c"
s=p.read_text()
old='''	if ( !strcmp( cmd, "rockandroll" ) ) {   // map loaded, game is ready to begin.
		CG_Fade( 0, 0, 0, 255, cg.time, 0 );      // go black
		trap_UI_Popup( "pregame" );                // start pregame menu
		trap_Cvar_Set( "cg_norender", "1" );    // don't render the world until the player clicks in and the 'playerstart' func has been called (g_main in G_UpdateCvars() ~ilne 949)

		trap_S_FadeAllSound( 1.0f, 1000 );    // fade sound up

		return;
	}
'''
new='''	if ( !strcmp( cmd, "rockandroll" ) ) {   // map loaded, game is ready to begin.
		// DarkWolf TestLab only: emulate the retail pregame "Continue" action.
		// This patch is never packaged into production or the Win64 PBR candidate.
		CG_Fade( 0, 0, 0, 0, cg.time, 0 );
		trap_Cvar_Set( "cl_paused", "0" );
		trap_Cvar_Set( "cg_norender", "0" );
		trap_Cvar_Set( "g_playerstart", "1" );
		trap_S_FadeAllSound( 1.0f, 1000 );
		CG_Printf( "DW_PBR_TESTLAB_AUTOSTART playerstart=1 render=1\\n" );
		return;
	}
'''
if s.count(old)!=1:
    raise SystemExit(f"rockandroll block anchor count={s.count(old)}")
p.write_text(s.replace(old,new,1))

# Add a TestLab-only console command that terminates any active intro camera
# on both cgame and game sides immediately before material capture.
cp=Path(args.source)/"SP/code/cgame/cg_consolecmds.c"
cs=cp.read_text()
anchor='''	{ "camera", CG_Camera_f },   // duffy
	{ "fade", CG_Fade_f },   // duffy
'''
replacement='''	{ "camera", CG_Camera_f },   // duffy
	{ "fade", CG_Fade_f },   // duffy
	{ "dw_test_stopcamera", CG_StopCamera },
'''
if cs.count(anchor)!=1:
    raise SystemExit(f"console camera anchor count={cs.count(anchor)}")
cs=cs.replace(anchor,replacement,1)

start=cs.find("void CG_StartCamera( const char *name, qboolean startBlack ) {")
stop_marker="/*\n==============\nCG_StopCamera"
stop=cs.find(stop_marker,start)
if start < 0 or stop < 0:
    raise SystemExit(f"CG_StartCamera function anchors missing start={start} stop={stop}")
test_start='''void CG_StartCamera( const char *name, qboolean startBlack ) {
	// DarkWolf TestLab only: suppress map intro/cutscene cameras so scripted
	// material captures use the real player refdef after setviewpos.
	(void)name;
	(void)startBlack;
	cg.cameraMode = qfalse;
	trap_SendClientCommand( "stopCamera" );
	trap_stopCamera( CAM_PRIMARY );
	trap_Cvar_Set( "cg_letterbox", "0" );
	CG_Fade( 0, 0, 0, 0, cg.time, 0 );
	CG_Printf( "DW_PBR_TESTLAB_CAMERA_SUPPRESSED\\n" );
}

'''
cs=cs[:start]+test_start+cs[stop:]
cp.write_text(cs)

print("DW_PBR_TESTLAB_AUTOSTART_APPLIED stopcamera_command=1 suppress_startcamera=1")
