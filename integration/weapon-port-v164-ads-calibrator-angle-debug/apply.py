#!/usr/bin/env python3
from pathlib import Path
import sys,json,hashlib

MARK="DARKWOLF_WEAPON_PORT_V164_ADS_CALIBRATOR_ANGLE_DEBUG"

def fail(m): raise SystemExit(m)
def one(s,a,b,label):
    n=s.count(a)
    if n!=1: fail(f"{label}: expected 1 anchor, got {n}")
    return s.replace(a,b,1)

if len(sys.argv)<2: fail("usage: apply.py <source-root> [evidence-dir]")
root=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/"evidence"
ev.mkdir(parents=True,exist_ok=True)

# ---- cg_weapons: robust current-weapon selection + angular calibration ----
p=root/"SP/code/cgame/cg_weapons.c"
before=p.read_text(encoding="utf-8")
if MARK in before:
    print("DW_WEAPON_PORT_V164_ALREADY_APPLIED")
    raise SystemExit(0)

s=before
old='''// DARKWOLF_WEAPON_PORT_V16_EXPANDED_ARSENAL_ADS_CAL
static vec3_t dwAdsCalMP40 = { 0.0f, 0.0f, 0.0f }; // right, up, forward
static vec3_t dwAdsCalSten = { 0.0f, 0.0f, 0.0f };

static vec3_t *CG_DWADSCalCurrent( void ) {
	if ( cg.weaponSelect == WP_MP40 ) return &dwAdsCalMP40;
	if ( cg.weaponSelect == WP_STEN ) return &dwAdsCalSten;
	return NULL;
}

void CG_DWADSCal_f( void ) {
	vec3_t *cal = CG_DWADSCalCurrent();
	char a[32], b[32], cbuf[32];
	if ( !cal ) {
		CG_Printf( "DW ADS CAL: select MP40 or STEN first.\\n" );
		return;
	}
	if ( trap_Argc() == 4 ) {
		trap_Argv( 1, a, sizeof(a) );
		trap_Argv( 2, b, sizeof(b) );
		trap_Argv( 3, cbuf, sizeof(cbuf) );
		(*cal)[0] = atof( a );
		(*cal)[1] = atof( b );
		(*cal)[2] = atof( cbuf );
	}
	CG_Printf( "DW ADS CAL %s: right=%.3f up=%.3f forward=%.3f\\n",
		cg.weaponSelect == WP_MP40 ? "MP40" : "STEN", (*cal)[0], (*cal)[1], (*cal)[2] );
	CG_Printf( "Usage: /dw_ads_cal <right> <up> <forward> ; negative up moves sight down.\\n" );
}

void CG_DWADSReset_f( void ) {
	vec3_t *cal = CG_DWADSCalCurrent();
	if ( !cal ) {
		CG_Printf( "DW ADS RESET: select MP40 or STEN first.\\n" );
		return;
	}
	VectorClear( *cal );
	CG_DWADSCal_f();
}
'''
new='''// DARKWOLF_WEAPON_PORT_V16_EXPANDED_ARSENAL_ADS_CAL
static vec3_t dwAdsCalMP40 = { 0.0f, 0.0f, 0.0f }; // right, up, forward
static vec3_t dwAdsCalSten = { 0.0f, 0.0f, 0.0f };

// DARKWOLF_WEAPON_PORT_V164_ADS_CALIBRATOR_ANGLE_DEBUG
// Angular calibration is separate from translational calibration because
// aligning a true iron-sight line requires changing the viewmodel direction,
// not only sliding the complete model on screen.
static vec3_t dwAdsAngMP40 = { 0.0f, 0.0f, 0.0f }; // pitch, yaw, roll
static vec3_t dwAdsAngSten = { 0.0f, 0.0f, 0.0f };
static qboolean dwAdsDebugCrosshair = qfalse;

static int CG_DWADSCurrentWeapon( void ) {
	int w = cg.predictedPlayerState.weapon;
	if ( CG_DWADSSupportedWeapon( w ) ) return w;
	w = cg.weaponSelect;
	if ( CG_DWADSSupportedWeapon( w ) ) return w;
	return WP_NONE;
}

static vec3_t *CG_DWADSCalForWeapon( int w ) {
	if ( w == WP_MP40 ) return &dwAdsCalMP40;
	if ( w == WP_STEN ) return &dwAdsCalSten;
	return NULL;
}

static vec3_t *CG_DWADSAngForWeapon( int w ) {
	if ( w == WP_MP40 ) return &dwAdsAngMP40;
	if ( w == WP_STEN ) return &dwAdsAngSten;
	return NULL;
}

static vec3_t *CG_DWADSCalCurrent( void ) {
	return CG_DWADSCalForWeapon( CG_DWADSCurrentWeapon() );
}

static vec3_t *CG_DWADSAngCurrent( void ) {
	return CG_DWADSAngForWeapon( CG_DWADSCurrentWeapon() );
}

qboolean CG_DWADSDebugCrosshair( void ) {
	return dwAdsDebugCrosshair;
}

void CG_DWADSCal_f( void ) {
	int w = CG_DWADSCurrentWeapon();
	vec3_t *cal = CG_DWADSCalForWeapon( w );
	char a[32], b[32], cbuf[32];
	if ( !cal ) {
		CG_Printf( "DW ADS CAL: actual weapon is not MP40/STEN.\\n" );
		return;
	}
	if ( trap_Argc() == 4 ) {
		trap_Argv( 1, a, sizeof(a) );
		trap_Argv( 2, b, sizeof(b) );
		trap_Argv( 3, cbuf, sizeof(cbuf) );
		(*cal)[0] = atof( a );
		(*cal)[1] = atof( b );
		(*cal)[2] = atof( cbuf );
	}
	CG_Printf( "DW ADS CAL %s: right=%.3f up=%.3f forward=%.3f\\n",
		w == WP_MP40 ? "MP40" : "STEN", (*cal)[0], (*cal)[1], (*cal)[2] );
	CG_Printf( "Usage: /dw_ads_cal <right> <up> <forward>\\n" );
}

void CG_DWADSAng_f( void ) {
	int w = CG_DWADSCurrentWeapon();
	vec3_t *ang = CG_DWADSAngForWeapon( w );
	char a[32], b[32], cbuf[32];
	if ( !ang ) {
		CG_Printf( "DW ADS ANG: actual weapon is not MP40/STEN.\\n" );
		return;
	}
	if ( trap_Argc() == 4 ) {
		trap_Argv( 1, a, sizeof(a) );
		trap_Argv( 2, b, sizeof(b) );
		trap_Argv( 3, cbuf, sizeof(cbuf) );
		(*ang)[0] = atof( a );
		(*ang)[1] = atof( b );
		(*ang)[2] = atof( cbuf );
	}
	CG_Printf( "DW ADS ANG %s: pitch=%.3f yaw=%.3f roll=%.3f\\n",
		w == WP_MP40 ? "MP40" : "STEN", (*ang)[0], (*ang)[1], (*ang)[2] );
	CG_Printf( "Usage: /dw_ads_ang <pitch> <yaw> <roll>\\n" );
}

void CG_DWADSDebug_f( void ) {
	char arg[16];
	if ( trap_Argc() == 2 ) {
		trap_Argv( 1, arg, sizeof(arg) );
		dwAdsDebugCrosshair = atoi( arg ) ? qtrue : qfalse;
	}
	CG_Printf( "DW ADS DEBUG crosshair=%d\\n", dwAdsDebugCrosshair ? 1 : 0 );
}

void CG_DWADSReset_f( void ) {
	int w = CG_DWADSCurrentWeapon();
	vec3_t *cal = CG_DWADSCalForWeapon( w );
	vec3_t *ang = CG_DWADSAngForWeapon( w );
	if ( !cal || !ang ) {
		CG_Printf( "DW ADS RESET: actual weapon is not MP40/STEN.\\n" );
		return;
	}
	VectorClear( *cal );
	VectorClear( *ang );
	CG_DWADSCal_f();
	CG_DWADSAng_f();
}
'''
s=one(s,old,new,"replace ADS calibrator core")

# Existing positional calibration must use the exact weapon being rendered,
# not an implicit MP40 fallback.
old='''			{
				vec3_t *cal = ( weaponNum == WP_STEN ) ? &dwAdsCalSten : &dwAdsCalMP40;
				VectorMA( parent->origin, (*cal)[0] * ads, cg.refdef.viewaxis[1], parent->origin );
				VectorMA( parent->origin, (*cal)[1] * ads, cg.refdef.viewaxis[2], parent->origin );
				VectorMA( parent->origin, (*cal)[2] * ads, cg.refdef.viewaxis[0], parent->origin );
			}
'''
new='''			{
				vec3_t *cal = CG_DWADSCalForWeapon( weaponNum );
				if ( cal ) {
					VectorMA( parent->origin, (*cal)[0] * ads, cg.refdef.viewaxis[1], parent->origin );
					VectorMA( parent->origin, (*cal)[1] * ads, cg.refdef.viewaxis[2], parent->origin );
					VectorMA( parent->origin, (*cal)[2] * ads, cg.refdef.viewaxis[0], parent->origin );
				}
			}
'''
s=one(s,old,new,"render positional calibration exact weapon")

# Angular calibration is applied to the hand/viewmodel orientation before
# AnglesToAxis(), so the complete weapon hierarchy rotates together.
old='''		VectorMA( hand.origin, ( gunoff[2] + fovOffset[2] ), cg.refdef.viewaxis[2], hand.origin );

		AnglesToAxis( angles, hand.axis );
'''
new='''		VectorMA( hand.origin, ( gunoff[2] + fovOffset[2] ), cg.refdef.viewaxis[2], hand.origin );

		if ( CG_DWADSSupportedWeapon( ps->weapon ) ) {
			float ads = CG_DWADSFrac();
			vec3_t *ang = CG_DWADSAngForWeapon( ps->weapon );
			if ( ads > 0.0f && ang ) {
				angles[PITCH] += (*ang)[0] * ads;
				angles[YAW]   += (*ang)[1] * ads;
				angles[ROLL]  += (*ang)[2] * ads;
			}
		}

		AnglesToAxis( angles, hand.axis );
'''
s=one(s,old,new,"apply angular calibration in CG_AddViewWeapon")

p.write_text(s,encoding="utf-8")

# ---- cg_local prototypes ----
p=root/"SP/code/cgame/cg_local.h"
h0=p.read_text(encoding="utf-8")
old='''void CG_DWADSCal_f( void );
void CG_DWADSReset_f( void );
'''
new='''void CG_DWADSCal_f( void );
void CG_DWADSAng_f( void );
void CG_DWADSDebug_f( void );
void CG_DWADSReset_f( void );
qboolean CG_DWADSDebugCrosshair( void );
'''
h=one(h0,old,new,"ADS calibrator prototypes")
p.write_text(h,encoding="utf-8")

# ---- console command registration ----
p=root/"SP/code/cgame/cg_consolecmds.c"
cc0=p.read_text(encoding="utf-8")
old='''static consoleCommand_t commands[] = {
	{ "dw_ads_cal", CG_DWADSCal_f },
	{ "dw_ads_reset", CG_DWADSReset_f },
	{ "testgun", CG_TestGun_f },'''
new='''static consoleCommand_t commands[] = {
	{ "dw_ads_cal", CG_DWADSCal_f },
	{ "dw_ads_ang", CG_DWADSAng_f },
	{ "dw_ads_debug", CG_DWADSDebug_f },
	{ "dw_ads_reset", CG_DWADSReset_f },
	{ "testgun", CG_TestGun_f },'''
cc=one(cc0,old,new,"ADS calibrator console commands")
p.write_text(cc,encoding="utf-8")

# ---- crosshair visibility in debug calibration mode ----
p=root/"SP/code/cgame/cg_draw.c"
d0=p.read_text(encoding="utf-8")
old='''	if ( CG_DWADSFrac() > 0.75f ) return; // DARKWOLF_WEAPON_PORT_V1_MP44_PPSH_ADS
'''
new='''	if ( CG_DWADSFrac() > 0.75f && !CG_DWADSDebugCrosshair() ) return; // DARKWOLF_WEAPON_PORT_V164_ADS_CALIBRATOR_ANGLE_DEBUG
'''
d=one(d0,old,new,"ADS debug crosshair gate")
p.write_text(d,encoding="utf-8")

proof={
  "feature":"DarkWolf Weapon Port V1.6.4 ADS Calibrator Angle + Debug",
  "base_run":43168374368,
  "base_sha":"b456bb10be1fd5427873a92218628072b5f1a85a",
  "scope":["SP/code/cgame/cg_weapons.c","SP/code/cgame/cg_consolecmds.c","SP/code/cgame/cg_local.h","SP/code/cgame/cg_draw.c"],
  "fixes":[
    "dw_ads_cal targets cg.predictedPlayerState.weapon first, not only cg.weaponSelect",
    "new dw_ads_ang pitch/yaw/roll calibration rotates complete viewmodel",
    "new dw_ads_debug 1 keeps exact center crosshair visible during ADS calibration",
    "dw_ads_reset resets both position and angle for current MP40/STEN"
  ],
  "ballistic_alignment_v163_preserved":True,
  "ported_weapons_changed":False,
  "assets_changed":False,
  "server_gameplay_changed":False,
  "cgame_before_sha256":hashlib.sha256(before.encode()).hexdigest(),
  "cgame_after_sha256":hashlib.sha256(s.encode()).hexdigest()
}
(ev/"DW_WEAPON_PORT_V164_ADS_CALIBRATOR_ANGLE_DEBUG_PROOF.json").write_text(json.dumps(proof,indent=2)+"\n",encoding="utf-8")
print(json.dumps(proof,indent=2))
print("DW_WEAPON_PORT_V164_ADS_CALIBRATOR_ANGLE_DEBUG_APPLY_PASS")
