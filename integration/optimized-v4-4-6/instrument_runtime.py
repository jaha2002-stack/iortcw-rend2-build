#!/usr/bin/env python3
"""Diagnostic-only capture after real gameplay frames, never used in Win64 binaries."""
from pathlib import Path
import sys
src=Path(sys.argv[1])/'SP/code/cgame'
def replace(path,old,new):
 text=path.read_text()
 assert text.count(old)==1,(path,old)
 path.write_text(text.replace(old,new))
replace(src/'cg_servercmds.c',
 'CG_Printf( "TESTLAB_GAMEPLAY_START requested=1\\n" );',
 'trap_Cvar_Set( "dw_testlabGameplayStarted", "1" );\n\t\t\tCG_Printf( "TESTLAB_GAMEPLAY_START requested=1\\n" );')
replace(src/'cg_view.c','\tCG_DrawActive( stereoView );',r'''	CG_DrawActive( stereoView );
	/* Diagnostic copy only. Loading/briefing redraws do not reach this point.
	 * Wait for stock playerstart, 32 gameplay scenes, warmup and completed fades. */
	{
		static int testlabRenderedFrames, testlabFirstTime;
		static qboolean testlabCaptureQueued;
		char testlabStarted[16], testlabCapture[64], testlabScenario[64];
		trap_Cvar_VariableStringBuffer( "dw_testlabGameplayStarted", testlabStarted, sizeof(testlabStarted) );
		trap_Cvar_VariableStringBuffer( "dw_testlabSmokeCapture", testlabCapture, sizeof(testlabCapture) );
		trap_Cvar_VariableStringBuffer( "dw_testlabScenario", testlabScenario, sizeof(testlabScenario) );
		if ( atoi(testlabStarted) && testlabCapture[0] && !testlabCaptureQueued && stereoView != STEREO_RIGHT ) {
			if (!testlabRenderedFrames) testlabFirstTime = cg.time;
			testlabRenderedFrames++;
			if (testlabRenderedFrames == 32)
				CG_Printf("TESTLAB_CAPTURE_WAIT time=%d viewFade=%.4f scriptFade=%.4f fadeRate=%.4f\n", cg.time, cg.viewFade, cgs.scrFadeAlphaCurrent, cg.fadeRate);
			if ( testlabRenderedFrames >= 32 && cg.time - testlabFirstTime >= 6000 && !cg.fadeRate && cg.viewFade <= 0.001f && cgs.scrFadeAlphaCurrent <= 0.001f ) {
				testlabCaptureQueued = qtrue;
				CG_Printf( "TESTLAB_CAPTURE_READY frames=%d fadeRate=0 viewFade=0 scriptFade=0 time=%d origin=%.3f,%.3f,%.3f\n",
					testlabRenderedFrames, cg.time, cg.refdef.vieworg[0], cg.refdef.vieworg[1], cg.refdef.vieworg[2] );
				if (testlabScenario[0])
					trap_SendConsoleCommand( va("exec %s\n", testlabScenario) );
				else
					trap_SendConsoleCommand( va("viewpos\nscreenshot %s\nwait 5\nquit\n", testlabCapture) );
			}
		}
	}''')
print('DIAGNOSTIC_GAMEPLAY_CAPTURE_INSTRUMENTED')

# The historical diagnostic refers to the removed production report counter.
# Derive its identical emission delta locally, on BOTH diagnostic variants.
scene=Path(sys.argv[1])/'SP/code/rend2/tr_scene.c'
replace(scene, '\tif (enable)\n\t{\n\t\tif (manualOverride)',
        '\tint testlabAddedStart = r_numdlights;\n\tif (enable)\n\t{\n\t\tif (manualOverride)')
replace(scene, 'enable, maxLights, selectedCount, activeCount,',
        'enable, maxLights, selectedCount, r_numdlights - testlabAddedStart,')
