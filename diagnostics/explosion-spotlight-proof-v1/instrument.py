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
anchor="""\tlevel.time = levelTime;
"""
insert="""\tlevel.time = levelTime;

\t// DARKWOLF_EXPLOSION_SPOTLIGHT_PROOF_TESTLAB_V1
\t// Diagnostic-only autonomous proof. No production behavior uses this block.
\t{
\t\tstatic int dwProofMask = 0;
\t\tchar dwMap[MAX_QPATH];
\t\tint dwElapsed = level.time - level.startTime;
\t\tgentity_t *dwEnt;
\t\tgentity_t *dwPlayer = AICast_FindEntityForName( "player" );
\t\ttrap_Cvar_VariableStringBuffer( "mapname", dwMap, sizeof(dwMap) );

\t\t// Keep Dam spotlights visible to cgame during the diagnostic alive/dead proof.
\t\tif ( !Q_stricmp(dwMap,"dam") ) {
\t\t\tfor ( dwEnt = g_entities; dwEnt < &g_entities[level.num_entities]; ++dwEnt )
\t\t\t\tif ( dwEnt->inuse && dwEnt->s.eType == ET_SPOTLIGHT_EF )
\t\t\t\t\tdwEnt->r.svFlags |= SVF_BROADCAST;
\t\t}

\t\tif ( !Q_stricmp(dwMap,"swf") && dwElapsed > 4000 && !(dwProofMask & 1) ) {
\t\t\tdwProofMask |= 1;
\t\t\tG_Printf("DWPROOF_SERVER_BEGIN map=swf kind=gas\\n");
\t\t\tfor ( dwEnt = g_entities; dwEnt < &g_entities[level.num_entities]; ++dwEnt ) {
\t\t\t\tif ( dwEnt->inuse && dwEnt->classname && !Q_stricmp(dwEnt->classname,"func_explosive") && dwEnt->die ) {
\t\t\t\t\tvec3_t dwCenter;
\t\t\t\t\tVectorAdd(dwEnt->r.absmin, dwEnt->r.absmax, dwCenter);
\t\t\t\t\tVectorScale(dwCenter, 0.5f, dwCenter);
\t\t\t\t\tif ( fabs(dwCenter[0] - 2370.5f) < 80.0f && fabs(dwCenter[1] + 64.0f) < 80.0f && fabs(dwCenter[2] - 557.0f) < 80.0f ) {
\t\t\t\t\t\tG_Printf("DWPROOF_SERVER_ENTITY kind=gas entity=%d model=%s modelindex=%d center=%.1f,%.1f,%.1f absmin=%.1f,%.1f,%.1f absmax=%.1f,%.1f,%.1f damage=%d key=%d\\n",
\t\t\t\t\t\t\tdwEnt->s.number,dwEnt->model?dwEnt->model:"<null>",dwEnt->s.modelindex,
\t\t\t\t\t\t\tdwCenter[0],dwCenter[1],dwCenter[2],
\t\t\t\t\t\t\tdwEnt->r.absmin[0],dwEnt->r.absmin[1],dwEnt->r.absmin[2],
\t\t\t\t\t\t\tdwEnt->r.absmax[0],dwEnt->r.absmax[1],dwEnt->r.absmax[2],dwEnt->damage,dwEnt->key);
\t\t\t\t\t\tdwEnt->die(dwEnt,dwPlayer?dwPlayer:dwEnt,dwPlayer?dwPlayer:dwEnt,dwEnt->health+100,MOD_MACHINEGUN);
\t\t\t\t\t\tbreak;
\t\t\t\t\t}
\t\t\t\t}
\t\t\t}
\t\t}
\t\tif ( !Q_stricmp(dwMap,"swf") && dwElapsed > 6000 && !(dwProofMask & 2) && dwPlayer ) {
\t\t\tgentity_t *ev;
\t\t\tdwProofMask |= 2;
\t\t\tev = G_TempEntity(dwPlayer->r.currentOrigin, EV_EFFECT);
\t\t\tev->s.eventParm = 0; ev->s.time2 = 0x44575244;
\t\t\tG_Printf("DWPROOF_SERVER_ENTITY kind=radio_profile semantic_marker=0x%x\\n",ev->s.time2);
\t\t}
\t\tif ( !Q_stricmp(dwMap,"swf") && dwElapsed > 8000 && !(dwProofMask & 4) && dwPlayer ) {
\t\t\tgentity_t *ev;
\t\t\tdwProofMask |= 4;
\t\t\tev = G_TempEntity(dwPlayer->r.currentOrigin, EV_EFFECT);
\t\t\tev->s.eventParm = 0; ev->s.time2 = 0x44574D45;
\t\t\tG_Printf("DWPROOF_SERVER_ENTITY kind=me109_profile semantic_marker=0x%x\\n",ev->s.time2);
\t\t}
\t\tif ( !Q_stricmp(dwMap,"rocket") && dwElapsed > 4000 && !(dwProofMask & 8) ) {
\t\t\tdwProofMask |= 8;
\t\t\tG_Printf("DWPROOF_SERVER_BEGIN map=rocket kind=v2\\n");
\t\t\tfor ( dwEnt = g_entities; dwEnt < &g_entities[level.num_entities]; ++dwEnt ) {
\t\t\t\tif ( dwEnt->inuse && dwEnt->classname && dwEnt->target &&
\t\t\t\t\t !Q_stricmp(dwEnt->classname,"target_kill") && !Q_stricmp(dwEnt->target,"v2_rocket") && dwEnt->use ) {
\t\t\t\t\tG_Printf("DWPROOF_SERVER_ENTITY kind=v2 entity=%d target=%s\\n",dwEnt->s.number,dwEnt->target);
\t\t\t\t\tdwEnt->use(dwEnt,dwPlayer?dwPlayer:dwEnt,dwPlayer?dwPlayer:dwEnt);
\t\t\t\t\tbreak;
\t\t\t\t}
\t\t\t}
\t\t}
\t\tif ( !Q_stricmp(dwMap,"rocket") && dwElapsed > 7000 && !(dwProofMask & 16) ) {
\t\t\tdwProofMask |= 16;
\t\t\tfor ( dwEnt = g_entities; dwEnt < &g_entities[level.num_entities]; ++dwEnt ) {
\t\t\t\tif ( dwEnt->inuse && dwEnt->classname && !Q_stricmp(dwEnt->classname,"alarm_box") && dwEnt->die ) {
\t\t\t\t\tG_Printf("DWPROOF_SERVER_ENTITY kind=alarm entity=%d origin=%.1f,%.1f,%.1f\\n",
\t\t\t\t\t\tdwEnt->s.number,dwEnt->r.currentOrigin[0],dwEnt->r.currentOrigin[1],dwEnt->r.currentOrigin[2]);
\t\t\t\t\tdwEnt->die(dwEnt,dwPlayer?dwPlayer:dwEnt,dwPlayer?dwPlayer:dwEnt,dwEnt->health+100,MOD_MACHINEGUN);
\t\t\t\t\tbreak;
\t\t\t\t}
\t\t\t}
\t\t}
\t\tif ( !Q_stricmp(dwMap,"dam") && dwElapsed > 4000 && !(dwProofMask & 32) ) {
\t\t\tdwProofMask |= 32;
\t\t\tfor ( dwEnt = g_entities; dwEnt < &g_entities[level.num_entities]; ++dwEnt ) {
\t\t\t\tif ( dwEnt->inuse && dwEnt->s.eType == ET_SPOTLIGHT_EF && dwEnt->die ) {
\t\t\t\t\tG_Printf("DWPROOF_SERVER_ENTITY kind=spotlight entity=%d frame_before=%d\\n",dwEnt->s.number,dwEnt->s.frame);
\t\t\t\t\tdwEnt->die(dwEnt,dwPlayer?dwPlayer:dwEnt,dwPlayer?dwPlayer:dwEnt,100,MOD_MACHINEGUN);
\t\t\t\t\tG_Printf("DWPROOF_SERVER_SPOTLIGHT_DEAD entity=%d frame_after=%d\\n",dwEnt->s.number,dwEnt->s.frame);
\t\t\t\t\tbreak;
\t\t\t\t}
\t\t\t}
\t\t}
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
print("instrumented explosion/spotlight proof v1")
