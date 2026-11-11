#!/usr/bin/env python3
from pathlib import Path
import sys, json, hashlib

MARK="DARKWOLF_WEAPON_PORT_V12_FIRE_SAFE"

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
    print("DW_WEAPON_PORT_V12_FIRE_SAFE_ALREADY_APPLIED")
    raise SystemExit(0)

old='''\tcase WP_DW_MP44:
\t\tMAKERGB( weaponInfo->flashDlightColor, 1.0, 0.6, 0.23 );
\t\tweaponInfo->flashSound[0]=trap_S_RegisterSound("sound/weapons/mp44/mp44_fire.wav");
\t\tweaponInfo->flashEchoSound[0]=trap_S_RegisterSound("sound/weapons/mp44/mp44_far.wav");
\t\tweaponInfo->reloadSound=trap_S_RegisterSound("sound/weapons/mp44/mp44_reload.wav");
\t\tweaponInfo->ejectBrassFunc=CG_MachineGunEjectBrass; break;
\tcase WP_DW_PPSH:
\t\tMAKERGB( weaponInfo->flashDlightColor, 1.0, 0.6, 0.23 );
\t\tweaponInfo->flashSound[0]=trap_S_RegisterSound("sound/weapons/ppsh/ppsh_fire.wav");
\t\tweaponInfo->flashEchoSound[0]=trap_S_RegisterSound("sound/weapons/ppsh/ppsh_far.wav");
\t\tweaponInfo->reloadSound=trap_S_RegisterSound("sound/weapons/ppsh/ppsh_reload.wav");
\t\tweaponInfo->ejectBrassFunc=CG_MachineGunEjectBrass; break;
'''
new='''\tcase WP_DW_MP44:
\t\t// DARKWOLF_WEAPON_PORT_V12_FIRE_SAFE: first stabilize the complete firing chain before
\t\t// re-enabling optional RealRTCW first-shot presentation effects.
\t\tVectorClear( weaponInfo->flashDlightColor ); // no shadowed muzzle dlight
\t\tweaponInfo->flashSound[0]=trap_S_RegisterSound("sound/weapons/mp40/mp40f1.wav");
\t\tweaponInfo->reloadSound=trap_S_RegisterSound("sound/weapons/mp40/mp40_reload.wav");
\t\tweaponInfo->ejectBrassFunc=NULL; // no optional brass local-entity path in V1.2
\t\tbreak;
\tcase WP_DW_PPSH:
\t\t// DARKWOLF_WEAPON_PORT_V12_FIRE_SAFE
\t\tVectorClear( weaponInfo->flashDlightColor ); // no shadowed muzzle dlight
\t\tweaponInfo->flashSound[0]=trap_S_RegisterSound("sound/weapons/mp40/mp40f1.wav");
\t\tweaponInfo->reloadSound=trap_S_RegisterSound("sound/weapons/mp40/mp40_reload.wav");
\t\tweaponInfo->ejectBrassFunc=NULL; // no optional brass local-entity path in V1.2
\t\tbreak;
'''
s=one(before,old,new,"new weapon fire presentation block")

old2='''\tif ( ps ) {
\t\tflash.hModel = weapon->flashModel[W_FP_MODEL];
\t} else {
\t\tflash.hModel = weapon->flashModel[W_TP_MODEL];
\t}
'''
new2='''\tif ( ps ) {
\t\tflash.hModel = weapon->flashModel[W_FP_MODEL];
\t} else {
\t\tflash.hModel = weapon->flashModel[W_TP_MODEL];
\t}
\t// DARKWOLF_WEAPON_PORT_V12_FIRE_SAFE: imported HD models are already stable at idle.
\t// Keep bullet, recoil, sound and impact active; suppress the optional imported flash refEntity.
\tif ( weaponNum == WP_DW_MP44 || weaponNum == WP_DW_PPSH ) {
\t\tflash.hModel = 0;
\t}
'''
s=one(s,old2,new2,"flash model suppression")

p.write_text(s,encoding="utf-8")

# Reuse the stock g_debugBullets cheat cvar as a CI-only proof bit (8).
# It is off by default and adds no new production/debug cvar.
gp=root/"SP/code/game/g_weapon.c"
gbefore=gp.read_text(encoding="utf-8")
ga="void FireWeapon( gentity_t *ent ) {\n"
gb=ga+"\tif ( (g_debugBullets.integer & 8) && (ent->s.weapon == WP_DW_MP44 || ent->s.weapon == WP_DW_PPSH) ) {\n\t\tG_Printf( \"DW_WEAPON_PORT_V12_FIRE weapon=%d\\n\", ent->s.weapon );\n\t}\n"
gafter=one(gbefore,ga,gb,"CI fire proof")
gp.write_text(gafter,encoding="utf-8")

proof={
  "feature":"DarkWolf Weapon Port V1.2 Fire-Safe",
  "base_run":42980800200,
  "base_sha":"24455cb405bf986009d3a81815f80d65335fa5b6",
  "new_weapons":["WP_DW_MP44","WP_DW_PPSH"],
  "server_bullet_path":"unchanged from V1/V1.1",
  "kept":["weapon attack animation","server Bullet_Fire","damage/spread","client recoil","stock-safe fire sound","standard bullet impact path"],
  "temporarily_suppressed":["new-weapon muzzle dynamic light","new-weapon brass ejection","new-weapon flash refEntity","RealRTCW custom fire/reload audio"],
  "before_sha256":hashlib.sha256(before.encode()).hexdigest(),
  "after_sha256":hashlib.sha256(s.encode()).hexdigest(),
  "fire_proof_gate":"existing g_debugBullets bit 8; default off"
}
(ev/"DW_WEAPON_PORT_V12_FIRE_SAFE_PROOF.json").write_text(json.dumps(proof,indent=2)+"\n",encoding="utf-8")
print(json.dumps(proof,indent=2))
print("DW_WEAPON_PORT_V12_FIRE_SAFE_APPLY_PASS")
