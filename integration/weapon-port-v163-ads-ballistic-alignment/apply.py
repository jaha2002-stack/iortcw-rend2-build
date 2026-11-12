#!/usr/bin/env python3
from pathlib import Path
import sys,json,hashlib

MARK="DARKWOLF_WEAPON_PORT_V163_ADS_BALLISTIC_ALIGNMENT"

def fail(m): raise SystemExit(m)
def one(s,a,b,label):
    n=s.count(a)
    if n!=1: fail(f"{label}: expected 1 anchor, got {n}")
    return s.replace(a,b,1)

if len(sys.argv)<2: fail("usage: apply.py <source-root> [evidence-dir]")
root=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/"evidence"
ev.mkdir(parents=True,exist_ok=True)

p=root/"SP/code/game/g_weapon.c"
before=p.read_text(encoding="utf-8")
if MARK in before:
    print("DW_WEAPON_PORT_V163_ALREADY_APPLIED")
    raise SystemExit(0)

old='''void Bullet_Fire( gentity_t *ent, float spread, int damage ) {
	vec3_t end;

	// DARKWOLF_WEAPON_PORT_V1_MP44_PPSH_ADS: ADS improves actual server bullet cone, not only camera FOV.
	if ( ent->client && (ent->client->ps.eFlags & EF_DW_ADS) && (ent->s.weapon == WP_MP40 || ent->s.weapon == WP_STEN) ) spread *= 0.55f;

	Bullet_Endpos( ent, spread, &end );
	Bullet_Fire_Extended( ent, ent, muzzleTrace, end, spread, damage, 0 );
}
'''
new='''void Bullet_Fire( gentity_t *ent, float spread, int damage ) {
	vec3_t end;

	// DARKWOLF_WEAPON_PORT_V163_ADS_BALLISTIC_ALIGNMENT
	// MP40/STEN iron-sight ADS must hit the same world point represented by the
	// center of the camera/sight picture.  The legacy userAim path always leaves
	// a minimum random cone, and V1 only reduced that cone to 55%%.  In ADS,
	// remove only the random ballistic cone; muzzleTrace already starts at the
	// camera eye line and forward/right/up already come from ps.viewangles.
	// Hip-fire remains completely unchanged.
	if ( ent->client &&
		 ( ent->client->ps.eFlags & EF_DW_ADS ) &&
		 ( ent->s.weapon == WP_MP40 || ent->s.weapon == WP_STEN ) ) {
		spread = 0.0f;
	}

	Bullet_Endpos( ent, spread, &end );
	Bullet_Fire_Extended( ent, ent, muzzleTrace, end, spread, damage, 0 );
}
'''
s=one(before,old,new,"Bullet_Fire ADS ballistic alignment")
p.write_text(s,encoding="utf-8")

proof={
  "feature":"DarkWolf Weapon Port V1.6.3 ADS Ballistic Alignment",
  "base_run":43163828898,
  "base_sha":"f8cdc9cc7b59a3776b6d4bc11b30c760fc96e473",
  "scope":["SP/code/game/g_weapon.c::Bullet_Fire"],
  "root_cause":[
    "legacy FireWeapon adds minimum aimSpreadScale to player weapons",
    "V1 ADS only multiplied MP40/STEN spread by 0.55, so random r/u deviation remained"
  ],
  "fix":"when EF_DW_ADS is active for MP40 or STEN, set Bullet_Fire spread to 0 before Bullet_Endpos",
  "hip_fire_changed":False,
  "recoil_changed":False,
  "view_model_calibration_changed":False,
  "new_weapon_port_changed":False,
  "assets_changed":False,
  "before_sha256":hashlib.sha256(before.encode()).hexdigest(),
  "after_sha256":hashlib.sha256(s.encode()).hexdigest()
}
(ev/"DW_WEAPON_PORT_V163_ADS_BALLISTIC_ALIGNMENT_PROOF.json").write_text(json.dumps(proof,indent=2)+"\n",encoding="utf-8")
print(json.dumps(proof,indent=2))
print("DW_WEAPON_PORT_V163_ADS_BALLISTIC_ALIGNMENT_APPLY_PASS")
