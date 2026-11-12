#!/usr/bin/env python3
from pathlib import Path
import sys,json,re
if len(sys.argv)<2: raise SystemExit("usage: run_tests.py <source-root> [evidence-dir]")
root=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/"evidence"
ev.mkdir(parents=True,exist_ok=True)

s=(root/"SP/code/game/g_weapon.c").read_text(encoding="utf-8")
start=s.index("void Bullet_Fire( gentity_t *ent, float spread, int damage )")
end=s.index("void Bullet_Fire_Extended",start)
fn=s[start:end]

checks={
 "marker":"DARKWOLF_WEAPON_PORT_V163_ADS_BALLISTIC_ALIGNMENT" in fn,
 "ads_flag":"ent->client->ps.eFlags & EF_DW_ADS" in fn,
 "mp40_only":"ent->s.weapon == WP_MP40" in fn,
 "sten_only":"ent->s.weapon == WP_STEN" in fn,
 "zero_spread":"spread = 0.0f;" in fn,
 "old_055_removed":"spread *= 0.55f" not in fn,
 "bullet_endpos_preserved":"Bullet_Endpos( ent, spread, &end );" in fn,
 "bullet_extended_preserved":"Bullet_Fire_Extended( ent, ent, muzzleTrace, end, spread, damage, 0 );" in fn,
}
bad=[k for k,v in checks.items() if not v]
(ev/"DW_WEAPON_PORT_V163_TESTS.json").write_text(json.dumps(checks,indent=2)+"\n",encoding="utf-8")
if bad: raise SystemExit("FAIL "+",".join(bad))
print("DW_WEAPON_PORT_V163_TESTS_PASS",len(checks))
