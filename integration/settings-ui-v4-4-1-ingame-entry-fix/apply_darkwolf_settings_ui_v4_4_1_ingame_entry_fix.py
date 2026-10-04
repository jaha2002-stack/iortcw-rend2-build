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


# v4.4 root cause:
# The same front-end tab anchor set (controls/system/gameoptions/defaults) was
# required for setup_menu2. Retail in-game UI is loaded from its own ingame
# menu set, so setup_menu2 may legitimately not expose those front-end anchors.
# The old function then returned without creating REND2 SETTINGS.
#
# v4.4.1 keeps the front-end semantic relayout unchanged, but gives setup_menu2
# an independent, idempotent native button that needs no retail asset names.
shared = "SP/code/ui/ui_shared.c"
old_inject_head = '''static void DarkWolf_InjectOptionsRend2TabInto( menuDef_t *menu, qboolean inGame ) {
\titemDef_t *controls, *system, *game, *mods, *defaults, *item;
\tfloat left, right, y, h, slot;
\tint i;
\tchar action[160];

\tif ( !menu || menu->itemCount >= MAX_MENUITEMS ) return;

\tfor ( i = 0; i < menu->itemCount; i++ ) {
\t\tif ( menu->items[i] && menu->items[i]->window.name &&
\t\t\t !Q_stricmp( menu->items[i]->window.name, "ctr_darkwolf_rend2_settings" ) ) {
\t\t\treturn;
\t\t}
\t}

\tcontrols = DarkWolf_FindMenuItemByName( menu, "controls" );'''

new_inject_head = '''static void DarkWolf_InjectIngameRend2Button( menuDef_t *menu ) {
\titemDef_t *item, *styleSource = NULL;
\tfloat menuW, menuH, w, h, x, y;
\tint i;

\tif ( !menu || menu->itemCount >= MAX_MENUITEMS ) return;

\t/*
\t * setup_menu2 belongs to the separately loaded in-game menu set.  Do not
\t * depend on front-end item names/text here.  Pick a visible button only as
\t * an optional style source; geometry and visibility have deterministic
\t * fallbacks so the entry remains available with the retail menu pack.
\t */
\tfor ( i = 0; i < menu->itemCount; i++ ) {
\t\titemDef_t *candidate = menu->items[i];
\t\tif ( candidate && candidate->type == ITEM_TYPE_BUTTON && candidate->text &&
\t\t\t( candidate->window.flags & WINDOW_VISIBLE ) &&
\t\t\t!( candidate->window.flags & WINDOW_DECORATION ) ) {
\t\t\tstyleSource = candidate;
\t\t\tbreak;
\t\t}
\t}

\tmenuW = menu->window.rect.w > 0.0f ? menu->window.rect.w : 640.0f;
\tmenuH = menu->window.rect.h > 0.0f ? menu->window.rect.h : 480.0f;
\tw = 158.0f;
\th = 22.0f;
\tx = menuW - w - 12.0f;
\ty = 10.0f;
\tif ( x < 8.0f ) x = 8.0f;
\tif ( y + h > menuH - 4.0f ) y = menuH - h - 8.0f;
\tif ( y < 8.0f ) y = 8.0f;

\titem = UI_Alloc( sizeof( *item ) );
\tif ( !item ) return;
\tItem_Init( item );
\titem->window.name = String_Alloc( "ctr_darkwolf_rend2_settings" );
\titem->window.rectClient.x = x;
\titem->window.rectClient.y = y;
\titem->window.rectClient.w = w;
\titem->window.rectClient.h = h;

\tif ( styleSource ) {
\t\titem->window.style = styleSource->window.style;
\t\titem->window.border = styleSource->window.border;
\t\titem->window.borderSize = styleSource->window.borderSize;
\t\titem->window.background = styleSource->window.background;
\t\titem->window.flags = ( styleSource->window.flags | WINDOW_VISIBLE | WINDOW_FORECOLORSET ) &
\t\t\t~( WINDOW_HASFOCUS | WINDOW_GREY | WINDOW_DECORATION );
\t\tVector4Copy( styleSource->window.foreColor, item->window.foreColor );
\t\tVector4Copy( styleSource->window.backColor, item->window.backColor );
\t\tVector4Copy( styleSource->window.borderColor, item->window.borderColor );
\t\titem->textscale = styleSource->textscale > 0.0f ? styleSource->textscale : 0.20f;
\t\titem->textaligny = styleSource->textaligny > 0.0f ? styleSource->textaligny : 15.0f;
\t\titem->textStyle = styleSource->textStyle;
\t\titem->font = styleSource->font;
\t\titem->focusSound = styleSource->focusSound;
\t} else {
\t\titem->window.style = WINDOW_STYLE_FILLED;
\t\titem->window.border = WINDOW_BORDER_FULL;
\t\titem->window.borderSize = 1.0f;
\t\titem->window.flags = WINDOW_VISIBLE | WINDOW_FORECOLORSET | WINDOW_BACKCOLORSET;
\t\titem->window.foreColor[0] = 1.0f; item->window.foreColor[1] = 0.82f; item->window.foreColor[2] = 0.22f; item->window.foreColor[3] = 1.0f;
\t\titem->window.backColor[0] = 0.12f; item->window.backColor[1] = 0.10f; item->window.backColor[2] = 0.05f; item->window.backColor[3] = 0.94f;
\t\titem->window.borderColor[0] = 0.65f; item->window.borderColor[1] = 0.48f; item->window.borderColor[2] = 0.16f; item->window.borderColor[3] = 0.95f;
\t\titem->textscale = 0.20f;
\t\titem->textaligny = 15.0f;
\t}

\titem->type = ITEM_TYPE_BUTTON;
\titem->text = String_Alloc( "REND2 SETTINGS" );
\titem->textalignment = ITEM_ALIGN_CENTER;
\titem->textalignx = w * 0.5f;
\titem->action = String_Alloc( "setcvar ui_darkwolfReturnIngame 1 ; open darkwolf_graphics" );
\titem->parent = menu;
\tmenu->items[menu->itemCount++] = item;
\tItem_InitControls( item );
\tMenu_PostParse( menu );
\tCom_Printf( S_COLOR_GREEN "DarkWolf UI v4.4.1: REND2 SETTINGS attached to in-game setup_menu2.\\n" );
}

static void DarkWolf_InjectOptionsRend2TabInto( menuDef_t *menu, qboolean inGame ) {
\titemDef_t *controls, *system, *game, *mods, *defaults, *item;
\tfloat left, right, y, h, slot;
\tint i;
\tchar action[160];

\tif ( !menu || menu->itemCount >= MAX_MENUITEMS ) return;

\tfor ( i = 0; i < menu->itemCount; i++ ) {
\t\tif ( menu->items[i] && menu->items[i]->window.name &&
\t\t\t !Q_stricmp( menu->items[i]->window.name, "ctr_darkwolf_rend2_settings" ) ) {
\t\t\treturn;
\t\t}
\t}

\tif ( inGame ) {
\t\tDarkWolf_InjectIngameRend2Button( menu );
\t\treturn;
\t}

\tcontrols = DarkWolf_FindMenuItemByName( menu, "controls" );'''
replace_once(shared, old_inject_head, new_inject_head)

# Re-assert the in-game entry immediately before the engine activates setup_menu2.
# This makes the hook resilient to later UI menu reloads and removes load-order
# assumptions from the original v4.4 implementation.
main = "SP/code/ui/ui_main.c"
old_controls = '''\t\t} else if ( Q_stricmp( name, "Controls" ) == 0 ) {
\t\t\ttrap_Cvar_Set( "cl_paused", "1" );
\t\t\ttrap_Key_SetCatcher( KEYCATCH_UI );
\t\t\tMenus_CloseAll();
\t\t\tMenus_ActivateByName( "setup_menu2" );'''
new_controls = '''\t\t} else if ( Q_stricmp( name, "Controls" ) == 0 ) {
\t\t\ttrap_Cvar_Set( "cl_paused", "1" );
\t\t\ttrap_Key_SetCatcher( KEYCATCH_UI );
\t\t\tMenus_CloseAll();
\t\t\tDarkWolf_InjectOptionsRend2Tab();
\t\t\tMenus_ActivateByName( "setup_menu2" );'''
replace_once(main, old_controls, new_controls)

# Re-assert before returning from DarkWolf graphics to the in-game options menu.
old_back = '''\t\t} else if ( Q_stricmp( name, "darkwolfSettingsBack" ) == 0 ) {
\t\t\tMenus_CloseAll();
\t\t\tif ( trap_Cvar_VariableValue( "ui_darkwolfReturnIngame" ) > 0.5f && Menus_FindByName( "setup_menu2" ) ) {
\t\t\t\tMenus_ActivateByName( "setup_menu2" );''

new_back = '''\t\t} else if ( Q_stricmp( name, "darkwolfSettingsBack" ) == 0 ) {
\t\t\tMenus_CloseAll();
\t\t\tif ( trap_Cvar_VariableValue( "ui_darkwolfReturnIngame" ) > 0.5f && Menus_FindByName( "setup_menu2" ) ) {
\t\t\t\tDarkWolf_InjectOptionsRend2Tab();
\t\t\t\tMenus_ActivateByName( "setup_menu2" );''

replace_once(main, old_back, new_back)

print("DARKWOLF_UI_V4_4_1_INGAME_ENTRY_FIX_PATCH_OK")
