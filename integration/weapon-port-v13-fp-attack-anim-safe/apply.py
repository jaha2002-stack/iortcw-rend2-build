#!/usr/bin/env python3
from pathlib import Path
import sys,json,hashlib

MARK="DARKWOLF_WEAPON_PORT_V13_FP_ATTACK_ANIM_SAFE"

def fail(m): raise SystemExit(m)
def one(s,a,b,label):
    n=s.count(a)
    if n!=1: fail(f"{label}: expected 1 anchor, got {n}")
    return s.replace(a,b,1)

if len(sys.argv)<2: fail("usage: apply.py <source-root> [evidence-dir]")
root=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/"evidence"
ev.mkdir(parents=True,exist_ok=True)

p=root/"SP/code/cgame/cg_weapons.c"
before=p.read_text(encoding="utf-8")
if MARK in before:
    print("DW_WEAPON_PORT_V13_FP_ATTACK_ANIM_SAFE_ALREADY_APPLIED")
    raise SystemExit(0)

anchor='''\t\t} else {  // get the animation state
\t\t\tCG_WeaponAnimation( ps, weapon, &hand.oldframe, &hand.frame, &hand.backlerp );   //----(SA)\tchanged
\t\t}
'''
replacement='''\t\t} else {  // get the animation state
\t\t\tCG_WeaponAnimation( ps, weapon, &hand.oldframe, &hand.frame, &hand.backlerp );   //----(SA)\tchanged
\t\t}

\t\t// DARKWOLF_WEAPON_PORT_V13_FP_ATTACK_ANIM_SAFE
\t\t// RealRTCW HD hands are tag-animation carriers.  Until their complete
\t\t// RealRTCW weapon-animation contract is ported, never feed attack-frame
\t\t// transitions into the legacy ioRTCW first-person tag lerp.  Gameplay
\t\t// firing, Bullet_Fire, impacts and camera recoil remain fully active.
\t\tif ( ps->weapon == WP_DW_MP44 || ps->weapon == WP_DW_PPSH ) {
\t\t\tint dwAnim = ps->weapAnim & ~ANIM_TOGGLEBIT;
\t\t\tif ( dwAnim == WEAP_ATTACK1 || dwAnim == WEAP_ATTACK2 || dwAnim == WEAP_ATTACK_LASTSHOT ) {
\t\t\t\tint dwSafeFrame = ( ps->weapon == WP_DW_MP44 ) ? 0 : 8;
\t\t\t\thand.oldframe = dwSafeFrame;
\t\t\t\thand.frame = dwSafeFrame;
\t\t\t\thand.backlerp = 0.0f;
\t\t\t\tif ( cg_debugAnim.integer & 8 ) {
\t\t\t\t\tCG_Printf( "DW_WEAPON_PORT_V13_FP_ATTACK_SAFE weapon=%d anim=%d frame=%d\\n",
\t\t\t\t\t\tps->weapon, dwAnim, dwSafeFrame );
\t\t\t\t}
\t\t\t}
\t\t}
'''
after=one(before,anchor,replacement,"CG_AddViewWeapon animation block")
p.write_text(after,encoding="utf-8")

proof={
 "feature":"DarkWolf Weapon Port V1.3 First-Person Attack Animation Compatibility Fix",
 "base_run":42985989906,
 "base_sha":"127c716aac51a499f63da9acb0a0babba1271f69",
 "scope":["SP/code/cgame/cg_weapons.c"],
 "weapons":{"WP_DW_MP44":{"id":32,"safe_attack_frame":0},"WP_DW_PPSH":{"id":33,"safe_attack_frame":8}},
 "frozen_only_during":["WEAP_ATTACK1","WEAP_ATTACK2","WEAP_ATTACK_LASTSHOT"],
 "unchanged":["server Bullet_Fire","damage","spread","ammo consumption","impact events","camera recoil","idle model placement","B2 V2.4.1","PBR/Owner renderer features"],
 "inherits_v12_fire_safe":True,
 "diagnostic_gate":"existing cg_debugAnim bit 8; default off",
 "before_sha256":hashlib.sha256(before.encode()).hexdigest(),
 "after_sha256":hashlib.sha256(after.encode()).hexdigest()
}
(ev/"DW_WEAPON_PORT_V13_FP_ATTACK_ANIM_SAFE_PROOF.json").write_text(json.dumps(proof,indent=2)+"\n",encoding="utf-8")
print(json.dumps(proof,indent=2))
print("DW_WEAPON_PORT_V13_FP_ATTACK_ANIM_SAFE_APPLY_PASS")
