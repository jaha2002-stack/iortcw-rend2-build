#!/usr/bin/env python3
from pathlib import Path
import sys

root=Path(sys.argv[1])
gmain=root/"SP/code/game/g_main.c"
cgevent=root/"SP/code/cgame/cg_event.c"
cgents=root/"SP/code/cgame/cg_ents.c"
trscene=root/"SP/code/rend2/tr_scene.c"

def once(s,a,b,label):
    n=s.count(a)
    if n!=1:
        raise SystemExit(f"{label}: expected 1 anchor, got {n}")
    return s.replace(a,b,1)

# Server-side deterministic proof trigger. It is diagnostic-only and gated by cvars.
s=gmain.read_text()
anchor="""\tlevel.previousTime = level.time;
\tlevel.time = levelTime;

\t// Ridah, check for loading a save game
"""
insert="""\tlevel.previousTime = level.time;
\tlevel.time = levelTime;

\t// DARKWOLF_EXPLOSION_SPOTLIGHT_PROOF_TESTLAB_V1
\t// Diagnostic-only deterministic runtime trigger; production never contains this block.
\tif ( trap_Cvar_VariableIntegerValue( "dw_explosionProofLab" ) ) {
\t\tstatic int dwLastFire = 0;
\t\tint dwFire = trap_Cvar_VariableIntegerValue( "dw_explosionProofFire" );
\t\tif ( dwFire && !dwLastFire ) {
\t\t\tchar dwMap[MAX_QPATH];
\t\t\tint dwMode = trap_Cvar_VariableIntegerValue( "dw_explosionProofMode" );
\t\t\tgentity_t *dwEnt;
\t\t\tgentity_t *dwPlayer = AICast_FindEntityForName( "player" );
\t\t\ttrap_Cvar_VariableStringBuffer( "mapname", dwMap, sizeof(dwMap) );
\t\t\tG_Printf( "DWPROOF_SERVER_BEGIN map=%s mode=%d\\n", dwMap, dwMode );

\t\t\tif ( dwMode == 1 ) {
\t\t\t\tfor ( dwEnt = g_entities; dwEnt < &g_entities[level.num_entities]; ++dwEnt ) {
\t\t\t\t\tif ( dwEnt->inuse && dwEnt->classname && dwEnt->model &&
\t\t\t\t\t\t !Q_stricmp(dwEnt->classname,"func_explosive") && !Q_stricmp(dwEnt->model,"*90") && dwEnt->die ) {
\t\t\t\t\t\tG_Printf("DWPROOF_SERVER_ENTITY kind=gas entity=%d model=%s origin=%.1f,%.1f,%.1f\\n",
\t\t\t\t\t\t\tdwEnt->s.number,dwEnt->model,dwEnt->r.currentOrigin[0],dwEnt->r.currentOrigin[1],dwEnt->r.currentOrigin[2]);
\t\t\t\t\t\tdwEnt->die(dwEnt,dwPlayer?dwPlayer:dwEnt,dwPlayer?dwPlayer:dwEnt,dwEnt->health+100,MOD_MACHINEGUN);
\t\t\t\t\t\tbreak;
\t\t\t\t\t}
\t\t\t\t}
\t\t\t} else if ( dwMode == 2 ) {
\t\t\t\tfor ( dwEnt = g_entities; dwEnt < &g_entities[level.num_entities]; ++dwEnt ) {
\t\t\t\t\tif ( dwEnt->inuse && dwEnt->classname && dwEnt->target && !Q_stricmp(dwEnt->classname,"target_kill") &&
\t\t\t\t\t\t !Q_stricmp(dwEnt->target,"v2_rocket") && dwEnt->use ) {
\t\t\t\t\t\tG_Printf("DWPROOF_SERVER_ENTITY kind=v2 target=%s entity=%d\\n",dwEnt->target,dwEnt->s.number);
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
\t\t\t\t\t\tG_Printf("DWPROOF_SERVER_ENTITY kind=spotlight entity=%d frame_before=%d origin=%.1f,%.1f,%.1f\\n",
\t\t\t\t\t\t\tdwEnt->s.number,dwEnt->s.frame,dwEnt->r.currentOrigin[0],dwEnt->r.currentOrigin[1],dwEnt->r.currentOrigin[2]);
\t\t\t\t\t\tdwEnt->die(dwEnt,dwPlayer?dwPlayer:dwEnt,dwPlayer?dwPlayer:dwEnt,100,MOD_MACHINEGUN);
\t\t\t\t\t\tG_Printf("DWPROOF_SERVER_SPOTLIGHT_DEAD entity=%d frame_after=%d\\n",dwEnt->s.number,dwEnt->s.frame);
\t\t\t\t\t\tbreak;
\t\t\t\t\t}
\t\t\t\t}
\t\t\t} else if ( dwMode == 5 || dwMode == 6 ) {
\t\t\t\tif ( dwPlayer ) {
\t\t\t\t\tgentity_t *ev = G_TempEntity(dwPlayer->r.currentOrigin, EV_EFFECT);
\t\t\t\t\tev->s.eventParm = 0;
\t\t\t\t\tev->s.time2 = (dwMode == 5) ? 0x44575244 : 0x44574D45;
\t\t\t\t\tG_Printf("DWPROOF_SERVER_ENTITY kind=%s semantic_marker=0x%x origin=%.1f,%.1f,%.1f\\n",
\t\t\t\t\t\tdwMode==5?"radio_profile":"me109_profile",ev->s.time2,
\t\t\t\t\t\tdwPlayer->r.currentOrigin[0],dwPlayer->r.currentOrigin[1],dwPlayer->r.currentOrigin[2]);
\t\t\t\t}
\t\t\t}
\t\t\tG_Printf( "DWPROOF_SERVER_END map=%s mode=%d\\n", dwMap, dwMode );
\t\t}
\t\tdwLastFire = dwFire;
\t}

\t// Ridah, check for loading a save game
"""
s=once(s,anchor,insert,"g_main trigger")
gmain.write_text(s)

# cgame proof: event marker -> LE_EXPLOSION profile.
s=cgevent.read_text()
anchor="""\tle->light = peak;
\tle->lightColor[0] = red;
\tle->lightColor[1] = green;
\tle->lightColor[2] = blue;
}
"""
insert="""\tle->light = peak;
\tle->lightColor[0] = red;
\tle->lightColor[1] = green;
\tle->lightColor[2] = blue;
\tCG_Printf("DWPROOF_CGAME_BLAST profile=%d leType=%d peak=%.1f floor=%.1f hold=%d total=%d origin=%.1f,%.1f,%.1f\\n",
\t\tprofile, le->leType, peak, floorRadius, holdMs, totalMs, origin[0], origin[1], origin[2]);
}
"""
s=once(s,anchor,insert,"cg event spawn proof")
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
anchor="""\tdl->transientBlast = transientBlastMarker; // DARKWOLF_GRENADE_DYNAMITE_EXPLOSION_DLIGHT_PRODUCTION_V1
\tdl->noDlightShadow = fxNoDlightShadowMarker;
"""
insert="""\tdl->transientBlast = transientBlastMarker; // DARKWOLF_GRENADE_DYNAMITE_EXPLOSION_DLIGHT_PRODUCTION_V1
\tif (transientBlastMarker) {
\t\tri.Printf(PRINT_ALL, "DWPROOF_RENDERER_DLIGHT transientBlast=1 index=%d radius=%.1f rgb=%.3f,%.3f,%.3f origin=%.1f,%.1f,%.1f\\n",
\t\t\tr_numdlights-1, intensity, r, g, b, org[0], org[1], org[2]);
\t}
\tdl->noDlightShadow = fxNoDlightShadowMarker;
"""
s=once(s,anchor,insert,"renderer dlight accept")
anchor2="""\telse if (shadowSourceExplosionMarker || transientBlastMarker)
\t\tdl->shadowSourceClass = DWSHADOW_SOURCE_TRANSIENT_EXPLOSION;
"""
insert2="""\telse if (shadowSourceExplosionMarker || transientBlastMarker) {
\t\tdl->shadowSourceClass = DWSHADOW_SOURCE_TRANSIENT_EXPLOSION;
\t\tif (transientBlastMarker)
\t\t\tri.Printf(PRINT_ALL, "DWPROOF_RENDERER_CLASS transientBlast=1 class=%d\\n", dl->shadowSourceClass);
\t}
"""
s=once(s,anchor2,insert2,"renderer class")
# LocalVol acceptance proof.
anchor3="""\tif (overdraw & DARKWOLF_REF_LOCALVOL_SPOTLIGHT)
\t{
"""
insert3="""\tif (overdraw & DARKWOLF_REF_LOCALVOL_SPOTLIGHT)
\t{
\t\tri.Printf(PRINT_ALL, "DWPROOF_RENDERER_SPOT_LOCALVOL_ACCEPT origin=%.1f,%.1f,%.1f range=%.1f\\n", org[0],org[1],org[2],intensity);
"""
s=once(s,anchor3,insert3,"renderer spotlight")
trscene.write_text(s)
print("instrumented explosion/spotlight proof v1")
