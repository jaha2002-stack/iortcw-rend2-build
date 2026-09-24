from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('source')
asset_root = Path(sys.argv[2]) if len(sys.argv) > 2 else None

MARK = 'DARKWOLF_NEW_CHARACTERS_POC_V0_1'
p_chars = root / 'SP/code/game/ai_cast_characters.c'
p_spawn = root / 'SP/code/game/g_spawn.c'
p_funcs = root / 'SP/code/game/g_funcs.h'
p_decs = root / 'SP/code/game/g_func_decs.h'


def read(p):
    return p.read_text(encoding='utf-8')

def write(p, s):
    p.write_text(s, encoding='utf-8', newline='\n')

def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'ERROR: {label}: expected exactly one anchor, got {n}')
    return text.replace(old, new, 1)

for p in (p_chars, p_spawn, p_funcs, p_decs):
    if MARK in read(p):
        raise SystemExit(f'ERROR: {MARK} already present in {p}')

spawn_impl = r'''
// DARKWOLF_NEW_CHARACTERS_POC_V0_1
// Original DarkWolf character aliases built on stock RTCW cast behavior.
void SP_ai_darkwolf_eliteguard( gentity_t *ent ) {
    ent->aiSkin = "infantryss/darkwolf_eliteguard";
    ent->aihSkin = "darkwolf_eliteguard";
    AICast_DelayedSpawnCast( ent, AICHAR_BLACKGUARD );
}

void SP_ai_darkwolf_heavytrooper( gentity_t *ent ) {
    ent->aiSkin = "supersoldier/darkwolf_heavytrooper";
    ent->aihSkin = "darkwolf_heavytrooper";
    AICast_DelayedSpawnCast( ent, AICHAR_SUPERSOLDIER );
}

void SP_ai_darkwolf_flamethrower( gentity_t *ent ) {
    ent->aiSkin = "venom/darkwolf_flamethrower";
    ent->aihSkin = "darkwolf_flamethrower";
    ent->r.svFlags |= SVF_NOFOOTSTEPS;
    AICast_DelayedSpawnCast( ent, AICHAR_VENOM );
}

void SP_ai_darkwolf_catacomb_lurker( gentity_t *ent ) {
    ent->aiSkin = "loper/darkwolf_catacomb_lurker";
    ent->aihSkin = "darkwolf_catacomb_lurker";
    ent->r.svFlags |= SVF_NOFOOTSTEPS;
    AICast_DelayedSpawnCast( ent, AICHAR_LOPER );
    level.loperZapSound = G_SoundIndex( "loperZap" );
}

void SP_ai_darkwolf_mutated_failure( gentity_t *ent ) {
    ent->aiSkin = "loper/darkwolf_mutated_failure";
    ent->aihSkin = "darkwolf_mutated_failure";
    ent->r.svFlags |= SVF_NOFOOTSTEPS;
    AICast_DelayedSpawnCast( ent, AICHAR_LOPER );
    level.loperZapSound = G_SoundIndex( "loperZap" );
}

void SP_ai_darkwolf_undead_soldier( gentity_t *ent ) {
    ent->aiSkin = "zombie/darkwolf_undead_soldier";
    ent->aihSkin = "darkwolf_undead_soldier";
    ent->r.svFlags |= SVF_NOFOOTSTEPS;
    AICast_DelayedSpawnCast( ent, AICHAR_ZOMBIE );
}

void SP_ai_darkwolf_stitched_experiment( gentity_t *ent ) {
    ent->aiSkin = "beast/darkwolf_stitched_experiment";
    ent->aihSkin = "darkwolf_stitched_experiment";
    AICast_DelayedSpawnCast( ent, AICHAR_HELGA );
}

'''

s = read(p_chars)
anchor = '/*QUAKED ai_soldier (1 0.25 0) (-16 -16 -24) (16 16 64) TriggerSpawn NoRevive\n'
s = replace_once(s, anchor, spawn_impl + anchor, 'ai_cast character spawn insertion')
write(p_chars, s)

proto_anchor = 'void SP_ai_civilian( gentity_t *ent );\n// done.\n'
proto_block = '''void SP_ai_civilian( gentity_t *ent );
// DARKWOLF_NEW_CHARACTERS_POC_V0_1
void SP_ai_darkwolf_eliteguard( gentity_t *ent );
void SP_ai_darkwolf_heavytrooper( gentity_t *ent );
void SP_ai_darkwolf_flamethrower( gentity_t *ent );
void SP_ai_darkwolf_catacomb_lurker( gentity_t *ent );
void SP_ai_darkwolf_mutated_failure( gentity_t *ent );
void SP_ai_darkwolf_undead_soldier( gentity_t *ent );
void SP_ai_darkwolf_stitched_experiment( gentity_t *ent );
// done.
'''
s = read(p_spawn)
s = replace_once(s, proto_anchor, proto_block, 'g_spawn declarations')

table_anchor = '\t{"ai_civilian", SP_ai_civilian},\n\n\n\t{"ai_marker", SP_ai_marker},\n'
table_block = '''\t{"ai_civilian", SP_ai_civilian},

\t// DARKWOLF_NEW_CHARACTERS_POC_V0_1
\t{"ai_darkwolf_eliteguard", SP_ai_darkwolf_eliteguard},
\t{"ai_darkwolf_heavytrooper", SP_ai_darkwolf_heavytrooper},
\t{"ai_darkwolf_flamethrower", SP_ai_darkwolf_flamethrower},
\t{"ai_darkwolf_catacomb_lurker", SP_ai_darkwolf_catacomb_lurker},
\t{"ai_darkwolf_mutated_failure", SP_ai_darkwolf_mutated_failure},
\t{"ai_darkwolf_undead_soldier", SP_ai_darkwolf_undead_soldier},
\t{"ai_darkwolf_stitched_experiment", SP_ai_darkwolf_stitched_experiment},

\t{"ai_marker", SP_ai_marker},
'''
s = replace_once(s, table_anchor, table_block, 'g_spawn table')
write(p_spawn, s)

func_anchor = '{"SP_ai_blackguard", (byte *)SP_ai_blackguard},\n'
func_block = '''// DARKWOLF_NEW_CHARACTERS_POC_V0_1
{"SP_ai_darkwolf_eliteguard", (byte *)SP_ai_darkwolf_eliteguard},
{"SP_ai_darkwolf_heavytrooper", (byte *)SP_ai_darkwolf_heavytrooper},
{"SP_ai_darkwolf_flamethrower", (byte *)SP_ai_darkwolf_flamethrower},
{"SP_ai_darkwolf_catacomb_lurker", (byte *)SP_ai_darkwolf_catacomb_lurker},
{"SP_ai_darkwolf_mutated_failure", (byte *)SP_ai_darkwolf_mutated_failure},
{"SP_ai_darkwolf_undead_soldier", (byte *)SP_ai_darkwolf_undead_soldier},
{"SP_ai_darkwolf_stitched_experiment", (byte *)SP_ai_darkwolf_stitched_experiment},
{"SP_ai_blackguard", (byte *)SP_ai_blackguard},
'''
s = read(p_funcs)
s = replace_once(s, func_anchor, func_block, 'g_funcs registry')
write(p_funcs, s)

dec_anchor = 'extern void SP_ai_blackguard ( gentity_t * ent ) ;\n'
dec_block = '''// DARKWOLF_NEW_CHARACTERS_POC_V0_1
extern void SP_ai_darkwolf_eliteguard ( gentity_t * ent ) ;
extern void SP_ai_darkwolf_heavytrooper ( gentity_t * ent ) ;
extern void SP_ai_darkwolf_flamethrower ( gentity_t * ent ) ;
extern void SP_ai_darkwolf_catacomb_lurker ( gentity_t * ent ) ;
extern void SP_ai_darkwolf_mutated_failure ( gentity_t * ent ) ;
extern void SP_ai_darkwolf_undead_soldier ( gentity_t * ent ) ;
extern void SP_ai_darkwolf_stitched_experiment ( gentity_t * ent ) ;
extern void SP_ai_blackguard ( gentity_t * ent ) ;
'''
s = read(p_decs)
s = replace_once(s, dec_anchor, dec_block, 'g_func_decs declarations')
write(p_decs, s)

if asset_root is not None:
    asset_root.mkdir(parents=True, exist_ok=True)
    def put(rel, data):
        p = asset_root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(data.strip() + '\n', encoding='utf-8', newline='\n')

    put('models/players/infantryss/body_darkwolf_eliteguard.skin', r'''
tag_head,
tag_footleft,
tag_legleft,
tag_footright,
tag_legright,
tag_lbelt,
tag_torso,
tag_bleft,
tag_bright,
l_legs,darkwolf/newchars/eliteguard_legs
u_body,darkwolf/newchars/eliteguard_body
u_rthand,darkwolf/newchars/eliteguard_body
u_lfthand,darkwolf/newchars/eliteguard_body
md3_back,acc/snowgearB
md3_beltl,acc/snowgearL
md3_beltr,acc/snowgearR
''')
    put('models/players/infantryss/head_darkwolf_eliteguard.skin', r'''
md3_part,"head.md3"
md3_hat,"acc/helmutsn"
tag_head,
h_head,darkwolf/newchars/eliteguard_head
h_mouthin,darkwolf/newchars/eliteguard_head
h_teethbot,darkwolf/newchars/eliteguard_head
h_teethup,darkwolf/newchars/eliteguard_head
h_blink,models/players/infantrySS/i_head_blink.tga
''')

    put('models/players/supersoldier/body_darkwolf_heavytrooper.skin', r'''
md3_weapon,"acc/gun.md3"
l_leglft,darkwolf/newchars/heavy_legs
l_legrt,darkwolf/newchars/heavy_legs
u_body,darkwolf/newchars/heavy_body
u_lftarm,darkwolf/newchars/heavy_body
u_rtarm,darkwolf/newchars/heavy_body
u_stim1,darkwolf/newchars/heavy_stim
u_stim2,darkwolf/newchars/heavy_stim
u_head,darkwolf/newchars/heavy_head
''')
    put('models/players/supersoldier/head_darkwolf_heavytrooper.skin', r'''
md3_hat,"acc/helmet.md3"
tag_head,darkwolf/newchars/heavy_head
''')

    put('models/players/venom/body_darkwolf_flamethrower.skin', r'''
tag_head,
tag_footleft,
tag_legleft,
tag_footright,
tag_legright,
tag_lbelt,
tag_torso,
tag_bleft,
tag_bright,
l_legs,darkwolf/newchars/flame_legs
u_body,darkwolf/newchars/flame_body
u_handrt,darkwolf/newchars/flame_legs
u_handlft,darkwolf/newchars/flame_legs
u_ammo,darkwolf/newchars/flame_legs
u_gascan,darkwolf/newchars/flame_head
u_head,darkwolf/newchars/flame_head
u_glass,models/players/venom/v_glassn1.tga
u_headin,models/players/venom/vi_head.tga
md3_back,"acc/backpack.md3"
''')
    put('models/players/venom/head_darkwolf_flamethrower.skin', r'''
tag_head,
h_head,darkwolf/newchars/flame_head
''')

    loper_tags = '''tag_spinner,
tag_head,
tag_torso,
tag_weapon2,
tag_weapon,
tag_spinner,
tag_head,
tag_torso,
'''
    put('models/players/loper/body_darkwolf_catacomb_lurker.skin', loper_tags + r'''
l_l_shoulder,darkwolf/newchars/lurker_body
l_r_shoulder,darkwolf/newchars/lurker_body
l_armlft,darkwolf/newchars/lurker_body
l_armrt,darkwolf/newchars/lurker_body
l_body,darkwolf/newchars/lurker_body
l_stimengine,darkwolf/newchars/lurker_lower
l_leftfoot,darkwolf/newchars/lurker_body
l_rightfoot,darkwolf/newchars/lurker_body
''')
    put('models/players/loper/head_darkwolf_catacomb_lurker.skin', r'''
tag_head,
h_head,darkwolf/newchars/lurker_head
h_teethuppe0,darkwolf/newchars/lurker_head
h_teethupper,darkwolf/newchars/lurker_head
''')

    put('models/players/loper/body_darkwolf_mutated_failure.skin', loper_tags + r'''
l_l_shoulder,darkwolf/newchars/mutated_body
l_r_shoulder,darkwolf/newchars/mutated_body
l_armlft,darkwolf/newchars/mutated_body
l_armrt,darkwolf/newchars/mutated_body
l_body,darkwolf/newchars/mutated_body
l_stimengine,darkwolf/newchars/mutated_lower
l_leftfoot,darkwolf/newchars/mutated_body
l_rightfoot,darkwolf/newchars/mutated_body
''')
    put('models/players/loper/head_darkwolf_mutated_failure.skin', r'''
tag_head,
h_head,darkwolf/newchars/mutated_head
h_teethuppe0,darkwolf/newchars/mutated_head
h_teethupper,darkwolf/newchars/mutated_head
''')

    put('models/players/zombie/body_darkwolf_undead_soldier.skin', r'''
tag_head,
tag_footleft,
tag_legleft,
tag_footright,
tag_legright,
tag_lbelt,
tag_torso,
tag_bleft,
tag_bright,
u_body,darkwolf/newchars/undead_body
''')
    put('models/players/zombie/head_darkwolf_undead_soldier.skin', r'''
md3_part,"head.md3"
md3_hat,"acc/helmut.md3"
tag_head,
h_head,darkwolf/newchars/undead_head
''')

    put('models/players/beast/body_darkwolf_stitched_experiment.skin', r'''
u_body,darkwolf/newchars/stitched_body
u_skulls,darkwolf/newchars/stitched_skulls
u_mouth,models/players/beast/mouth.tga
''')
    put('models/players/beast/head_darkwolf_stitched_experiment.skin', r'''
tag_head,
h_head,models/players/beast/mouth.tga
''')

    put('scripts/darkwolf_new_characters.shader', r'''
// DARKWOLF_NEW_CHARACTERS_POC_V0_1

darkwolf/newchars/eliteguard_body
{
    { map models/players/infantrySS/i_bodysn1.tga rgbGen lightingDiffuse }
    { map $whiteimage blendFunc GL_DST_COLOR GL_ZERO rgbGen const ( 0.45 0.48 0.47 ) }
}
darkwolf/newchars/eliteguard_legs
{
    { map models/players/infantrySS/i_legssn2.tga rgbGen lightingDiffuse }
    { map $whiteimage blendFunc GL_DST_COLOR GL_ZERO rgbGen const ( 0.40 0.42 0.42 ) }
}
darkwolf/newchars/eliteguard_head
{
    { map models/players/infantrySS/i_headsn1.tga rgbGen lightingDiffuse }
    { map $whiteimage blendFunc GL_DST_COLOR GL_ZERO rgbGen const ( 0.33 0.34 0.34 ) }
}

darkwolf/newchars/heavy_body
{
    { map models/players/supersoldier/sup_body1.tga rgbGen lightingDiffuse }
    { map $whiteimage blendFunc GL_DST_COLOR GL_ZERO rgbGen const ( 0.48 0.52 0.47 ) }
}
darkwolf/newchars/heavy_legs
{
    { map models/players/supersoldier/sup_legs1.tga rgbGen lightingDiffuse }
    { map $whiteimage blendFunc GL_DST_COLOR GL_ZERO rgbGen const ( 0.45 0.48 0.44 ) }
}
darkwolf/newchars/heavy_head
{
    { map models/players/supersoldier/sup_head1.tga rgbGen lightingDiffuse }
    { map $whiteimage blendFunc GL_DST_COLOR GL_ZERO rgbGen const ( 0.48 0.48 0.43 ) }
}
darkwolf/newchars/heavy_stim
{
    { map models/players/supersoldier/sup_stim1.tga rgbGen lightingDiffuse }
    { map $whiteimage blendFunc GL_DST_COLOR GL_ZERO rgbGen const ( 0.35 0.40 0.34 ) }
}

darkwolf/newchars/flame_body
{
    { map models/players/venom/v_bodysn1.tga rgbGen lightingDiffuse }
    { map $whiteimage blendFunc GL_DST_COLOR GL_ZERO rgbGen const ( 0.55 0.50 0.42 ) }
}
darkwolf/newchars/flame_legs
{
    { map models/players/venom/v_legssn1.tga rgbGen lightingDiffuse }
    { map $whiteimage blendFunc GL_DST_COLOR GL_ZERO rgbGen const ( 0.46 0.44 0.39 ) }
}
darkwolf/newchars/flame_head
{
    { map models/players/venom/v_headsn1.tga rgbGen lightingDiffuse }
    { map $whiteimage blendFunc GL_DST_COLOR GL_ZERO rgbGen const ( 0.40 0.40 0.38 ) }
}

darkwolf/newchars/lurker_body
{
    { map models/players/loper/lop_body2.tga rgbGen lightingDiffuse }
    { map $whiteimage blendFunc GL_DST_COLOR GL_ZERO rgbGen const ( 0.72 0.66 0.58 ) }
}
darkwolf/newchars/lurker_lower
{
    { map models/players/loper/lop_lower1.tga rgbGen lightingDiffuse }
    { map $whiteimage blendFunc GL_DST_COLOR GL_ZERO rgbGen const ( 0.45 0.42 0.38 ) }
}
darkwolf/newchars/lurker_head
{
    { map models/players/loper/lop_head2.tga rgbGen lightingDiffuse }
    { map $whiteimage blendFunc GL_DST_COLOR GL_ZERO rgbGen const ( 0.72 0.64 0.56 ) }
}

darkwolf/newchars/mutated_body
{
    { map models/players/loper/lop_body1.tga rgbGen lightingDiffuse }
    { map $whiteimage blendFunc GL_DST_COLOR GL_ZERO rgbGen const ( 0.62 0.38 0.35 ) }
}
darkwolf/newchars/mutated_lower
{
    { map models/players/loper/lop_lower1.tga rgbGen lightingDiffuse }
    { map $whiteimage blendFunc GL_DST_COLOR GL_ZERO rgbGen const ( 0.45 0.28 0.27 ) }
}
darkwolf/newchars/mutated_head
{
    { map models/players/loper/lop_head1.tga rgbGen lightingDiffuse }
    { map $whiteimage blendFunc GL_DST_COLOR GL_ZERO rgbGen const ( 0.63 0.38 0.35 ) }
}

darkwolf/newchars/undead_body
{
    { map models/players/zombie/zom_body2.tga rgbGen lightingDiffuse }
    { map $whiteimage blendFunc GL_DST_COLOR GL_ZERO rgbGen const ( 0.62 0.58 0.47 ) }
}
darkwolf/newchars/undead_head
{
    { map models/players/zombie/zom_head2.tga rgbGen lightingDiffuse }
    { map $whiteimage blendFunc GL_DST_COLOR GL_ZERO rgbGen const ( 0.66 0.60 0.48 ) }
}

darkwolf/newchars/stitched_body
{
    { map models/players/beast/bes_body1.tga rgbGen lightingDiffuse }
    { map $whiteimage blendFunc GL_DST_COLOR GL_ZERO rgbGen const ( 0.78 0.58 0.52 ) }
}
darkwolf/newchars/stitched_skulls
{
    { map models/players/beast/skulls2.tga rgbGen lightingDiffuse }
    { map $whiteimage blendFunc GL_DST_COLOR GL_ZERO rgbGen const ( 0.58 0.44 0.40 ) }
}
''')

    put('docs/DARKWOLF_NEW_CHARACTERS_POC_V0_1.txt', r'''
DarkWolf New Characters POC v0.1
================================

Spawnable classes:
  ai_darkwolf_eliteguard
  ai_darkwolf_heavytrooper
  ai_darkwolf_flamethrower
  ai_darkwolf_catacomb_lurker
  ai_darkwolf_mutated_failure
  ai_darkwolf_undead_soldier
  ai_darkwolf_stitched_experiment

Runtime test command:
  /aicast spawn <classname>

Examples:
  /aicast spawn ai_darkwolf_eliteguard
  /aicast spawn ai_darkwolf_catacomb_lurker

POC scope:
- separate new classnames; existing campaign actors are not replaced;
- stock AI/animation families are reused for stability;
- custom skins/shaders reference original RTCW retail player assets;
- no original retail binary models or textures are redistributed;
- no renderer, StaticPromote, shadow, Bloom, ToneMap or Exposure changes.
''')

print(f'{MARK}: source patch PASS')
if asset_root is not None:
    print(f'{MARK}: asset overlay written to {asset_root}')
