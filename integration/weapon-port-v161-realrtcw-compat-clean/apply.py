#!/usr/bin/env python3
from pathlib import Path
import sys,json,hashlib

MARK="DARKWOLF_WEAPON_PORT_V161_REALRTCW_COMPAT_CLEAN"

def fail(m): raise SystemExit(m)
def one(s,a,b,label):
    n=s.count(a)
    if n!=1: fail(f"{label}: expected 1 anchor, got {n}")
    return s.replace(a,b,1)

if len(sys.argv)<2: fail("usage: apply.py <source-root> [evidence-dir]")
root=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/"evidence"
ev.mkdir(parents=True,exist_ok=True)

# V1.6.1 is intentionally a compatibility cleanup on top of the V1.6 gameplay/id expansion.
p=root/"SP/code/cgame/cg_weapons.c"
c0=p.read_text(encoding="utf-8")
if MARK in c0:
    print("DW_WEAPON_PORT_V161_ALREADY_APPLIED")
    raise SystemExit(0)
for req in (
    "DARKWOLF_WEAPON_PORT_V14_COMPONENT_ANIM_INDEX_SAFETY",
    "DARKWOLF_WEAPON_PORT_V15_FULL_FIRE_ADS_RELOAD",
    "DARKWOLF_WEAPON_PORT_V16_EXPANDED_ARSENAL_ADS_CAL",
):
    if req not in c0: fail("V1.6.1 missing prerequisite "+req)
if "DARKWOLF_WEAPON_PORT_V13_FP_ATTACK_ANIM_SAFE" in c0:
    fail("V1.6.1 must not inherit V1.3 hand-frame freeze")

c=c0

# ----------------------------------------------------------------------
# Exact RealRTCW first-person part map.
# Do NOT infer every _barrelN file.  RealRTCW .weap files explicitly choose
# which components are linked; several packages contain files that must not be
# drawn (M1 barrel5) and several weapons use parts above old ioRTCW W_MAX_PARTS.
# All mapped component models are static one-frame meshes in the supplied pack,
# so they do not use the legacy component animation bitfield at all.
# ----------------------------------------------------------------------
anchor='''static qboolean debuggingweapon = qfalse;

void CG_AddPlayerWeapon( refEntity_t *parent, playerState_t *ps, centity_t *cent ) {
'''
helper=r'''// DARKWOLF_WEAPON_PORT_V161_REALRTCW_COMPAT_CLEAN
#define DW_V161_MAX_IMPORT_PARTS 12
static qhandle_t dwV161PartModels[MAX_WEAPONS][DW_V161_MAX_IMPORT_PARTS];
static qboolean dwV161PartsRegistered[MAX_WEAPONS];

static qboolean DW_V161IsImportedWeapon( int weaponNum ) {
	return (qboolean)( weaponNum >= WP_DW_MP34 && weaponNum <= WP_DW_MG42M );
}

static const char *DW_V161PartModelPath( int weaponNum, int part ) {
	switch ( weaponNum ) {
	case WP_DW_MP34:
		switch ( part ) {
		case 0: return "models/weapons/smgs/mp34/v_mp34_barrel.md3";
		case 1: return "models/weapons/smgs/mp34/v_mp34_barrel2.md3";
		case 2: return "models/weapons/smgs/mp34/v_mp34_barrel3.md3";
		} break;
	case WP_DW_BAR:
		// RealRTCW definition references barrel1, but it is absent from the
		// supplied model pack.  Register only components that really exist.
		switch ( part ) {
		case 1: return "models/weapons/assault_rifles/bar/v_bar_barrel2.md3";
		case 2: return "models/weapons/assault_rifles/bar/v_bar_barrel3.md3";
		case 3: return "models/weapons/assault_rifles/bar/v_bar_barrel4.md3";
		} break;
	case WP_DW_TT33:
		switch ( part ) {
		case 1: return "models/weapons/pistols/tt33/v_tt33_barrel2.md3";
		case 2: return "models/weapons/pistols/tt33/v_tt33_barrel3.md3";
		case 3: return "models/weapons/pistols/tt33/v_tt33_barrel4.md3";
		} break;
	case WP_DW_DUAL_TT33:
		switch ( part ) {
		case 0: return "models/weapons/pistols/tt33_2/v_tt33_2_barrel.md3";
		case 1: return "models/weapons/pistols/tt33_2/v_tt33_2_barrel2.md3";
		case 2: return "models/weapons/pistols/tt33_2/v_tt33_2_barrel3.md3";
		case 3: return "models/weapons/pistols/tt33_2/v_tt33_2_barrel4.md3";
		case 4: return "models/weapons/pistols/tt33_2/v_tt33_2_barrel5.md3";
		} break;
	case WP_DW_REVOLVER:
		switch ( part ) {
		case 0: return "models/weapons/pistols/revolver/v_revolver_barrel.md3";
		case 1: return "models/weapons/pistols/revolver/v_revolver_barrel2.md3";
		case 2: return "models/weapons/pistols/revolver/v_revolver_barrel3.md3";
		case 3: return "models/weapons/pistols/revolver/v_revolver_barrel4.md3";
		case 4: return "models/weapons/pistols/revolver/v_revolver_barrel5.md3";
		case 5: return "models/weapons/pistols/revolver/v_revolver_barrel6.md3";
		case 8: return "models/weapons/pistols/revolver/v_revolver_barrel9.md3";
		} break;
	case WP_DW_HDM:
		// As with BAR, v_hdm_barrel.md3 is referenced by the script but absent
		// from the supplied model pack.  Do not fabricate or alias it.
		switch ( part ) {
		case 1: return "models/weapons/pistols/hdm/v_hdm_barrel2.md3";
		case 2: return "models/weapons/pistols/hdm/v_hdm_barrel3.md3";
		case 3: return "models/weapons/pistols/hdm/v_hdm_barrel4.md3";
		} break;
	case WP_DW_MOSIN:
		switch ( part ) {
		case 0: return "models/weapons/rifles/mosin/v_mosin_barrel.md3";
		case 2: return "models/weapons/rifles/mosin/v_mosin_barrel3.md3";
		case 3: return "models/weapons/rifles/mosin/v_mosin_barrel4.md3";
		} break;
	case WP_DW_M1GARAND:
		switch ( part ) {
		case 0: return "models/weapons/auto_rifles/m1_garand/v_m1_barrel.md3";
		case 2: return "models/weapons/auto_rifles/m1_garand/v_m1_barrel3.md3";
		case 3: return "models/weapons/auto_rifles/m1_garand/v_m1_barrel4.md3";
		// v_m1_barrel5.md3 exists but is NOT linked by RealRTCW: deliberately skip it.
		case 5: return "models/weapons/auto_rifles/m1_garand/v_m1_barrel6.md3";
		} break;
	case WP_DW_G43:
		switch ( part ) {
		case 0: return "models/weapons/auto_rifles/g43/v_g43_barrel.md3";
		case 1: return "models/weapons/auto_rifles/g43/v_g43_barrel2.md3";
		case 2: return "models/weapons/auto_rifles/g43/v_g43_barrel3.md3";
		} break;
	case WP_DW_M97:
		switch ( part ) {
		case 4: return "models/weapons/shotguns/ithaca/v_ithaca_barrel5.md3";
		case 8: return "models/weapons/shotguns/ithaca/v_ithaca_barrel9.md3";
		case 9: return "models/weapons/shotguns/ithaca/v_ithaca_barrel10.md3";
		} break;
	case WP_DW_BROWNING:
		switch ( part ) {
		case 0: return "models/weapons/heavy/browning/v_brown30cal_barrel.md3";
		case 1: return "models/weapons/heavy/browning/v_brown30cal_barrel2.md3";
		case 2: return "models/weapons/heavy/browning/v_brown30cal_barrel3.md3";
		} break;
	case WP_DW_MG42M:
		switch ( part ) {
		case 0: return "models/weapons/heavy/mg42/v_mg42_barrel.md3";
		case 1: return "models/weapons/heavy/mg42/v_mg42_barrel2.md3";
		} break;
	default:
		break;
	}
	return NULL;
}

static const char *DW_V161PartTagName( int part ) {
	if ( part == 0 ) return "tag_barrel";
	return va( "tag_barrel%d", part + 1 );
}

static qboolean DW_V161TagExists( const refEntity_t *parent, const char *tagName ) {
	orientation_t tag;
	return (qboolean)( trap_R_LerpTag( &tag, parent, tagName, 0 ) >= 0 );
}

static void DW_V161RegisterParts( int weaponNum ) {
	int i;
	if ( weaponNum < 0 || weaponNum >= MAX_WEAPONS || !DW_V161IsImportedWeapon( weaponNum ) ) return;
	if ( dwV161PartsRegistered[weaponNum] ) return;
	dwV161PartsRegistered[weaponNum] = qtrue;
	for ( i = 0; i < DW_V161_MAX_IMPORT_PARTS; i++ ) {
		const char *path = DW_V161PartModelPath( weaponNum, i );
		if ( path && path[0] ) {
			dwV161PartModels[weaponNum][i] = trap_R_RegisterModel( path );
		}
	}
}

static void DW_V161AddImportedParts( refEntity_t *parent, playerState_t *ps, centity_t *cent, int weaponNum, qboolean drawrealweap ) {
	int i;
	refEntity_t part;
	if ( !ps || !drawrealweap ) return;
	DW_V161RegisterParts( weaponNum );
	for ( i = 0; i < DW_V161_MAX_IMPORT_PARTS; i++ ) {
		const char *tagName;
		qhandle_t model = dwV161PartModels[weaponNum][i];
		if ( !model ) continue;
		tagName = DW_V161PartTagName( i );
		if ( !DW_V161TagExists( parent, tagName ) ) {
			if ( cg_debugAnim.integer & 8 ) {
				CG_Printf( "DW_V161_SKIP_PART weapon=%d part=%d missingTag=%s\n", weaponNum, i, tagName );
			}
			continue;
		}
		memset( &part, 0, sizeof(part) );
		VectorCopy( parent->lightingOrigin, part.lightingOrigin );
		part.shadowPlane = parent->shadowPlane;
		part.renderfx = parent->renderfx;
		part.hModel = model;
		AxisClear( part.axis );
		CG_PositionEntityOnTag( &part, parent, (char *)tagName, 0, NULL );
		// Supplied RealRTCW component meshes are static one-frame models.
		part.frame = part.oldframe = 0;
		part.backlerp = 0;
		CG_AddWeaponWithPowerups( &part, cent->currentState.powerups, ps, cent );
	}
}

static void DW_V161ApplyWeaponPosition( int weaponNum, vec3_t origin ) {
	vec3_t off;
	VectorClear( off );
	switch ( weaponNum ) {
	case WP_DW_MP34:     VectorSet( off, -12, -1,  0 ); break;
	case WP_DW_BAR:      VectorSet( off,  -2, -1, -1 ); break;
	case WP_DW_TT33:     VectorSet( off,   0,  0, -1 ); break;
	case WP_DW_DUAL_TT33:VectorSet( off,   0,  0,  0 ); break;
	case WP_DW_REVOLVER: VectorSet( off,   0,  0,  0 ); break;
	case WP_DW_HDM:      VectorSet( off,   0,  0, -1 ); break;
	case WP_DW_MOSIN:    VectorSet( off,   0,  0, -1 ); break;
	case WP_DW_M1GARAND: VectorSet( off,   0,  0, -2 ); break;
	case WP_DW_G43:      VectorSet( off,   1,  0, -1 ); break;
	case WP_DW_M97:      VectorSet( off,  -3,  0, -1 ); break;
	case WP_DW_BROWNING: VectorSet( off,  -6,  0,  0 ); break;
	case WP_DW_MG42M:    VectorSet( off,   2, -3, -4 ); break;
	default: return;
	}
	VectorMA( origin, off[0], cg.refdef.viewaxis[0], origin );
	VectorMA( origin, off[1], cg.refdef.viewaxis[1], origin );
	VectorMA( origin, off[2], cg.refdef.viewaxis[2], origin );
}

static qboolean debuggingweapon = qfalse;

void CG_AddPlayerWeapon( refEntity_t *parent, playerState_t *ps, centity_t *cent ) {
'''
c=one(c,anchor,helper,"insert RealRTCW compatibility helpers")

# Safe brass tag lookup.  A missing tag must never produce a bogus ejection origin.
old=r'''	if ( isPlayer ) {
		refEntity_t brass;

		// opposite tag in akimbo, since at this point the weapon
		// has fired and the fire seq has switched over
		if ( weaponNum == WP_AKIMBO && akimboFire ) {
			CG_PositionRotatedEntityOnTag( &brass, &gun, "tag_brass2" );
		} else {
			CG_PositionRotatedEntityOnTag( &brass, &gun, "tag_brass" );
		}

		VectorCopy( brass.origin, ejectBrassCasingOrigin );
	}
'''
new=r'''	if ( isPlayer ) {
		refEntity_t brass;
		const char *brassTag = ( weaponNum == WP_AKIMBO && akimboFire ) ? "tag_brass2" : "tag_brass";
		memset( &brass, 0, sizeof(brass) );
		AxisClear( brass.axis );
		if ( DW_V161TagExists( &gun, brassTag ) ) {
			CG_PositionRotatedEntityOnTag( &brass, &gun, (char *)brassTag );
			VectorCopy( brass.origin, ejectBrassCasingOrigin );
		} else {
			// Revolver in the supplied RealRTCW model set has no tag_brass.
			// Fall back to a finite, valid origin; its brass effect is disabled below.
			VectorCopy( gun.origin, ejectBrassCasingOrigin );
			if ( DW_V161IsImportedWeapon( weaponNum ) && ( cg_debugAnim.integer & 8 ) ) {
				CG_Printf( "DW_V161_NO_BRASS_TAG weapon=%d tag=%s\n", weaponNum, brassTag );
			}
		}
	}
'''
c=one(c,old,new,"safe brass tag lookup")

# Bypass old filename-inference/W_MAX_PARTS=7 path for new V1.6 weapons.
old='''	if ( ps ) {
		qboolean spunpart;
'''
new='''	if ( ps && DW_V161IsImportedWeapon( weaponNum ) ) {
		DW_V161AddImportedParts( parent, ps, cent, weaponNum, drawrealweap );
	} else if ( ps ) {
		qboolean spunpart;
'''
c=one(c,old,new,"explicit imported component path")

# Revolver correctly has no ejected casing in RealRTCW.  Do not run a generic
# machinegun brass path against a weapon with no brass tag.
old='''	case WP_DW_REVOLVER:
		MAKERGB( weaponInfo->flashDlightColor, 1.0, 0.6, 0.23 );
		weaponInfo->flashSound[0]=trap_S_RegisterSound("sound/weapons/revolver/revolver_fire.wav");
		weaponInfo->flashEchoSound[0]=trap_S_RegisterSound("sound/weapons/revolver/revolver_far.wav");
		weaponInfo->reloadSound=trap_S_RegisterSound("sound/weapons/revolver/revolver_reload.wav");
		weaponInfo->ejectBrassFunc=CG_MachineGunEjectBrass; break;
'''
new='''	case WP_DW_REVOLVER:
		MAKERGB( weaponInfo->flashDlightColor, 1.0, 0.6, 0.23 );
		weaponInfo->flashSound[0]=trap_S_RegisterSound("sound/weapons/revolver/revolver_fire.wav");
		weaponInfo->flashEchoSound[0]=trap_S_RegisterSound("sound/weapons/revolver/revolver_far.wav");
		weaponInfo->reloadSound=trap_S_RegisterSound("sound/weapons/revolver/revolver_reload.wav");
		weaponInfo->ejectBrassFunc=NULL; // RealRTCW: revolver does not eject brass
		break;
'''
c=one(c,old,new,"revolver brass behavior")

p.write_text(c,encoding="utf-8")

# Apply exact RealRTCW first-person position offsets after base bob/sway position.
p=root/"SP/code/cgame/cg_weapons.c"
c=p.read_text(encoding="utf-8")
old='''		CG_CalculateWeaponPosition( hand.origin, angles );

		VectorMA( hand.origin, cg_gun_x.value + fovOffset[0], cg.refdef.viewaxis[0], hand.origin );'''
new='''		CG_CalculateWeaponPosition( hand.origin, angles );
		DW_V161ApplyWeaponPosition( ps->weapon, hand.origin );

		VectorMA( hand.origin, cg_gun_x.value + fovOffset[0], cg.refdef.viewaxis[0], hand.origin );'''
# Some exact source variants format this block slightly differently; try the legacy line first.
if old not in c:
    old='''		CG_CalculateWeaponPosition( hand.origin, angles );

		VectorMA( hand.origin, cg_gun_x.value, cg.refdef.viewaxis[0], hand.origin );'''
    new='''		CG_CalculateWeaponPosition( hand.origin, angles );
		DW_V161ApplyWeaponPosition( ps->weapon, hand.origin );

		VectorMA( hand.origin, cg_gun_x.value, cg.refdef.viewaxis[0], hand.origin );'''
c=one(c,old,new,"RealRTCW weaponPosition offsets")
p.write_text(c,encoding="utf-8")

# Shared pmove: classify imported automatics vs triggered semi-auto weapons in the
# same early fire-animation path as their stock equivalents.
p=root/"SP/code/game/bg_pmove.c"
m0=p.read_text(encoding="utf-8")
m=m0
old='''	case WP_MP40:
	case WP_THOMPSON:
	case WP_STEN:
	case WP_DW_MP44:
	case WP_DW_PPSH:
	case WP_VENOM:'''
new='''	case WP_MP40:
	case WP_THOMPSON:
	case WP_STEN:
	case WP_DW_MP44:
	case WP_DW_PPSH:
	case WP_DW_MP34:
	case WP_DW_BAR:
	case WP_DW_BROWNING:
	case WP_DW_MG42M:
	case WP_VENOM:'''
m=one(m,old,new,"automatic fire animation group")

old='''	case WP_SNIPERRIFLE:
	case WP_SNOOPERSCOPE:
	case WP_MAUSER:
	case WP_GARAND:
		if ( !weaponstateFiring ) {'''
new='''	case WP_SNIPERRIFLE:
	case WP_SNOOPERSCOPE:
	case WP_MAUSER:
	case WP_GARAND:
	case WP_DW_TT33:
	case WP_DW_DUAL_TT33:
	case WP_DW_REVOLVER:
	case WP_DW_HDM:
	case WP_DW_MOSIN:
	case WP_DW_M1GARAND:
	case WP_DW_G43:
	case WP_DW_M97:
		if ( !weaponstateFiring ) {'''
m=one(m,old,new,"triggered fire animation group")
p.write_text(m,encoding="utf-8")

proof={
  "feature":"DarkWolf Weapon Port V1.6.1 RealRTCW Compatibility Clean",
  "baseline":"V1.5 proven stable, then V1.6 gameplay/id expansion, then compatibility cleanup",
  "v14_component_animation_index_safety":True,
  "v13_hand_frame_freeze":False,
  "fixes":[
    "explicit RealRTCW component map for IDs 34-45; no auto-draw of stray parts",
    "supports RealRTCW parts 8/9 without changing legacy W_MAX_PARTS",
    "skips absent BAR/HDM part0 assets instead of fabricating them",
    "skips unlinked M1 barrel5",
    "safe brass-tag lookup",
    "revolver brass disabled as in RealRTCW",
    "RealRTCW weaponPosition offsets",
    "automatic vs triggered firing animation groups corrected"
  ],
  "asset_rule":"corrected cumulative PK3 must contain NO broad RealRTCW scripts/*.shader; selected MD3 direct texture refs only",
  "stock_tesla_rule":"no shader or texture override under models/weapons2/tesla",
  "source_cgame_sha256":hashlib.sha256(c.encode()).hexdigest(),
  "source_pmove_sha256":hashlib.sha256(m.encode()).hexdigest()
}
(ev/"DW_WEAPON_PORT_V161_REALRTCW_COMPAT_CLEAN_PROOF.json").write_text(json.dumps(proof,indent=2)+"\n",encoding="utf-8")
print(json.dumps(proof,indent=2))
print("DW_WEAPON_PORT_V161_REALRTCW_COMPAT_CLEAN_APPLY_PASS")
