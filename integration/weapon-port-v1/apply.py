from pathlib import Path
import sys

M="DARKWOLF_WEAPON_PORT_V1_MP44_PPSH_ADS"

def fail(x): raise SystemExit(x)
def one(s,a,b,n):
    c=s.count(a)
    if c!=1: fail(f"{n}: expected 1 match, got {c}")
    return s.replace(a,b,1)
def patch(root,path,fn):
    p=root/path
    s=p.read_text(encoding="utf-8")
    if M in s:
        print("already",path); return
    p.write_text(fn(s),encoding="utf-8")
    print("patched",path)

def bg_public(s):
    s=one(s,
      "#define EF_RECENTLY_FIRING  0x40000000      // fired recently, lock torso angles, etc\n",
      "#define EF_RECENTLY_FIRING  0x40000000      // fired recently, lock torso angles, etc\n"
      "#define EF_DW_ADS           ((int)0x80000000u) // "+M+": non-scope ADS\n","eflag")
    return one(s,
      "\tVERYBIGEXPLOSION,       // 31\t// explosion effect for airplanes\n\n\tWP_NUM_WEAPONS          // 32   NOTE: this cannot be larger than 64 for AI/player weapons!\n",
      "\tVERYBIGEXPLOSION,       // 31\t// explosion effect for airplanes\n\n"
      "\t// DarkWolf V1: append-only ids; legacy 0..31 remain unchanged.\n"
      "\tWP_DW_MP44,             // 32 StG44 / MP44\n"
      "\tWP_DW_PPSH,             // 33 PPSh-41\n\n"
      "\tWP_NUM_WEAPONS          // 34   NOTE: this cannot be larger than 64 for AI/player weapons!\n","enum")

def bg_misc(s):
    s=one(s,"ammotable_t ammoTable[] = {","ammotable_t ammoTable[WP_NUM_WEAPONS] = {","ammo decl")
    tail="\t{   999,            0,      999,    0,      50,             0,      0,      0,      0                       }   //\tWP_GAUNTLET\t\t\t\t// 36\n};"
    ext=(
      "\t{   999,            0,      999,    0,      50,             0,      0,      0,      0                       },  // WP_GAUNTLET / id 26\n"
      "\t{   999,            0,      999,    0,      50,             0,      0,      0,      0                       },  // WP_SNIPER / 27\n"
      "\t{   10,             1,      10,     1000,   DELAY_THROW,    1600,   0,      0,      0                       },  // WP_GRENADE_SMOKE / 28\n"
      "\t{   999,            0,      999,    0,      50,             0,      0,      0,      0                       },  // WP_MEDIC_HEAL / 29\n"
      "\t{   10,             1,      1,      1000,   DELAY_SHOULDER, 1200,   0,      0,      0                       },  // WP_MORTAR / 30\n"
      "\t{   0,              0,      0,      0,      50,             0,      0,      0,      0                       },  // VERYBIGEXPLOSION / 31\n"
      "\t{   200,            1,      30,     2600,   DELAY_LOW,      115,    0,      0,      MOD_FG42                },  // WP_DW_MP44 / 32\n"
      "\t{   400,            1,      71,     2600,   DELAY_LOW,      65,     0,      0,      MOD_MP40                }   // WP_DW_PPSH / 33\n};")
    s=one(s,tail,"".join(ext),"ammo tail")
    s=one(s,"int weapAlts[] = {","int weapAlts[WP_NUM_WEAPONS] = {","alts decl")
    anchor='''\t{\n\t\t"weapon_mp40",\n\t\t"sound/misc/w_pkup.wav",\n\t\t{   "models/weapons2/mp40/mp40.md3",\n\t\t\t"models/weapons2/mp40/v_mp40.md3",\n\t\t\t"models/weapons2/mp40/pu_mp40.md3",\n\t\t\t0, 0 },\n\n\t\t"icons/iconw_mp40_1",    // icon\n\t\t"icons/ammo2",       // ammo icon\n\t\t"MP40",              // pickup\n\t\t30,\n\t\tIT_WEAPON,\n\t\tWP_MP40,\n\t\tWP_LUGER,\n\t\tWP_MP40,\n\t\t"",                  // precache\n\t\t"",                  // sounds\n\t\t{0,0,0,0}\n\t},\n'''
    add=anchor+'''\n\t// DARKWOLF_WEAPON_PORT_V1_MP44_PPSH_ADS\n\t{\n\t\t"weapon_dw_mp44", "sound/misc/w_pkup.wav",\n\t\t{ "models/weapons/assault_rifles/mp44/mp44_3rd.md3", "models/weapons/assault_rifles/mp44/v_mp44.md3", "models/weapons/assault_rifles/mp44/mp44_3rd.md3", 0, 0 },\n\t\t"icons/iconw_mp44", "icons/ammo5", "StG44", 30, IT_WEAPON,\n\t\tWP_DW_MP44, WP_DW_MP44, WP_DW_MP44, "", "", {0,0,0,0}\n\t},\n\t{\n\t\t"weapon_dw_ppsh", "sound/misc/w_pkup.wav",\n\t\t{ "models/weapons/smgs/ppsh/ppsh_3rd.md3", "models/weapons/smgs/ppsh/v_ppsh.md3", "models/weapons/smgs/ppsh/ppsh_3rd.md3", 0, 0 },\n\t\t"icons/iconw_ppsh_1", "icons/ammo2", "PPSh-41", 71, IT_WEAPON,\n\t\tWP_DW_PPSH, WP_DW_PPSH, WP_DW_PPSH, "", "", {0,0,0,0}\n\t},\n'''
    return one(s,anchor,add,"items")

def bg_pmove(s):
    s=one(s,"void PM_Weapon( void ) {\n",
      "void PM_Weapon( void ) {\n"
      "\t// "+M+": clear replicated ADS on death or unsupported weapon.\n"
      "\tif ( (pm->ps->eFlags & EF_DW_ADS) && (pm->ps->stats[STAT_HEALTH] <= 0 || (pm->ps->weapon != WP_MP40 && pm->ps->weapon != WP_STEN)) ) pm->ps->eFlags &= ~EF_DW_ADS;\n","pm weapon")
    s=one(s,"\tcase WP_MP40:\n\t\twpnScale = 0.5f;        // 2 handed, but not as long as mauser, so harder to keep aim\n\t\tbreak;",
      "\tcase WP_MP40:\n\t\twpnScale = 0.5f;        // 2 handed, but not as long as mauser, so harder to keep aim\n\t\tbreak;\n\tcase WP_DW_MP44: wpnScale = 0.8f; break;\n\tcase WP_DW_PPSH: wpnScale = 0.6f; break;","aimscale")
    s=one(s,"\tcase WP_MP40:\n\tcase WP_THOMPSON:\n\tcase WP_STEN:\n\tcase WP_VENOM:",
      "\tcase WP_MP40:\n\tcase WP_THOMPSON:\n\tcase WP_STEN:\n\tcase WP_DW_MP44:\n\tcase WP_DW_PPSH:\n\tcase WP_VENOM:","fire group")
    s=one(s,"\tcase WP_VENOM:\n\tcase WP_MP40:\n\tcase WP_THOMPSON:\n\tcase WP_STEN:\n\t\tPM_ContinueWeaponAnim( weapattackanim );",
      "\tcase WP_VENOM:\n\tcase WP_MP40:\n\tcase WP_THOMPSON:\n\tcase WP_STEN:\n\tcase WP_DW_MP44:\n\tcase WP_DW_PPSH:\n\t\tPM_ContinueWeaponAnim( weapattackanim );","anim group")
    return one(s,"\tcase WP_FG42:\n\tcase WP_MP40:\n\tcase WP_THOMPSON:\n\t\taddTime = ammoTable[pm->ps->weapon].nextShotTime;",
      "\tcase WP_FG42:\n\tcase WP_MP40:\n\tcase WP_THOMPSON:\n\tcase WP_DW_MP44:\n\tcase WP_DW_PPSH:\n\t\taddTime = ammoTable[pm->ps->weapon].nextShotTime;","shot time")

def g_weapon(s):
    s=one(s,"\t\tcase WP_MP40: return 6;\n\t\tcase WP_THOMPSON: return 8;",
      "\t\tcase WP_MP40: return 6;\n\t\tcase WP_DW_MP44: return 9;\n\t\tcase WP_DW_PPSH: return 6;\n\t\tcase WP_THOMPSON: return 8;","sp damage")
    s=one(s,"\t\tcase WP_MP40: return 14;\n\t\tcase WP_THOMPSON: return 18;",
      "\t\tcase WP_MP40: return 14;\n\t\tcase WP_DW_MP44: return 18;\n\t\tcase WP_DW_PPSH: return 14;\n\t\tcase WP_THOMPSON: return 18;","mp damage")
    s=one(s,"\t\t\tcase WP_MP40:       return 1000;\n\t\t\tcase WP_FG42SCOPE:",
      "\t\t\tcase WP_MP40:       return 1000;\n\t\t\tcase WP_DW_MP44:    return 800;\n\t\t\tcase WP_DW_PPSH:    return 1000;\n\t\t\tcase WP_FG42SCOPE:","aim spread")
    s=one(s,"\t\t\tcase WP_MP40:       return 200;\n\t\t\tcase WP_FG42SCOPE:",
      "\t\t\tcase WP_MP40:       return 200;\n\t\t\tcase WP_DW_MP44:    return 180;\n\t\t\tcase WP_DW_PPSH:    return 250;\n\t\t\tcase WP_FG42SCOPE:","legacy spread")
    s=one(s,"\t\tcase WP_MP40: return 400;\n\t\tcase WP_FG42SCOPE:",
      "\t\tcase WP_MP40: return 400;\n\t\tcase WP_DW_MP44: return 500;\n\t\tcase WP_DW_PPSH: return 600;\n\t\tcase WP_FG42SCOPE:","mp spread")
    a="#define MP40_DAMAGE     G_GetWeaponDamage( WP_MP40 ) // JPW\n"
    s=one(s,a,a+"#define DW_MP44_SPREAD G_GetWeaponSpread( WP_DW_MP44 )\n#define DW_MP44_DAMAGE G_GetWeaponDamage( WP_DW_MP44 )\n#define DW_PPSH_SPREAD G_GetWeaponSpread( WP_DW_PPSH )\n#define DW_PPSH_DAMAGE G_GetWeaponDamage( WP_DW_PPSH )\n","macros")
    s=one(s,"void Bullet_Fire( gentity_t *ent, float spread, int damage ) {\n\tvec3_t end;\n\n\tBullet_Endpos( ent, spread, &end );",
      "void Bullet_Fire( gentity_t *ent, float spread, int damage ) {\n\tvec3_t end;\n\n"
      "\t// "+M+": ADS improves actual server bullet cone, not only camera FOV.\n"
      "\tif ( ent->client && (ent->client->ps.eFlags & EF_DW_ADS) && (ent->s.weapon == WP_MP40 || ent->s.weapon == WP_STEN) ) spread *= 0.55f;\n\n"
      "\tBullet_Endpos( ent, spread, &end );","ads spread")
    return one(s,"\tcase WP_MP40:\n\t\tBullet_Fire( ent, MP40_SPREAD * aimSpreadScale, MP40_DAMAGE );\n\t\tbreak;\n\tcase WP_THOMPSON:",
      "\tcase WP_MP40:\n\t\tBullet_Fire( ent, MP40_SPREAD * aimSpreadScale, MP40_DAMAGE );\n\t\tbreak;\n"
      "\tcase WP_DW_MP44:\n\t\tBullet_Fire( ent, DW_MP44_SPREAD * aimSpreadScale, DW_MP44_DAMAGE );\n\t\tbreak;\n"
      "\tcase WP_DW_PPSH:\n\t\tBullet_Fire( ent, DW_PPSH_SPREAD * aimSpreadScale, DW_PPSH_DAMAGE );\n\t\tbreak;\n\tcase WP_THOMPSON:","fire cases")

def g_cmds(s):
    a='\t// done.\n\n\tif ( Q_stricmp( cmd, "say" ) == 0 ) {'
    b='\t// done.\n\n\t// '+M+'''\n\tif ( Q_stricmp( cmd, "dw_ads" ) == 0 ) {\n\t\tchar arg[8]; trap_Argv( 1, arg, sizeof(arg) );\n\t\tif ( atoi(arg) && ent->client->ps.stats[STAT_HEALTH] > 0 && (ent->client->ps.weapon == WP_MP40 || ent->client->ps.weapon == WP_STEN) ) ent->client->ps.eFlags |= EF_DW_ADS;\n\t\telse ent->client->ps.eFlags &= ~EF_DW_ADS;\n\t\treturn;\n\t}\n\n\tif ( Q_stricmp( cmd, "say" ) == 0 ) {'''
    s=one(s,a,b,"dw_ads command")
    return one(s,"if ( WEAPS_ONE_HANDED & ( 1 << ( ent->client->pers.cmd.weapon ) ) ) {",
      "if ( ent->client->pers.cmd.weapon < 32 && ( WEAPS_ONE_HANDED & ( 1 << ent->client->pers.cmd.weapon ) ) ) {","g melee mask")

def cg_local(s):
    a="void CG_WeaponSuggest( int weap );\n"
    return one(s,a,a+"qboolean CG_DWADSSupportedWeapon( int weapon ); // "+M+"\nfloat CG_DWADSFrac( void );\nvoid CG_DWADSReset( void );\n","prototypes")

def cg_weapons(s):
    a="vec3_t ejectBrassCasingOrigin;\n"
    b=a+'''\n// DARKWOLF_WEAPON_PORT_V1_MP44_PPSH_ADS\nstatic qboolean dwAdsActive=qfalse;\nstatic int dwAdsTime=0;\nstatic float dwAdsFrom=0.0f;\nqboolean CG_DWADSSupportedWeapon(int w){ return (qboolean)(w==WP_MP40 || w==WP_STEN); }\nstatic float DWAdsRaw(void){\n\tfloat t,target,k;\n\tif(!cg.snap || cg.snap->ps.stats[STAT_HEALTH]<=0 || !CG_DWADSSupportedWeapon(cg.weaponSelect)) { dwAdsActive=qfalse; dwAdsFrom=0; return 0; }\n\tt=(float)(cg.time-dwAdsTime)/160.0f; if(t<0)t=0; if(t>1)t=1; k=t*t*(3.0f-2.0f*t); target=dwAdsActive?1.0f:0.0f;\n\treturn dwAdsFrom+(target-dwAdsFrom)*k;\n}\nfloat CG_DWADSFrac(void){ float f=DWAdsRaw(); return f<0?0:(f>1?1:f); }\nvoid CG_DWADSReset(void){ float f=CG_DWADSFrac(); if(dwAdsActive||f>0){dwAdsFrom=f;dwAdsActive=qfalse;dwAdsTime=cg.time;trap_SendClientCommand("dw_ads 0");} }\nstatic void DWAdsToggle(void){dwAdsFrom=CG_DWADSFrac();dwAdsActive=(qboolean)!dwAdsActive;dwAdsTime=cg.time;trap_SendClientCommand(dwAdsActive?"dw_ads 1":"dw_ads 0");}\n'''
    s=one(s,a,b,"ads globals")
    s=one(s,"\t{WP_FG42,               0,                      0           },  //\t5",
      "\t{WP_FG42,               WP_DW_MP44,             WP_DW_PPSH  },  //\t5 DarkWolf V1","bank")
    mp='\tcase WP_MP40:\n\t\tMAKERGB( weaponInfo->flashDlightColor, 1.0, 0.6, 0.23 );\n\t\tweaponInfo->flashSound[0] = trap_S_RegisterSound( "sound/weapons/mp40/mp40f1.wav" );'
    cases='''\tcase WP_DW_MP44:\n\t\tMAKERGB( weaponInfo->flashDlightColor, 1.0, 0.6, 0.23 );\n\t\tweaponInfo->flashSound[0]=trap_S_RegisterSound("sound/weapons/mp44/mp44_fire.wav");\n\t\tweaponInfo->flashEchoSound[0]=trap_S_RegisterSound("sound/weapons/mp44/mp44_far.wav");\n\t\tweaponInfo->reloadSound=trap_S_RegisterSound("sound/weapons/mp44/mp44_reload.wav");\n\t\tweaponInfo->ejectBrassFunc=CG_MachineGunEjectBrass; break;\n\tcase WP_DW_PPSH:\n\t\tMAKERGB( weaponInfo->flashDlightColor, 1.0, 0.6, 0.23 );\n\t\tweaponInfo->flashSound[0]=trap_S_RegisterSound("sound/weapons/ppsh/ppsh_fire.wav");\n\t\tweaponInfo->flashEchoSound[0]=trap_S_RegisterSound("sound/weapons/ppsh/ppsh_far.wav");\n\t\tweaponInfo->reloadSound=trap_S_RegisterSound("sound/weapons/ppsh/ppsh_reload.wav");\n\t\tweaponInfo->ejectBrassFunc=CG_MachineGunEjectBrass; break;\n\n'''+mp
    s=one(s,mp,cases,"sounds")
    s=one(s,"\tcase WP_FG42SCOPE:\n\tcase WP_FG42:\n\tcase WP_MP40:\n\tcase WP_THOMPSON:\n\tcase WP_STEN:",
      "\tcase WP_FG42SCOPE:\n\tcase WP_FG42:\n\tcase WP_MP40:\n\tcase WP_THOMPSON:\n\tcase WP_STEN:\n\tcase WP_DW_MP44:\n\tcase WP_DW_PPSH:","recoil")
    s=one(s,"\tcase WP_MP40:\n\tcase WP_FG42:",
      "\tcase WP_MP40:\n\tcase WP_DW_MP44:\n\tcase WP_DW_PPSH:\n\tcase WP_FG42:","impact")
    s=one(s,"\tif ( cg.snap->ps.eFlags & EF_MELEE_ACTIVE ) {\n\t\tif ( !( WEAPS_ONE_HANDED & ( 1 << i ) ) ) {",
      "\tif ( cg.snap->ps.eFlags & EF_MELEE_ACTIVE ) {\n\t\tif ( i >= 32 || !( WEAPS_ONE_HANDED & ( 1 << i ) ) ) {","select mask")
    old="if ( drawweap && ( bits[0] & ( 1 << drawweap ) ) ) {"
    if s.count(old)!=2: fail("draw mask count")
    s=s.replace(old,"if ( drawweap && COM_BitCheck( bits, drawweap ) ) {")
    s=one(s,"\t\tcase WP_THOMPSON:\n\t\tcase WP_MP40:\n\t\tcase WP_STEN:",
      "\t\tcase WP_THOMPSON:\n\t\tcase WP_MP40:\n\t\tcase WP_STEN:\n\t\tcase WP_DW_MP44:\n\t\tcase WP_DW_PPSH:","wide icons")
    s=one(s,'\tCG_PositionRotatedEntityOnTag( &flash, &gun, "tag_flash" );\n',
      '\tif ( ps && weaponNum == WP_DW_MP44 ) CG_PositionRotatedEntityOnTag( &flash, &gun, "tag_weapon" );\n\telse CG_PositionRotatedEntityOnTag( &flash, &gun, "tag_flash" );\n',"mp44 flash tag")
    pos='\tCG_PositionEntityOnTag( &gun, parent, "tag_weapon", 0, NULL );\n\n\tplayerScaled'
    pos2='''\tCG_PositionEntityOnTag( &gun, parent, "tag_weapon", 0, NULL );\n\n\t// Tag-driven bore alignment: keeps stock model/animation and centers it for ADS.\n\tif ( ps && CG_DWADSSupportedWeapon(weaponNum) ) {\n\t\tfloat ads=CG_DWADSFrac();\n\t\tif(ads>0){ refEntity_t sight; vec3_t d; float r,u; memset(&sight,0,sizeof(sight)); AxisClear(sight.axis);\n\t\t\tCG_PositionEntityOnTag(&sight,&gun,"tag_flash",0,NULL); VectorSubtract(sight.origin,cg.refdef.vieworg,d);\n\t\t\tr=DotProduct(d,cg.refdef.viewaxis[1]); u=DotProduct(d,cg.refdef.viewaxis[2]); if(r>24)r=24;if(r<-24)r=-24;if(u>24)u=24;if(u<-24)u=-24;\n\t\t\tVectorMA(parent->origin,-r*ads,cg.refdef.viewaxis[1],parent->origin); VectorMA(parent->origin,-u*ads,cg.refdef.viewaxis[2],parent->origin); VectorMA(parent->origin,1.5f*ads,cg.refdef.viewaxis[0],parent->origin);\n\t\t\tCG_PositionEntityOnTag(&gun,parent,"tag_weapon",0,NULL); }\n\t}\n\n\tplayerScaled'''
    s=one(s,pos,pos2,"ads alignment")
    s=one(s,"\toriginal = cg.weaponSelect;\n\n\tnum = getAltWeapon( original );",
      "\toriginal = cg.weaponSelect;\n\n\tif ( CG_DWADSSupportedWeapon(original) ) { DWAdsToggle(); cg.weaponSelectTime=cg.time; return; }\n\n\tnum = getAltWeapon( original );","toggle")
    return one(s,"\tif ( lastweap == newweap ) {   // no need to do any more than flash the icon\n\t\treturn;\n\t}\n\n\tCG_PlaySwitchSound",
      "\tif ( lastweap == newweap ) {   // no need to do any more than flash the icon\n\t\treturn;\n\t}\n\n\tCG_DWADSReset();\n\n\tCG_PlaySwitchSound","reset")

def cg_view(s):
    a="\tif ( cg.snap->ps.persistant[PERS_HWEAPON_USE] ) {\n\t\tfov_x = 55;\n\t}\n\n\tif ( cg_fixedAspect.integer ) {"
    b="\tif ( cg.snap->ps.persistant[PERS_HWEAPON_USE] ) {\n\t\tfov_x = 55;\n\t}\n\n\t// "+M+": independent iron-sight FOV.\n\t{ float a=CG_DWADSFrac(); if(a>0 && fov_x>62.0f) fov_x+=(62.0f-fov_x)*a; }\n\n\tif ( cg_fixedAspect.integer ) {"
    s=one(s,a,b,"fov")
    a="\t} else {\n\t\tcg.zoomSensitivity = cg.refdef.fov_y / 75.0;\n\t}\n\n\treturn inwater;"
    b="\t} else {\n\t\tcg.zoomSensitivity = cg.refdef.fov_y / 75.0;\n\t}\n\t{ float a=CG_DWADSFrac(); if(a>0) cg.zoomSensitivity *= (1.0f-0.25f*a); }\n\n\treturn inwater;"
    return one(s,a,b,"sensitivity")

def cg_draw(s):
    a="\tif ( cg.renderingThirdPerson ) {\n\t\treturn;\n\t}\n\n\thcolor[3] = cg_crosshairAlpha.value;"
    if s.count(a)<1: fail("crosshair anchor")
    return s.replace(a,"\tif ( cg.renderingThirdPerson ) {\n\t\treturn;\n\t}\n\n\tif ( CG_DWADSFrac() > 0.75f ) return; // "+M+"\n\n\thcolor[3] = cg_crosshairAlpha.value;",1)

def cg_playerstate(s):
    return one(s,"\t\tif ( !( weapons[0] & ( 1 << i ) ) ) {\n\t\t\tcontinue;\n\t\t}",
      "\t\tif ( !COM_BitCheck( weapons, i ) ) {\n\t\t\tcontinue;\n\t\t}","ownership")

def cg_event(s):
    return one(s,"\t\tif ( cg.snap->ps.eFlags & EF_MELEE_ACTIVE ) {\n\t\t\tif ( !( ( 1 << weapon ) & WEAPS_ONE_HANDED ) ) {",
      "\t\tif ( cg.snap->ps.eFlags & EF_MELEE_ACTIVE ) {\n\t\t\tif ( weapon >= 32 || !( ( 1 << weapon ) & WEAPS_ONE_HANDED ) ) {","event mask")

def cg_newdraw(s):
    return one(s,"if ( cg.predictedPlayerState.weapon && !( WEAPS_ONE_HANDED & ( 1 << ( cg.predictedPlayerState.weapon ) ) ) ) {",
      "if ( cg.predictedPlayerState.weapon && ( cg.predictedPlayerState.weapon >= 32 || !( WEAPS_ONE_HANDED & ( 1 << cg.predictedPlayerState.weapon ) ) ) ) {","hint mask")

def ai_cast(s):
    return one(s,"if ( WEAPS_ONE_HANDED & ( 1 << ucmd->weapon ) ) { // one-handed wepons don't draw, others do",
      "if ( ucmd->weapon < 32 && ( WEAPS_ONE_HANDED & ( 1 << ucmd->weapon ) ) ) { // legacy one-handed mask","ai mask")

def main():
    if len(sys.argv)<2: fail("usage: apply.py source [evidence]")
    r=Path(sys.argv[1])
    for p,f in [
      ("SP/code/game/bg_public.h",bg_public),("SP/code/game/bg_misc.c",bg_misc),("SP/code/game/bg_pmove.c",bg_pmove),
      ("SP/code/game/g_weapon.c",g_weapon),("SP/code/game/g_cmds.c",g_cmds),("SP/code/cgame/cg_local.h",cg_local),
      ("SP/code/cgame/cg_weapons.c",cg_weapons),("SP/code/cgame/cg_view.c",cg_view),("SP/code/cgame/cg_draw.c",cg_draw),
      ("SP/code/cgame/cg_playerstate.c",cg_playerstate),("SP/code/cgame/cg_event.c",cg_event),
      ("SP/code/cgame/cg_newdraw.c",cg_newdraw),("SP/code/game/ai_cast_think.c",ai_cast)]:
        patch(r,Path(p),f)
    if len(sys.argv)>2:
        e=Path(sys.argv[2]);e.mkdir(parents=True,exist_ok=True);(e/"DW_WEAPON_PORT_V1_APPLY.txt").write_text(M+"\nPASS\n")
    print("DW_WEAPON_PORT_V1_APPLY_PASS")
if __name__=="__main__": main()
