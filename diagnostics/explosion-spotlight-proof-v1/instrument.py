#!/usr/bin/env python3
from pathlib import Path
import sys

root=Path(sys.argv[1])
gmain=root/"SP/code/game/g_main.c"
cgevent=root/"SP/code/cgame/cg_event.c"
cgents=root/"SP/code/cgame/cg_ents.c"
trscene=root/"SP/code/rend2/tr_scene.c"
svmain=root/"SP/code/server/sv_main.c"
uimain=root/"SP/code/ui/ui_main.c"

def once(s,a,b,label):
    n=s.count(a)
    if n!=1:
        raise SystemExit(f"{label}: expected 1 anchor, got {n}")
    return s.replace(a,b,1)

# Server-side deterministic proof trigger. It is diagnostic-only and gated by cvars.
s=gmain.read_text()
anchor="""\tlevel.time = levelTime;
"""
insert="""\tlevel.time = levelTime;

\t// DARKWOLF_EXPLOSION_SPOTLIGHT_PROOF_TESTLAB_V1
\t// Diagnostic-only explicit runtime trigger. Production never contains this block.
\t{
\t\tstatic int dwHeartbeat = 0;
\t\tstatic int dwLastFire = 0;
\t\tchar dwMap[MAX_QPATH];
\t\tint dwMode = trap_Cvar_VariableIntegerValue( "dw_explosionProofMode" );
\t\tint dwFire = trap_Cvar_VariableIntegerValue( "dw_explosionProofFire" );
\t\tgentity_t *dwEnt;
\t\tgentity_t *dwPlayer = AICast_FindEntityForName( "player" );
\t\ttrap_Cvar_VariableStringBuffer( "mapname", dwMap, sizeof(dwMap) );

\t\tif ( !dwHeartbeat ) {
\t\t\tdwHeartbeat = 1;
\t\t\tG_Printf("DWPROOF_SERVER_HEARTBEAT map=%s frame=%d levelTime=%d entities=%d\\n",
\t\t\t\tdwMap, level.framenum, level.time, level.num_entities);
\t\t}

\t\t// Keep Dam spotlight entities visible to cgame for alive/dead LocalVol proof.
\t\tif ( dwMode == 4 ) {
\t\t\tfor ( dwEnt = g_entities; dwEnt < &g_entities[level.num_entities]; ++dwEnt )
\t\t\t\tif ( dwEnt->inuse && dwEnt->s.eType == ET_SPOTLIGHT_EF )
\t\t\t\t\tdwEnt->r.svFlags |= SVF_BROADCAST;
\t\t}

\t\tif ( dwFire && !dwLastFire ) {
\t\t\tG_Printf("DWPROOF_SERVER_TRIGGER map=%s mode=%d frame=%d\\n",dwMap,dwMode,level.framenum);

\t\t\tif ( dwMode == 1 ) {
\t\t\t\tfor ( dwEnt = g_entities; dwEnt < &g_entities[level.num_entities]; ++dwEnt ) {
\t\t\t\t\tif ( dwEnt->inuse && dwEnt->classname && dwEnt->model &&
\t\t\t\t\t\t !Q_stricmp(dwEnt->classname,"func_explosive") && !Q_stricmp(dwEnt->model,"*90") && dwEnt->die ) {
\t\t\t\t\t\tG_Printf("DWPROOF_SERVER_ENTITY kind=gas entity=%d model=%s modelindex=%d damage=%d key=%d\\n",
\t\t\t\t\t\t\tdwEnt->s.number,dwEnt->model,dwEnt->s.modelindex,dwEnt->damage,dwEnt->key);
\t\t\t\t\t\tdwEnt->die(dwEnt,dwPlayer?dwPlayer:dwEnt,dwPlayer?dwPlayer:dwEnt,dwEnt->health+100,MOD_MACHINEGUN);
\t\t\t\t\t\tbreak;
\t\t\t\t\t}
\t\t\t\t}
\t\t\t} else if ( dwMode == 2 ) {
\t\t\t\tfor ( dwEnt = g_entities; dwEnt < &g_entities[level.num_entities]; ++dwEnt ) {
\t\t\t\t\tif ( dwEnt->inuse && dwEnt->classname && dwEnt->target &&
\t\t\t\t\t\t !Q_stricmp(dwEnt->classname,"target_kill") && !Q_stricmp(dwEnt->target,"v2_rocket") && dwEnt->use ) {
\t\t\t\t\t\tG_Printf("DWPROOF_SERVER_ENTITY kind=v2 entity=%d target=%s\\n",dwEnt->s.number,dwEnt->target);
\t\t\t\t\t\tdwEnt->use(dwEnt,dwPlayer?dwPlayer:dwEnt,dwPlayer?dwPlayer:dwEnt);
\t\t\t\t\t\tbreak;
\t\t\t\t\t}
\t\t\t\t}
\t\t\t} else if ( dwMode == 3 ) {
\t\t\t\tfor ( dwEnt = g_entities; dwEnt < &g_entities[level.num_entities]; ++dwEnt ) {
\t\t\t\t\tif ( dwEnt->inuse && dwEnt->classname && !Q_stricmp(dwEnt->classname,"alarm_box") && dwEnt->die ) {
\t\t\t\t\t\tG_Printf("DWPROOF_SERVER_ENTITY kind=alarm entity=%d origin=%.1f,%.1f,%.1f\\n",
\t\t\t\t\t\t\tdwEnt->s.number,dwEnt->r.currentOrigin[0],dwEnt->r.currentOrigin[1],dwEnt->r.currentOrigin[2]);
\t\t\t\t\t\tdwEnt->die(dwEnt,dwPlayer?dwPlayer:dwEnt,dwPlayer?dwPlayer:dwEnt,dwEnt->health+100,MOD_MACHINEGUN);
\t\t\t\t\t\tbreak;
\t\t\t\t\t}
\t\t\t\t}
\t\t\t} else if ( dwMode == 4 ) {
\t\t\t\tfor ( dwEnt = g_entities; dwEnt < &g_entities[level.num_entities]; ++dwEnt ) {
\t\t\t\t\tif ( dwEnt->inuse && dwEnt->s.eType == ET_SPOTLIGHT_EF && dwEnt->die ) {
\t\t\t\t\t\tG_Printf("DWPROOF_SERVER_ENTITY kind=spotlight entity=%d frame_before=%d\\n",dwEnt->s.number,dwEnt->s.frame);
\t\t\t\t\t\tdwEnt->die(dwEnt,dwPlayer?dwPlayer:dwEnt,dwPlayer?dwPlayer:dwEnt,100,MOD_MACHINEGUN);
\t\t\t\t\t\tG_Printf("DWPROOF_SERVER_SPOTLIGHT_DEAD entity=%d frame_after=%d\\n",dwEnt->s.number,dwEnt->s.frame);
\t\t\t\t\t\tbreak;
\t\t\t\t\t}
\t\t\t\t}
\t\t\t} else if ( dwMode == 5 && dwPlayer ) {
\t\t\t\tgentity_t *ev = G_TempEntity(dwPlayer->r.currentOrigin, EV_EFFECT);
\t\t\t\tev->s.eventParm = 0;
\t\t\t\tev->s.time2 = 0x44575244;
\t\t\t\tG_Printf("DWPROOF_SERVER_ENTITY kind=radio_profile semantic_marker=0x%x\\n",ev->s.time2);
\t\t\t} else if ( dwMode == 6 && dwPlayer ) {
\t\t\t\tgentity_t *ev = G_TempEntity(dwPlayer->r.currentOrigin, EV_EFFECT);
\t\t\t\tev->s.eventParm = 0;
\t\t\t\tev->s.time2 = 0x44574D45;
\t\t\t\tG_Printf("DWPROOF_SERVER_ENTITY kind=me109_profile semantic_marker=0x%x\\n",ev->s.time2);
\t\t\t}
\t\t}
\t\tdwLastFire = dwFire;
\t}

"""
runframe = s.index("void G_RunFrame( int levelTime ) {")
idx = s.index(anchor, runframe)
s = s[:idx] + insert + s[idx + len(anchor):]
gmain.write_text(s)

# cgame proof: event marker -> LE_EXPLOSION profile.
s=cgevent.read_text()
fn=s.index("static void CG_SpawnDarkWolfPropBlastDlight")
needle="\tle->lightColor[2] = blue;"
idx=s.index(needle,fn)+len(needle)
s=s[:idx]+"""\n\tCG_Printf("DWPROOF_CGAME_BLAST profile=%d leType=%d peak=%.1f floor=%.1f hold=%d total=%d origin=%.1f,%.1f,%.1f\\n",
\t\tprofile, le->leType, peak, floorRadius, holdMs, totalMs, origin[0], origin[1], origin[2]);"""+s[idx:]
cgevent.write_text(s)

# Spotlight proof of alive submit vs dead suppression.
s=cgents.read_text()
old="""\t\t\tif (cent->currentState.frame != 1 && localVolEnabled[0] == '1')
\t\t\t{
"""
new="""\t\t\tif (cent->currentState.frame != 1 && localVolEnabled[0] == '1')
\t\t\t{
\t\t\t\tstatic int dwSpotAliveLogged[MAX_GENTITIES];
\t\t\t\tif (!dwSpotAliveLogged[cent->currentState.number]) {
\t\t\t\t\tCG_Printf("DWPROOF_SPOTLIGHT_ALIVE_SUBMIT entity=%d frame=%d\\n", cent->currentState.number, cent->currentState.frame);
\t\t\t\t\tdwSpotAliveLogged[cent->currentState.number] = 1;
\t\t\t\t}
"""
s=once(s,old,new,"spot alive")
anchor="""\t\t\t\ttrap_R_AddLightToScene(cent->currentState.origin, 4096.0f,
\t\t\t\t\t(normalized_direction[0] + 1.0f) * 0.5f,
"""
# Don't alter actual call; add suppression telemetry before gate by expanding preceding cvar area.
old2="""\t\t\ttrap_Cvar_VariableStringBuffer("r_volumetricLocal", localVolEnabled, sizeof(localVolEnabled));
\t\t\t// DARKWOLF_SPOTLIGHT_DEATH_LOCALVOL_SYNC_V445
"""
new2="""\t\t\ttrap_Cvar_VariableStringBuffer("r_volumetricLocal", localVolEnabled, sizeof(localVolEnabled));
\t\t\tif (cent->currentState.frame == 1 && localVolEnabled[0] == '1') {
\t\t\t\tstatic int dwSpotDeadLogged[MAX_GENTITIES];
\t\t\t\tif (!dwSpotDeadLogged[cent->currentState.number]) {
\t\t\t\t\tCG_Printf("DWPROOF_SPOTLIGHT_DEAD_SUPPRESS entity=%d frame=%d\\n", cent->currentState.number, cent->currentState.frame);
\t\t\t\t\tdwSpotDeadLogged[cent->currentState.number] = 1;
\t\t\t\t}
\t\t\t}
\t\t\t// DARKWOLF_SPOTLIGHT_DEATH_LOCALVOL_SYNC_V445
"""
s=once(s,old2,new2,"spot dead")
cgents.write_text(s)

# Renderer proof: transient blast marker is accepted as a real dlight and classified.
s=trscene.read_text()
fn=s.index("void RE_AddLightToScene(")
needle="\tdl->transientBlast = transientBlastMarker; // DARKWOLF_GRENADE_DYNAMITE_EXPLOSION_DLIGHT_PRODUCTION_V1"
idx=s.index(needle,fn)+len(needle)
s=s[:idx]+"""\n\tif (transientBlastMarker) {
\t\tri.Printf(PRINT_ALL, "DWPROOF_RENDERER_DLIGHT transientBlast=1 index=%d radius=%.1f rgb=%.3f,%.3f,%.3f origin=%.1f,%.1f,%.1f\\n",
\t\t\tr_numdlights-1, intensity, r, g, b, org[0], org[1], org[2]);
\t}"""+s[idx:]
needle="\telse if (shadowSourceExplosionMarker || transientBlastMarker)\n\t\tdl->shadowSourceClass = DWSHADOW_SOURCE_TRANSIENT_EXPLOSION;"
idx=s.index(needle,fn)
rep="""\telse if (shadowSourceExplosionMarker || transientBlastMarker) {
\t\tdl->shadowSourceClass = DWSHADOW_SOURCE_TRANSIENT_EXPLOSION;
\t\tif (transientBlastMarker)
\t\t\tri.Printf(PRINT_ALL, "DWPROOF_RENDERER_CLASS transientBlast=1 class=%d\\n", dl->shadowSourceClass);
\t}"""
s=s[:idx]+rep+s[idx+len(needle):]
needle="\tif (overdraw & DARKWOLF_REF_LOCALVOL_SPOTLIGHT)\n\t{"
idx=s.index(needle,fn)+len(needle)
s=s[:idx]+"""\n\t\tri.Printf(PRINT_ALL, "DWPROOF_RENDERER_SPOT_LOCALVOL_ACCEPT origin=%.1f,%.1f,%.1f range=%.1f\\n", org[0],org[1],org[2],intensity);"""+s[idx:]
trscene.write_text(s)

# Headless SP TestLab otherwise remains paused after the first server frame.
# Bypass pause only when the explicit diagnostic cvar is enabled.
s=svmain.read_text()
old="""\t// allow pause if only the local client is connected
\tif ( SV_CheckPaused() ) {
\t\treturn;
\t}
"""
new="""\t// DARKWOLF_EXPLOSION_SPOTLIGHT_PROOF_TESTLAB_V1
\t// Let the headless diagnostic simulation advance; production keeps stock pause behavior.
\tif ( !Cvar_VariableIntegerValue("dw_explosionProofLab") && SV_CheckPaused() ) {
\t\treturn;
\t}
"""
s=once(s,old,new,"headless pause bypass")
svmain.write_text(s)

# Headless TestLab must enter the actual 3D game instead of remaining on the SP briefing page.
# This is diagnostic-only; production UI is untouched.
s=uimain.read_text()
old="""\t\tcase UIMENU_BRIEFING:
\t\t\tMenus_CloseAll();
\t\t\tMenus_ActivateByName( "briefing" );
\t\t\treturn;
"""
new="""\t\tcase UIMENU_BRIEFING:
\t\t\t// DARKWOLF_EXPLOSION_SPOTLIGHT_PROOF_TESTLAB_V1
\t\t\tif ( trap_Cvar_VariableValue( "dw_explosionProofLab" ) ) {
\t\t\t\ttrap_Key_SetCatcher( trap_Key_GetCatcher() & ~KEYCATCH_UI );
\t\t\t\ttrap_Key_ClearStates();
\t\t\t\ttrap_Cvar_Set( "cl_paused", "0" );
\t\t\t\tMenus_CloseAll();
\t\t\t\ttrap_Print( "DWPROOF_UI_BRIEFING_BYPASS\\n" );
\t\t\t\treturn;
\t\t\t}
\t\t\tMenus_CloseAll();
\t\t\tMenus_ActivateByName( "briefing" );
\t\t\treturn;
"""
s=once(s,old,new,"briefing bypass")
uimain.write_text(s)
print("instrumented explosion/spotlight proof v1")
