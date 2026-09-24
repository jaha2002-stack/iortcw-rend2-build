from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("source")

MARK = "DARKWOLF_ELITE_GUARD_V0_5_GAME"
p_chars = root / "SP/code/game/ai_cast_characters.c"
p_spawn = root / "SP/code/game/g_spawn.c"
p_funcs = root / "SP/code/game/g_funcs.h"
p_decs = root / "SP/code/game/g_func_decs.h"


def read(p):
    return p.read_text(encoding="utf-8")


def write(p, s):
    p.write_text(s, encoding="utf-8", newline="\n")


def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(
            f"ERROR: {label}: expected exactly one anchor, got {n}"
        )
    return text.replace(old, new, 1)


for p in (p_chars, p_spawn, p_funcs, p_decs):
    if MARK in read(p):
        raise SystemExit(f"ERROR: {MARK} already present in {p}")


spawn_impl = r'''
// DARKWOLF_ELITE_GUARD_V0_5_GAME
// Game-runtime alias for the production DarkWolf Elite Guard model.
// Uses BlackGuard combat/animation behavior while loading the dedicated
// models/players/darkwolf_eliteguard visual package.
void SP_ai_darkwolf_eliteguard( gentity_t *ent ) {
    ent->aiSkin = "darkwolf_eliteguard/default";
    ent->aihSkin = "default";
    AICast_DelayedSpawnCast( ent, AICHAR_BLACKGUARD );
}

'''

s = read(p_chars)
anchor = (
    "/*QUAKED ai_soldier (1 0.25 0) (-16 -16 -24) "
    "(16 16 64) TriggerSpawn NoRevive\n"
)
s = replace_once(
    s,
    anchor,
    spawn_impl + anchor,
    "ai_cast character spawn insertion",
)
write(p_chars, s)

proto_anchor = "void SP_ai_civilian( gentity_t *ent );\n// done.\n"
proto_block = """void SP_ai_civilian( gentity_t *ent );
// DARKWOLF_ELITE_GUARD_V0_5_GAME
void SP_ai_darkwolf_eliteguard( gentity_t *ent );
// done.
"""
s = read(p_spawn)
s = replace_once(s, proto_anchor, proto_block, "g_spawn declarations")

table_anchor = (
    '\t{"ai_civilian", SP_ai_civilian},\n\n\n'
    '\t{"ai_marker", SP_ai_marker},\n'
)
table_block = """\t{"ai_civilian", SP_ai_civilian},

\t// DARKWOLF_ELITE_GUARD_V0_5_GAME
\t{"ai_darkwolf_eliteguard", SP_ai_darkwolf_eliteguard},

\t{"ai_marker", SP_ai_marker},
"""
s = replace_once(s, table_anchor, table_block, "g_spawn table")
write(p_spawn, s)

func_anchor = '{"SP_ai_blackguard", (byte *)SP_ai_blackguard},\n'
func_block = """// DARKWOLF_ELITE_GUARD_V0_5_GAME
{"SP_ai_darkwolf_eliteguard", (byte *)SP_ai_darkwolf_eliteguard},
{"SP_ai_blackguard", (byte *)SP_ai_blackguard},
"""
s = read(p_funcs)
s = replace_once(s, func_anchor, func_block, "g_funcs registry")
write(p_funcs, s)

dec_anchor = "extern void SP_ai_blackguard ( gentity_t * ent ) ;\n"
dec_block = """// DARKWOLF_ELITE_GUARD_V0_5_GAME
extern void SP_ai_darkwolf_eliteguard ( gentity_t * ent ) ;
extern void SP_ai_blackguard ( gentity_t * ent ) ;
"""
s = read(p_decs)
s = replace_once(s, dec_anchor, dec_block, "g_func_decs declarations")
write(p_decs, s)

print(f"{MARK}: source patch PASS")
