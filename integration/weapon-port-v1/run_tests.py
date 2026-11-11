from pathlib import Path
import sys,re
root=Path(sys.argv[1])
ev=Path(sys.argv[2]) if len(sys.argv)>2 else root/'evidence'
ev.mkdir(parents=True,exist_ok=True)
checks=[]
def ck(path, needle, label):
    s=(root/path).read_text(encoding='utf-8')
    if needle not in s:
        raise SystemExit(f'FAIL {label}: missing {needle!r} in {path}')
    checks.append(label)
ck(Path('SP/code/game/bg_public.h'),'WP_DW_MP44','MP44 enum')
ck(Path('SP/code/game/bg_public.h'),'WP_DW_PPSH','PPSh enum')
ck(Path('SP/code/game/bg_public.h'),'EF_DW_ADS','ADS flag')
ck(Path('SP/code/game/bg_misc.c'),'weapon_dw_mp44','MP44 item')
ck(Path('SP/code/game/bg_misc.c'),'weapon_dw_ppsh','PPSh item')
ck(Path('SP/code/game/bg_misc.c'),'ammotable_t ammoTable[WP_NUM_WEAPONS]','ammo table sized')
ck(Path('SP/code/cgame/cg_weapons.c'),'CG_DWADSToggle','ADS toggle')
ck(Path('SP/code/game/g_weapon.c'),'DW_MP44_DAMAGE','MP44 firing')
ck(Path('SP/code/game/g_weapon.c'),'DW_PPSH_DAMAGE','PPSh firing')
ck(Path('SP/code/game/g_cmds.c'),'dw_ads','ADS server command')
ck(Path('SP/code/cgame/cg_view.c'),'62.0f','ADS FOV')
s=(root/'SP/code/game/bg_public.h').read_text(encoding='utf-8')
i=s.index('typedef enum {',s.index('WP_NONE')-100)
j=s.index('} weapon_t;',i)
names=[]
for line in s[i:j].splitlines():
    m=re.match(r'\s*(WP_[A-Z0-9_]+|VERYBIGEXPLOSION)\s*,',line)
    if m: names.append(m.group(1))
for name,expect in [('WP_NONE',0),('WP_KNIFE',1),('WP_MP40',3),('WP_STEN',18),('WP_SILENCER',19),('VERYBIGEXPLOSION',31),('WP_DW_MP44',32),('WP_DW_PPSH',33)]:
    if name not in names or names.index(name)!=expect:
        raise SystemExit(f'FAIL enum {name}: got {names.index(name) if name in names else "missing"}, expected {expect}')
checks.append('legacy weapon ids preserved')
report='\n'.join(f'{x}: PASS' for x in checks)+'\nDW_WEAPON_PORT_V1_TEST_PASS\n'
(ev/'DW_WEAPON_PORT_V1_TESTS.txt').write_text(report,encoding='utf-8')
print(report,end='')
