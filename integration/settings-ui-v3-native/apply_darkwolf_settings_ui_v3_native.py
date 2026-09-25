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
void DarkWolf_CreateNativeMenus( void );
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

Adds a non-destructive entry point to the retail System menus.  Both DarkWolf
menus are constructed natively in ui_sp_x64.dll; no external DarkWolf menu,
PK3, CFG, or retail menu replacement is required.
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

/*
===============================
DarkWolf native settings UI

The complete Graphics and Developer/Tools menus live in ui_sp_x64.dll.
No .menu/.txt/.cfg/PK3 payload is required for the DarkWolf settings UI.
===============================
*/
static void DarkWolf_SetColor4( vec4_t c, float r, float g, float b, float a ) {
	c[0] = r; c[1] = g; c[2] = b; c[3] = a;
}

static menuDef_t *DarkWolf_BeginNativeMenu( const char *name, float x, float y, float w, float h,
	const char *onOpen, const char *onESC, qboolean developer ) {
	menuDef_t *menu;

	if ( menuCount >= MAX_MENUS ) {
		return NULL;
	}

	menu = &Menus[menuCount++];
	Menu_Init( menu );
	menu->window.name = String_Alloc( name );
	menu->window.rect.x = x;
	menu->window.rect.y = y;
	menu->window.rect.w = w;
	menu->window.rect.h = h;
	menu->window.style = WINDOW_STYLE_FILLED;
	menu->window.border = WINDOW_BORDER_FULL;
	menu->window.borderSize = 1.0f;
	menu->window.flags |= WINDOW_BACKCOLORSET;
	DarkWolf_SetColor4( menu->window.backColor, 0.02f, 0.02f, 0.02f, 0.97f );
	if ( developer ) {
		DarkWolf_SetColor4( menu->window.borderColor, 0.45f, 0.32f, 0.18f, 0.95f );
	} else {
		DarkWolf_SetColor4( menu->window.borderColor, 0.40f, 0.48f, 0.40f, 0.90f );
	}
	DarkWolf_SetColor4( menu->focusColor, 1.0f, 0.75f, 0.0f, 1.0f );
	if ( onOpen ) menu->onOpen = String_Alloc( onOpen );
	if ( onESC ) menu->onESC = String_Alloc( onESC );
	return menu;
}

static itemDef_t *DarkWolf_AddNativeBase( menuDef_t *menu, const char *name, const char *group,
	int type, const char *text, float x, float y, float w, float h, float scale, qboolean visible ) {
	itemDef_t *item;

	if ( !menu || menu->itemCount >= MAX_MENUITEMS ) {
		return NULL;
	}
	item = UI_Alloc( sizeof( *item ) );
	if ( !item ) {
		return NULL;
	}
	Item_Init( item );
	item->window.name = String_Alloc( name );
	if ( group ) item->window.group = String_Alloc( group );
	item->window.rectClient.x = x;
	item->window.rectClient.y = y;
	item->window.rectClient.w = w;
	item->window.rectClient.h = h;
	item->window.flags |= WINDOW_FORECOLORSET;
	if ( visible ) item->window.flags |= WINDOW_VISIBLE;
	DarkWolf_SetColor4( item->window.foreColor, 1.0f, 1.0f, 1.0f, 1.0f );
	item->type = type;
	if ( text ) item->text = String_Alloc( text );
	item->textscale = scale;
	item->textaligny = ( h >= 20.0f ) ? 15.0f : 13.0f;
	item->parent = menu;
	menu->items[menu->itemCount++] = item;
	return item;
}

static itemDef_t *DarkWolf_AddNativeText( menuDef_t *menu, const char *name, const char *group,
	const char *text, float x, float y, float w, float h, float scale, qboolean visible, qboolean centered ) {
	itemDef_t *item = DarkWolf_AddNativeBase( menu, name, group, ITEM_TYPE_TEXT, text, x, y, w, h, scale, visible );
	if ( !item ) return NULL;
	item->window.flags |= WINDOW_DECORATION;
	if ( centered ) {
		item->textalignment = ITEM_ALIGN_CENTER;
		item->textalignx = w * 0.5f;
	}
	return item;
}

static itemDef_t *DarkWolf_AddNativeButton( menuDef_t *menu, const char *name, const char *group,
	const char *text, float x, float y, float w, float h, float scale, qboolean visible,
	const char *action, int tone ) {
	itemDef_t *item = DarkWolf_AddNativeBase( menu, name, group, ITEM_TYPE_BUTTON, text, x, y, w, h, scale, visible );
	if ( !item ) return NULL;
	item->textalignment = ITEM_ALIGN_CENTER;
	item->textalignx = w * 0.5f;
	item->window.style = WINDOW_STYLE_FILLED;
	item->window.border = WINDOW_BORDER_FULL;
	item->window.borderSize = 1.0f;
	item->window.flags |= WINDOW_BACKCOLORSET;
	if ( tone == 2 ) {
		DarkWolf_SetColor4( item->window.backColor, 0.30f, 0.07f, 0.05f, 0.95f );
	} else if ( tone == 1 ) {
		DarkWolf_SetColor4( item->window.backColor, 0.22f, 0.12f, 0.06f, 0.92f );
	} else if ( tone == 3 ) {
		DarkWolf_SetColor4( item->window.backColor, 0.08f, 0.12f, 0.20f, 0.92f );
	} else {
		DarkWolf_SetColor4( item->window.backColor, 0.11f, 0.14f, 0.11f, 0.92f );
	}
	DarkWolf_SetColor4( item->window.borderColor, 0.40f, 0.45f, 0.40f, 0.80f );
	if ( action ) item->action = String_Alloc( action );
	return item;
}

static itemDef_t *DarkWolf_AddNativeMulti( menuDef_t *menu, const char *name, const char *group,
	const char *text, const char *cvar, const char *options,
	float x, float y, float w, float h, float scale, qboolean visible ) {
	itemDef_t *item = DarkWolf_AddNativeBase( menu, name, group, ITEM_TYPE_MULTI, text, x, y, w, h, scale, visible );
	multiDef_t *multi;
	char buffer[1024];
	char *p;
	const char *label;
	float value;

	if ( !item ) return NULL;
	item->textalignment = ITEM_ALIGN_RIGHT;
	item->textalignx = w * 0.49f;
	item->cvar = String_Alloc( cvar );
	Item_ValidateTypeData( item );
	multi = (multiDef_t *)item->typeData;
	if ( !multi ) return item;
	memset( multi, 0, sizeof( *multi ) );
	multi->strDef = qfalse;

	Q_strncpyz( buffer, options, sizeof( buffer ) );
	p = buffer;
	while ( multi->count < MAX_MULTI_CVARS && String_Parse( &p, &label ) ) {
		if ( !Float_Parse( &p, &value ) ) break;
		multi->cvarList[multi->count] = String_Alloc( label );
		multi->cvarValue[multi->count] = value;
		multi->count++;
	}
	return item;
}

static itemDef_t *DarkWolf_AddNativeToggle( menuDef_t *menu, const char *name, const char *group,
	const char *text, const char *cvar, float x, float y, float w, float h, float scale, qboolean visible ) {
	return DarkWolf_AddNativeMulti( menu, name, group, text, cvar, "Off 0 On 1", x, y, w, h, scale, visible );
}

static itemDef_t *DarkWolf_AddNativeSlider( menuDef_t *menu, const char *name, const char *group,
	const char *text, const char *cvar, float defVal, float minVal, float maxVal,
	float x, float y, float w, float h, float scale, qboolean visible ) {
	itemDef_t *item = DarkWolf_AddNativeBase( menu, name, group, ITEM_TYPE_SLIDER, text, x, y, w, h, scale, visible );
	editFieldDef_t *edit;

	if ( !item ) return NULL;
	item->textalignment = ITEM_ALIGN_RIGHT;
	item->textalignx = w * 0.49f;
	item->cvar = String_Alloc( cvar );
	Item_ValidateTypeData( item );
	edit = (editFieldDef_t *)item->typeData;
	if ( edit ) {
		edit->defVal = defVal;
		edit->minVal = minVal;
		edit->maxVal = maxVal;
	}
	return item;
}

static void DarkWolf_ShowNativeWhen( itemDef_t *item, const char *cvar, const char *value ) {
	if ( !item ) return;
	item->cvarTest = String_Alloc( cvar );
	item->enableCvar = String_Alloc( value );
	item->cvarFlags = CVAR_SHOW;
}

static void DarkWolf_FinalizeNativeMenu( menuDef_t *menu ) {
	int i;
	if ( !menu ) return;
	for ( i = 0; i < menu->itemCount; i++ ) {
		Item_InitControls( menu->items[i] );
	}
	Menu_PostParse( menu );
}

static void DarkWolf_BuildGraphicsNativeMenu( void ) {
	menuDef_t *m;
	itemDef_t *it;

	if ( Menus_FindByName( "darkwolf_graphics" ) ) return;
	m = DarkWolf_BeginNativeMenu( "darkwolf_graphics", 70, 55, 500, 370,
		"hide dw_core ; hide dw_lighting ; hide dw_effects ; hide dw_advanced ; show dw_core",
		"close darkwolf_graphics", qfalse );
	if ( !m ) return;

	it = DarkWolf_AddNativeText( m, "title", NULL, "DARKWOLF / ioRTCW REND2 GRAPHICS", 0, 0, 500, 28, .30f, qtrue, qtrue );
	if ( it ) DarkWolf_SetColor4( it->window.foreColor, 1, 1, 1, 1 );

	DarkWolf_AddNativeButton( m, "tab_core", NULL, "GRAPHICS", 18, 32, 88, 18, .20f, qtrue, "hide dw_core ; hide dw_lighting ; hide dw_effects ; hide dw_advanced ; show dw_core", 0 );
	DarkWolf_AddNativeButton( m, "tab_lighting", NULL, "LIGHTING", 111, 32, 88, 18, .20f, qtrue, "hide dw_core ; hide dw_lighting ; hide dw_effects ; hide dw_advanced ; show dw_lighting", 0 );
	DarkWolf_AddNativeButton( m, "tab_effects", NULL, "EFFECTS", 204, 32, 88, 18, .20f, qtrue, "hide dw_core ; hide dw_lighting ; hide dw_effects ; hide dw_advanced ; show dw_effects", 0 );
	DarkWolf_AddNativeButton( m, "tab_advanced", NULL, "ADVANCED", 297, 32, 88, 18, .20f, qtrue, "hide dw_core ; hide dw_lighting ; hide dw_effects ; hide dw_advanced ; show dw_advanced", 0 );
	DarkWolf_AddNativeButton( m, "tab_dev", NULL, "DEV / TOOLS", 390, 32, 92, 18, .17f, qtrue, "open darkwolf_developer", 1 );

	DarkWolf_AddNativeText( m, "profile_label", NULL, "PROFILE:", 18, 58, 90, 15, .20f, qtrue, qfalse );
	DarkWolf_AddNativeButton( m, "p_perf", NULL, "PERFORMANCE", 105, 57, 82, 18, .17f, qtrue, "uiScript darkwolfProfile 0", 0 );
	DarkWolf_AddNativeButton( m, "p_quality", NULL, "QUALITY", 191, 57, 82, 18, .18f, qtrue, "uiScript darkwolfProfile 1", 0 );
	DarkWolf_AddNativeButton( m, "p_hq", NULL, "HIGH QUALITY", 277, 57, 94, 18, .17f, qtrue, "uiScript darkwolfProfile 2", 0 );
	DarkWolf_AddNativeButton( m, "p_cine", NULL, "CINEMATIC", 375, 57, 105, 18, .18f, qtrue, "uiScript darkwolfProfile 3", 0 );

	DarkWolf_AddNativeToggle( m, "core_pbr", "dw_core", "PBR:", "r_pbr", 18, 88, 220, 16, .19f, qtrue );
	DarkWolf_AddNativeToggle( m, "core_normal", "dw_core", "Normal maps:", "r_normalMapping", 18, 112, 220, 16, .19f, qtrue );
	DarkWolf_AddNativeToggle( m, "core_spec", "dw_core", "Specular maps:", "r_specularMapping", 18, 136, 220, 16, .19f, qtrue );
	DarkWolf_AddNativeToggle( m, "core_mat", "dw_core", "Material-aware:", "r_materialAwareFallback", 18, 160, 220, 16, .19f, qtrue );
	DarkWolf_AddNativeToggle( m, "core_refl", "dw_core", "Reflections:", "r_materialAwareReflections", 18, 184, 220, 16, .19f, qtrue );
	DarkWolf_AddNativeToggle( m, "core_cube", "dw_core", "Cubemaps:", "r_cubeMapping", 18, 208, 220, 16, .19f, qtrue );
	DarkWolf_AddNativeMulti( m, "core_pic", "dw_core", "World textures:", "r_picmip", "Ultra 0 High 1 Medium 2", 255, 88, 220, 16, .19f, qtrue );
	DarkWolf_AddNativeMulti( m, "core_char", "dw_core", "Character textures:", "r_picmip2", "Ultra 0 High 1 Medium 2 Low 3", 255, 112, 220, 16, .19f, qtrue );
	DarkWolf_AddNativeToggle( m, "core_hdr", "dw_core", "HDR:", "r_hdr", 255, 136, 220, 16, .19f, qtrue );
	DarkWolf_AddNativeToggle( m, "core_tone", "dw_core", "Tone mapping:", "r_toneMap", 255, 160, 220, 16, .19f, qtrue );
	DarkWolf_AddNativeToggle( m, "core_exp", "dw_core", "Auto exposure:", "r_autoExposure", 255, 184, 220, 16, .19f, qtrue );
	DarkWolf_AddNativeToggle( m, "core_ssgi", "dw_core", "SSGI:", "r_ssgi", 255, 208, 220, 16, .19f, qtrue );

	DarkWolf_AddNativeMulti( m, "li_dlight", "dw_lighting", "Dynamic lights:", "r_dlightMode", "Off 0 Direct 1 Shadows 2", 18, 88, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeMulti( m, "li_map", "dw_lighting", "Point shadow map:", "r_dlightShadowMapSize", "1024 1024 2048 2048", 18, 112, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeMulti( m, "li_slots", "dw_lighting", "Shadow lights:", "r_dlightShadowMaxLights", "1 1 2 2 3 3 4 4", 18, 136, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeToggle( m, "li_player", "dw_lighting", "Player point shadow:", "r_dlightPlayerShadow", 18, 160, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeToggle( m, "li_sun", "dw_lighting", "Sun shadows:", "r_sunShadows", 18, 184, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeMulti( m, "li_filter", "dw_lighting", "Sun filter:", "r_shadowFilter", "Classic 1 Stable 4", 18, 208, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeMulti( m, "li_smap", "dw_lighting", "Sun shadow map:", "r_shadowMapSize", "1024 1024 2048 2048", 255, 88, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeToggle( m, "li_static", "dw_lighting", "Static Promote:", "r_staticPromote", 255, 112, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeMulti( m, "li_staticmax", "dw_lighting", "Active lamps:", "r_staticPromoteMaxLights", "8 8 16 16 24 24 32 32", 255, 136, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeToggle( m, "li_pvs", "dw_lighting", "Lamp PVS:", "r_staticPromotePVS", 255, 160, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeToggle( m, "li_phys", "dw_lighting", "Physical residency:", "r_staticPromotePhysicalResidency", 255, 184, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeToggle( m, "li_rec", "dw_lighting", "Fixture recognition:", "r_staticPromotePhysicalRecognition", 255, 208, 220, 16, .19f, qfalse );

	DarkWolf_AddNativeToggle( m, "fx_local", "dw_effects", "Local volumetrics:", "r_volumetricLocal", 18, 88, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeMulti( m, "fx_localmode", "dw_effects", "Local mode:", "r_volumetricLocalMode", "Basic 1 Production 5", 18, 112, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeMulti( m, "fx_localsamp", "dw_effects", "Local samples:", "r_volumetricLocalSamples", "16 16 24 24 32 32 48 48", 18, 136, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeToggle( m, "fx_sun", "dw_effects", "Sun volumetrics:", "r_volumetricSun", 18, 160, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeMulti( m, "fx_sunsamp", "dw_effects", "Sun samples:", "r_volumetricSunSamples", "24 24 32 32 48 48 64 64", 18, 184, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeToggle( m, "fx_soft", "dw_effects", "Soft particles:", "r_softParticles", 18, 208, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeToggle( m, "fx_fire", "dw_effects", "Volumetric fire:", "r_volumetricFire", 255, 88, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeMulti( m, "fx_firesamp", "dw_effects", "Fire samples:", "r_volumetricFireSamples", "16 16 24 24 32 32 48 48", 255, 112, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeMulti( m, "fx_firemax", "dw_effects", "Active fire volumes:", "r_volumetricFireMaxActive", "1 1 2 2 3 3 4 4", 255, 136, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeToggle( m, "fx_stage", "dw_effects", "Enhanced fire/smoke:", "r_fxStage9Enable", 255, 160, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeToggle( m, "fx_depth", "dw_effects", "Depth prepass:", "r_depthPrepass", 255, 184, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeToggle( m, "fx_ssao", "dw_effects", "SSAO:", "r_ssao", 255, 208, 220, 16, .19f, qfalse );

	DarkWolf_AddNativeMulti( m, "ad_kernel", "dw_advanced", "Point kernel:", "r_dlightShadowKernelMode", "0 0 1 1", 18, 88, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeSlider( m, "ad_bias", "dw_advanced", "Shadow bias:", "r_dlightShadowBias", .0033f, .001f, .008f, 18, 112, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeSlider( m, "ad_soft", "dw_advanced", "Shadow softness:", "r_dlightShadowSoftness", 1.70f, .50f, 2.50f, 18, 136, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeSlider( m, "ad_strength", "dw_advanced", "Shadow strength:", "r_dlightShadowStrength", .88f, .20f, 1.0f, 18, 160, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeSlider( m, "ad_ssgis", "dw_advanced", "SSGI strength:", "r_ssgiStrength", .75f, 0, 1.5f, 18, 184, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeSlider( m, "ad_ssgir", "dw_advanced", "SSGI radius:", "r_ssgiRadius", 32, 8, 64, 18, 208, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeSlider( m, "ad_gain", "dw_advanced", "Lamp direct gain:", "r_staticPromoteDirectGain", 1.10f, .50f, 2.0f, 255, 88, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeSlider( m, "ad_radius", "dw_advanced", "Lamp radius scale:", "r_staticPromoteRadiusScale", .70f, .30f, 1.50f, 255, 112, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeSlider( m, "ad_reflmax", "dw_advanced", "Reflection max:", "r_materialReflectionMax", .75f, 0, 1.0f, 255, 136, 220, 16, .19f, qfalse );
	DarkWolf_AddNativeButton( m, "ad_inspect", "dw_advanced", "INSPECT LAMP", 265, 176, 92, 20, .16f, qfalse, "uiScript darkwolfTool staticInspect", 0 );
	DarkWolf_AddNativeButton( m, "ad_wide", "dw_advanced", "WIDE INSPECT", 367, 176, 92, 20, .16f, qfalse, "uiScript darkwolfTool staticWideInspect", 0 );
	DarkWolf_AddNativeText( m, "ad_note", "dw_advanced", "Authoring and destructive commands are available under DEV / TOOLS.", 255, 208, 220, 32, .15f, qfalse, qfalse );

	DarkWolf_AddNativeButton( m, "restart", NULL, "APPLY / RESTART", 18, 330, 125, 22, .18f, qtrue, "exec vid_restart", 0 );
	it = DarkWolf_AddNativeButton( m, "back_main", NULL, "BACK", 357, 330, 125, 22, .19f, qtrue, "close darkwolf_graphics ; open system_menu", 0 );
	DarkWolf_ShowNativeWhen( it, "ui_darkwolfReturnIngame", "0" );
	it = DarkWolf_AddNativeButton( m, "back_game", NULL, "BACK", 357, 330, 125, 22, .19f, qtrue, "close darkwolf_graphics ; open ingame_system", 0 );
	DarkWolf_ShowNativeWhen( it, "ui_darkwolfReturnIngame", "1" );
	DarkWolf_AddNativeText( m, "footer", NULL, "Latched options require APPLY / RESTART.", 154, 332, 190, 18, .15f, qtrue, qtrue );

	DarkWolf_FinalizeNativeMenu( m );
}

static void DarkWolf_BuildDeveloperNativeMenu( void ) {
	menuDef_t *m;
	itemDef_t *it;

	if ( Menus_FindByName( "darkwolf_developer" ) ) return;
	m = DarkWolf_BeginNativeMenu( "darkwolf_developer", 55, 45, 530, 390,
		"hide dev_static ; hide dev_shadow ; hide dev_material ; hide dev_fire ; show dev_static",
		"close darkwolf_developer", qtrue );
	if ( !m ) return;

	it = DarkWolf_AddNativeText( m, "title", NULL, "DARKWOLF DEVELOPER / TOOLS", 0, 0, 530, 28, .30f, qtrue, qtrue );
	if ( it ) DarkWolf_SetColor4( it->window.foreColor, 1.0f, .82f, .50f, 1.0f );

	DarkWolf_AddNativeButton( m, "tab_static", NULL, "STATIC / MAP", 12, 32, 116, 18, .17f, qtrue, "hide dev_static ; hide dev_shadow ; hide dev_material ; hide dev_fire ; show dev_static", 1 );
	DarkWolf_AddNativeButton( m, "tab_shadow", NULL, "SHADOW DIAG", 137, 32, 116, 18, .17f, qtrue, "hide dev_static ; hide dev_shadow ; hide dev_material ; hide dev_fire ; show dev_shadow", 0 );
	DarkWolf_AddNativeButton( m, "tab_mat", NULL, "MATERIAL / SSGI", 262, 32, 116, 18, .16f, qtrue, "hide dev_static ; hide dev_shadow ; hide dev_material ; hide dev_fire ; show dev_material", 0 );
	DarkWolf_AddNativeButton( m, "tab_fire", NULL, "FIRE / FX", 387, 32, 116, 18, .17f, qtrue, "hide dev_static ; hide dev_shadow ; hide dev_material ; hide dev_fire ; show dev_fire", 0 );

	DarkWolf_AddNativeMulti( m, "arm", NULL, "AUTHORING ARM:", "ui_darkwolfToolsArm", "SAFE 0 ARMED 1", 18, 58, 235, 18, .18f, qtrue );
	DarkWolf_AddNativeMulti( m, "slot", NULL, "Candidate slot:", "ui_darkwolfToolSlot", "0 0 1 1 2 2 3 3 4 4 5 5 6 6 7 7 8 8 9 9 10 10 11 11 12 12 13 13 14 14 15 15", 275, 58, 230, 18, .17f, qtrue );

	it = DarkWolf_AddNativeText( m, "sh", "dev_static", "STATIC PROMOTE / FIXTURE", 18, 86, 220, 15, .18f, qtrue, qfalse );
	if ( it ) DarkWolf_SetColor4( it->window.foreColor, .72f, .95f, .72f, 1 );
	DarkWolf_AddNativeButton( m, "i1", "dev_static", "INSPECT", 18, 106, 102, 19, .15f, qtrue, "uiScript darkwolfTool staticInspect", 0 );
	DarkWolf_AddNativeButton( m, "i2", "dev_static", "WIDE INSPECT", 126, 106, 102, 19, .14f, qtrue, "uiScript darkwolfTool staticWideInspect", 0 );
	DarkWolf_AddNativeButton( m, "i3", "dev_static", "LEARN", 18, 132, 64, 19, .14f, qtrue, "uiScript darkwolfTool staticLearn", 1 );
	DarkWolf_AddNativeButton( m, "i4", "dev_static", "BLOCK", 88, 132, 64, 19, .14f, qtrue, "uiScript darkwolfTool staticBlock", 1 );
	DarkWolf_AddNativeButton( m, "i5", "dev_static", "AUTO", 158, 132, 64, 19, .14f, qtrue, "uiScript darkwolfTool staticAuto", 1 );
	DarkWolf_AddNativeButton( m, "i6", "dev_static", "C-LEARN", 18, 158, 64, 19, .13f, qtrue, "uiScript darkwolfTool staticCandidateLearn", 1 );
	DarkWolf_AddNativeButton( m, "i7", "dev_static", "C-BLOCK", 88, 158, 64, 19, .13f, qtrue, "uiScript darkwolfTool staticCandidateBlock", 1 );
	DarkWolf_AddNativeButton( m, "i8", "dev_static", "C-AUTO", 158, 158, 64, 19, .13f, qtrue, "uiScript darkwolfTool staticCandidateAuto", 1 );
	DarkWolf_AddNativeToggle( m, "sp1", "dev_static", "Classifier:", "r_staticPromoteClassifier", 18, 184, 210, 18, .16f, qtrue );
	DarkWolf_AddNativeToggle( m, "sp2", "dev_static", "Auto map lights:", "r_staticPromoteAutoMapLights", 18, 208, 210, 18, .16f, qtrue );
	DarkWolf_AddNativeSlider( m, "sp3", "dev_static", "PVS hold ms:", "r_staticPromotePVSHoldMs", 8000, 0, 15000, 18, 232, 210, 18, .16f, qtrue );
	DarkWolf_AddNativeSlider( m, "sp4", "dev_static", "Influence radius:", "r_staticPromoteInfluenceRadius", 320, 64, 640, 18, 256, 210, 18, .16f, qtrue );

	it = DarkWolf_AddNativeText( m, "mh", "dev_static", "MAP LIGHTING AUTHORING", 270, 86, 220, 15, .18f, qtrue, qfalse );
	if ( it ) DarkWolf_SetColor4( it->window.foreColor, .72f, .85f, 1, 1 );
	DarkWolf_AddNativeButton( m, "m1", "dev_static", "HELP", 270, 106, 66, 19, .14f, qtrue, "uiScript darkwolfTool mapHelp", 3 );
	DarkWolf_AddNativeButton( m, "m2", "dev_static", "STATUS", 342, 106, 66, 19, .14f, qtrue, "uiScript darkwolfTool mapStatus", 3 );
	DarkWolf_AddNativeButton( m, "m3", "dev_static", "LIST", 414, 106, 66, 19, .14f, qtrue, "uiScript darkwolfTool mapList", 3 );
	DarkWolf_AddNativeButton( m, "m4", "dev_static", "SURFACE INSPECT", 270, 132, 210, 19, .14f, qtrue, "uiScript darkwolfTool mapSurfaceInspect", 3 );
	DarkWolf_AddNativeMulti( m, "mz", "dev_static", "Zone:", "ui_darkwolfMapZone", "0 0 1 1 2 2 3 3 4 4 5 5 6 6 7 7 8 8 9 9 10 10 11 11 12 12 13 13 14 14 15 15", 270, 158, 210, 18, .16f, qtrue );
	DarkWolf_AddNativeButton( m, "m5", "dev_static", "SELECT", 270, 184, 66, 19, .13f, qtrue, "uiScript darkwolfTool mapZoneSelect", 3 );
	DarkWolf_AddNativeButton( m, "m6", "dev_static", "NEW", 342, 184, 66, 19, .13f, qtrue, "uiScript darkwolfTool mapZoneNew", 1 );
	DarkWolf_AddNativeButton( m, "m7", "dev_static", "DELETE", 414, 184, 66, 19, .13f, qtrue, "uiScript darkwolfTool mapZoneDeleteConfirmed", 2 );
	DarkWolf_AddNativeButton( m, "m8", "dev_static", "ADD HERE", 270, 210, 66, 19, .12f, qtrue, "uiScript darkwolfTool mapAddHere", 1 );
	DarkWolf_AddNativeButton( m, "m9", "dev_static", "REMOVE", 342, 210, 66, 19, .12f, qtrue, "uiScript darkwolfTool mapRemoveHere", 2 );
	DarkWolf_AddNativeButton( m, "m10", "dev_static", "SAVE", 414, 210, 66, 19, .12f, qtrue, "uiScript darkwolfTool mapSave", 1 );
	DarkWolf_AddNativeToggle( m, "md1", "dev_static", "Map override:", "r_mapLightingOverride", 270, 236, 210, 18, .16f, qtrue );
	DarkWolf_AddNativeToggle( m, "md2", "dev_static", "Map debug:", "r_mapLightingDebug", 270, 260, 210, 18, .16f, qtrue );
	DarkWolf_AddNativeToggle( m, "md3", "dev_static", "Learn overlay:", "r_mapLightingLearnShow", 270, 284, 210, 18, .16f, qtrue );

	it = DarkWolf_AddNativeText( m, "dh", "dev_shadow", "DYNAMIC-LIGHT DIAGNOSTICS", 18, 88, 220, 15, .18f, qfalse, qfalse );
	if ( it ) DarkWolf_SetColor4( it->window.foreColor, .85f, .85f, 1, 1 );
	DarkWolf_AddNativeToggle( m, "d1", "dev_shadow", "Diag overlay:", "r_dlightDiagOverlay", 18, 110, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeToggle( m, "d2", "dev_shadow", "Inject test light:", "r_dlightDiagInject", 18, 134, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeToggle( m, "d3", "dev_shadow", "Freeze selector:", "r_dlightDiagFreeze", 18, 158, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeToggle( m, "d4", "dev_shadow", "Force selected:", "r_dlightDiagForceSelect", 18, 182, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeToggle( m, "d5", "dev_shadow", "Tint selected:", "r_dlightDiagTintSelected", 18, 206, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeToggle( m, "d6", "dev_shadow", "Shadow view:", "r_dlightDiagShadowView", 18, 230, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeToggle( m, "d7", "dev_shadow", "Depth diag:", "r_dlightDiagDepth", 18, 254, 220, 18, .16f, qfalse );

	it = DarkWolf_AddNativeText( m, "shh", "dev_shadow", "SHADOW SELECTOR / FILTER", 270, 88, 220, 15, .18f, qfalse, qfalse );
	if ( it ) DarkWolf_SetColor4( it->window.foreColor, .85f, .85f, 1, 1 );
	DarkWolf_AddNativeMulti( m, "s1", "dev_shadow", "Caster mode:", "r_dlightShadowCasterMode", "0 0 1 1 2 2", 270, 110, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeMulti( m, "s2", "dev_shadow", "Filter:", "r_dlightShadowFilter", "1 1 2 2 3 3 4 4", 270, 134, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeSlider( m, "s3", "dev_shadow", "Hysteresis:", "r_dlightShadowHysteresis", .25f, 0, 1, 270, 158, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeSlider( m, "s4", "dev_shadow", "Hold frames:", "r_dlightShadowHoldFrames", 12, 0, 60, 270, 182, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeSlider( m, "s5", "dev_shadow", "Diag radius:", "r_dlightDiagRadius", 360, 64, 768, 270, 206, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeSlider( m, "s6", "dev_shadow", "Diag distance:", "r_dlightDiagDistance", 112, 16, 512, 270, 230, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeSlider( m, "s7", "dev_shadow", "Diag orbit:", "r_dlightDiagOrbit", 72, 0, 256, 270, 254, 220, 18, .16f, qfalse );

	it = DarkWolf_AddNativeText( m, "mh1", "dev_material", "MATERIAL DEBUG", 18, 88, 220, 15, .18f, qfalse, qfalse );
	if ( it ) DarkWolf_SetColor4( it->window.foreColor, .80f, .95f, .80f, 1 );
	DarkWolf_AddNativeToggle( m, "ma1", "dev_material", "Material debug:", "r_materialDebug", 18, 110, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeToggle( m, "ma2", "dev_material", "Material trace:", "r_materialTrace", 18, 134, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeMulti( m, "ma3", "dev_material", "Reflection class mask:", "r_materialReflectionClassMask", "0 0 10 10 255 255", 18, 158, 220, 18, .15f, qfalse );
	DarkWolf_AddNativeSlider( m, "ma4", "dev_material", "Metal reflection:", "r_materialReflectionMetalScale", .60f, 0, 1, 18, 182, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeSlider( m, "ma5", "dev_material", "Glass reflection:", "r_materialReflectionGlassScale", .70f, 0, 1, 18, 206, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeSlider( m, "ma6", "dev_material", "Ceramic reflection:", "r_materialReflectionCeramicScale", .20f, 0, 1, 18, 230, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeSlider( m, "ma7", "dev_material", "Wood reflection:", "r_materialReflectionWoodScale", .10f, 0, 1, 18, 254, 220, 18, .16f, qfalse );

	it = DarkWolf_AddNativeText( m, "gh", "dev_material", "SSGI DEBUG / GUARDS", 270, 88, 220, 15, .18f, qfalse, qfalse );
	if ( it ) DarkWolf_SetColor4( it->window.foreColor, .80f, .95f, .80f, 1 );
	DarkWolf_AddNativeToggle( m, "g1", "dev_material", "SSGI debug:", "r_ssgiDebug", 270, 110, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeToggle( m, "g2", "dev_material", "SSGI trace:", "r_ssgiTrace", 270, 134, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeMulti( m, "g3", "dev_material", "Bright source fix:", "r_ssgiBrightSourceFix", "0 0 1 1 2 2", 270, 158, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeMulti( m, "g4", "dev_material", "Resolve mode:", "r_ssgiResolveMode", "0 0 1 1 2 2", 270, 182, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeMulti( m, "g5", "dev_material", "Entity guard:", "r_ssgiEntityGuardMode", "0 0 1 1 2 2", 270, 206, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeMulti( m, "g6", "dev_material", "Entity mask:", "r_ssgiEntityMaskMode", "0 0 1 1 2 2", 270, 230, 220, 18, .16f, qfalse );

	it = DarkWolf_AddNativeText( m, "fh", "dev_fire", "VOLUMETRIC FIRE DIAGNOSTICS", 18, 88, 220, 15, .18f, qfalse, qfalse );
	if ( it ) DarkWolf_SetColor4( it->window.foreColor, 1, .75f, .50f, 1 );
	DarkWolf_AddNativeToggle( m, "f1", "dev_fire", "Diag:", "r_volumetricFireDiag", 18, 110, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeToggle( m, "f2", "dev_fire", "Residency diag:", "r_volumetricFireResidencyDiag", 18, 134, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeToggle( m, "f3", "dev_fire", "Proof mode:", "r_volumetricFireProofMode", 18, 158, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeToggle( m, "f4", "dev_fire", "Dual debug:", "r_volumetricFireDualDebug", 18, 182, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeToggle( m, "f5", "dev_fire", "Green marker:", "r_volumetricFireGreenMarker", 18, 206, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeToggle( m, "f6", "dev_fire", "V0.7 mode:", "r_volumetricFireV07Mode", 18, 230, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeToggle( m, "f7", "dev_fire", "GPU isolation:", "r_volumetricFireV072GpuIsolation", 18, 254, 220, 18, .16f, qfalse );

	it = DarkWolf_AddNativeText( m, "fp", "dev_fire", "FIRE TUNING / RESIDENCY", 270, 88, 220, 15, .18f, qfalse, qfalse );
	if ( it ) DarkWolf_SetColor4( it->window.foreColor, 1, .75f, .50f, 1 );
	DarkWolf_AddNativeSlider( m, "ft1", "dev_fire", "Strength:", "r_volumetricFireStrength", 1.0f, 0, 2, 270, 110, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeSlider( m, "ft2", "dev_fire", "Density:", "r_volumetricFireDensity", .006f, .001f, .020f, 270, 134, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeSlider( m, "ft3", "dev_fire", "Plume radius:", "r_volumetricFirePlumeRadius", .42f, .1f, 1.2f, 270, 158, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeSlider( m, "ft4", "dev_fire", "Plume height:", "r_volumetricFirePlumeHeight", .95f, .2f, 2.0f, 270, 182, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeSlider( m, "ft5", "dev_fire", "Turbulence:", "r_volumetricFireTurbulence", .35f, 0, 1, 270, 206, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeSlider( m, "ft6", "dev_fire", "Speed:", "r_volumetricFireSpeed", 1.40f, .2f, 3.0f, 270, 230, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeToggle( m, "ft7", "dev_fire", "Owner lock:", "r_volumetricFireOwnerLock", 270, 254, 220, 18, .16f, qfalse );
	DarkWolf_AddNativeButton( m, "reset", "dev_fire", "RESET DEV DIAGNOSTICS", 158, 300, 214, 20, .15f, qfalse, "uiScript darkwolfTool resetDevDiagnostics", 0 );

	DarkWolf_AddNativeText( m, "note", NULL, "ARMED actions auto-disarm after one use. Diagnostics do not require arming.", 18, 336, 494, 20, .15f, qtrue, qtrue );
	DarkWolf_AddNativeButton( m, "back", NULL, "BACK TO GRAPHICS", 390, 362, 122, 22, .16f, qtrue, "close darkwolf_developer", 0 );

	DarkWolf_FinalizeNativeMenu( m );
}

void DarkWolf_CreateNativeMenus( void ) {
	DarkWolf_BuildGraphicsNativeMenu();
	DarkWolf_BuildDeveloperNativeMenu();
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
	DarkWolf_CreateNativeMenus();
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
	DarkWolf_CreateNativeMenus();
	DarkWolf_InjectSystemGraphicsEntry();
#endif

	Menus_CloseAll();"""
    ),
    (
        """	UI_LoadMenus( menuSet, qfalse );
	uiInfo.inGameLoad = qfalse;""",
        """	UI_LoadMenus( menuSet, qfalse );
	DarkWolf_CreateNativeMenus();
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

profile_case_anchor = """		} else if ( Q_stricmp( name, "glCustom" ) == 0 ) {
			trap_Cvar_Set( "ui_glCustom", "4" );"""
profile_case = """		} else if ( Q_stricmp( name, "darkwolfProfile" ) == 0 ) {
			int profile;
			if ( Int_Parse( args, &profile ) ) {
				DarkWolf_ApplyGraphicsProfile( profile );
			}
		} else if ( Q_stricmp( name, "darkwolfTool" ) == 0 ) {
			if ( String_Parse( args, &name2 ) ) {
				DarkWolf_RunTool( name2 );
			}
		} else if ( Q_stricmp( name, "glCustom" ) == 0 ) {
			trap_Cvar_Set( "ui_glCustom", "4" );"""
if data.count(profile_case_anchor) != 1:
    raise SystemExit(f"{main}: profile case anchor count={data.count(profile_case_anchor)}")
data = data.replace(profile_case_anchor, profile_case, 1)

if not CHECK_ONLY:
    p.write_text(data, encoding="utf-8", newline="\n")

print("DARKWOLF_SETTINGS_UI_V3_NATIVE_PATCH_OK")
