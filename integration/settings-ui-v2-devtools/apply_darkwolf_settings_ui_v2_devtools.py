#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("source")
CHECK_ONLY = "--check-only" in sys.argv[2:]

def replace_once(path, old, new):
    p = ROOT / path
    data = p.read_text(encoding="utf-8")
    count = data.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected anchor exactly once, found {count}")
    if not CHECK_ONLY:
        p.write_text(data.replace(old, new, 1), encoding="utf-8", newline="\n")

header = "SP/code/ui/ui_shared.h"
old_h = """int Menu_Count( void );
void Menu_New( int handle );
void Menu_PaintAll( void );"""
new_h = """int Menu_Count( void );
void Menu_New( int handle );
void DarkWolf_InjectSystemGraphicsEntry( void );
void Menu_PaintAll( void );"""
replace_once(header, old_h, new_h)

shared = "SP/code/ui/ui_shared.c"
old_s = """void Menu_New( int handle ) {
	menuDef_t *menu = &Menus[menuCount];

	if ( menuCount < MAX_MENUS ) {
		Menu_Init( menu );
		if ( Menu_Parse( handle, menu ) ) {
			Menu_PostParse( menu );
			menuCount++;
		}
	}
}

int Menu_Count( void ) {
"""
new_s = """void Menu_New( int handle ) {
	menuDef_t *menu = &Menus[menuCount];

	if ( menuCount < MAX_MENUS ) {
		Menu_Init( menu );
		if ( Menu_Parse( handle, menu ) ) {
			Menu_PostParse( menu );
			menuCount++;
		}
	}
}

/*
===============================
DarkWolf_InjectSystemGraphicsEntry

Adds a non-destructive entry point to the retail System menus.  The actual
DarkWolf menu is loaded from our GPL/custom PK3; no retail menu asset is
replaced or repackaged.
===============================
*/
static void DarkWolf_AddSystemGraphicsButton( menuDef_t *menu, qboolean ingame ) {
	itemDef_t *item;
	int i;

	if ( !menu || menu->itemCount >= MAX_MENUITEMS ) {
		return;
	}

	for ( i = 0; i < menu->itemCount; i++ ) {
		if ( menu->items[i] && menu->items[i]->window.name &&
			 !Q_stricmp( menu->items[i]->window.name, "ctr_darkwolf_graphics" ) ) {
			return;
		}
	}

	item = UI_Alloc( sizeof( *item ) );
	if ( !item ) {
		return;
	}
	Item_Init( item );

	item->window.name = String_Alloc( "ctr_darkwolf_graphics" );
	item->window.group = String_Alloc( "grpSystembutton" );
	item->window.rectClient.x = 171.0f;
	item->window.rectClient.y = 306.0f;
	item->window.rectClient.w = 102.0f;
	item->window.rectClient.h = 18.0f;
	item->window.style = WINDOW_STYLE_FILLED;
	item->window.border = WINDOW_BORDER_FULL;
	item->window.borderSize = 1.0f;
	item->window.flags = WINDOW_VISIBLE | WINDOW_FORECOLORSET | WINDOW_BACKCOLORSET;
	item->window.foreColor[0] = 1.0f;
	item->window.foreColor[1] = 1.0f;
	item->window.foreColor[2] = 1.0f;
	item->window.foreColor[3] = 1.0f;
	item->window.backColor[0] = 0.10f;
	item->window.backColor[1] = 0.22f;
	item->window.backColor[2] = 0.10f;
	item->window.backColor[3] = 0.85f;
	item->window.borderColor[0] = 0.50f;
	item->window.borderColor[1] = 0.60f;
	item->window.borderColor[2] = 0.50f;
	item->window.borderColor[3] = 0.80f;

	item->type = ITEM_TYPE_BUTTON;
	item->text = String_Alloc( "DARKWOLF GRAPHICS" );
	item->textscale = 0.20f;
	item->textalignment = ITEM_ALIGN_CENTER;
	item->textalignx = 51.0f;
	item->textaligny = 13.0f;
	item->action = String_Alloc( ingame ?
		"setcvar ui_darkwolfReturnIngame 1 ; open darkwolf_graphics" :
		"setcvar ui_darkwolfReturnIngame 0 ; open darkwolf_graphics" );
	item->parent = menu;

	menu->items[menu->itemCount++] = item;
	Menu_PostParse( menu );
}

void DarkWolf_InjectSystemGraphicsEntry( void ) {
	DarkWolf_AddSystemGraphicsButton( Menus_FindByName( "system_menu" ), qfalse );
	DarkWolf_AddSystemGraphicsButton( Menus_FindByName( "ingame_system" ), qtrue );
}

int Menu_Count( void ) {
"""
replace_once(shared, old_s, new_s)

main = "SP/code/ui/ui_main.c"
p = ROOT / main
data = p.read_text(encoding="utf-8")

hooks = [
    (
        """	UI_LoadMenus( menuSet, qtrue );
	Menus_CloseAll();""",
        """	UI_LoadMenus( menuSet, qtrue );
	UI_LoadMenus( "ui/darkwolf_menus.txt", qfalse );
	DarkWolf_InjectSystemGraphicsEntry();
	Menus_CloseAll();"""
    ),
    (
        """	UI_LoadMenus( menuSet, qtrue );
	UI_LoadMenus( "ui/ingame.txt", qfalse );
#endif

	Menus_CloseAll();""",
        """	UI_LoadMenus( menuSet, qtrue );
	UI_LoadMenus( "ui/ingame.txt", qfalse );
	UI_LoadMenus( "ui/darkwolf_menus.txt", qfalse );
	DarkWolf_InjectSystemGraphicsEntry();
#endif

	Menus_CloseAll();"""
    ),
    (
        """	UI_LoadMenus( menuSet, qfalse );
	uiInfo.inGameLoad = qfalse;""",
        """	UI_LoadMenus( menuSet, qfalse );
	UI_LoadMenus( "ui/darkwolf_menus.txt", qfalse );
	DarkWolf_InjectSystemGraphicsEntry();
	uiInfo.inGameLoad = qfalse;"""
    ),
]
for old, new in hooks:
    count = data.count(old)
    if count != 1:
        raise SystemExit(f"{main}: expected load hook exactly once, found {count}")
    data = data.replace(old, new, 1)


profile_anchor = """/*
==============
UI_RunMenuScript
==============
*/

static void UI_RunMenuScript( char **args ) {"""

profile_impl = r"""/*
===============================
DarkWolf_ApplyGraphicsProfile

Production presets are compiled into ui_sp_x64.dll. They do not execute or
read external cfg files. Selecting a profile writes renderer CVars through
the UI trap API and restarts video so latched values take effect immediately.
===============================
*/
typedef struct {
	const char *name;
	const char *value;
} darkWolfProfileCvar_t;

static const darkWolfProfileCvar_t s_darkWolfPerformance[] = {
	{ "r_pbr", "0" }, { "r_normalMapping", "1" }, { "r_specularMapping", "1" },
	{ "r_cubeMapping", "1" }, { "r_materialAwareFallback", "1" },
	{ "r_materialAwareReflections", "1" }, { "r_picmip", "1" }, { "r_picmip2", "1" },
	{ "r_hdr", "1" }, { "r_toneMap", "1" }, { "r_autoExposure", "1" },
	{ "r_ssgi", "0" }, { "r_ssao", "0" }, { "r_dlightMode", "2" },
	{ "r_dlightShadowMapSize", "1024" }, { "r_dlightShadowMaxLights", "1" },
	{ "r_dlightPlayerShadow", "1" }, { "r_dlightShadowKernelMode", "0" },
	{ "r_sunShadows", "1" }, { "r_shadowFilter", "4" }, { "r_shadowMapSize", "1024" },
	{ "r_staticPromote", "1" }, { "r_staticPromoteMaxLights", "24" },
	{ "r_staticPromotePVS", "1" }, { "r_volumetricLocal", "0" },
	{ "r_volumetricSun", "0" }, { "r_volumetricFire", "0" },
	{ "r_softParticles", "1" }, { "r_fxStage9Enable", "1" }
};

static const darkWolfProfileCvar_t s_darkWolfQuality[] = {
	{ "r_pbr", "0" }, { "r_normalMapping", "1" }, { "r_specularMapping", "1" },
	{ "r_cubeMapping", "1" }, { "r_materialAwareFallback", "1" },
	{ "r_materialAwareReflections", "1" }, { "r_picmip", "1" }, { "r_picmip2", "0" },
	{ "r_hdr", "1" }, { "r_toneMap", "1" }, { "r_autoExposure", "1" },
	{ "r_ssgi", "0" }, { "r_ssao", "0" }, { "r_dlightMode", "2" },
	{ "r_dlightShadowMapSize", "2048" }, { "r_dlightShadowMaxLights", "3" },
	{ "r_dlightPlayerShadow", "1" }, { "r_dlightShadowKernelMode", "0" },
	{ "r_dlightShadowBias", "0.0033" }, { "r_dlightShadowSoftness", "1.70" },
	{ "r_dlightShadowStrength", "0.88" }, { "r_sunShadows", "1" },
	{ "r_shadowFilter", "4" }, { "r_shadowMapSize", "1024" }, { "r_staticPromote", "1" },
	{ "r_staticPromoteMaxLights", "32" }, { "r_staticPromotePVS", "1" },
	{ "r_volumetricLocal", "1" }, { "r_volumetricLocalMode", "5" },
	{ "r_volumetricLocalSamples", "24" }, { "r_volumetricSun", "1" },
	{ "r_volumetricSunSamples", "32" }, { "r_volumetricFire", "0" },
	{ "r_softParticles", "1" }, { "r_fxStage9Enable", "1" }
};

static const darkWolfProfileCvar_t s_darkWolfHighQuality[] = {
	{ "r_pbr", "0" }, { "r_normalMapping", "1" }, { "r_specularMapping", "1" },
	{ "r_cubeMapping", "1" }, { "r_materialAwareFallback", "1" },
	{ "r_materialAwareReflections", "1" }, { "r_picmip", "0" }, { "r_picmip2", "0" },
	{ "r_hdr", "1" }, { "r_toneMap", "1" }, { "r_autoExposure", "1" },
	{ "r_ssgi", "1" }, { "r_ssgiStrength", "0.75" }, { "r_ssgiRadius", "32" },
	{ "r_ssgiSaturation", "0.85" }, { "r_ssgiMax", "0.30" }, { "r_ssao", "0" },
	{ "r_dlightMode", "2" }, { "r_dlightShadowMapSize", "2048" },
	{ "r_dlightShadowMaxLights", "3" }, { "r_dlightPlayerShadow", "1" },
	{ "r_dlightShadowKernelMode", "1" }, { "r_dlightShadowBias", "0.0033" },
	{ "r_dlightShadowSoftness", "1.70" }, { "r_dlightShadowStrength", "0.88" },
	{ "r_sunShadows", "1" }, { "r_shadowFilter", "4" }, { "r_shadowMapSize", "2048" },
	{ "r_staticPromote", "1" }, { "r_staticPromoteMaxLights", "32" },
	{ "r_staticPromotePVS", "1" }, { "r_volumetricLocal", "1" },
	{ "r_volumetricLocalMode", "5" }, { "r_volumetricLocalSamples", "32" },
	{ "r_volumetricSun", "1" }, { "r_volumetricSunSamples", "48" },
	{ "r_volumetricFire", "0" }, { "r_softParticles", "1" }, { "r_fxStage9Enable", "1" }
};

static const darkWolfProfileCvar_t s_darkWolfCinematic[] = {
	{ "r_pbr", "0" }, { "r_normalMapping", "1" }, { "r_specularMapping", "1" },
	{ "r_cubeMapping", "1" }, { "r_materialAwareFallback", "1" },
	{ "r_materialAwareReflections", "1" }, { "r_picmip", "0" }, { "r_picmip2", "0" },
	{ "r_hdr", "1" }, { "r_toneMap", "1" }, { "r_autoExposure", "1" },
	{ "r_ssgi", "1" }, { "r_ssgiStrength", "0.85" }, { "r_ssgiRadius", "32" },
	{ "r_ssgiSaturation", "0.90" }, { "r_ssgiMax", "0.35" }, { "r_ssao", "0" },
	{ "r_dlightMode", "2" }, { "r_dlightShadowMapSize", "2048" },
	{ "r_dlightShadowMaxLights", "3" }, { "r_dlightPlayerShadow", "1" },
	{ "r_dlightShadowKernelMode", "1" }, { "r_dlightShadowBias", "0.0033" },
	{ "r_dlightShadowSoftness", "1.70" }, { "r_dlightShadowStrength", "0.88" },
	{ "r_sunShadows", "1" }, { "r_shadowFilter", "4" }, { "r_shadowMapSize", "2048" },
	{ "r_staticPromote", "1" }, { "r_staticPromoteMaxLights", "32" },
	{ "r_staticPromotePVS", "1" }, { "r_volumetricLocal", "1" },
	{ "r_volumetricLocalMode", "5" }, { "r_volumetricLocalSamples", "48" },
	{ "r_volumetricSun", "1" }, { "r_volumetricSunSamples", "64" },
	{ "r_volumetricFire", "1" }, { "r_volumetricFireSamples", "32" },
	{ "r_volumetricFireMaxActive", "2" }, { "r_softParticles", "1" },
	{ "r_fxStage9Enable", "1" }
};

static void DarkWolf_ApplyGraphicsProfile( int profile ) {
	const darkWolfProfileCvar_t *list = NULL;
	int count = 0;
	int i;
	const char *label = "UNKNOWN";

	switch ( profile ) {
	case 0:
		list = s_darkWolfPerformance;
		count = ARRAY_LEN( s_darkWolfPerformance );
		label = "PERFORMANCE";
		break;
	case 1:
		list = s_darkWolfQuality;
		count = ARRAY_LEN( s_darkWolfQuality );
		label = "QUALITY";
		break;
	case 2:
		list = s_darkWolfHighQuality;
		count = ARRAY_LEN( s_darkWolfHighQuality );
		label = "HIGH QUALITY";
		break;
	case 3:
		list = s_darkWolfCinematic;
		count = ARRAY_LEN( s_darkWolfCinematic );
		label = "CINEMATIC";
		break;
	default:
		Com_Printf( S_COLOR_YELLOW "DarkWolf: invalid graphics profile %d\\n", profile );
		return;
	}

	for ( i = 0; i < count; i++ ) {
		trap_Cvar_Set( list[i].name, list[i].value );
	}
	trap_Cvar_Set( "ui_darkwolfProfile", va( "%d", profile ) );
	Com_Printf( S_COLOR_GREEN "DarkWolf graphics profile applied directly: %s (%d CVars)\\n", label, count );
	trap_Cmd_ExecuteText( EXEC_APPEND, "vid_restart\\n" );
}

static qboolean DarkWolf_ToolsArmed( void ) {
	return trap_Cvar_VariableValue( "ui_darkwolfToolsArm" ) > 0.5f ? qtrue : qfalse;
}

static qboolean DarkWolf_RequireToolsArm( const char *tool ) {
	if ( DarkWolf_ToolsArmed() ) {
		return qtrue;
	}
	Com_Printf( S_COLOR_YELLOW "DarkWolf Tools: '%s' blocked. Set AUTHORING ARM to ARMED and repeat.\\n", tool );
	return qfalse;
}

static void DarkWolf_DisarmTools( void ) {
	trap_Cvar_Set( "ui_darkwolfToolsArm", "0" );
}

static void DarkWolf_RunTool( const char *tool ) {
	int slot = (int)trap_Cvar_VariableValue( "ui_darkwolfToolSlot" );
	int zone = (int)trap_Cvar_VariableValue( "ui_darkwolfMapZone" );
	float baked = trap_Cvar_VariableValue( "r_mapLightingBakedScale" );

	if ( !tool || !tool[0] ) {
		return;
	}

	if ( Q_stricmp( tool, "staticInspect" ) == 0 ) {
		trap_Cmd_ExecuteText( EXEC_APPEND, "r_staticPromoteInspect\\n" );
	} else if ( Q_stricmp( tool, "staticWideInspect" ) == 0 ) {
		trap_Cmd_ExecuteText( EXEC_APPEND, "r_staticPromoteWideInspect\\n" );
	} else if ( Q_stricmp( tool, "staticLearn" ) == 0 ) {
		if ( !DarkWolf_RequireToolsArm( tool ) ) return;
		trap_Cmd_ExecuteText( EXEC_APPEND, "r_staticPromoteLearn\\n" );
		DarkWolf_DisarmTools();
	} else if ( Q_stricmp( tool, "staticBlock" ) == 0 ) {
		if ( !DarkWolf_RequireToolsArm( tool ) ) return;
		trap_Cmd_ExecuteText( EXEC_APPEND, "r_staticPromoteBlock\\n" );
		DarkWolf_DisarmTools();
	} else if ( Q_stricmp( tool, "staticAuto" ) == 0 ) {
		if ( !DarkWolf_RequireToolsArm( tool ) ) return;
		trap_Cmd_ExecuteText( EXEC_APPEND, "r_staticPromoteAuto\\n" );
		DarkWolf_DisarmTools();
	} else if ( Q_stricmp( tool, "staticCandidateLearn" ) == 0 ) {
		if ( !DarkWolf_RequireToolsArm( tool ) ) return;
		trap_Cmd_ExecuteText( EXEC_APPEND, va( "r_staticPromoteLearnCandidate %d\\n", slot ) );
		DarkWolf_DisarmTools();
	} else if ( Q_stricmp( tool, "staticCandidateBlock" ) == 0 ) {
		if ( !DarkWolf_RequireToolsArm( tool ) ) return;
		trap_Cmd_ExecuteText( EXEC_APPEND, va( "r_staticPromoteBlockCandidate %d\\n", slot ) );
		DarkWolf_DisarmTools();
	} else if ( Q_stricmp( tool, "staticCandidateAuto" ) == 0 ) {
		if ( !DarkWolf_RequireToolsArm( tool ) ) return;
		trap_Cmd_ExecuteText( EXEC_APPEND, va( "r_staticPromoteAutoCandidate %d\\n", slot ) );
		DarkWolf_DisarmTools();
	} else if ( Q_stricmp( tool, "staticSyntheticDefault" ) == 0 ) {
		if ( !DarkWolf_RequireToolsArm( tool ) ) return;
		trap_Cmd_ExecuteText( EXEC_APPEND, "r_staticPromoteSynthetic 96 60 1.0 0.90 0.80\\n" );
		DarkWolf_DisarmTools();
	} else if ( Q_stricmp( tool, "staticSyntheticRemoveConfirmed" ) == 0 ) {
		if ( !DarkWolf_RequireToolsArm( tool ) ) return;
		trap_Cmd_ExecuteText( EXEC_APPEND, "r_staticPromoteSyntheticRemove\\n" );
		DarkWolf_DisarmTools();
	} else if ( Q_stricmp( tool, "staticClearMapConfirmed" ) == 0 ) {
		if ( !DarkWolf_RequireToolsArm( tool ) ) return;
		trap_Cmd_ExecuteText( EXEC_APPEND, "r_staticPromoteClearMap\\n" );
		DarkWolf_DisarmTools();

	} else if ( Q_stricmp( tool, "mapHelp" ) == 0 ) {
		trap_Cmd_ExecuteText( EXEC_APPEND, "maplight_help\\n" );
	} else if ( Q_stricmp( tool, "mapStatus" ) == 0 ) {
		trap_Cmd_ExecuteText( EXEC_APPEND, "maplight_status\\n" );
	} else if ( Q_stricmp( tool, "mapList" ) == 0 ) {
		trap_Cmd_ExecuteText( EXEC_APPEND, "maplight_list\\n" );
	} else if ( Q_stricmp( tool, "mapSurfaceInspect" ) == 0 ) {
		trap_Cmd_ExecuteText( EXEC_APPEND, "maplight_surface_inspect\\n" );
	} else if ( Q_stricmp( tool, "mapZoneNew" ) == 0 ) {
		if ( !DarkWolf_RequireToolsArm( tool ) ) return;
		trap_Cmd_ExecuteText( EXEC_APPEND, "maplight_zone_new dev_zone\\n" );
		DarkWolf_DisarmTools();
	} else if ( Q_stricmp( tool, "mapZoneSelect" ) == 0 ) {
		trap_Cmd_ExecuteText( EXEC_APPEND, va( "maplight_zone_select %d\\n", zone ) );
	} else if ( Q_stricmp( tool, "mapZoneDeleteConfirmed" ) == 0 ) {
		if ( !DarkWolf_RequireToolsArm( tool ) ) return;
		trap_Cmd_ExecuteText( EXEC_APPEND, va( "maplight_zone_delete %d\\n", zone ) );
		DarkWolf_DisarmTools();
	} else if ( Q_stricmp( tool, "mapAddHere" ) == 0 ) {
		if ( !DarkWolf_RequireToolsArm( tool ) ) return;
		trap_Cmd_ExecuteText( EXEC_APPEND, "maplight_add_here\\n" );
		DarkWolf_DisarmTools();
	} else if ( Q_stricmp( tool, "mapRemoveHere" ) == 0 ) {
		if ( !DarkWolf_RequireToolsArm( tool ) ) return;
		trap_Cmd_ExecuteText( EXEC_APPEND, "maplight_remove_here\\n" );
		DarkWolf_DisarmTools();
	} else if ( Q_stricmp( tool, "mapAddCluster" ) == 0 ) {
		if ( !DarkWolf_RequireToolsArm( tool ) ) return;
		trap_Cmd_ExecuteText( EXEC_APPEND, "maplight_add_cluster\\n" );
		DarkWolf_DisarmTools();
	} else if ( Q_stricmp( tool, "mapRemoveCluster" ) == 0 ) {
		if ( !DarkWolf_RequireToolsArm( tool ) ) return;
		trap_Cmd_ExecuteText( EXEC_APPEND, "maplight_remove_cluster\\n" );
		DarkWolf_DisarmTools();
	} else if ( Q_stricmp( tool, "mapSurfaceAdd" ) == 0 ) {
		if ( !DarkWolf_RequireToolsArm( tool ) ) return;
		trap_Cmd_ExecuteText( EXEC_APPEND, "maplight_surface_add\\n" );
		DarkWolf_DisarmTools();
	} else if ( Q_stricmp( tool, "mapSurfaceRemove" ) == 0 ) {
		if ( !DarkWolf_RequireToolsArm( tool ) ) return;
		trap_Cmd_ExecuteText( EXEC_APPEND, "maplight_surface_remove\\n" );
		DarkWolf_DisarmTools();
	} else if ( Q_stricmp( tool, "mapModeOriginal" ) == 0 ) {
		if ( !DarkWolf_RequireToolsArm( tool ) ) return;
		trap_Cmd_ExecuteText( EXEC_APPEND, "maplight_mode original\\n" );
		DarkWolf_DisarmTools();
	} else if ( Q_stricmp( tool, "mapModeDynamic" ) == 0 ) {
		if ( !DarkWolf_RequireToolsArm( tool ) ) return;
		trap_Cmd_ExecuteText( EXEC_APPEND, "maplight_mode dynamic\\n" );
		DarkWolf_DisarmTools();
	} else if ( Q_stricmp( tool, "mapModeAtmospheric" ) == 0 ) {
		if ( !DarkWolf_RequireToolsArm( tool ) ) return;
		trap_Cmd_ExecuteText( EXEC_APPEND, "maplight_mode atmospheric\\n" );
		DarkWolf_DisarmTools();
	} else if ( Q_stricmp( tool, "mapModeCustom" ) == 0 ) {
		if ( !DarkWolf_RequireToolsArm( tool ) ) return;
		trap_Cmd_ExecuteText( EXEC_APPEND, "maplight_mode custom\\n" );
		trap_Cmd_ExecuteText( EXEC_APPEND, va( "maplight_baked %.3f\\n", baked ) );
		DarkWolf_DisarmTools();
	} else if ( Q_stricmp( tool, "mapSave" ) == 0 ) {
		if ( !DarkWolf_RequireToolsArm( tool ) ) return;
		trap_Cmd_ExecuteText( EXEC_APPEND, "maplight_save\\n" );
		DarkWolf_DisarmTools();
	} else if ( Q_stricmp( tool, "mapLoad" ) == 0 ) {
		trap_Cmd_ExecuteText( EXEC_APPEND, "maplight_load\\n" );
	} else if ( Q_stricmp( tool, "mapClearMemoryConfirmed" ) == 0 ) {
		if ( !DarkWolf_RequireToolsArm( tool ) ) return;
		trap_Cmd_ExecuteText( EXEC_APPEND, "maplight_clear_memory\\n" );
		DarkWolf_DisarmTools();

	} else if ( Q_stricmp( tool, "resetDevDiagnostics" ) == 0 ) {
		trap_Cvar_Set( "r_mapLightingDebug", "0" );
		trap_Cvar_Set( "r_mapLightingLearn", "0" );
		trap_Cvar_Set( "r_mapLightingLearnShow", "0" );
		trap_Cvar_Set( "r_volumetricFireDiag", "0" );
		trap_Cvar_Set( "r_volumetricFireResidencyDiag", "0" );
		trap_Cvar_Set( "r_volumetricFireProofMode", "0" );
		trap_Cvar_Set( "r_volumetricFireDualDebug", "0" );
		trap_Cvar_Set( "r_volumetricFireGreenMarker", "0" );
		trap_Cvar_Set( "r_volumetricFireV07Mode", "0" );
		trap_Cvar_Set( "r_volumetricFireV072GpuIsolation", "0" );
		DarkWolf_DisarmTools();
		Com_Printf( S_COLOR_GREEN "DarkWolf Tools: active developer diagnostics reset to production-safe OFF.\\n" );
	} else {
		Com_Printf( S_COLOR_YELLOW "DarkWolf Tools: unknown action '%s'\\n", tool );
	}
}

"""

if data.count(profile_anchor) != 1:
    raise SystemExit(f"{main}: profile anchor count={data.count(profile_anchor)}")
data = data.replace(profile_anchor, profile_impl + profile_anchor, 1)

profile_case_anchor = """		} else if ( Q_stricmp( name, "darkwolfTool" ) == 0 ) {
			if ( String_Parse( args, &name2 ) ) {
				DarkWolf_RunTool( name2 );
			}
		} else if ( Q_stricmp( name, "glCustom" ) == 0 ) {
			trap_Cvar_Set( "ui_glCustom", "4" );"""
profile_case = """		} else if ( Q_stricmp( name, "darkwolfProfile" ) == 0 ) {
			int profile;
			if ( Int_Parse( args, &profile ) ) {
				DarkWolf_ApplyGraphicsProfile( profile );
			}
		} else if ( Q_stricmp( name, "glCustom" ) == 0 ) {
			trap_Cvar_Set( "ui_glCustom", "4" );"""
if data.count(profile_case_anchor) != 1:
    raise SystemExit(f"{main}: profile case anchor count={data.count(profile_case_anchor)}")
data = data.replace(profile_case_anchor, profile_case, 1)

if not CHECK_ONLY:
    p.write_text(data, encoding="utf-8", newline="\n")

print("DARKWOLF_SETTINGS_UI_V2_DEVTOOLS_PATCH_OK")
