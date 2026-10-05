#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("source")
CG_EVENT = ROOT / "SP/code/cgame/cg_event.c"
G_PROPS = ROOT / "SP/code/game/g_props.c"
G_ALARM = ROOT / "SP/code/game/g_alarm.c"
G_TARGET = ROOT / "SP/code/game/g_target.c"
G_MOVER = ROOT / "SP/code/game/g_mover.c"

MARK = "DARKWOLF_EXPLOSION_COVERAGE_V446"

DW_GAS = "0x44574743"   # DWGC
DW_RADIO = "0x44575244" # DWRD
DW_V2 = "0x44575632"    # DWV2
DW_ALARM = "0x4457414C" # DWAL
DW_ME109 = "0x44574D45" # DWME


def once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"ERROR {label}: expected one anchor, found {n}")
    return text.replace(old, new, 1)


def require(text, markers, label):
    for m in markers:
        if m not in text:
            raise SystemExit(f"ERROR {label}: missing parent marker {m}")


cg = CG_EVENT.read_text(encoding="utf-8")
gp = G_PROPS.read_text(encoding="utf-8")
ga = G_ALARM.read_text(encoding="utf-8")
gt = G_TARGET.read_text(encoding="utf-8")
gm = G_MOVER.read_text(encoding="utf-8")

if MARK in cg:
    print(MARK + " already applied")
    raise SystemExit(0)

require(cg, [
    "DARKWOLF_EXPLOSIVE_PROPS_RADAR_TRANSIENT_DLIGHT_SHADOW_CLEAN_PRODUCTION_V1",
    "#define DARKWOLF_BARREL_BLAST_EVENT_MARKER 0x4457424C",
    "#define DARKWOLF_DAMAGE_PROP_BLAST_MARKER  0x44575046",
    "#define DARKWOLF_PROP_BLAST_PROFILE_SCRIPT_FIRE 3",
    "REF_FORCE_DLIGHT | DARKWOLF_REF_TRANSIENT_BLAST_DLIGHT",
], "cgame v4.4.5 blast contract")
require(gp, [
    "DARKWOLF_EXPLOSIVE_PROPS_RADAR_TRANSIENT_DLIGHT_SHADOW_CLEAN_PRODUCTION_V1",
    "void props_radio_die(",
    "void props_radio_dieSEVEN(",
    "void propExplosionLarge(",
], "g_props parent")
require(gm, [
    "DARKWOLF_EXPLOSIVE_PROPS_RADAR_TRANSIENT_DLIGHT_SHADOW_CLEAN_PRODUCTION_V1",
    "self->s.time2 = 0x44575046",
], "g_mover parent")
require(ga, ["void alarmExplosion( gentity_t *ent )"], "g_alarm parent")
require(gt, ["void target_kill_use( gentity_t *self, gentity_t *other, gentity_t *activator )"], "g_target parent")

# Extend only the existing light-only cgame profile dispatcher.
cg = once(cg,
"""#define DARKWOLF_PROP_BLAST_PROFILE_BARREL 1
#define DARKWOLF_PROP_BLAST_PROFILE_DAMAGE 2
#define DARKWOLF_PROP_BLAST_PROFILE_SCRIPT_FIRE 3
""",
"""#define DARKWOLF_PROP_BLAST_PROFILE_BARREL 1
#define DARKWOLF_PROP_BLAST_PROFILE_DAMAGE 2
#define DARKWOLF_PROP_BLAST_PROFILE_SCRIPT_FIRE 3
// DARKWOLF_EXPLOSION_COVERAGE_V446
#define DARKWOLF_GAS_BLAST_EVENT_MARKER   0x44574743
#define DARKWOLF_RADIO_BLAST_EVENT_MARKER 0x44575244
#define DARKWOLF_V2_BLAST_EVENT_MARKER    0x44575632
#define DARKWOLF_ALARM_BLAST_EVENT_MARKER 0x4457414C
#define DARKWOLF_ME109_BLAST_EVENT_MARKER 0x44574D45
#define DARKWOLF_PROP_BLAST_PROFILE_GAS   4
#define DARKWOLF_PROP_BLAST_PROFILE_RADIO 5
#define DARKWOLF_PROP_BLAST_PROFILE_V2    6
#define DARKWOLF_PROP_BLAST_PROFILE_ALARM 7
#define DARKWOLF_PROP_BLAST_PROFILE_ME109 8
""", "profile definitions")

cg = once(cg,
"""\tcase DARKWOLF_PROP_BLAST_PROFILE_SCRIPT_FIRE:
\t\t// Accepted Mode 2 energy: authored destruction scenes may fire several points together.
\t\tpeak = 420.0f; floorRadius = 140.0f; holdMs = 100; totalMs = 800;
\t\tred = 1.00f; green = 0.52f; blue = 0.18f;
\t\tbreak;
\tdefault:
""",
"""\tcase DARKWOLF_PROP_BLAST_PROFILE_SCRIPT_FIRE:
\t\t// Accepted Mode 2 energy: authored destruction scenes may fire several points together.
\t\tpeak = 420.0f; floorRadius = 140.0f; holdMs = 100; totalMs = 800;
\t\tred = 1.00f; green = 0.52f; blue = 0.18f;
\t\tbreak;
\tcase DARKWOLF_PROP_BLAST_PROFILE_GAS:
\t\tpeak = 500.0f; floorRadius = 150.0f; holdMs = 120; totalMs = 900;
\t\tred = 1.00f; green = 0.58f; blue = 0.22f;
\t\tbreak;
\tcase DARKWOLF_PROP_BLAST_PROFILE_RADIO:
\t\tpeak = 300.0f; floorRadius = 96.0f; holdMs = 80; totalMs = 620;
\t\tred = 1.00f; green = 0.62f; blue = 0.26f;
\t\tbreak;
\tcase DARKWOLF_PROP_BLAST_PROFILE_V2:
\t\tpeak = 760.0f; floorRadius = 220.0f; holdMs = 170; totalMs = 1250;
\t\tred = 1.00f; green = 0.54f; blue = 0.18f;
\t\tbreak;
\tcase DARKWOLF_PROP_BLAST_PROFILE_ALARM:
\t\tpeak = 280.0f; floorRadius = 90.0f; holdMs = 70; totalMs = 560;
\t\tred = 1.00f; green = 0.45f; blue = 0.12f;
\t\tbreak;
\tcase DARKWOLF_PROP_BLAST_PROFILE_ME109:
\t\tpeak = 680.0f; floorRadius = 210.0f; holdMs = 150; totalMs = 1150;
\t\tred = 1.00f; green = 0.55f; blue = 0.20f;
\t\tbreak;
\tdefault:
""", "new profiles")

cg = once(cg,
"""\tif ( cent->currentState.time2 == DARKWOLF_BARREL_BLAST_EVENT_MARKER ) {
\t\tCG_SpawnDarkWolfPropBlastDlight( origin, DARKWOLF_PROP_BLAST_PROFILE_BARREL );
\t\treturn; // light-only semantic event; do not manufacture duplicate fire/explosion visuals
\t}

\t// Runtime-accepted Matrix Mode 2: authored target_effect FIRE receives the same short shadow-capable blast treatment.
""",
"""\tif ( cent->currentState.time2 == DARKWOLF_BARREL_BLAST_EVENT_MARKER ) {
\t\tCG_SpawnDarkWolfPropBlastDlight( origin, DARKWOLF_PROP_BLAST_PROFILE_BARREL );
\t\treturn; // light-only semantic event; do not manufacture duplicate fire/explosion visuals
\t}

\t// DARKWOLF_EXPLOSION_COVERAGE_V446: additional semantic blast sources.
\tif ( cent->currentState.time2 == DARKWOLF_GAS_BLAST_EVENT_MARKER ) {
\t\tCG_SpawnDarkWolfPropBlastDlight( origin, DARKWOLF_PROP_BLAST_PROFILE_GAS );
\t\treturn;
\t}
\tif ( cent->currentState.time2 == DARKWOLF_RADIO_BLAST_EVENT_MARKER ) {
\t\tCG_SpawnDarkWolfPropBlastDlight( origin, DARKWOLF_PROP_BLAST_PROFILE_RADIO );
\t\treturn;
\t}
\tif ( cent->currentState.time2 == DARKWOLF_V2_BLAST_EVENT_MARKER ) {
\t\tCG_SpawnDarkWolfPropBlastDlight( origin, DARKWOLF_PROP_BLAST_PROFILE_V2 );
\t\treturn;
\t}
\tif ( cent->currentState.time2 == DARKWOLF_ALARM_BLAST_EVENT_MARKER ) {
\t\tCG_SpawnDarkWolfPropBlastDlight( origin, DARKWOLF_PROP_BLAST_PROFILE_ALARM );
\t\treturn;
\t}
\tif ( cent->currentState.time2 == DARKWOLF_ME109_BLAST_EVENT_MARKER ) {
\t\tCG_SpawnDarkWolfPropBlastDlight( origin, DARKWOLF_PROP_BLAST_PROFILE_ME109 );
\t\treturn;
\t}

\t// Runtime-accepted Matrix Mode 2: authored target_effect FIRE receives the same short shadow-capable blast treatment.
""", "event dispatch")

# Radios: preserve their stock propExplosion() entirely, add a separate light-only event.
gp = once(gp,
"""void props_radio_die( gentity_t *ent, gentity_t *inflictor, gentity_t *attacker, int damage, int mod ) {

\tpropExplosion( ent );
""",
"""void props_radio_die( gentity_t *ent, gentity_t *inflictor, gentity_t *attacker, int damage, int mod ) {

\t// DARKWOLF_EXPLOSION_COVERAGE_V446: radio light-only blast; stock propExplosion remains authoritative.
\t{
\t\tgentity_t *blastEvent = G_TempEntity( ent->r.currentOrigin, EV_EFFECT );
\t\tblastEvent->s.eventParm = 0;
\t\tblastEvent->s.time2 = 0x44575244; // DWRD
\t}
\tpropExplosion( ent );
""", "props_radio_die")

gp = once(gp,
"""void props_radio_dieSEVEN( gentity_t *ent, gentity_t *inflictor, gentity_t *attacker, int damage, int mod ) {

\tint i;

\tpropExplosion( ent );
""",
"""void props_radio_dieSEVEN( gentity_t *ent, gentity_t *inflictor, gentity_t *attacker, int damage, int mod ) {

\tint i;

\t// DARKWOLF_EXPLOSION_COVERAGE_V446: seven-radio rack uses the same small electronics blast profile.
\t{
\t\tgentity_t *blastEvent = G_TempEntity( ent->r.currentOrigin, EV_EFFECT );
\t\tblastEvent->s.eventParm = 0;
\t\tblastEvent->s.time2 = 0x44575244; // DWRD
\t}
\tpropExplosion( ent );
""", "props_radio_dieSEVEN")

# Large prop explosion is used by the SP Me-109 death path.
gp = once(gp,
"""void propExplosionLarge( gentity_t *ent ) {
\tgentity_t *bolt;

\tbolt = G_Spawn();
""",
"""void propExplosionLarge( gentity_t *ent ) {
\tgentity_t *bolt;

\t// DARKWOLF_EXPLOSION_COVERAGE_V446: Me-109 large explosion gets one dedicated light-only blast.
\t{
\t\tgentity_t *blastEvent = G_TempEntity( ent->r.currentOrigin, EV_EFFECT );
\t\tblastEvent->s.eventParm = 0;
\t\tblastEvent->s.time2 = 0x44574D45; // DWME
\t}

\tbolt = G_Spawn();
""", "propExplosionLarge")

# Alarm box explosion: preserve radius damage/sound/death event.
ga = once(ga,
"""void alarmExplosion( gentity_t *ent ) {

\t// death sound
""",
"""void alarmExplosion( gentity_t *ent ) {

\t// DARKWOLF_EXPLOSION_COVERAGE_V446: alarm-box death light, independent of stock sound/radius damage.
\t{
\t\tgentity_t *blastEvent = G_TempEntity( ent->r.currentOrigin, EV_EFFECT );
\t\tblastEvent->s.eventParm = 0;
\t\tblastEvent->s.time2 = 0x4457414C; // DWAL
\t}

\t// death sound
""", "alarmExplosion")

# Rocket: fire one central light exactly when target_kill processes target v2_rocket.
gt = once(gt,
"""\twhile ( ( targ = G_Find( targ, FOFS( targetname ), self->target ) ) != NULL ) {
\t\tif ( targ->aiCharacter ) {       // (SA) if it's an ai character, free it nicely
""",
"""\twhile ( ( targ = G_Find( targ, FOFS( targetname ), self->target ) ) != NULL ) {
\t\t// DARKWOLF_EXPLOSION_COVERAGE_V446: one central V2 blast at the scripted rocket kill.
\t\t// Existing target_effect FIRE points are untouched and keep their accepted profile.
\t\tif ( self->target && !Q_stricmp( self->target, "v2_rocket" ) &&
\t\t\t targ->classname && !Q_stricmp( targ->classname, "script_mover" ) ) {
\t\t\tgentity_t *blastEvent = G_TempEntity( targ->r.currentOrigin, EV_EFFECT );
\t\t\tblastEvent->s.eventParm = 0;
\t\t\tblastEvent->s.time2 = 0x44575632; // DWV2
\t\t}
\t\tif ( targ->aiCharacter ) {       // (SA) if it's an ai character, free it nicely
""", "V2 target kill")

# SWF gas cylinder: the retail audit identifies brush model *90 near the lower start-elevator landing.
# Mark only this exact map/submodel and only when it has no existing damaging DWPF marker.
gm = once(gm,
"""\tself->s.effect3Time = self->key;            // pass the type to the client ("glass", "wood", "metal", "gibs", "brick", "stone", "fabric", 0, 1, 2, 3, 4, 5, 6)

\tif ( self->damage ) {
""",
"""\tself->s.effect3Time = self->key;            // pass the type to the client ("glass", "wood", "metal", "gibs", "brick", "stone", "fabric", 0, 1, 2, 3, 4, 5, 6)

\t// DARKWOLF_EXPLOSION_COVERAGE_V446: SWF start-elevator gas cylinder.
\t// Exact retail BSP identity from audit run 37253370299; keep all other func_explosives unchanged.
\tif ( !self->damage && self->model && !Q_stricmp( self->model, "*90" ) ) {
\t\tchar dwMapName[MAX_QPATH];
\t\ttrap_Cvar_VariableStringBuffer( "mapname", dwMapName, sizeof(dwMapName) );
\t\tif ( !Q_stricmp( dwMapName, "swf" ) ) {
\t\t\tself->s.time2 = 0x44574743; // DWGC
\t\t}
\t}

\tif ( self->damage ) {
""", "SWF gas marker")

CG_EVENT.write_text(cg, encoding="utf-8")
G_PROPS.write_text(gp, encoding="utf-8")
G_ALARM.write_text(ga, encoding="utf-8")
G_TARGET.write_text(gt, encoding="utf-8")
G_MOVER.write_text(gm, encoding="utf-8")
print("Applied " + MARK)
