#!/usr/bin/env python3
from pathlib import Path
import sys, json, hashlib

MARK="DARKWOLF_WEAPON_PORT_V15_FULL_FIRE_ADS_RELOAD"

def fail(m): raise SystemExit(m)
def one(s,a,b,label):
    n=s.count(a)
    if n!=1: fail(f"{label}: expected 1 anchor, got {n}")
    return s.replace(a,b,1)

if len(sys.argv)<2: fail("usage: apply.py <source-root> [evidence-dir]")
root=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/"evidence"
ev.mkdir(parents=True,exist_ok=True)

# ---- cgame: restore full RealRTCW fire presentation and replace V1 ADS geometry hack ----
p=root/"SP/code/cgame/cg_weapons.c"
before=p.read_text(encoding="utf-8")
if MARK in before:
    print("DW_WEAPON_PORT_V15_ALREADY_APPLIED")
    raise SystemExit(0)
if "DARKWOLF_WEAPON_PORT_V14_COMPONENT_ANIM_INDEX_SAFETY" not in before:
    fail("V1.5 requires V1.4 component animation safety fix")
if "DARKWOLF_WEAPON_PORT_V13_FP_ATTACK_ANIM_SAFE" in before:
    fail("V1.5 must not inherit V1.3 hand-frame freeze")

s=before

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
\t\t// DARKWOLF_WEAPON_PORT_V15_FULL_FIRE_ADS_RELOAD: V1.4 proved the firing crash
\t\t// was the component-animation index bug, so restore the complete presentation.
\t\tMAKERGB( weaponInfo->flashDlightColor, 1.0, 0.6, 0.23 );
\t\tweaponInfo->flashSound[0]=trap_S_RegisterSound("sound/weapons/mp44/mp44_fire.wav");
\t\tweaponInfo->flashEchoSound[0]=trap_S_RegisterSound("sound/weapons/mp44/mp44_far.wav");
\t\tweaponInfo->reloadSound=trap_S_RegisterSound("sound/weapons/mp44/mp44_reload.wav");
\t\tweaponInfo->ejectBrassFunc=CG_MachineGunEjectBrass;
\t\tbreak;
\tcase WP_DW_PPSH:
\t\t// DARKWOLF_WEAPON_PORT_V15_FULL_FIRE_ADS_RELOAD
\t\tMAKERGB( weaponInfo->flashDlightColor, 1.0, 0.6, 0.23 );
\t\tweaponInfo->flashSound[0]=trap_S_RegisterSound("sound/weapons/ppsh/ppsh_fire.wav");
\t\tweaponInfo->flashEchoSound[0]=trap_S_RegisterSound("sound/weapons/ppsh/ppsh_far.wav");
\t\tweaponInfo->reloadSound=trap_S_RegisterSound("sound/weapons/ppsh/ppsh_reload.wav");
\t\tweaponInfo->ejectBrassFunc=CG_MachineGunEjectBrass;
\t\tbreak;
'''
s=one(s,old_fire,new_fire,"restore full fire presentation")

old_flash='''\t// DARKWOLF_WEAPON_PORT_V12_FIRE_SAFE: imported HD models are already stable at idle.
\t// Keep bullet, recoil, sound and impact active; suppress the optional imported flash refEntity.
\tif ( weaponNum == WP_DW_MP44 || weaponNum == WP_DW_PPSH ) {
\t\tflash.hModel = 0;
\t}
'''
s=one(s,old_flash,"","restore real flash refEntity")

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
new_ads='''\t// DARKWOLF_WEAPON_PORT_V15_FULL_FIRE_ADS_RELOAD
\t// ADS eye-line alignment for the stock MP40/STEN view models.
\t// Do NOT center tag_flash itself: that puts the muzzle at the camera and causes
\t// the giant/clipped view seen in V1.  Build a virtual rear-sight point a safe
\t// distance behind the muzzle, center only its screen-space right/up offset,
\t// and push the complete viewmodel slightly forward away from the eye.
\tif ( ps && CG_DWADSSupportedWeapon( weaponNum ) ) {
\t\tfloat ads = CG_DWADSFrac();
\t\tif ( ads > 0.0f ) {
\t\t\trefEntity_t muzzle;
\t\t\tvec3_t sightPoint, delta;
\t\t\tfloat rightOffset, upOffset;
\t\t\tfloat rearSightBack = ( weaponNum == WP_STEN ) ? 25.0f : 29.0f;
\t\t\tfloat eyeClearance  = ( weaponNum == WP_STEN ) ? 8.0f : 7.0f;
\t\t\tmemset( &muzzle, 0, sizeof( muzzle ) );
\t\t\tAxisClear( muzzle.axis );
\t\t\tCG_PositionEntityOnTag( &muzzle, &gun, "tag_flash", 0, NULL );
\t\t\tVectorMA( muzzle.origin, -rearSightBack, gun.axis[0], sightPoint );
\t\t\tVectorSubtract( sightPoint, cg.refdef.vieworg, delta );
\t\t\trightOffset = DotProduct( delta, cg.refdef.viewaxis[1] );
\t\t\tupOffset    = DotProduct( delta, cg.refdef.viewaxis[2] );
\t\t\tif ( rightOffset > 16.0f ) rightOffset = 16.0f;
\t\t\tif ( rightOffset < -16.0f ) rightOffset = -16.0f;
\t\t\tif ( upOffset > 16.0f ) upOffset = 16.0f;
\t\t\tif ( upOffset < -16.0f ) upOffset = -16.0f;
\t\t\tVectorMA( parent->origin, -rightOffset * ads, cg.refdef.viewaxis[1], parent->origin );
\t\t\tVectorMA( parent->origin, -upOffset * ads, cg.refdef.viewaxis[2], parent->origin );
\t\t\tVectorMA( parent->origin, eyeClearance * ads, cg.refdef.viewaxis[0], parent->origin );
\t\t\tCG_PositionEntityOnTag( &gun, parent, "tag_weapon", 0, NULL );
\t\t}
\t}
'''
s=one(s,old_ads,new_ads,"replace muzzle-centered ADS with rear-sight eye-line alignment")
p.write_text(s,encoding="utf-8")

# ---- shared pmove: allow the two append-only weapons through the legacy reload gate ----
bp=root/"SP/code/game/bg_pmove.c"
b0=bp.read_text(encoding="utf-8")
old_gate='''\tif ( weapon < WP_BEGINGERMAN || weapon > WP_DYNAMITE ) {
\t\treturn;
\t}
'''
new_gate='''\t// DARKWOLF_WEAPON_PORT_V15_FULL_FIRE_ADS_RELOAD:
\t// the original range predates append-only WP_DW_MP44/WP_DW_PPSH (32/33).
\t// Keep monster/special weapons excluded, but explicitly allow the two ports.
\tif ( weapon < WP_BEGINGERMAN ||
\t\t ( weapon > WP_DYNAMITE && weapon != WP_DW_MP44 && weapon != WP_DW_PPSH ) ) {
\t\treturn;
\t}
'''
if b0.count(old_gate)!=1:
    fail(f"reload gate anchor mismatch: {b0.count(old_gate)}")
b1=b0.replace(old_gate,new_gate,1)
bp.write_text(b1,encoding="utf-8")

proof={
  "feature":"DarkWolf Weapon Port V1.5 Full Fire + ADS Eye Line + Reload",
  "base":"V1.4 Component Animation Index Safety",
  "v14_crash_fix_preserved":True,
  "v13_hand_frame_freeze_inherited":False,
  "fire_presentation_restored":[
    "RealRTCW MP44/PPSh flash models","brass ejection","muzzle dynamic light",
    "RealRTCW fire sounds","RealRTCW far/echo sounds","RealRTCW reload sounds"
  ],
  "reload_fix":"legacy PM_BeginWeaponReload WP_DYNAMITE upper gate now explicitly allows WP_DW_MP44/WP_DW_PPSH",
  "reload_times":{"MP44_ms":2600,"PPSh_ms":2600},
  "clip_sizes":{"MP44":30,"PPSh":71},
  "ads_fix":"replace muzzle-at-camera alignment with virtual rear-sight eye-line alignment + forward eye clearance",
  "cgame_before_sha256":hashlib.sha256(before.encode()).hexdigest(),
  "cgame_after_sha256":hashlib.sha256(s.encode()).hexdigest(),
  "pmove_before_sha256":hashlib.sha256(b0.encode()).hexdigest(),
  "pmove_after_sha256":hashlib.sha256(b1.encode()).hexdigest()
}
(ev/"DW_WEAPON_PORT_V15_FULL_FIRE_ADS_RELOAD_PROOF.json").write_text(json.dumps(proof,indent=2)+"\n",encoding="utf-8")
print(json.dumps(proof,indent=2))
print("DW_WEAPON_PORT_V15_FULL_FIRE_ADS_RELOAD_APPLY_PASS")
