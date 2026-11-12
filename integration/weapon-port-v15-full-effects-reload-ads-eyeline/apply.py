#!/usr/bin/env python3
from pathlib import Path
import sys, json, hashlib

MARK="DARKWOLF_WEAPON_PORT_V15_FULL_EFFECTS_RELOAD_ADS_EYELINE"

def fail(m): raise SystemExit(m)
def one(s,a,b,label):
    n=s.count(a)
    if n!=1: fail(f"{label}: expected 1 anchor, got {n}")
    return s.replace(a,b,1)

if len(sys.argv)<2:
    fail("usage: apply.py <source-root> [evidence-dir]")

root=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/"evidence"
ev.mkdir(parents=True,exist_ok=True)

# ------------------------------------------------------------------
# 1) Reload root fix: append-only weapon IDs 32/33 must be allowed
# ------------------------------------------------------------------
pm=root/"SP/code/game/bg_pmove.c"
pmb=pm.read_text(encoding="utf-8")
if "DARKWOLF_WEAPON_PORT_V15_RELOAD_RANGE_FIX" not in pmb:
    old='''\tif ( weapon < WP_BEGINGERMAN || weapon > WP_DYNAMITE ) {
\t\treturn;
\t}
'''
    new='''\t// DARKWOLF_WEAPON_PORT_V15_RELOAD_RANGE_FIX
\t// Legacy RTCW assumed every reloadable player weapon lived in the
\t// contiguous WP_BEGINGERMAN..WP_DYNAMITE range.  DarkWolf MP44/PPSh
\t// are append-only IDs 32/33, so the old guard rejected them before
\t// WEAP_RELOAD1 / WEAPON_RELOADING / EV_FILL_CLIP could run.
\tif ( ( weapon < WP_BEGINGERMAN || weapon > WP_DYNAMITE ) &&
\t\t weapon != WP_DW_MP44 && weapon != WP_DW_PPSH ) {
\t\treturn;
\t}
'''
    pms=one(pmb,old,new,"PM_BeginWeaponReload legacy range gate")
    pm.write_text(pms,encoding="utf-8")
else:
    pms=pmb

# ------------------------------------------------------------------
# 2) Restore full presentation now that V1.4 fixed component index OOB
# ------------------------------------------------------------------
cg=root/"SP/code/cgame/cg_weapons.c"
cgb=cg.read_text(encoding="utf-8")
if MARK in cgb:
    print("DW_WEAPON_PORT_V15_ALREADY_APPLIED")
    raise SystemExit(0)
if "DARKWOLF_WEAPON_PORT_V14_COMPONENT_ANIM_INDEX_SAFETY" not in cgb:
    fail("V1.5 requires V1.4 Component Animation Index Safety first")
if "DARKWOLF_WEAPON_PORT_V13_FP_ATTACK_ANIM_SAFE" in cgb:
    fail("V1.5 must not inherit V1.3 hand-frame freeze")

s=cgb

old_fire='''\tcase WP_DW_MP44:
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
new_fire='''\tcase WP_DW_MP44:
\t\t// DARKWOLF_WEAPON_PORT_V15_FULL_EFFECTS_RELOAD_ADS_EYELINE
\t\t// V1.4 removed the component-animation OOB root cause, so restore
\t\t// the complete imported firing presentation for visual testing.
\t\tMAKERGB( weaponInfo->flashDlightColor, 1.0, 0.6, 0.23 );
\t\tweaponInfo->flashSound[0]=trap_S_RegisterSound("sound/weapons/mp44/mp44_fire.wav");
\t\tweaponInfo->flashEchoSound[0]=trap_S_RegisterSound("sound/weapons/mp44/mp44_far.wav");
\t\tweaponInfo->reloadSound=trap_S_RegisterSound("sound/weapons/mp44/mp44_reload.wav");
\t\tweaponInfo->ejectBrassFunc=CG_MachineGunEjectBrass;
\t\tbreak;
\tcase WP_DW_PPSH:
\t\t// DARKWOLF_WEAPON_PORT_V15_FULL_EFFECTS_RELOAD_ADS_EYELINE
\t\tMAKERGB( weaponInfo->flashDlightColor, 1.0, 0.6, 0.23 );
\t\tweaponInfo->flashSound[0]=trap_S_RegisterSound("sound/weapons/ppsh/ppsh_fire.wav");
\t\tweaponInfo->flashEchoSound[0]=trap_S_RegisterSound("sound/weapons/ppsh/ppsh_far.wav");
\t\tweaponInfo->reloadSound=trap_S_RegisterSound("sound/weapons/ppsh/ppsh_reload.wav");
\t\tweaponInfo->ejectBrassFunc=CG_MachineGunEjectBrass;
\t\tbreak;
'''
s=one(s,old_fire,new_fire,"restore RealRTCW fire presentation")

old_flash='''\t// DARKWOLF_WEAPON_PORT_V12_FIRE_SAFE: imported HD models are already stable at idle.
\t// Keep bullet, recoil, sound and impact active; suppress the optional imported flash refEntity.
\tif ( weaponNum == WP_DW_MP44 || weaponNum == WP_DW_PPSH ) {
\t\tflash.hModel = 0;
\t}
'''
new_flash='''\t// DARKWOLF_WEAPON_PORT_V15_FULL_EFFECTS_RELOAD_ADS_EYELINE:
\t// imported MP44/PPSh flash refEntities are intentionally enabled again.
'''
s=one(s,old_flash,new_flash,"restore flash refEntity")

# ------------------------------------------------------------------
# 3) ADS eye-line: keep tag-derived lateral/up centering, but push the
#    stock MP40/STEN viewmodel forward to the correct eye relief.
#    This replaces the V1 close-camera tag_flash hack seen in user shots.
# ------------------------------------------------------------------
old_ads='''\t// Tag-driven bore alignment: keeps stock model/animation and centers it for ADS.
\tif ( ps && CG_DWADSSupportedWeapon(weaponNum) ) {
\t\tfloat ads=CG_DWADSFrac();
\t\tif(ads>0){ refEntity_t sight; vec3_t d; float r,u; memset(&sight,0,sizeof(sight)); AxisClear(sight.axis);
\t\t\tCG_PositionEntityOnTag(&sight,&gun,"tag_flash",0,NULL); VectorSubtract(sight.origin,cg.refdef.vieworg,d);
\t\t\tr=DotProduct(d,cg.refdef.viewaxis[1]); u=DotProduct(d,cg.refdef.viewaxis[2]); if(r>24)r=24;if(r<-24)r=-24;if(u>24)u=24;if(u<-24)u=-24;
\t\t\tVectorMA(parent->origin,-r*ads,cg.refdef.viewaxis[1],parent->origin); VectorMA(parent->origin,-u*ads,cg.refdef.viewaxis[2],parent->origin); VectorMA(parent->origin,1.5f*ads,cg.refdef.viewaxis[0],parent->origin);
\t\t\tCG_PositionEntityOnTag(&gun,parent,"tag_weapon",0,NULL); }
\t}
'''
new_ads='''\t// DARKWOLF_WEAPON_PORT_V15_ADS_EYELINE
\t// tag_flash is a muzzle reference, not an eye/sight reference.  V1 moved
\t// the muzzle onto the camera plane with almost no eye relief, which made
\t// the rear of MP40/STEN fill or clip through the view.  Keep the useful
\t// lateral/up tag-derived centering, but place the weapon farther forward
\t// and leave the bore slightly below screen center so the iron-sight line
\t// itself meets the player's eye.
\tif ( ps && CG_DWADSSupportedWeapon( weaponNum ) ) {
\t\tfloat ads = CG_DWADSFrac();
\t\tif ( ads > 0.0f ) {
\t\t\trefEntity_t sight;
\t\t\tvec3_t d;
\t\t\tfloat r, u;
\t\t\tfloat eyeRelief = ( weaponNum == WP_STEN ) ? 10.0f : 8.0f;
\t\t\tconst float boreBelowEye = 1.25f;
\t\t\tmemset( &sight, 0, sizeof( sight ) );
\t\t\tAxisClear( sight.axis );
\t\t\tCG_PositionEntityOnTag( &sight, &gun, "tag_flash", 0, NULL );
\t\t\tVectorSubtract( sight.origin, cg.refdef.vieworg, d );
\t\t\tr = DotProduct( d, cg.refdef.viewaxis[1] );
\t\t\tu = DotProduct( d, cg.refdef.viewaxis[2] ) + boreBelowEye;
\t\t\tif ( r > 18.0f ) r = 18.0f;
\t\t\tif ( r < -18.0f ) r = -18.0f;
\t\t\tif ( u > 18.0f ) u = 18.0f;
\t\t\tif ( u < -18.0f ) u = -18.0f;
\t\t\tVectorMA( parent->origin, -r * ads, cg.refdef.viewaxis[1], parent->origin );
\t\t\tVectorMA( parent->origin, -u * ads, cg.refdef.viewaxis[2], parent->origin );
\t\t\tVectorMA( parent->origin, eyeRelief * ads, cg.refdef.viewaxis[0], parent->origin );
\t\t\tCG_PositionEntityOnTag( &gun, parent, "tag_weapon", 0, NULL );
\t\t}
\t}
'''
s=one(s,old_ads,new_ads,"replace V1 ADS tag_flash close-camera placement")

cg.write_text(s,encoding="utf-8")

proof={
  "feature":"DarkWolf Weapon Port V1.5 Full Effects + Reload + ADS Eye-Line",
  "base":"V1.4 Component Animation Index Safety",
  "reload_fix":{
    "root_cause":"PM_BeginWeaponReload rejected append-only IDs 32/33 via legacy WP_BEGINGERMAN..WP_DYNAMITE range gate",
    "allowed":["WP_DW_MP44","WP_DW_PPSH"],
    "path":["PM_CheckForReload","PM_BeginWeaponReload","WEAP_RELOAD1","WEAPON_RELOADING","EV_FILL_CLIP","PM_ReloadClip"]
  },
  "fire_presentation_restored":["flash refEntity","brass ejection","muzzle dynamic light","RealRTCW fire sound","RealRTCW echo sound","RealRTCW reload sound"],
  "ads":{
    "weapons":["WP_MP40","WP_STEN"],
    "method":"tag-derived lateral/up centering + per-weapon forward eye relief",
    "mp40_eye_relief":8.0,
    "sten_eye_relief":10.0,
    "bore_below_eye":1.25,
    "fov_target_unchanged":62.0
  },
  "v13_hand_frame_freeze_inherited":False,
  "v14_component_index_safety_required":True,
  "bg_pmove_sha256":hashlib.sha256(pms.encode()).hexdigest(),
  "cg_weapons_sha256":hashlib.sha256(s.encode()).hexdigest()
}
(ev/"DW_WEAPON_PORT_V15_PROOF.json").write_text(json.dumps(proof,indent=2)+"\n",encoding="utf-8")
print(json.dumps(proof,indent=2))
print("DW_WEAPON_PORT_V15_APPLY_PASS")
