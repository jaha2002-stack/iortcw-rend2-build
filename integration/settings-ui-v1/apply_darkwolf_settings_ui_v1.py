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

if not CHECK_ONLY:
    p.write_text(data, encoding="utf-8", newline="\n")

print("DARKWOLF_SETTINGS_UI_V1_PATCH_OK")
