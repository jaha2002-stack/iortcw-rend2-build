#!/usr/bin/env python3
from pathlib import Path
import sys, json, hashlib

MARK="DARKWOLF_WEAPON_PORT_V14_COMPONENT_ANIM_INDEX_SAFETY"

def fail(m): raise SystemExit(m)
def one(s,a,b,label):
    n=s.count(a)
    if n!=1:
        fail(f"{label}: expected 1 anchor, got {n}")
    return s.replace(a,b,1)

if len(sys.argv)<2:
    fail("usage: apply.py <source-root> [evidence-dir]")

root=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/"evidence"
ev.mkdir(parents=True,exist_ok=True)

p=root/"SP/code/cgame/cg_weapons.c"
before=p.read_text(encoding="utf-8")
if MARK in before:
    print("DW_WEAPON_PORT_V14_COMPONENT_ANIM_INDEX_SAFETY_ALREADY_APPLIED")
    raise SystemExit(0)

# V1.4 intentionally does NOT inherit the V1.3 hand-frame freeze.
if "DARKWOLF_WEAPON_PORT_V13_FP_ATTACK_ANIM_SAFE" in before:
    fail("V1.4 must be applied without the V1.3 hand-frame freeze")

s=before

old_decl='''qboolean CG_GetPartFramesFromWeap( centity_t *cent, refEntity_t *part, refEntity_t *parent, int partid, weaponInfo_t *wi ) {
\tint i;
\tint frameoffset = 0;
\tanimation_t *anim;

\tanim = cent->pe.weap.animation;
'''
new_decl='''qboolean CG_GetPartFramesFromWeap( centity_t *cent, refEntity_t *part, refEntity_t *parent, int partid, weaponInfo_t *wi ) {
\tint i;
\tint frameoffset = 0;
\tint animNumber;
\tanimation_t *anim;

\tanim = cent->pe.weap.animation;

\t// DARKWOLF_WEAPON_PORT_V14_COMPONENT_ANIM_INDEX_SAFETY
\t// animationNumber intentionally carries ANIM_TOGGLEBIT for lerp restart
\t// detection.  It must never be used as an array bound before masking.
\tanimNumber = cent->pe.weap.animationNumber & ~ANIM_TOGGLEBIT;
\tif ( animNumber < 0 || animNumber >= MAX_WP_ANIMATIONS ) {
\t\tif ( cg_debugAnim.integer & 8 ) {
\t\t\tCG_Printf( "DW_WEAPON_PORT_V14_BAD_COMPONENT_ANIM raw=%d masked=%d max=%d partid=%d\\n",
\t\t\t\tcent->pe.weap.animationNumber, animNumber, MAX_WP_ANIMATIONS, partid );
\t\t}
\t\treturn qfalse;
\t}
'''
s=one(s,old_decl,new_decl,"CG_GetPartFramesFromWeap declaration/guard")

old_loop='''\t// find part's start frame for this animation sequence
\tfor ( i = 0; i < cent->pe.weap.animationNumber; i++ ) {
\t\tif ( wi->weapAnimations[i].moveSpeed & ( 1 << partid ) ) {     // this part has animation for this sequence
\t\t\tframeoffset += wi->weapAnimations[i].numFrames;
\t\t}
\t}
'''
new_loop='''\t// find part's start frame for this animation sequence.
\t// Use the validated, toggle-bit-free index; raw animationNumber can be
\t// 512+N and would otherwise read far beyond weapAnimations[].
\tfor ( i = 0; i < animNumber; i++ ) {
\t\tif ( wi->weapAnimations[i].moveSpeed & ( 1 << partid ) ) {     // this part has animation for this sequence
\t\t\tframeoffset += wi->weapAnimations[i].numFrames;
\t\t}
\t}
'''
s=one(s,old_loop,new_loop,"CG_GetPartFramesFromWeap frameoffset loop")

p.write_text(s,encoding="utf-8")

proof={
    "feature":"DarkWolf Weapon Port V1.4 Component Animation Index Safety Fix",
    "base_run":43014836342,
    "base_sha":"9cef12c401ecdcf43bf18d157cc8d56d19d25a65",
    "scope":["SP/code/cgame/cg_weapons.c::CG_GetPartFramesFromWeap"],
    "root_cause":"raw cent->pe.weap.animationNumber includes ANIM_TOGGLEBIT and was used as weapAnimations[] loop bound",
    "fix":[
        "animNumber = cent->pe.weap.animationNumber & ~ANIM_TOGGLEBIT",
        "reject animNumber outside [0, MAX_WP_ANIMATIONS)",
        "iterate frameoffset loop only to validated animNumber"
    ],
    "v13_hand_frame_freeze_inherited":False,
    "kept_from_v12":["server Bullet_Fire","damage/spread","ammo consumption","impact events","camera recoil","stock-safe fire audio"],
    "before_sha256":hashlib.sha256(before.encode()).hexdigest(),
    "after_sha256":hashlib.sha256(s.encode()).hexdigest()
}
(ev/"DW_WEAPON_PORT_V14_COMPONENT_ANIM_INDEX_SAFETY_PROOF.json").write_text(json.dumps(proof,indent=2)+"\n",encoding="utf-8")
print(json.dumps(proof,indent=2))
print("DW_WEAPON_PORT_V14_COMPONENT_ANIM_INDEX_SAFETY_APPLY_PASS")
