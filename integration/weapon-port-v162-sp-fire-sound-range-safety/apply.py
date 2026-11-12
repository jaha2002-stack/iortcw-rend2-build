#!/usr/bin/env python3
from pathlib import Path
import sys,json,hashlib

MARK="DARKWOLF_WEAPON_PORT_V162_SP_FIRE_SOUND_RANGE_SAFETY"

def fail(m): raise SystemExit(m)
def one(s,a,b,label):
    n=s.count(a)
    if n!=1: fail(f"{label}: expected 1 anchor, got {n}")
    return s.replace(a,b,1)

if len(sys.argv)<2: fail("usage: apply.py <source-root> [evidence-dir]")
root=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/"evidence"
ev.mkdir(parents=True,exist_ok=True)

p=root/"SP/code/game/ai_cast_fight.c"
before=p.read_text(encoding="utf-8")
if MARK in before:
    print("DW_WEAPON_PORT_V162_ALREADY_APPLIED")
    raise SystemExit(0)

# AICast_RecordWeaponFire is called after every FireWeapon() in GT_SINGLE_PLAYER.
# Guard the weaponFireTimes[] write even though current imported IDs are < MAX_WEAPONS.
old='''void AICast_RecordWeaponFire( gentity_t *ent ) {
	cast_state_t *cs;
	float range;

	cs = AICast_GetCastState( ent->s.number );
	cs->lastWeaponFired = level.time;
	cs->lastWeaponFiredWeaponNum = ent->client->ps.weapon;
	VectorCopy( ent->r.currentOrigin, cs->lastWeaponFiredPos );

	cs->weaponFireTimes[cs->lastWeaponFiredWeaponNum] = level.time;

	// do sighting
	range = AICast_GetWeaponSoundRange( cs->lastWeaponFiredWeaponNum );
'''
new='''void AICast_RecordWeaponFire( gentity_t *ent ) {
	cast_state_t *cs;
	float range;

	cs = AICast_GetCastState( ent->s.number );
	cs->lastWeaponFired = level.time;
	cs->lastWeaponFiredWeaponNum = ent->client->ps.weapon;
	VectorCopy( ent->r.currentOrigin, cs->lastWeaponFiredPos );

	// DARKWOLF_WEAPON_PORT_V162_SP_FIRE_SOUND_RANGE_SAFETY
	// Append-only DarkWolf weapon IDs are valid player weapons, but this legacy
	// SP AI path predates them. Never index weaponFireTimes[] outside MAX_WEAPONS.
	if ( cs->lastWeaponFiredWeaponNum < 0 || cs->lastWeaponFiredWeaponNum >= MAX_WEAPONS ) {
		G_Printf( "DW_V162_SKIP_AI_FIRE_RECORD weapon=%d out of range 0..%d\\n",
			cs->lastWeaponFiredWeaponNum, MAX_WEAPONS - 1 );
		return;
	}
	cs->weaponFireTimes[cs->lastWeaponFiredWeaponNum] = level.time;

	// do sighting
	range = AICast_GetWeaponSoundRange( cs->lastWeaponFiredWeaponNum );
'''
s=one(before,old,new,"AICast_RecordWeaponFire guard")

# Add every imported weapon to the legacy AI audible-range switch.  The exact
# values only affect how far AI can hear the shot; the critical behavior is that
# no valid imported weapon falls through to the fatal G_Error default.
old='''	case    WP_STEN:
	case    WP_SILENCER:
		return 64;
'''
new='''	case    WP_STEN:
	case    WP_SILENCER:
	case    WP_DW_HDM:
		return 64;
'''
s=one(s,old,new,"suppressed sound range")

old='''	case    WP_LUGER:
	case    WP_COLT:
	case    WP_AKIMBO:
		return 700;
'''
new='''	case    WP_LUGER:
	case    WP_COLT:
	case    WP_AKIMBO:
	case    WP_DW_TT33:
	case    WP_DW_DUAL_TT33:
	case    WP_DW_REVOLVER:
		return 700;
'''
s=one(s,old,new,"pistol sound range")

old='''	case    WP_MP40:
	case    WP_THOMPSON:
		return 1000;
'''
new='''	case    WP_MP40:
	case    WP_THOMPSON:
	case    WP_DW_PPSH:
	case    WP_DW_MP34:
		return 1000;
'''
s=one(s,old,new,"SMG sound range")

old='''	case    WP_FG42:
	case    WP_FG42SCOPE:
		return 1500;
'''
new='''	case    WP_FG42:
	case    WP_FG42SCOPE:
	case    WP_DW_MP44:
	case    WP_DW_BAR:
	case    WP_DW_M97:
	case    WP_DW_BROWNING:
	case    WP_DW_MG42M:
		return 1500;
'''
s=one(s,old,new,"automatic/rifle sound range")

old='''	case    WP_SNIPERRIFLE:
	case    WP_MAUSER:
		return 2000;
'''
new='''	case    WP_SNIPERRIFLE:
	case    WP_MAUSER:
	case    WP_DW_MOSIN:
		return 2000;
'''
s=one(s,old,new,"bolt rifle sound range")

old='''	case    WP_GARAND:
	case    WP_SNOOPERSCOPE:
		return 128;
'''
new='''	case    WP_GARAND:
	case    WP_SNOOPERSCOPE:
		return 128;
	case    WP_DW_M1GARAND:
	case    WP_DW_G43:
		return 1500;
'''
s=one(s,old,new,"semi-auto rifle sound range")

p.write_text(s,encoding="utf-8")

proof={
  "feature":"DarkWolf Weapon Port V1.6.2 SP Fire Sound Range Safety Fix",
  "base_run":43158266053,
  "base_sha":"b6735889bf5b755d4f2fe5d97ecbddc93a34dd8c",
  "root_cause":"GT_SINGLE_PLAYER FireWeapon() always calls AICast_RecordWeaponFire(); legacy AICast_GetWeaponSoundRange() fatally G_Error'd for append-only imported weapon IDs",
  "scope":["SP/code/game/ai_cast_fight.c"],
  "imported_ids_covered":"WP_DW_MP44..WP_DW_MG42M (32..45)",
  "renderer_changed":False,
  "assets_changed":False,
  "ads_changed":False,
  "reload_changed":False,
  "before_sha256":hashlib.sha256(before.encode()).hexdigest(),
  "after_sha256":hashlib.sha256(s.encode()).hexdigest()
}
(ev/"DW_WEAPON_PORT_V162_SP_FIRE_SOUND_RANGE_SAFETY_PROOF.json").write_text(json.dumps(proof,indent=2)+"\n",encoding="utf-8")
print(json.dumps(proof,indent=2))
print("DW_WEAPON_PORT_V162_SP_FIRE_SOUND_RANGE_SAFETY_APPLY_PASS")
