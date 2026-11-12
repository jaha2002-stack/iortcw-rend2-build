#!/usr/bin/env python3
from pathlib import Path
import sys,json,re
if len(sys.argv)<2: raise SystemExit("usage: run_tests.py <source-root> [evidence-dir]")
root=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/"evidence"
ev.mkdir(parents=True,exist_ok=True)

def read(p): return (root/p).read_text(encoding="utf-8")
pub=read("SP/code/game/bg_public.h")
misc=read("SP/code/game/bg_misc.c")
pm=read("SP/code/game/bg_pmove.c")
gw=read("SP/code/game/g_weapon.c")
cg=read("SP/code/cgame/cg_weapons.c")
cc=read("SP/code/cgame/cg_consolecmds.c")
qf=read("SP/code/qcommon/qfiles.h")
qs=read("SP/code/qcommon/q_shared.h")

ids=["WP_DW_MP34","WP_DW_BAR","WP_DW_TT33","WP_DW_DUAL_TT33","WP_DW_REVOLVER","WP_DW_HDM","WP_DW_MOSIN","WP_DW_M1GARAND","WP_DW_G43","WP_DW_M97","WP_DW_BROWNING","WP_DW_MG42M"]
checks={
 "v15_preserved":"DARKWOLF_WEAPON_PORT_V15_FULL_FIRE_ADS_RELOAD" in cg and "DARKWOLF_WEAPON_PORT_V14_COMPONENT_ANIM_INDEX_SAFETY" in cg,
 "v13_absent":"DARKWOLF_WEAPON_PORT_V13_FP_ATTACK_ANIM_SAFE" not in cg,
 "all_ids":all(x in pub for x in ids),
 "wp_num_46":"WP_NUM_WEAPONS          // 46" in pub,
 "ammo_table_sized":"ammotable_t ammoTable[WP_NUM_WEAPONS]" in misc,
 "all_items":all(x in misc for x in ["weapon_dw_mp34","weapon_dw_bar","weapon_dw_tt33","weapon_dw_dual_tt33","weapon_dw_revolver","weapon_dw_hdm","weapon_dw_mosin","weapon_dw_m1garand","weapon_dw_g43","weapon_dw_m97","weapon_dw_browning","weapon_dw_mg42m"]),
 "reload_range":"weapon >= WP_DW_MP44 && weapon < WP_NUM_WEAPONS" in pm,
 "shotgun_12":"for ( i = 0; i < 12; i++ )" in gw and "DW_M97_Fire" in gw,
 "all_fire_cases":all(("case "+x+":") in gw for x in ids),
 "bank_width":"MAX_WEAPS_IN_BANK   10" in qs,
 "browning_triangles":"MD3_MAX_TRIANGLES   32768" in qf,
 "ads_cal_cmd":'"dw_ads_cal", CG_DWADSCal_f' in cc,
 "ads_reset_cmd":'"dw_ads_reset", CG_DWADSReset_f' in cc,
 "ads_cal_applied":"dwAdsCalMP40" in cg and "dwAdsCalSten" in cg and "negative up moves sight down" in cg,
 "mdc_flash_fallback":"_flash.mdc" in cg,
 "append_safe_onehand":"DW_IS_ONE_HANDED_WEAPON" in pub,
 "no_tesla_port":"WP_DW_TESLA" not in pub,
 "no_venom_port":"WP_DW_VENOM" not in pub,
 "no_rocket_port":"WP_DW_PANZERFAUST" not in pub,
}
# enum positions
start=pub.index("typedef enum {",pub.index("WP_NONE")-100)
end=pub.index("} weapon_t;",start)
names=[]
for line in pub[start:end].splitlines():
    m=re.match(r"\s*(WP_[A-Z0-9_]+|VERYBIGEXPLOSION)\s*,",line)
    if m: names.append(m.group(1))
expect={"WP_DW_MP44":32,"WP_DW_PPSH":33,"WP_DW_MP34":34,"WP_DW_BAR":35,"WP_DW_TT33":36,"WP_DW_DUAL_TT33":37,"WP_DW_REVOLVER":38,"WP_DW_HDM":39,"WP_DW_MOSIN":40,"WP_DW_M1GARAND":41,"WP_DW_G43":42,"WP_DW_M97":43,"WP_DW_BROWNING":44,"WP_DW_MG42M":45}
checks["enum_positions"]=all(k in names and names.index(k)==v for k,v in expect.items())
bad=[k for k,v in checks.items() if not v]
(ev/"DW_WEAPON_PORT_V16_TESTS.json").write_text(json.dumps(checks,indent=2)+"\n",encoding="utf-8")
if bad: raise SystemExit("FAIL "+",".join(bad))
print("DW_WEAPON_PORT_V16_TESTS_PASS",len(checks))
