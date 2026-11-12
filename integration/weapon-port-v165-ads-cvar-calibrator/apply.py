#!/usr/bin/env python3
from pathlib import Path
import sys,json,hashlib

MARK="DARKWOLF_WEAPON_PORT_V165_ADS_CVAR_CALIBRATOR"

def fail(m): raise SystemExit(m)
def one(s,a,b,label):
    n=s.count(a)
    if n!=1: fail(f"{label}: expected 1 anchor, got {n}")
    return s.replace(a,b,1)

if len(sys.argv)<2: fail("usage: apply.py <source-root> [evidence-dir]")
root=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/"evidence"
ev.mkdir(parents=True,exist_ok=True)

# ---- cgame ADS calibrator: move state from static variables to engine cvars ----
p=root/"SP/code/cgame/cg_weapons.c"
before=p.read_text(encoding="utf-8")
if MARK in before:
    print("DW_WEAPON_PORT_V165_ALREADY_APPLIED")
    raise SystemExit(0)

old=r'''// DARKWOLF_WEAPON_PORT_V16_EXPANDED_ARSENAL_ADS_CAL
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
		CG_Printf( "DW ADS CAL: actual weapon is not MP40/STEN.\n" );
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
	CG_Printf( "DW ADS CAL %s: right=%.3f up=%.3f forward=%.3f\n",
		w == WP_MP40 ? "MP40" : "STEN", (*cal)[0], (*cal)[1], (*cal)[2] );
	CG_Printf( "Usage: /dw_ads_cal <right> <up> <forward>\n" );
}

void CG_DWADSAng_f( void ) {
	int w = CG_DWADSCurrentWeapon();
	vec3_t *ang = CG_DWADSAngForWeapon( w );
	char a[32], b[32], cbuf[32];
	if ( !ang ) {
		CG_Printf( "DW ADS ANG: actual weapon is not MP40/STEN.\n" );
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
	CG_Printf( "DW ADS ANG %s: pitch=%.3f yaw=%.3f roll=%.3f\n",
		w == WP_MP40 ? "MP40" : "STEN", (*ang)[0], (*ang)[1], (*ang)[2] );
	CG_Printf( "Usage: /dw_ads_ang <pitch> <yaw> <roll>\n" );
}

void CG_DWADSDebug_f( void ) {
	char arg[16];
	if ( trap_Argc() == 2 ) {
		trap_Argv( 1, arg, sizeof(arg) );
		dwAdsDebugCrosshair = atoi( arg ) ? qtrue : qfalse;
	}
	CG_Printf( "DW ADS DEBUG crosshair=%d\n", dwAdsDebugCrosshair ? 1 : 0 );
}

void CG_DWADSReset_f( void ) {
	int w = CG_DWADSCurrentWeapon();
	vec3_t *cal = CG_DWADSCalForWeapon( w );
	vec3_t *ang = CG_DWADSAngForWeapon( w );
	if ( !cal || !ang ) {
		CG_Printf( "DW ADS RESET: actual weapon is not MP40/STEN.\n" );
		return;
	}
	VectorClear( *cal );
	VectorClear( *ang );
	CG_DWADSCal_f();
	CG_DWADSAng_f();
}
'''

new=r'''// DARKWOLF_WEAPON_PORT_V165_ADS_CVAR_CALIBRATOR
// Calibration state now lives in normal engine cvars.  This makes the values
// immediately observable/editable from the console and removes dependency on
// transient cgame-local static state.
static int CG_DWADSCurrentWeapon( void ) {
	int w = cg.predictedPlayerState.weapon;
	if ( CG_DWADSSupportedWeapon( w ) ) return w;
	w = cg.weaponSelect;
	if ( CG_DWADSSupportedWeapon( w ) ) return w;
	return WP_NONE;
}

static float CG_DWADSReadFloat( const char *name ) {
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

static void CG_DWADSSetPosForWeapon( int w, const char *a, const char *b, const char *c ) {
	if ( w == WP_MP40 ) {
		trap_Cvar_Set( "cg_dwAdsMP40Right", a );
		trap_Cvar_Set( "cg_dwAdsMP40Up", b );
		trap_Cvar_Set( "cg_dwAdsMP40Forward", c );
	} else if ( w == WP_STEN ) {
		trap_Cvar_Set( "cg_dwAdsStenRight", a );
		trap_Cvar_Set( "cg_dwAdsStenUp", b );
		trap_Cvar_Set( "cg_dwAdsStenForward", c );
	}
}

static void CG_DWADSSetAngForWeapon( int w, const char *a, const char *b, const char *c ) {
	if ( w == WP_MP40 ) {
		trap_Cvar_Set( "cg_dwAdsMP40Pitch", a );
		trap_Cvar_Set( "cg_dwAdsMP40Yaw", b );
		trap_Cvar_Set( "cg_dwAdsMP40Roll", c );
	} else if ( w == WP_STEN ) {
		trap_Cvar_Set( "cg_dwAdsStenPitch", a );
		trap_Cvar_Set( "cg_dwAdsStenYaw", b );
		trap_Cvar_Set( "cg_dwAdsStenRoll", c );
	}
}

qboolean CG_DWADSDebugCrosshair( void ) {
	return CG_DWADSReadFloat( "cg_dwAdsDebug" ) != 0.0f ? qtrue : qfalse;
}

void CG_DWADSCal_f( void ) {
	int w = CG_DWADSCurrentWeapon();
	vec3_t cal;
	char a[32], b[32], cbuf[32];
	if ( !CG_DWADSSupportedWeapon( w ) ) {
		CG_Printf( "DW ADS CAL: actual weapon is not MP40/STEN.\n" );
		return;
	}
	if ( trap_Argc() == 4 ) {
		trap_Argv( 1, a, sizeof(a) );
		trap_Argv( 2, b, sizeof(b) );
		trap_Argv( 3, cbuf, sizeof(cbuf) );
		CG_DWADSSetPosForWeapon( w, a, b, cbuf );
	}
	CG_DWADSReadPosForWeapon( w, cal );
	CG_Printf( "DW ADS CAL %s: right=%.3f up=%.3f forward=%.3f\n",
		w == WP_MP40 ? "MP40" : "STEN", cal[0], cal[1], cal[2] );
	CG_Printf( "Direct cvars are also available: cg_dwAds*Right / Up / Forward.\n" );
}

void CG_DWADSAng_f( void ) {
	int w = CG_DWADSCurrentWeapon();
	vec3_t ang;
	char a[32], b[32], cbuf[32];
	if ( !CG_DWADSSupportedWeapon( w ) ) {
		CG_Printf( "DW ADS ANG: actual weapon is not MP40/STEN.\n" );
		return;
	}
	if ( trap_Argc() == 4 ) {
		trap_Argv( 1, a, sizeof(a) );
		trap_Argv( 2, b, sizeof(b) );
		trap_Argv( 3, cbuf, sizeof(cbuf) );
		CG_DWADSSetAngForWeapon( w, a, b, cbuf );
	}
	CG_DWADSReadAngForWeapon( w, ang );
	CG_Printf( "DW ADS ANG %s: pitch=%.3f yaw=%.3f roll=%.3f\n",
		w == WP_MP40 ? "MP40" : "STEN", ang[0], ang[1], ang[2] );
	CG_Printf( "Direct cvars are also available: cg_dwAds*Pitch / Yaw / Roll.\n" );
}

void CG_DWADSDebug_f( void ) {
	char arg[16];
	if ( trap_Argc() == 2 ) {
		trap_Argv( 1, arg, sizeof(arg) );
		trap_Cvar_Set( "cg_dwAdsDebug", atoi( arg ) ? "1" : "0" );
	}
	CG_Printf( "DW ADS DEBUG crosshair=%d\n", CG_DWADSDebugCrosshair() ? 1 : 0 );
}

void CG_DWADSReset_f( void ) {
	int w = CG_DWADSCurrentWeapon();
	if ( !CG_DWADSSupportedWeapon( w ) ) {
		CG_Printf( "DW ADS RESET: actual weapon is not MP40/STEN.\n" );
		return;
	}
	CG_DWADSSetPosForWeapon( w, "0", "0", "0" );
	CG_DWADSSetAngForWeapon( w, "0", "0", "0" );
	CG_DWADSCal_f();
	CG_DWADSAng_f();
}
'''

s=one(before,old,new,"replace static ADS calibration state with cvars")

old=r'''			{
				vec3_t *cal = CG_DWADSCalForWeapon( weaponNum );
				if ( cal ) {
					VectorMA( parent->origin, (*cal)[0] * ads, cg.refdef.viewaxis[1], parent->origin );
					VectorMA( parent->origin, (*cal)[1] * ads, cg.refdef.viewaxis[2], parent->origin );
					VectorMA( parent->origin, (*cal)[2] * ads, cg.refdef.viewaxis[0], parent->origin );
				}
			}
'''
new=r'''			{
				vec3_t cal;
				if ( CG_DWADSReadPosForWeapon( weaponNum, cal ) ) {
					VectorMA( parent->origin, cal[0] * ads, cg.refdef.viewaxis[1], parent->origin );
					VectorMA( parent->origin, cal[1] * ads, cg.refdef.viewaxis[2], parent->origin );
					VectorMA( parent->origin, cal[2] * ads, cg.refdef.viewaxis[0], parent->origin );
				}
			}
'''
s=one(s,old,new,"render position from cvars")

old=r'''		if ( CG_DWADSSupportedWeapon( ps->weapon ) ) {
			float ads = CG_DWADSFrac();
			vec3_t *ang = CG_DWADSAngForWeapon( ps->weapon );
			if ( ads > 0.0f && ang ) {
				angles[PITCH] += (*ang)[0] * ads;
				angles[YAW]   += (*ang)[1] * ads;
				angles[ROLL]  += (*ang)[2] * ads;
			}
		}
'''
new=r'''		if ( CG_DWADSSupportedWeapon( ps->weapon ) ) {
			float ads = CG_DWADSFrac();
			vec3_t ang;
			if ( ads > 0.0f && CG_DWADSReadAngForWeapon( ps->weapon, ang ) ) {
				angles[PITCH] += ang[0] * ads;
				angles[YAW]   += ang[1] * ads;
				angles[ROLL]  += ang[2] * ads;
			}
		}
'''
s=one(s,old,new,"render angles from cvars")
p.write_text(s,encoding="utf-8")

# Register the calibration cvars in the engine so they are direct console commands
# and CVAR_ARCHIVE persists final user calibration.
p=root/"SP/code/cgame/cg_main.c"
m0=p.read_text(encoding="utf-8")
anchor=r'''	for ( i = 0, cv = cvarTable ; i < cvarTableSize ; i++, cv++ ) {
		trap_Cvar_Register( cv->vmCvar, cv->cvarName,
							cv->defaultString, cv->cvarFlags );
	}

	// see if we are also running the server on this machine
'''
insert=r'''	for ( i = 0, cv = cvarTable ; i < cvarTableSize ; i++, cv++ ) {
		trap_Cvar_Register( cv->vmCvar, cv->cvarName,
							cv->defaultString, cv->cvarFlags );
	}

	// DARKWOLF_WEAPON_PORT_V165_ADS_CVAR_CALIBRATOR
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

	// see if we are also running the server on this machine
'''
m=one(m0,anchor,insert,"register ADS calibration cvars")
p.write_text(m,encoding="utf-8")

proof={
  "feature":"DarkWolf Weapon Port V1.6.5 ADS Cvar Calibrator",
  "base_run":43171019287,
  "base_sha":"18143137440f926166461c3e03090b3b7b8082b5",
  "root_problem":"V1.6.4 command handlers existed in the shipped DLL, but calibration depended on transient cgame-local static state and was not reliably observable/applied in the user's runtime.",
  "fixes":[
    "ADS calibration values moved to registered CVAR_ARCHIVE engine cvars",
    "renderer reads cvars every frame",
    "dw_ads_cal/dw_ads_ang wrappers now write the same cvars",
    "cg_dwAdsDebug directly controls ADS center crosshair",
    "values persist in config"
  ],
  "ballistics_v163_preserved":True,
  "arsenal_v162_preserved":True,
  "assets_changed":False,
  "cgame_before_sha256":hashlib.sha256(before.encode()).hexdigest(),
  "cgame_after_sha256":hashlib.sha256(s.encode()).hexdigest()
}
(ev/"DW_WEAPON_PORT_V165_ADS_CVAR_CALIBRATOR_PROOF.json").write_text(json.dumps(proof,indent=2)+"\n",encoding="utf-8")
print(json.dumps(proof,indent=2))
print("DW_WEAPON_PORT_V165_ADS_CVAR_CALIBRATOR_APPLY_PASS")
