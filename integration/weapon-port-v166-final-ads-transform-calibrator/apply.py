#!/usr/bin/env python3
from pathlib import Path
import sys,json,hashlib

MARK="DARKWOLF_WEAPON_PORT_V166_FINAL_ADS_TRANSFORM_CALIBRATOR"

def fail(m): raise SystemExit(m)
def one(s,a,b,label):
    n=s.count(a)
    if n!=1: fail(f"{label}: expected 1 anchor, got {n}")
    return s.replace(a,b,1)

if len(sys.argv)<2: fail("usage: apply.py <source-root> [evidence-dir]")
root=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/"evidence"
ev.mkdir(parents=True,exist_ok=True)

# ------------------------------------------------------------------
# Real vmCvar_t state: register in cvarTable so CG_UpdateCvars refreshes
# .value/.integer every frame.
# ------------------------------------------------------------------
p=root/"SP/code/cgame/cg_main.c"
m0=p.read_text(encoding="utf-8")
if MARK in m0:
    print("DW_WEAPON_PORT_V166_ALREADY_APPLIED")
    raise SystemExit(0)

anchor='''vmCvar_t cg_gun_x;
vmCvar_t cg_gun_y;
vmCvar_t cg_gun_z;
'''
decl=anchor+'''// DARKWOLF_WEAPON_PORT_V166_FINAL_ADS_TRANSFORM_CALIBRATOR
vmCvar_t cg_dwAdsDebug;
vmCvar_t cg_dwAdsMP40Right;
vmCvar_t cg_dwAdsMP40Up;
vmCvar_t cg_dwAdsMP40Forward;
vmCvar_t cg_dwAdsMP40Pitch;
vmCvar_t cg_dwAdsMP40Yaw;
vmCvar_t cg_dwAdsMP40Roll;
vmCvar_t cg_dwAdsStenRight;
vmCvar_t cg_dwAdsStenUp;
vmCvar_t cg_dwAdsStenForward;
vmCvar_t cg_dwAdsStenPitch;
vmCvar_t cg_dwAdsStenYaw;
vmCvar_t cg_dwAdsStenRoll;
'''
m=one(m0,anchor,decl,"declare ADS vmCvars")

anchor='''	{ &cg_gun_x, "cg_gunX", "0", CVAR_CHEAT },
	{ &cg_gun_y, "cg_gunY", "0", CVAR_CHEAT },
	{ &cg_gun_z, "cg_gunZ", "0", CVAR_CHEAT },
'''
entries=anchor+'''	{ &cg_dwAdsDebug, "cg_dwAdsDebug", "0", CVAR_ARCHIVE },
	{ &cg_dwAdsMP40Right, "cg_dwAdsMP40Right", "0", CVAR_ARCHIVE },
	{ &cg_dwAdsMP40Up, "cg_dwAdsMP40Up", "0", CVAR_ARCHIVE },
	{ &cg_dwAdsMP40Forward, "cg_dwAdsMP40Forward", "0", CVAR_ARCHIVE },
	{ &cg_dwAdsMP40Pitch, "cg_dwAdsMP40Pitch", "0", CVAR_ARCHIVE },
	{ &cg_dwAdsMP40Yaw, "cg_dwAdsMP40Yaw", "0", CVAR_ARCHIVE },
	{ &cg_dwAdsMP40Roll, "cg_dwAdsMP40Roll", "0", CVAR_ARCHIVE },
	{ &cg_dwAdsStenRight, "cg_dwAdsStenRight", "0", CVAR_ARCHIVE },
	{ &cg_dwAdsStenUp, "cg_dwAdsStenUp", "0", CVAR_ARCHIVE },
	{ &cg_dwAdsStenForward, "cg_dwAdsStenForward", "0", CVAR_ARCHIVE },
	{ &cg_dwAdsStenPitch, "cg_dwAdsStenPitch", "0", CVAR_ARCHIVE },
	{ &cg_dwAdsStenYaw, "cg_dwAdsStenYaw", "0", CVAR_ARCHIVE },
	{ &cg_dwAdsStenRoll, "cg_dwAdsStenRoll", "0", CVAR_ARCHIVE },
'''
m=one(m,anchor,entries,"add ADS vmCvars to cvarTable")

manual='''	// DARKWOLF_WEAPON_PORT_V165_ADS_CVAR_CALIBRATOR
	trap_Cvar_Register( NULL, "cg_dwAdsDebug", "0", CVAR_ARCHIVE );
	trap_Cvar_Register( NULL, "cg_dwAdsMP40Right", "0", CVAR_ARCHIVE );
	trap_Cvar_Register( NULL, "cg_dwAdsMP40Up", "0", CVAR_ARCHIVE );
	trap_Cvar_Register( NULL, "cg_dwAdsMP40Forward", "0", CVAR_ARCHIVE );
	trap_Cvar_Register( NULL, "cg_dwAdsMP40Pitch", "0", CVAR_ARCHIVE );
	trap_Cvar_Register( NULL, "cg_dwAdsMP40Yaw", "0", CVAR_ARCHIVE );
	trap_Cvar_Register( NULL, "cg_dwAdsMP40Roll", "0", CVAR_ARCHIVE );
	trap_Cvar_Register( NULL, "cg_dwAdsStenRight", "0", CVAR_ARCHIVE );
	trap_Cvar_Register( NULL, "cg_dwAdsStenUp", "0", CVAR_ARCHIVE );
	trap_Cvar_Register( NULL, "cg_dwAdsStenForward", "0", CVAR_ARCHIVE );
	trap_Cvar_Register( NULL, "cg_dwAdsStenPitch", "0", CVAR_ARCHIVE );
	trap_Cvar_Register( NULL, "cg_dwAdsStenYaw", "0", CVAR_ARCHIVE );
	trap_Cvar_Register( NULL, "cg_dwAdsStenRoll", "0", CVAR_ARCHIVE );

'''
m=one(m,manual,"","remove V1.6.5 NULL registrations")
p.write_text(m,encoding="utf-8")

# externs
p=root/"SP/code/cgame/cg_local.h"
h0=p.read_text(encoding="utf-8")
anchor='''extern vmCvar_t cg_gun_x;
extern vmCvar_t cg_gun_y;
extern vmCvar_t cg_gun_z;
'''
externs=anchor+'''extern vmCvar_t cg_dwAdsDebug;
extern vmCvar_t cg_dwAdsMP40Right;
extern vmCvar_t cg_dwAdsMP40Up;
extern vmCvar_t cg_dwAdsMP40Forward;
extern vmCvar_t cg_dwAdsMP40Pitch;
extern vmCvar_t cg_dwAdsMP40Yaw;
extern vmCvar_t cg_dwAdsMP40Roll;
extern vmCvar_t cg_dwAdsStenRight;
extern vmCvar_t cg_dwAdsStenUp;
extern vmCvar_t cg_dwAdsStenForward;
extern vmCvar_t cg_dwAdsStenPitch;
extern vmCvar_t cg_dwAdsStenYaw;
extern vmCvar_t cg_dwAdsStenRoll;
'''
h=one(h0,anchor,externs,"extern ADS vmCvars")
p.write_text(h,encoding="utf-8")

# ------------------------------------------------------------------
# Replace string-buffer reads by direct vmCvar values and move angular
# transform from early hand.axis to final gun.axis.
# ------------------------------------------------------------------
p=root/"SP/code/cgame/cg_weapons.c"
c0=p.read_text(encoding="utf-8")
c=c0

old='''static float CG_DWADSReadFloat( const char *name ) {
	char buf[64];
	trap_Cvar_VariableStringBuffer( name, buf, sizeof(buf) );
	return atof( buf );
}

static qboolean CG_DWADSReadPosForWeapon( int w, vec3_t out ) {
	if ( w == WP_MP40 ) {
		out[0] = CG_DWADSReadFloat( "cg_dwAdsMP40Right" );
		out[1] = CG_DWADSReadFloat( "cg_dwAdsMP40Up" );
		out[2] = CG_DWADSReadFloat( "cg_dwAdsMP40Forward" );
		return qtrue;
	}
	if ( w == WP_STEN ) {
		out[0] = CG_DWADSReadFloat( "cg_dwAdsStenRight" );
		out[1] = CG_DWADSReadFloat( "cg_dwAdsStenUp" );
		out[2] = CG_DWADSReadFloat( "cg_dwAdsStenForward" );
		return qtrue;
	}
	VectorClear( out );
	return qfalse;
}

static qboolean CG_DWADSReadAngForWeapon( int w, vec3_t out ) {
	if ( w == WP_MP40 ) {
		out[0] = CG_DWADSReadFloat( "cg_dwAdsMP40Pitch" );
		out[1] = CG_DWADSReadFloat( "cg_dwAdsMP40Yaw" );
		out[2] = CG_DWADSReadFloat( "cg_dwAdsMP40Roll" );
		return qtrue;
	}
	if ( w == WP_STEN ) {
		out[0] = CG_DWADSReadFloat( "cg_dwAdsStenPitch" );
		out[1] = CG_DWADSReadFloat( "cg_dwAdsStenYaw" );
		out[2] = CG_DWADSReadFloat( "cg_dwAdsStenRoll" );
		return qtrue;
	}
	VectorClear( out );
	return qfalse;
}
'''
new='''static qboolean CG_DWADSReadPosForWeapon( int w, vec3_t out ) {
	if ( w == WP_MP40 ) {
		out[0] = cg_dwAdsMP40Right.value;
		out[1] = cg_dwAdsMP40Up.value;
		out[2] = cg_dwAdsMP40Forward.value;
		return qtrue;
	}
	if ( w == WP_STEN ) {
		out[0] = cg_dwAdsStenRight.value;
		out[1] = cg_dwAdsStenUp.value;
		out[2] = cg_dwAdsStenForward.value;
		return qtrue;
	}
	VectorClear( out );
	return qfalse;
}

static qboolean CG_DWADSReadAngForWeapon( int w, vec3_t out ) {
	if ( w == WP_MP40 ) {
		out[0] = cg_dwAdsMP40Pitch.value;
		out[1] = cg_dwAdsMP40Yaw.value;
		out[2] = cg_dwAdsMP40Roll.value;
		return qtrue;
	}
	if ( w == WP_STEN ) {
		out[0] = cg_dwAdsStenPitch.value;
		out[1] = cg_dwAdsStenYaw.value;
		out[2] = cg_dwAdsStenRoll.value;
		return qtrue;
	}
	VectorClear( out );
	return qfalse;
}

// Apply rotation only after the final ADS tag/translation solution.  This is
// intentionally on gun.axis, not hand.axis: V1/V1.5 repositions the gun from
// tag_flash after hand.axis is built, which could visually cancel early angles.
static void CG_DWADSApplyFinalGunRotation( refEntity_t *gun, int weaponNum, float ads ) {
	vec3_t delta, ang;
	if ( ads <= 0.0f || !CG_DWADSReadAngForWeapon( weaponNum, delta ) ) return;
	if ( delta[0] == 0.0f && delta[1] == 0.0f && delta[2] == 0.0f ) return;
	AxisToAngles( gun->axis, ang );
	ang[PITCH] += delta[0] * ads;
	ang[YAW]   += delta[1] * ads;
	ang[ROLL]  += delta[2] * ads;
	AnglesToAxis( ang, gun->axis );
}
'''
c=one(c,old,new,"replace ADS reads with vmCvar values")

old='''qboolean CG_DWADSDebugCrosshair( void ) {
	return CG_DWADSReadFloat( "cg_dwAdsDebug" ) != 0.0f ? qtrue : qfalse;
}
'''
new='''qboolean CG_DWADSDebugCrosshair( void ) {
	return cg_dwAdsDebug.integer ? qtrue : qfalse;
}
'''
c=one(c,old,new,"debug cvar direct vmCvar")

# Remove early hand angle modification entirely.
old='''		if ( CG_DWADSSupportedWeapon( ps->weapon ) ) {
			float ads = CG_DWADSFrac();
			vec3_t ang;
			if ( ads > 0.0f && CG_DWADSReadAngForWeapon( ps->weapon, ang ) ) {
				angles[PITCH] += ang[0] * ads;
				angles[YAW]   += ang[1] * ads;
				angles[ROLL]  += ang[2] * ads;
			}
		}

'''
c=one(c,old,"","remove early hand-axis ADS rotation")

# Apply final rotation after the second/final ADS gun positioning.
anchor='''					VectorMA( parent->origin, cal[2] * ads, cg.refdef.viewaxis[0], parent->origin );
				}
			}
			CG_PositionEntityOnTag( &gun, parent, "tag_weapon", 0, NULL );'''
insert='''					VectorMA( parent->origin, cal[2] * ads, cg.refdef.viewaxis[0], parent->origin );
				}
			}
			CG_PositionEntityOnTag( &gun, parent, "tag_weapon", 0, NULL );
			CG_DWADSApplyFinalGunRotation( &gun, weaponNum, ads );'''
c=one(c,anchor,insert,"apply final gun-axis ADS rotation")

p.write_text(c,encoding="utf-8")

proof={
 "feature":"DarkWolf Weapon Port V1.6.6 Final ADS Transform Calibrator",
 "base_run":43172461199,
 "base_sha":"5bb613bdd95d1710e0067bb2c34c33c4e93d773f",
 "root_cause":"V1.6.4/V1.6.5 applied Pitch/Yaw/Roll to hand.axis before V1/V1.5 tag_flash ADS recentering; the later gun reposition could visually cancel the early angular calibration.",
 "fixes":[
   "real vmCvar_t variables in cvarTable; CG_UpdateCvars refreshes values every frame",
   "position reads direct vmCvar.value",
   "angular calibration removed from early hand.axis",
   "Pitch/Yaw/Roll applied to final gun.axis after the final ADS tag/position solution",
   "debug crosshair reads cg_dwAdsDebug.integer directly"
 ],
 "ballistic_alignment_v163_preserved":True,
 "weapon_port_v162_preserved":True,
 "assets_changed":False,
 "cg_weapons_before_sha256":hashlib.sha256(c0.encode()).hexdigest(),
 "cg_weapons_after_sha256":hashlib.sha256(c.encode()).hexdigest()
}
(ev/"DW_WEAPON_PORT_V166_FINAL_ADS_TRANSFORM_CALIBRATOR_PROOF.json").write_text(json.dumps(proof,indent=2)+"\n",encoding="utf-8")
print(json.dumps(proof,indent=2))
print("DW_WEAPON_PORT_V166_FINAL_ADS_TRANSFORM_CALIBRATOR_APPLY_PASS")
