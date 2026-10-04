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


shared = "SP/code/ui/ui_shared.c"

old_head = r'''static void DarkWolf_InjectOptionsRend2TabInto( menuDef_t *menu, qboolean inGame ) {
	itemDef_t *controls, *system, *game, *mods, *defaults, *item;
	float left, right, y, h, slot;
	int i;
	char action[160];

	if ( !menu || menu->itemCount >= MAX_MENUITEMS ) return;

	for ( i = 0; i < menu->itemCount; i++ ) {
		if ( menu->items[i] && menu->items[i]->window.name &&
			 !Q_stricmp( menu->items[i]->window.name, "ctr_darkwolf_rend2_settings" ) ) {
			return;
		}
	}

	controls = DarkWolf_FindMenuItemByName( menu, "controls" );'''

new_head = r'''static void DarkWolf_InjectIngameSystemRend2Tab( menuDef_t *menu ) {
	itemDef_t *graphics, *driver, *sound, *item, *styleSource;
	float left, right, y, h, slot;
	int i;

	if ( !menu || menu->itemCount >= MAX_MENUITEMS ) return;

	for ( i = 0; i < menu->itemCount; i++ ) {
		if ( menu->items[i] && menu->items[i]->window.name &&
			 !Q_stricmp( menu->items[i]->window.name, "ctr_darkwolf_rend2_settings" ) ) {
			return;
		}
	}

	graphics = DarkWolf_FindMenuItemByName( menu, "ctr_graphics" );
	driver   = DarkWolf_FindMenuItemByName( menu, "ctr_driver" );
	sound    = DarkWolf_FindMenuItemByName( menu, "ctr_sound" );
	if ( !graphics || !driver || !sound ) {
		Com_Printf( S_COLOR_YELLOW "DarkWolf UI: ingame_system tab anchors not found; REND2 SETTINGS not injected.\n" );
		return;
	}

	left = 18.0f;
	right = menu->window.rect.w - 18.0f;
	if ( right - left < 320.0f ) {
		left = graphics->window.rectClient.x;
		right = sound->window.rectClient.x + sound->window.rectClient.w;
	}
	y = graphics->window.rectClient.y;
	h = graphics->window.rectClient.h;
	slot = ( right - left ) / 4.0f;

	DarkWolf_RelayoutOptionsTab( graphics, left + slot * 0.0f, y, slot, h );
	DarkWolf_RelayoutOptionsTab( driver,   left + slot * 1.0f, y, slot, h );
	DarkWolf_RelayoutOptionsTab( sound,    left + slot * 2.0f, y, slot, h );

	item = UI_Alloc( sizeof( *item ) );
	if ( !item ) return;
	Item_Init( item );
	styleSource = sound;

	item->window.name = String_Alloc( "ctr_darkwolf_rend2_settings" );
	item->window.group = styleSource->window.group;
	item->window.rectClient.x = left + slot * 3.0f;
	item->window.rectClient.y = y;
	item->window.rectClient.w = slot;
	item->window.rectClient.h = h;
	item->window.style = styleSource->window.style;
	item->window.border = styleSource->window.border;
	item->window.borderSize = styleSource->window.borderSize;
	item->window.background = styleSource->window.background;
	item->window.flags = ( styleSource->window.flags | WINDOW_VISIBLE | WINDOW_FORECOLORSET ) &
		~( WINDOW_HASFOCUS | WINDOW_GREY | WINDOW_DECORATION );
	Vector4Copy( styleSource->window.foreColor, item->window.foreColor );
	Vector4Copy( styleSource->window.backColor, item->window.backColor );
	Vector4Copy( styleSource->window.borderColor, item->window.borderColor );
	item->textscale = styleSource->textscale > 0.0f ? styleSource->textscale : 0.23f;
	item->textaligny = styleSource->textaligny;
	item->textStyle = styleSource->textStyle;
	item->font = styleSource->font;
	item->focusSound = styleSource->focusSound;
	item->type = ITEM_TYPE_BUTTON;
	item->text = String_Alloc( "REND2 SETTINGS" );
	item->textalignment = ITEM_ALIGN_CENTER;
	item->textalignx = slot * 0.5f;
	item->action = String_Alloc( "setcvar ui_darkwolfReturnIngame 1 ; close ingame_system ; open darkwolf_graphics" );
	item->parent = menu;
	menu->items[menu->itemCount++] = item;
	Item_InitControls( item );
	Menu_PostParse( menu );

	Com_Printf( S_COLOR_GREEN "DarkWolf UI v4.4.2: REND2 SETTINGS attached to ingame_system.\n" );
}

static void DarkWolf_InjectOptionsRend2TabInto( menuDef_t *menu, qboolean inGame ) {
	itemDef_t *controls, *system, *game, *mods, *defaults, *item;
	float left, right, y, h, slot;
	int i;
	char action[160];

	if ( !menu || menu->itemCount >= MAX_MENUITEMS ) return;

	if ( inGame ) {
		DarkWolf_InjectIngameSystemRend2Tab( menu );
		return;
	}

	for ( i = 0; i < menu->itemCount; i++ ) {
		if ( menu->items[i] && menu->items[i]->window.name &&
			 !Q_stricmp( menu->items[i]->window.name, "ctr_darkwolf_rend2_settings" ) ) {
			return;
		}
	}

	controls = DarkWolf_FindMenuItemByName( menu, "controls" );'''

replace_once(shared, old_head, new_head)

old_wrapper = r'''void DarkWolf_InjectOptionsRend2Tab( void ) {
	// setup_menu = front-end Options; setup_menu2 = in-game ESC -> Options.
	// Inject into both when both are loaded. This is intentionally idempotent.
	DarkWolf_InjectOptionsRend2TabInto( Menus_FindByName( "setup_menu" ), qfalse );
	DarkWolf_InjectOptionsRend2TabInto( Menus_FindByName( "setup_menu2" ), qtrue );
}'''

new_wrapper = r'''void DarkWolf_InjectOptionsRend2Tab( void ) {
	// Front-end settings still use setup_menu.
	// Retail SP in-game SYSTEM uses its own menuDef: ingame_system.
	// Do not use setup_menu2 here: that path belongs to Controls in UI_RunMenuScript.
	DarkWolf_InjectOptionsRend2TabInto( Menus_FindByName( "setup_menu" ), qfalse );
	DarkWolf_InjectOptionsRend2TabInto( Menus_FindByName( "ingame_system" ), qtrue );
}'''

replace_once(shared, old_wrapper, new_wrapper)

main = "SP/code/ui/ui_main.c"

old_back = r'''		} else if ( Q_stricmp( name, "darkwolfSettingsBack" ) == 0 ) {
			Menus_CloseAll();
			if ( trap_Cvar_VariableValue( "ui_darkwolfReturnIngame" ) > 0.5f && Menus_FindByName( "setup_menu2" ) ) {
				Menus_ActivateByName( "setup_menu2" );
			} else {
				Menus_ActivateByName( "setup_menu" );
			}'''

new_back = r'''		} else if ( Q_stricmp( name, "darkwolfSettingsBack" ) == 0 ) {
			Menus_CloseAll();
			if ( trap_Cvar_VariableValue( "ui_darkwolfReturnIngame" ) > 0.5f && Menus_FindByName( "ingame_system" ) ) {
				Menus_ActivateByName( "ingame" );
				Menus_ActivateByName( "ingame_system" );
			} else {
				Menus_ActivateByName( "setup_menu" );
			}'''

replace_once(main, old_back, new_back)

print("DARKWOLF_UI_V4_4_2_REAL_INGAME_SYSTEM_FIX_PATCH_OK")
