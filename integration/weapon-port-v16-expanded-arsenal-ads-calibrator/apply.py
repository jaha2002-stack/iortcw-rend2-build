#!/usr/bin/env python3
from pathlib import Path
import sys,json,hashlib,re

MARK="DARKWOLF_WEAPON_PORT_V16_EXPANDED_ARSENAL_ADS_CAL"

def fail(m): raise SystemExit(m)
def one(s,a,b,label):
    n=s.count(a)
    if n!=1: fail(f"{label}: expected 1 anchor, got {n}")
    return s.replace(a,b,1)

if len(sys.argv)<2: fail("usage: apply.py <source-root> [evidence-dir]")
root=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/"evidence"
ev.mkdir(parents=True,exist_ok=True)

# ---- weapon enum: append-only, preserve legacy and V1/V1.5 ids ----
p=root/"SP/code/game/bg_public.h"
s0=p.read_text(encoding="utf-8")
if MARK in s0:
    print("DW_WEAPON_PORT_V16_ALREADY_APPLIED")
    raise SystemExit(0)
old='''\tWP_DW_MP44,             // 32 StG44 / MP44
\tWP_DW_PPSH,             // 33 PPSh-41

\tWP_NUM_WEAPONS          // 34   NOTE: this cannot be larger than 64 for AI/player weapons!
'''
new='''\tWP_DW_MP44,             // 32 StG44 / MP44
\tWP_DW_PPSH,             // 33 PPSh-41
\t// DARKWOLF_WEAPON_PORT_V16_EXPANDED_ARSENAL_ADS_CAL
\tWP_DW_MP34,             // 34
\tWP_DW_BAR,              // 35
\tWP_DW_TT33,             // 36
\tWP_DW_DUAL_TT33,        // 37
\tWP_DW_REVOLVER,         // 38
\tWP_DW_HDM,              // 39 suppressed pistol
\tWP_DW_MOSIN,            // 40
\tWP_DW_M1GARAND,         // 41
\tWP_DW_G43,              // 42
\tWP_DW_M97,              // 43 Ithaca M97
\tWP_DW_BROWNING,         // 44
\tWP_DW_MG42M,            // 45 portable MG42

\tWP_NUM_WEAPONS          // 46   NOTE: must remain <= MAX_WEAPONS (64)
'''
s=one(s0,old,new,"weapon enum")
oldmask='#define WEAPS_ONE_HANDED    ( ( 1 << WP_KNIFE ) | ( 1 << WP_LUGER ) | ( 1 << WP_COLT ) | ( 1 << WP_SILENCER ) | ( 1 << WP_GRENADE_LAUNCHER ) | ( 1 << WP_GRENADE_PINEAPPLE ) )\n'
newmask=oldmask+'''// Append-only weapon ids cannot be represented in the legacy 32-bit mask.
#define DW_IS_ONE_HANDED_WEAPON(w) \
\t( ((w) >= 0) && ( (((w) < 32) && ( WEAPS_ONE_HANDED & ( 1u << (w) ) )) || \
\t  (w) == WP_DW_TT33 || (w) == WP_DW_REVOLVER || (w) == WP_DW_HDM ) )
'''
s=one(s,oldmask,newmask,"one-handed helper")
p.write_text(s,encoding="utf-8")

# ---- bank width: match RealRTCW-style expanded banks ----
p=root/"SP/code/qcommon/q_shared.h"
q0=p.read_text(encoding="utf-8")
q1=one(q0,"#define MAX_WEAPS_IN_BANK   3\n","#define MAX_WEAPS_IN_BANK   10 // DarkWolf V1.6 expanded conventional arsenal\n","bank width")
p.write_text(q1,encoding="utf-8")

# ---- model hard limit: Browning has 18,054 triangles on one surface ----
p=root/"SP/code/qcommon/qfiles.h"
f0=p.read_text(encoding="utf-8")
f1=one(f0,"#define MD3_MAX_TRIANGLES   16384   // per surface - DARKWOLF_WEAPON_PORT_V11_HD_MODEL_LIMIT","#define MD3_MAX_TRIANGLES   32768   // per surface - DARKWOLF_WEAPON_PORT_V16_EXPANDED_ARSENAL_ADS_CAL","MD3 triangle limit")
p.write_text(f1,encoding="utf-8")

# ---- ammo table and item definitions ----
p=root/"SP/code/game/bg_misc.c"
b0=p.read_text(encoding="utf-8")
oldtail='''\t{   200,            1,      30,     2600,   DELAY_LOW,      115,    0,      0,      MOD_FG42                },  // WP_DW_MP44 / 32
\t{   400,            1,      71,     2600,   DELAY_LOW,      65,     0,      0,      MOD_MP40                }   // WP_DW_PPSH / 33
};'''
newtail='''\t{   200,            1,      30,     2600,   DELAY_LOW,      115,    0,      0,      MOD_FG42                },  // WP_DW_MP44 / 32
\t{   400,            1,      71,     2600,   DELAY_LOW,      65,     0,      0,      MOD_MP40                },  // WP_DW_PPSH / 33
\t{   300,            1,      32,     2620,   DELAY_LOW,      105,    0,      0,      MOD_MP40                },  // WP_DW_MP34 / 34
\t{   300,            1,      20,     3300,   DELAY_LOW,      200,    0,      0,      MOD_BAR                 },  // WP_DW_BAR / 35
\t{   400,            1,      8,      1600,   DELAY_LOW,      350,    0,      0,      MOD_LUGER               },  // WP_DW_TT33 / 36
\t{   300,            1,      16,     2000,   DELAY_LOW,      220,    0,      0,      MOD_AKIMBO              },  // WP_DW_DUAL_TT33 / 37
\t{   60,             1,      6,      3600,   DELAY_LOW,      380,    0,      0,      MOD_COLT                },  // WP_DW_REVOLVER / 38
\t{   200,            1,      10,     2300,   DELAY_LOW,      300,    0,      0,      MOD_SILENCER            },  // WP_DW_HDM / 39
\t{   150,            1,      5,      2250,   DELAY_LOW,      1400,   0,      0,      MOD_MAUSER              },  // WP_DW_MOSIN / 40
\t{   300,            1,      8,      1650,   DELAY_LOW,      300,    0,      0,      MOD_GARAND              },  // WP_DW_M1GARAND / 41
\t{   200,            1,      10,     2300,   DELAY_LOW,      300,    0,      0,      MOD_GARAND              },  // WP_DW_G43 / 42
\t{   100,            1,      7,      2300,   DELAY_LOW,      800,    0,      0,      MOD_BAR                 },  // WP_DW_M97 / 43
\t{   1000,           1,      100,    7000,   DELAY_LOW,      100,    0,      0,      MOD_FG42                },  // WP_DW_BROWNING / 44
\t{   1000,           1,      50,     4800,   DELAY_LOW,      70,     0,      0,      MOD_FG42                }   // WP_DW_MG42M / 45
};'''
b=one(b0,oldtail,newtail,"ammo append")

ppsh='''\t{
\t\t"weapon_dw_ppsh", "sound/misc/w_pkup.wav",
\t\t{ "models/weapons/smgs/ppsh/ppsh_3rd.md3", "models/weapons/smgs/ppsh/v_ppsh.md3", "models/weapons/smgs/ppsh/ppsh_3rd.md3", 0, 0 },
\t\t"icons/iconw_ppsh_1", "icons/ammo2", "PPSh-41", 71, IT_WEAPON,
\t\tWP_DW_PPSH, WP_DW_PPSH, WP_DW_PPSH, "", "", {0,0,0,0}
\t},
'''
items=ppsh+'''\t// DARKWOLF_WEAPON_PORT_V16_EXPANDED_ARSENAL_ADS_CAL
\t{ "weapon_dw_mp34", "sound/misc/w_pkup.wav",
\t  { "models/weapons/smgs/mp34/mp34_3rd.md3", "models/weapons/smgs/mp34/v_mp34.md3", "models/weapons/smgs/mp34/mp34_3rd.md3", 0, 0 },
\t  "icons/iconw_mp34", "icons/ammo2", "MP34", 32, IT_WEAPON, WP_DW_MP34, WP_DW_MP34, WP_DW_MP34, "", "", {0,0,0,0} },
\t{ "weapon_dw_bar", "sound/misc/w_pkup.wav",
\t  { "models/weapons/assault_rifles/bar/bar_3rd.md3", "models/weapons/assault_rifles/bar/v_bar.md3", "models/weapons/assault_rifles/bar/bar_3rd.md3", 0, 0 },
\t  "icons/iconw_bar", "icons/ammo5", "BAR", 20, IT_WEAPON, WP_DW_BAR, WP_DW_BAR, WP_DW_BAR, "", "", {0,0,0,0} },
\t{ "weapon_dw_tt33", "sound/misc/w_pkup.wav",
\t  { "models/weapons/pistols/tt33/tt33_3rd.md3", "models/weapons/pistols/tt33/v_tt33.md3", "models/weapons/pistols/tt33/tt33_3rd.md3", 0, 0 },
\t  "icons/iconw_tt33", "icons/ammo2", "TT-33", 8, IT_WEAPON, WP_DW_TT33, WP_DW_TT33, WP_DW_TT33, "", "", {0,0,0,0} },
\t{ "weapon_dw_dual_tt33", "sound/misc/w_pkup.wav",
\t  { "models/weapons/pistols/tt33/tt33_3rd.md3", "models/weapons/pistols/tt33_2/v_tt33_2.md3", "models/weapons/pistols/tt33/tt33_3rd.md3", 0, 0 },
\t  "icons/iconw_dualtt33", "icons/ammo2", "Dual TT-33", 16, IT_WEAPON, WP_DW_DUAL_TT33, WP_DW_DUAL_TT33, WP_DW_DUAL_TT33, "", "", {0,0,0,0} },
\t{ "weapon_dw_revolver", "sound/misc/w_pkup.wav",
\t  { "models/weapons/pistols/revolver/revolver_3rd.md3", "models/weapons/pistols/revolver/v_revolver.md3", "models/weapons/pistols/revolver/revolver_3rd.md3", 0, 0 },
\t  "icons/iconw_revolver", "icons/ammo2", "Revolver", 6, IT_WEAPON, WP_DW_REVOLVER, WP_DW_REVOLVER, WP_DW_REVOLVER, "", "", {0,0,0,0} },
\t{ "weapon_dw_hdm", "sound/misc/w_pkup.wav",
\t  { "models/weapons/pistols/hdm/hdm_3rd.md3", "models/weapons/pistols/hdm/v_hdm.md3", "models/weapons/pistols/hdm/hdm_3rd.md3", 0, 0 },
\t  "icons/iconw_hdm_1", "icons/ammo2", "HDM", 10, IT_WEAPON, WP_DW_HDM, WP_DW_HDM, WP_DW_HDM, "", "", {0,0,0,0} },
\t{ "weapon_dw_mosin", "sound/misc/w_pkup.wav",
\t  { "models/weapons/rifles/mosin/mosin_3rd.md3", "models/weapons/rifles/mosin/v_mosin.md3", "models/weapons/rifles/mosin/mosin_3rd.md3", 0, 0 },
\t  "icons/iconw_mosin", "icons/ammo5", "Mosin-Nagant", 5, IT_WEAPON, WP_DW_MOSIN, WP_DW_MOSIN, WP_DW_MOSIN, "", "", {0,0,0,0} },
\t{ "weapon_dw_m1garand", "sound/misc/w_pkup.wav",
\t  { "models/weapons/auto_rifles/m1_garand/m1_3rd.md3", "models/weapons/auto_rifles/m1_garand/v_m1.md3", "models/weapons/auto_rifles/m1_garand/m1_3rd.md3", 0, 0 },
\t  "icons/iconw_m1garand", "icons/ammo5", "M1 Garand", 8, IT_WEAPON, WP_DW_M1GARAND, WP_DW_M1GARAND, WP_DW_M1GARAND, "", "", {0,0,0,0} },
\t{ "weapon_dw_g43", "sound/misc/w_pkup.wav",
\t  { "models/weapons/auto_rifles/g43/g43_3rd.md3", "models/weapons/auto_rifles/g43/v_g43.md3", "models/weapons/auto_rifles/g43/g43_3rd.md3", 0, 0 },
\t  "icons/iconw_g43", "icons/ammo5", "G43", 10, IT_WEAPON, WP_DW_G43, WP_DW_G43, WP_DW_G43, "", "", {0,0,0,0} },
\t{ "weapon_dw_m97", "sound/misc/w_pkup.wav",
\t  { "models/weapons/shotguns/ithaca/ithaca_3rd.md3", "models/weapons/shotguns/ithaca/v_ithaca.md3", "models/weapons/shotguns/ithaca/ithaca_3rd.md3", 0, 0 },
\t  "icons/iconw_ithaca", "icons/ammo5", "Ithaca M97", 7, IT_WEAPON, WP_DW_M97, WP_DW_M97, WP_DW_M97, "", "", {0,0,0,0} },
\t{ "weapon_dw_browning", "sound/misc/w_pkup.wav",
\t  { "models/weapons/heavy/browning/brown30cal_3rd.md3", "models/weapons/heavy/browning/v_brown30cal.md3", "models/weapons/heavy/browning/brown30cal_3rd.md3", 0, 0 },
\t  "icons/iconw_browning", "icons/ammo5", "Browning", 100, IT_WEAPON, WP_DW_BROWNING, WP_DW_BROWNING, WP_DW_BROWNING, "", "", {0,0,0,0} },
\t{ "weapon_dw_mg42m", "sound/misc/w_pkup.wav",
\t  { "models/weapons/heavy/mg42/mg42_3rd.md3", "models/weapons/heavy/mg42/v_mg42.md3", "models/weapons/heavy/mg42/mg42_3rd.md3", 0, 0 },
\t  "icons/iconw_mg42m", "icons/ammo5", "MG42M", 50, IT_WEAPON, WP_DW_MG42M, WP_DW_MG42M, WP_DW_MG42M, "", "", {0,0,0,0} },
'''
b=one(b,ppsh,items,"expanded item list")
p.write_text(b,encoding="utf-8")

# ---- pmove: reload eligibility, animation cadence, aim-spread cadence ----
p=root/"SP/code/game/bg_pmove.c"
m0=p.read_text(encoding="utf-8")
oldgate='''\t// DARKWOLF_WEAPON_PORT_V15_FULL_FIRE_ADS_RELOAD:
\t// the original range predates append-only WP_DW_MP44/WP_DW_PPSH (32/33).
\t// Keep monster/special weapons excluded, but explicitly allow the two ports.
\tif ( weapon < WP_BEGINGERMAN ||
\t\t ( weapon > WP_DYNAMITE && weapon != WP_DW_MP44 && weapon != WP_DW_PPSH ) ) {
\t\treturn;
\t}
'''
newgate='''\t// DARKWOLF_WEAPON_PORT_V16_EXPANDED_ARSENAL_ADS_CAL:
\t// All append-only DarkWolf conventional firearms are reloadable.
\tif ( weapon < WP_BEGINGERMAN ||
\t\t ( weapon > WP_DYNAMITE && !( weapon >= WP_DW_MP44 && weapon < WP_NUM_WEAPONS ) ) ) {
\t\treturn;
\t}
'''
m=one(m0,oldgate,newgate,"expanded reload gate")
oldanim='''\tcase WP_VENOM:
\tcase WP_MP40:
\tcase WP_THOMPSON:
\tcase WP_STEN:
\tcase WP_DW_MP44:
\tcase WP_DW_PPSH:
\t\tPM_ContinueWeaponAnim( weapattackanim );'''
newanim='''\tcase WP_VENOM:
\tcase WP_MP40:
\tcase WP_THOMPSON:
\tcase WP_STEN:
\tcase WP_DW_MP44:
\tcase WP_DW_PPSH:
\tcase WP_DW_MP34:
\tcase WP_DW_BAR:
\tcase WP_DW_BROWNING:
\tcase WP_DW_MG42M:
\t\tPM_ContinueWeaponAnim( weapattackanim );'''
m=one(m,oldanim,newanim,"automatic animation group")
oldauto='''\tcase WP_FG42:
\tcase WP_MP40:
\tcase WP_THOMPSON:
\tcase WP_DW_MP44:
\tcase WP_DW_PPSH:
\t\taddTime = ammoTable[pm->ps->weapon].nextShotTime;
\t\taimSpreadScaleAdd = 15 + rand() % 10;       // (SA) new values for DM
\t\tbreak;'''
newauto='''\tcase WP_FG42:
\tcase WP_MP40:
\tcase WP_THOMPSON:
\tcase WP_DW_MP44:
\tcase WP_DW_PPSH:
\tcase WP_DW_MP34:
\tcase WP_DW_BAR:
\tcase WP_DW_BROWNING:
\tcase WP_DW_MG42M:
\t\taddTime = ammoTable[pm->ps->weapon].nextShotTime;
\t\taimSpreadScaleAdd = 15 + rand() % 10;
\t\tbreak;'''
m=one(m,oldauto,newauto,"automatic shot cadence")
# Add semiauto pistol and rifle cadence before stock mauser case.
anchor='''\tcase WP_MAUSER:
\tcase WP_GARAND:
\t\taddTime = ammoTable[pm->ps->weapon].nextShotTime;
\t\taimSpreadScaleAdd = 50;
\t\tbreak;'''
insert='''\tcase WP_DW_TT33:
\tcase WP_DW_DUAL_TT33:
\tcase WP_DW_REVOLVER:
\tcase WP_DW_HDM:
\t\taddTime = ammoTable[pm->ps->weapon].nextShotTime;
\t\taimSpreadScaleAdd = 25;
\t\tbreak;
\tcase WP_DW_MOSIN:
\tcase WP_DW_M1GARAND:
\tcase WP_DW_G43:
\tcase WP_DW_M97:
\t\taddTime = ammoTable[pm->ps->weapon].nextShotTime;
\t\taimSpreadScaleAdd = 45;
\t\tbreak;
'''+anchor
m=one(m,anchor,insert,"semi-auto cadence")
# Aim-spread movement scale additions after V1 entries.
anchor='''\tcase WP_DW_MP44: wpnScale = 0.8f; break;
\tcase WP_DW_PPSH: wpnScale = 0.6f; break;'''
insert=anchor+'''
\tcase WP_DW_MP34: wpnScale = 0.6f; break;
\tcase WP_DW_BAR: wpnScale = 0.8f; break;
\tcase WP_DW_TT33:
\tcase WP_DW_DUAL_TT33:
\tcase WP_DW_REVOLVER:
\tcase WP_DW_HDM: wpnScale = 0.4f; break;
\tcase WP_DW_MOSIN:
\tcase WP_DW_M1GARAND:
\tcase WP_DW_G43: wpnScale = 1.0f; break;
\tcase WP_DW_M97: wpnScale = 0.9f; break;
\tcase WP_DW_BROWNING:
\tcase WP_DW_MG42M: wpnScale = 0.7f; break;'''
m=one(m,anchor,insert,"aim movement scale")
p.write_text(m,encoding="utf-8")

# ---- server fire behavior ----
p=root/"SP/code/game/g_weapon.c"
g0=p.read_text(encoding="utf-8")
g=g0
# damage blocks created by V1
old='''\t\tcase WP_MP40: return 6;
\t\tcase WP_DW_MP44: return 9;
\t\tcase WP_DW_PPSH: return 6;
\t\tcase WP_THOMPSON: return 8;'''
new='''\t\tcase WP_MP40: return 6;
\t\tcase WP_DW_MP44: return 9;
\t\tcase WP_DW_PPSH: return 6;
\t\tcase WP_DW_MP34: return 6;
\t\tcase WP_DW_BAR: return 15;
\t\tcase WP_DW_TT33: return 9;
\t\tcase WP_DW_DUAL_TT33: return 9;
\t\tcase WP_DW_REVOLVER: return 18;
\t\tcase WP_DW_HDM: return 8;
\t\tcase WP_DW_MOSIN: return 30;
\t\tcase WP_DW_M1GARAND: return 20;
\t\tcase WP_DW_G43: return 20;
\t\tcase WP_DW_M97: return 10;
\t\tcase WP_DW_BROWNING: return 15;
\t\tcase WP_DW_MG42M: return 15;
\t\tcase WP_THOMPSON: return 8;'''
g=one(g,old,new,"SP damage")
old='''\t\tcase WP_MP40: return 14;
\t\tcase WP_DW_MP44: return 18;
\t\tcase WP_DW_PPSH: return 14;
\t\tcase WP_THOMPSON: return 18;'''
new='''\t\tcase WP_MP40: return 14;
\t\tcase WP_DW_MP44: return 18;
\t\tcase WP_DW_PPSH: return 14;
\t\tcase WP_DW_MP34: return 14;
\t\tcase WP_DW_BAR: return 25;
\t\tcase WP_DW_TT33: return 18;
\t\tcase WP_DW_DUAL_TT33: return 18;
\t\tcase WP_DW_REVOLVER: return 32;
\t\tcase WP_DW_HDM: return 16;
\t\tcase WP_DW_MOSIN: return 50;
\t\tcase WP_DW_M1GARAND: return 30;
\t\tcase WP_DW_G43: return 30;
\t\tcase WP_DW_M97: return 10;
\t\tcase WP_DW_BROWNING: return 22;
\t\tcase WP_DW_MG42M: return 22;
\t\tcase WP_THOMPSON: return 18;'''
g=one(g,old,new,"MP damage")
# spread blocks
old='''\t\t\tcase WP_MP40:       return 1000;
\t\t\tcase WP_DW_MP44:    return 800;
\t\t\tcase WP_DW_PPSH:    return 1000;
\t\t\tcase WP_FG42SCOPE:'''
new='''\t\t\tcase WP_MP40:       return 1000;
\t\t\tcase WP_DW_MP44:    return 800;
\t\t\tcase WP_DW_PPSH:    return 1000;
\t\t\tcase WP_DW_MP34:    return 900;
\t\t\tcase WP_DW_BAR:     return 700;
\t\t\tcase WP_DW_TT33:    return 450;
\t\t\tcase WP_DW_DUAL_TT33:return 500;
\t\t\tcase WP_DW_REVOLVER:return 300;
\t\t\tcase WP_DW_HDM:     return 250;
\t\t\tcase WP_DW_MOSIN:   return 300;
\t\t\tcase WP_DW_M1GARAND:return 350;
\t\t\tcase WP_DW_G43:     return 350;
\t\t\tcase WP_DW_M97:     return 4500;
\t\t\tcase WP_DW_BROWNING:return 1000;
\t\t\tcase WP_DW_MG42M:   return 1200;
\t\t\tcase WP_FG42SCOPE:'''
g=one(g,old,new,"userAim spread")
old='''\t\t\tcase WP_MP40:       return 200;
\t\t\tcase WP_DW_MP44:    return 180;
\t\t\tcase WP_DW_PPSH:    return 250;
\t\t\tcase WP_FG42SCOPE:'''
new='''\t\t\tcase WP_MP40:       return 200;
\t\t\tcase WP_DW_MP44:    return 180;
\t\t\tcase WP_DW_PPSH:    return 250;
\t\t\tcase WP_DW_MP34:    return 225;
\t\t\tcase WP_DW_BAR:     return 175;
\t\t\tcase WP_DW_TT33:    return 115;
\t\t\tcase WP_DW_DUAL_TT33:return 125;
\t\t\tcase WP_DW_REVOLVER:return 75;
\t\t\tcase WP_DW_HDM:     return 65;
\t\t\tcase WP_DW_MOSIN:   return 75;
\t\t\tcase WP_DW_M1GARAND:return 90;
\t\t\tcase WP_DW_G43:     return 90;
\t\t\tcase WP_DW_M97:     return 1125;
\t\t\tcase WP_DW_BROWNING:return 250;
\t\t\tcase WP_DW_MG42M:   return 300;
\t\t\tcase WP_FG42SCOPE:'''
g=one(g,old,new,"legacy spread")
old='''\t\tcase WP_MP40: return 400;
\t\tcase WP_DW_MP44: return 500;
\t\tcase WP_DW_PPSH: return 600;
\t\tcase WP_FG42SCOPE:'''
new='''\t\tcase WP_MP40: return 400;
\t\tcase WP_DW_MP44: return 500;
\t\tcase WP_DW_PPSH: return 600;
\t\tcase WP_DW_MP34: return 550;
\t\tcase WP_DW_BAR: return 450;
\t\tcase WP_DW_TT33: return 300;
\t\tcase WP_DW_DUAL_TT33: return 350;
\t\tcase WP_DW_REVOLVER: return 200;
\t\tcase WP_DW_HDM: return 180;
\t\tcase WP_DW_MOSIN: return 200;
\t\tcase WP_DW_M1GARAND: return 250;
\t\tcase WP_DW_G43: return 250;
\t\tcase WP_DW_M97: return 2500;
\t\tcase WP_DW_BROWNING: return 600;
\t\tcase WP_DW_MG42M: return 700;
\t\tcase WP_FG42SCOPE:'''
g=one(g,old,new,"MP spread")
# macros
anchor='#define DW_PPSH_DAMAGE G_GetWeaponDamage( WP_DW_PPSH )\n'
macros=anchor+'''#define DW_MP34_SPREAD G_GetWeaponSpread( WP_DW_MP34 )
#define DW_MP34_DAMAGE G_GetWeaponDamage( WP_DW_MP34 )
#define DW_BAR_SPREAD G_GetWeaponSpread( WP_DW_BAR )
#define DW_BAR_DAMAGE G_GetWeaponDamage( WP_DW_BAR )
#define DW_TT33_SPREAD G_GetWeaponSpread( WP_DW_TT33 )
#define DW_TT33_DAMAGE G_GetWeaponDamage( WP_DW_TT33 )
#define DW_DUAL_TT33_SPREAD G_GetWeaponSpread( WP_DW_DUAL_TT33 )
#define DW_DUAL_TT33_DAMAGE G_GetWeaponDamage( WP_DW_DUAL_TT33 )
#define DW_REVOLVER_SPREAD G_GetWeaponSpread( WP_DW_REVOLVER )
#define DW_REVOLVER_DAMAGE G_GetWeaponDamage( WP_DW_REVOLVER )
#define DW_HDM_SPREAD G_GetWeaponSpread( WP_DW_HDM )
#define DW_HDM_DAMAGE G_GetWeaponDamage( WP_DW_HDM )
#define DW_MOSIN_SPREAD G_GetWeaponSpread( WP_DW_MOSIN )
#define DW_MOSIN_DAMAGE G_GetWeaponDamage( WP_DW_MOSIN )
#define DW_M1GARAND_SPREAD G_GetWeaponSpread( WP_DW_M1GARAND )
#define DW_M1GARAND_DAMAGE G_GetWeaponDamage( WP_DW_M1GARAND )
#define DW_G43_SPREAD G_GetWeaponSpread( WP_DW_G43 )
#define DW_G43_DAMAGE G_GetWeaponDamage( WP_DW_G43 )
#define DW_M97_SPREAD G_GetWeaponSpread( WP_DW_M97 )
#define DW_M97_DAMAGE G_GetWeaponDamage( WP_DW_M97 )
#define DW_BROWNING_SPREAD G_GetWeaponSpread( WP_DW_BROWNING )
#define DW_BROWNING_DAMAGE G_GetWeaponDamage( WP_DW_BROWNING )
#define DW_MG42M_SPREAD G_GetWeaponSpread( WP_DW_MG42M )
#define DW_MG42M_DAMAGE G_GetWeaponDamage( WP_DW_MG42M )
'''
g=one(g,anchor,macros,"new weapon macros")
# shotgun helper after Bullet_Fire
anchor='''\tBullet_Fire_Extended( ent, ent, muzzleTrace, end, spread, damage, 0 );
}


/*
==============
Bullet_Fire_Extended'''
insert='''\tBullet_Fire_Extended( ent, ent, muzzleTrace, end, spread, damage, 0 );
}

// DARKWOLF_WEAPON_PORT_V16_EXPANDED_ARSENAL_ADS_CAL
// RealRTCW-style shotgun payload: 12 independent pellets through the normal
// RTCW bullet trace/damage/impact path, preserving destructibles and decals.
static void DW_M97_Fire( gentity_t *ent, float spread, int damage ) {
\tint i;
\tfor ( i = 0; i < 12; i++ ) {
\t\tBullet_Fire( ent, spread, damage );
\t}
}


/*
==============
Bullet_Fire_Extended'''
g=one(g,anchor,insert,"M97 pellet helper")
# dual pistol muzzle offset
g=one(g,"\tcase WP_AKIMBO:     // left side rather than right\n",
      "\tcase WP_AKIMBO:     // left side rather than right\n\tcase WP_DW_DUAL_TT33:\n","dual TT33 muzzle")
# fire cases after V1 PPSH block
old='''\tcase WP_DW_PPSH:
\t\tBullet_Fire( ent, DW_PPSH_SPREAD * aimSpreadScale, DW_PPSH_DAMAGE );
\t\tbreak;
\tcase WP_THOMPSON:'''
new='''\tcase WP_DW_PPSH:
\t\tBullet_Fire( ent, DW_PPSH_SPREAD * aimSpreadScale, DW_PPSH_DAMAGE );
\t\tbreak;
\tcase WP_DW_MP34:
\t\tBullet_Fire( ent, DW_MP34_SPREAD * aimSpreadScale, DW_MP34_DAMAGE ); break;
\tcase WP_DW_BAR:
\t\tBullet_Fire( ent, DW_BAR_SPREAD * aimSpreadScale, DW_BAR_DAMAGE ); break;
\tcase WP_DW_TT33:
\t\tBullet_Fire( ent, DW_TT33_SPREAD * aimSpreadScale, DW_TT33_DAMAGE ); break;
\tcase WP_DW_DUAL_TT33:
\t\tBullet_Fire( ent, DW_DUAL_TT33_SPREAD * aimSpreadScale, DW_DUAL_TT33_DAMAGE ); break;
\tcase WP_DW_REVOLVER:
\t\tBullet_Fire( ent, DW_REVOLVER_SPREAD * aimSpreadScale, DW_REVOLVER_DAMAGE ); break;
\tcase WP_DW_HDM:
\t\tBullet_Fire( ent, DW_HDM_SPREAD * aimSpreadScale, DW_HDM_DAMAGE ); break;
\tcase WP_DW_MOSIN:
\t\tBullet_Fire( ent, DW_MOSIN_SPREAD * aimSpreadScale, DW_MOSIN_DAMAGE ); break;
\tcase WP_DW_M1GARAND:
\t\tBullet_Fire( ent, DW_M1GARAND_SPREAD * aimSpreadScale, DW_M1GARAND_DAMAGE ); break;
\tcase WP_DW_G43:
\t\tBullet_Fire( ent, DW_G43_SPREAD * aimSpreadScale, DW_G43_DAMAGE ); break;
\tcase WP_DW_M97:
\t\tDW_M97_Fire( ent, DW_M97_SPREAD * aimSpreadScale, DW_M97_DAMAGE ); break;
\tcase WP_DW_BROWNING:
\t\tBullet_Fire( ent, DW_BROWNING_SPREAD * aimSpreadScale, DW_BROWNING_DAMAGE ); break;
\tcase WP_DW_MG42M:
\t\tBullet_Fire( ent, DW_MG42M_SPREAD * aimSpreadScale, DW_MG42M_DAMAGE ); break;
\tcase WP_THOMPSON:'''
g=one(g,old,new,"expanded FireWeapon cases")
p.write_text(g,encoding="utf-8")

# ---- common one-handed checks beyond 31 bits ----
patches=[
 ("SP/code/game/g_cmds.c",
  "if ( ent->client->pers.cmd.weapon < 32 && ( WEAPS_ONE_HANDED & ( 1 << ent->client->pers.cmd.weapon ) ) ) {",
  "if ( DW_IS_ONE_HANDED_WEAPON( ent->client->pers.cmd.weapon ) ) {"),
 ("SP/code/cgame/cg_weapons.c",
  "if ( i >= 32 || !( WEAPS_ONE_HANDED & ( 1 << i ) ) ) {",
  "if ( !DW_IS_ONE_HANDED_WEAPON( i ) ) {"),
 ("SP/code/cgame/cg_event.c",
  "if ( weapon >= 32 || !( ( 1 << weapon ) & WEAPS_ONE_HANDED ) ) {",
  "if ( !DW_IS_ONE_HANDED_WEAPON( weapon ) ) {"),
 ("SP/code/cgame/cg_newdraw.c",
  "if ( cg.predictedPlayerState.weapon && ( cg.predictedPlayerState.weapon >= 32 || !( WEAPS_ONE_HANDED & ( 1 << cg.predictedPlayerState.weapon ) ) ) ) {",
  "if ( cg.predictedPlayerState.weapon && !DW_IS_ONE_HANDED_WEAPON( cg.predictedPlayerState.weapon ) ) {"),
 ("SP/code/game/ai_cast_think.c",
  "if ( ucmd->weapon < 32 && ( WEAPS_ONE_HANDED & ( 1 << ucmd->weapon ) ) ) { // legacy one-handed mask",
  "if ( DW_IS_ONE_HANDED_WEAPON( ucmd->weapon ) ) { // DarkWolf append-safe one-handed test"),
]
for rel,a,bv in patches:
    fp=root/rel; z=fp.read_text(encoding="utf-8"); z=one(z,a,bv,rel+" one-handed"); fp.write_text(z,encoding="utf-8")
# g_props was not covered by V1; eliminate its high-id shift too.
fp=root/"SP/code/game/g_props.c"; z=fp.read_text(encoding="utf-8")
z=one(z,"if ( player->s.weapon && !( WEAPS_ONE_HANDED & ( 1 << ( player->s.weapon ) ) ) ) {",
      "if ( player->s.weapon && !DW_IS_ONE_HANDED_WEAPON( player->s.weapon ) ) {","g_props one-handed")
fp.write_text(z,encoding="utf-8")

# ---- cgame weapon registration, banks, component format fallback, ADS calibrator ----
p=root/"SP/code/cgame/cg_weapons.c"
c0=p.read_text(encoding="utf-8")
c=c0
# expanded banks after V1 row.
old='''\t{WP_LUGER,              WP_COLT,                0           },  //\t2\t// WP_AKIMBO
\t{WP_MP40,               WP_THOMPSON,            WP_STEN     },  //\t3
\t{WP_MAUSER,             WP_GARAND,              0           },  //\t4
\t{WP_FG42,               WP_DW_MP44,             WP_DW_PPSH  },  //\t5 DarkWolf V1
\t{WP_GRENADE_LAUNCHER,   WP_GRENADE_PINEAPPLE,   WP_DYNAMITE },  //\t6
\t{WP_PANZERFAUST,        0,                      0           },  //\t7
\t{WP_VENOM,              0,                      0           },  //\t8
\t{WP_FLAMETHROWER,       0,                      0           },  //\t9
\t{WP_TESLA,              0,                      0           }   //\t10'''
new='''\t{WP_LUGER, WP_COLT, WP_SILENCER, WP_AKIMBO, WP_DW_TT33, WP_DW_DUAL_TT33, WP_DW_REVOLVER, WP_DW_HDM, 0, 0}, // 2 pistols
\t{WP_MP40, WP_THOMPSON, WP_STEN, WP_DW_MP34, WP_DW_PPSH, 0, 0, 0, 0, 0}, // 3 SMGs
\t{WP_MAUSER, WP_GARAND, WP_DW_MOSIN, WP_DW_M1GARAND, WP_DW_G43, 0, 0, 0, 0, 0}, // 4 rifles
\t{WP_FG42, WP_DW_MP44, WP_DW_BAR, 0, 0, 0, 0, 0, 0, 0}, // 5 assault rifles
\t{WP_GRENADE_LAUNCHER, WP_GRENADE_PINEAPPLE, WP_DYNAMITE, 0, 0, 0, 0, 0, 0, 0}, // 6
\t{WP_PANZERFAUST, WP_DW_M97, 0, 0, 0, 0, 0, 0, 0, 0}, // 7
\t{WP_VENOM, WP_DW_BROWNING, 0, 0, 0, 0, 0, 0, 0, 0}, // 8
\t{WP_FLAMETHROWER, WP_DW_MG42M, 0, 0, 0, 0, 0, 0, 0, 0}, // 9
\t{WP_TESLA, 0, 0, 0, 0, 0, 0, 0, 0, 0} // 10'''
c=one(c,old,new,"expanded weapon banks")
# flash .mdc fallback for RealRTCW Browning
old='''\t\tQ_strcat( path, sizeof(path), "_flash.md3" );
\t\tweaponInfo->flashModel[i] = trap_R_RegisterModel( path );


\t\tfor ( j = 0; j < W_MAX_PARTS; j++ ) {'''
new='''\t\tQ_strcat( path, sizeof(path), "_flash.md3" );
\t\tweaponInfo->flashModel[i] = trap_R_RegisterModel( path );
\t\tif ( !weaponInfo->flashModel[i] ) {
\t\t\tif ( !item->world_model[i] ) Q_strncpyz( path, comppath, sizeof(path) );
\t\t\telse Q_strncpyz( path, item->world_model[i], sizeof(path) );
\t\t\tCOM_StripExtension( path, path, sizeof(path) );
\t\t\tQ_strcat( path, sizeof(path), "_flash.mdc" );
\t\t\tweaponInfo->flashModel[i] = trap_R_RegisterModel( path );
\t\t}


\t\tfor ( j = 0; j < W_MAX_PARTS; j++ ) {'''
c=one(c,old,new,"flash mdc fallback")
# hand .mdc fallback
old='''\tQ_strcat( path, sizeof(path), "_hand.md3" );
\tweaponInfo->handsModel = trap_R_RegisterModel( path );

\tif ( !weaponInfo->handsModel ) {
\t\tweaponInfo->handsModel = trap_R_RegisterModel( "models/weapons2/shotgun/shotgun_hand.md3" );
\t}'''
new='''\tQ_strcat( path, sizeof(path), "_hand.md3" );
\tweaponInfo->handsModel = trap_R_RegisterModel( path );
\tif ( !weaponInfo->handsModel ) {
\t\tif ( !item->world_model[W_FP_MODEL] ) Q_strncpyz( path, comppath, sizeof(path) );
\t\telse Q_strncpyz( path, item->world_model[W_FP_MODEL], sizeof(path) );
\t\tCOM_StripExtension( path, path, sizeof(path) );
\t\tQ_strcat( path, sizeof(path), "_hand.mdc" );
\t\tweaponInfo->handsModel = trap_R_RegisterModel( path );
\t}
\tif ( !weaponInfo->handsModel ) {
\t\tweaponInfo->handsModel = trap_R_RegisterModel( "models/weapons2/shotgun/shotgun_hand.md3" );
\t}'''
c=one(c,old,new,"hand mdc fallback")
# add registration cases after V15 PPSh case
anchor='''\tcase WP_DW_PPSH:
\t\t// DARKWOLF_WEAPON_PORT_V15_FULL_FIRE_ADS_RELOAD
\t\tMAKERGB( weaponInfo->flashDlightColor, 1.0, 0.6, 0.23 );
\t\tweaponInfo->flashSound[0]=trap_S_RegisterSound("sound/weapons/ppsh/ppsh_fire.wav");
\t\tweaponInfo->flashEchoSound[0]=trap_S_RegisterSound("sound/weapons/ppsh/ppsh_far.wav");
\t\tweaponInfo->reloadSound=trap_S_RegisterSound("sound/weapons/ppsh/ppsh_reload.wav");
\t\tweaponInfo->ejectBrassFunc=CG_MachineGunEjectBrass;
\t\tbreak;
'''
extra=anchor+'''\tcase WP_DW_MP34:
\t\tMAKERGB( weaponInfo->flashDlightColor, 1.0, 0.6, 0.23 );
\t\tweaponInfo->flashSound[0]=trap_S_RegisterSound("sound/weapons/mp34/mp34_fire.wav");
\t\tweaponInfo->flashEchoSound[0]=trap_S_RegisterSound("sound/weapons/mp34/mp34_far.wav");
\t\tweaponInfo->reloadSound=trap_S_RegisterSound("sound/weapons/mp34/mp34_reload.wav");
\t\tweaponInfo->ejectBrassFunc=CG_MachineGunEjectBrass; break;
\tcase WP_DW_BAR:
\t\tMAKERGB( weaponInfo->flashDlightColor, 1.0, 0.6, 0.23 );
\t\tweaponInfo->flashSound[0]=trap_S_RegisterSound("sound/weapons/bar/bar_fire.wav");
\t\tweaponInfo->flashEchoSound[0]=trap_S_RegisterSound("sound/weapons/bar/bar_far.wav");
\t\tweaponInfo->reloadSound=trap_S_RegisterSound("sound/weapons/bar/bar_reload.wav");
\t\tweaponInfo->ejectBrassFunc=CG_MachineGunEjectBrass; break;
\tcase WP_DW_TT33:
\tcase WP_DW_DUAL_TT33:
\t\tMAKERGB( weaponInfo->flashDlightColor, 1.0, 0.6, 0.23 );
\t\tweaponInfo->flashSound[0]=trap_S_RegisterSound("sound/weapons/tt33/tt33_fire.wav");
\t\tweaponInfo->flashEchoSound[0]=trap_S_RegisterSound("sound/weapons/tt33/tt33_far.wav");
\t\tweaponInfo->reloadSound=trap_S_RegisterSound( weaponNum == WP_DW_DUAL_TT33 ? "sound/weapons/tt33/tt33_reload2.wav" : "sound/weapons/tt33/tt33_reload.wav" );
\t\tweaponInfo->ejectBrassFunc=CG_MachineGunEjectBrass; break;
\tcase WP_DW_REVOLVER:
\t\tMAKERGB( weaponInfo->flashDlightColor, 1.0, 0.6, 0.23 );
\t\tweaponInfo->flashSound[0]=trap_S_RegisterSound("sound/weapons/revolver/revolver_fire.wav");
\t\tweaponInfo->flashEchoSound[0]=trap_S_RegisterSound("sound/weapons/revolver/revolver_far.wav");
\t\tweaponInfo->reloadSound=trap_S_RegisterSound("sound/weapons/revolver/revolver_reload.wav");
\t\tweaponInfo->ejectBrassFunc=CG_MachineGunEjectBrass; break;
\tcase WP_DW_HDM:
\t\tVectorClear( weaponInfo->flashDlightColor );
\t\tweaponInfo->flashSound[0]=trap_S_RegisterSound("sound/weapons/hdm/hdm_fire.wav");
\t\tweaponInfo->reloadSound=trap_S_RegisterSound("sound/weapons/hdm/hdm_reload.wav");
\t\tweaponInfo->ejectBrassFunc=CG_MachineGunEjectBrass; break;
\tcase WP_DW_MOSIN:
\t\tMAKERGB( weaponInfo->flashDlightColor, 1.0, 0.6, 0.23 );
\t\tweaponInfo->flashSound[0]=trap_S_RegisterSound("sound/weapons/mosin/mosin_fire.wav");
\t\tweaponInfo->flashEchoSound[0]=trap_S_RegisterSound("sound/weapons/mosin/mosin_far.wav");
\t\tweaponInfo->reloadSound=trap_S_RegisterSound("sound/weapons/mosin/mosin_reload.wav");
\t\tweaponInfo->ejectBrassFunc=CG_MachineGunEjectBrass; break;
\tcase WP_DW_M1GARAND:
\t\tMAKERGB( weaponInfo->flashDlightColor, 1.0, 0.6, 0.23 );
\t\tweaponInfo->flashSound[0]=trap_S_RegisterSound("sound/weapons/m1_garand/m1garand_fire.wav");
\t\tweaponInfo->flashEchoSound[0]=trap_S_RegisterSound("sound/weapons/m1_garand/m1garand_far.wav");
\t\tweaponInfo->reloadSound=trap_S_RegisterSound("sound/weapons/m1_garand/m1garand_reload.wav");
\t\tweaponInfo->ejectBrassFunc=CG_MachineGunEjectBrass; break;
\tcase WP_DW_G43:
\t\tMAKERGB( weaponInfo->flashDlightColor, 1.0, 0.6, 0.23 );
\t\tweaponInfo->flashSound[0]=trap_S_RegisterSound("sound/weapons/g43/g43_fire.wav");
\t\tweaponInfo->flashEchoSound[0]=trap_S_RegisterSound("sound/weapons/g43/g43_far.wav");
\t\tweaponInfo->reloadSound=trap_S_RegisterSound("sound/weapons/g43/g43_reload.wav");
\t\tweaponInfo->ejectBrassFunc=CG_MachineGunEjectBrass; break;
\tcase WP_DW_M97:
\t\tMAKERGB( weaponInfo->flashDlightColor, 1.0, 0.6, 0.23 );
\t\tweaponInfo->flashSound[0]=trap_S_RegisterSound("sound/weapons/ithaca/ithaca_fire.wav");
\t\tweaponInfo->flashEchoSound[0]=trap_S_RegisterSound("sound/weapons/ithaca/ithaca_far.wav");
\t\tweaponInfo->reloadSound=trap_S_RegisterSound("sound/weapons/ithaca/ithaca_reload.wav");
\t\tweaponInfo->ejectBrassFunc=CG_MachineGunEjectBrass; break;
\tcase WP_DW_BROWNING:
\t\tMAKERGB( weaponInfo->flashDlightColor, 1.0, 0.6, 0.23 );
\t\tweaponInfo->flashSound[0]=trap_S_RegisterSound("sound/weapons/browning/browning_fire.wav");
\t\tweaponInfo->flashEchoSound[0]=trap_S_RegisterSound("sound/weapons/browning/browning_far.wav");
\t\tweaponInfo->reloadSound=trap_S_RegisterSound("sound/weapons/browning/browning_reload.wav");
\t\tweaponInfo->ejectBrassFunc=CG_MachineGunEjectBrass; break;
\tcase WP_DW_MG42M:
\t\tMAKERGB( weaponInfo->flashDlightColor, 1.0, 0.6, 0.23 );
\t\tweaponInfo->flashSound[0]=trap_S_RegisterSound("sound/weapons/mg42m/mg42m_fire.wav");
\t\tweaponInfo->flashEchoSound[0]=trap_S_RegisterSound("sound/weapons/mg42m/mg42m_far.wav");
\t\tweaponInfo->reloadSound=trap_S_RegisterSound("sound/weapons/mg42m/mg42m_reload.wav");
\t\tweaponInfo->ejectBrassFunc=CG_MachineGunEjectBrass; break;
'''
c=one(c,anchor,extra,"client registration cases")
# recoil group: V1 appends MP44/PPSh after STEN in the normal recoil path.
anchor='''\tcase WP_FG42SCOPE:
\tcase WP_FG42:
\tcase WP_MP40:
\tcase WP_THOMPSON:
\tcase WP_STEN:
\tcase WP_DW_MP44:
\tcase WP_DW_PPSH:'''
insert='''\tcase WP_FG42SCOPE:
\tcase WP_FG42:
\tcase WP_MP40:
\tcase WP_THOMPSON:
\tcase WP_STEN:
\tcase WP_DW_MP44:
\tcase WP_DW_PPSH:
\tcase WP_DW_MP34:
\tcase WP_DW_BAR:
\tcase WP_DW_TT33:
\tcase WP_DW_DUAL_TT33:
\tcase WP_DW_REVOLVER:
\tcase WP_DW_HDM:
\tcase WP_DW_MOSIN:
\tcase WP_DW_M1GARAND:
\tcase WP_DW_G43:
\tcase WP_DW_M97:
\tcase WP_DW_BROWNING:
\tcase WP_DW_MG42M:'''
c=one(c,anchor,insert,"recoil group")

# impact group: unique V1 sequence begins with MP40 then the two append-only weapons.
anchor='''\tcase WP_MP40:
\tcase WP_DW_MP44:
\tcase WP_DW_PPSH:
\tcase WP_FG42:'''
insert='''\tcase WP_MP40:
\tcase WP_DW_MP44:
\tcase WP_DW_PPSH:
\tcase WP_DW_MP34:
\tcase WP_DW_BAR:
\tcase WP_DW_TT33:
\tcase WP_DW_DUAL_TT33:
\tcase WP_DW_REVOLVER:
\tcase WP_DW_HDM:
\tcase WP_DW_MOSIN:
\tcase WP_DW_M1GARAND:
\tcase WP_DW_G43:
\tcase WP_DW_M97:
\tcase WP_DW_BROWNING:
\tcase WP_DW_MG42M:
\tcase WP_FG42:'''
c=one(c,anchor,insert,"impact group")
# wide icon group created by V1
anchor='''\t\tcase WP_DW_MP44:
\t\tcase WP_DW_PPSH:
\t\tcase WP_MAUSER:'''
insert='''\t\tcase WP_DW_MP44:
\t\tcase WP_DW_PPSH:
\t\tcase WP_DW_MP34:
\t\tcase WP_DW_BAR:
\t\tcase WP_DW_MOSIN:
\t\tcase WP_DW_M1GARAND:
\t\tcase WP_DW_G43:
\t\tcase WP_DW_M97:
\t\tcase WP_DW_BROWNING:
\t\tcase WP_DW_MG42M:
\t\tcase WP_MAUSER:'''
c=one(c,anchor,insert,"wide icons")
# ADS calibration globals/functions after DWAdsToggle
anchor='''static void DWAdsToggle(void){dwAdsFrom=CG_DWADSFrac();dwAdsActive=(qboolean)!dwAdsActive;dwAdsTime=cg.time;trap_SendClientCommand(dwAdsActive?"dw_ads 1":"dw_ads 0");}
'''
cal=anchor+'''
// DARKWOLF_WEAPON_PORT_V16_EXPANDED_ARSENAL_ADS_CAL
static vec3_t dwAdsCalMP40 = { 0.0f, 0.0f, 0.0f }; // right, up, forward
static vec3_t dwAdsCalSten = { 0.0f, 0.0f, 0.0f };

static vec3_t *CG_DWADSCalCurrent( void ) {
\tif ( cg.weaponSelect == WP_MP40 ) return &dwAdsCalMP40;
\tif ( cg.weaponSelect == WP_STEN ) return &dwAdsCalSten;
\treturn NULL;
}

void CG_DWADSCal_f( void ) {
\tvec3_t *cal = CG_DWADSCalCurrent();
\tchar a[32], b[32], cbuf[32];
\tif ( !cal ) {
\t\tCG_Printf( "DW ADS CAL: select MP40 or STEN first.\\n" );
\t\treturn;
\t}
\tif ( trap_Argc() == 4 ) {
\t\ttrap_Argv( 1, a, sizeof(a) );
\t\ttrap_Argv( 2, b, sizeof(b) );
\t\ttrap_Argv( 3, cbuf, sizeof(cbuf) );
\t\t(*cal)[0] = atof( a );
\t\t(*cal)[1] = atof( b );
\t\t(*cal)[2] = atof( cbuf );
\t}
\tCG_Printf( "DW ADS CAL %s: right=%.3f up=%.3f forward=%.3f\\n",
\t\tcg.weaponSelect == WP_MP40 ? "MP40" : "STEN", (*cal)[0], (*cal)[1], (*cal)[2] );
\tCG_Printf( "Usage: /dw_ads_cal <right> <up> <forward> ; negative up moves sight down.\\n" );
}

void CG_DWADSReset_f( void ) {
\tvec3_t *cal = CG_DWADSCalCurrent();
\tif ( !cal ) {
\t\tCG_Printf( "DW ADS RESET: select MP40 or STEN first.\\n" );
\t\treturn;
\t}
\tVectorClear( *cal );
\tCG_DWADSCal_f();
}
'''
c=one(c,anchor,cal,"ADS calibration functions")
# apply calibration to V1.5 eye-line alignment before repositioning gun
anchor='''\t\t\tVectorMA( parent->origin, -rightOffset * ads, cg.refdef.viewaxis[1], parent->origin );
\t\t\tVectorMA( parent->origin, -upOffset * ads, cg.refdef.viewaxis[2], parent->origin );
\t\t\tVectorMA( parent->origin, eyeClearance * ads, cg.refdef.viewaxis[0], parent->origin );
\t\t\tCG_PositionEntityOnTag( &gun, parent, "tag_weapon", 0, NULL );'''
insert='''\t\t\tVectorMA( parent->origin, -rightOffset * ads, cg.refdef.viewaxis[1], parent->origin );
\t\t\tVectorMA( parent->origin, -upOffset * ads, cg.refdef.viewaxis[2], parent->origin );
\t\t\tVectorMA( parent->origin, eyeClearance * ads, cg.refdef.viewaxis[0], parent->origin );
\t\t\t{
\t\t\t\tvec3_t *cal = ( weaponNum == WP_STEN ) ? &dwAdsCalSten : &dwAdsCalMP40;
\t\t\t\tVectorMA( parent->origin, (*cal)[0] * ads, cg.refdef.viewaxis[1], parent->origin );
\t\t\t\tVectorMA( parent->origin, (*cal)[1] * ads, cg.refdef.viewaxis[2], parent->origin );
\t\t\t\tVectorMA( parent->origin, (*cal)[2] * ads, cg.refdef.viewaxis[0], parent->origin );
\t\t\t}
\t\t\tCG_PositionEntityOnTag( &gun, parent, "tag_weapon", 0, NULL );'''
c=one(c,anchor,insert,"ADS apply calibration")
p.write_text(c,encoding="utf-8")

# prototypes
p=root/"SP/code/cgame/cg_local.h"; h0=p.read_text(encoding="utf-8")
anchor='''void CG_DWADSReset( void );
'''
h=one(h0,anchor,anchor+"void CG_DWADSCal_f( void );\nvoid CG_DWADSReset_f( void );\n","ADS calib prototypes")
p.write_text(h,encoding="utf-8")

# console commands
p=root/"SP/code/cgame/cg_consolecmds.c"; cc0=p.read_text(encoding="utf-8")
anchor='''static consoleCommand_t commands[] = {
\t{ "testgun", CG_TestGun_f },'''
cc=one(cc0,anchor,'''static consoleCommand_t commands[] = {
\t{ "dw_ads_cal", CG_DWADSCal_f },
\t{ "dw_ads_reset", CG_DWADSReset_f },
\t{ "testgun", CG_TestGun_f },''',"ADS console commands")
p.write_text(cc,encoding="utf-8")

proof={
 "feature":"DarkWolf Weapon Port V1.6 Expanded Arsenal + ADS Calibrator",
 "base":"V1.5 Full Fire + ADS + Reload (Run #43150467958 SUCCESS)",
 "append_ids":{"MP34":34,"BAR":35,"TT33":36,"DUAL_TT33":37,"REVOLVER":38,"HDM":39,"MOSIN":40,"M1GARAND":41,"G43":42,"M97":43,"BROWNING":44,"MG42M":45},
 "wp_num_weapons":46,
 "excluded_by_user":["Tesla port/replacement","Venom port/replacement","Panzerfaust/rocket port/replacement"],
 "asset_pack":"DW_RealRTCW_WeaponPort_V16_ExpandedArsenal.pk3",
 "ads_commands":["dw_ads_cal <right> <up> <forward>","dw_ads_reset"],
 "browning_limits":{"max_surface_vertices_observed":15843,"max_surface_triangles_observed":18054,"MD3_MAX_TRIANGLES":32768},
 "m97_pellets":12,
 "v14_component_animation_safety_required":True,
 "v13_hand_frame_freeze":False
}
(ev/"DW_WEAPON_PORT_V16_EXPANDED_ARSENAL_PROOF.json").write_text(json.dumps(proof,indent=2)+"\n",encoding="utf-8")
print(json.dumps(proof,indent=2))
print("DW_WEAPON_PORT_V16_EXPANDED_ARSENAL_ADS_CAL_APPLY_PASS")
