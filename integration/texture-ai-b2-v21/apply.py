#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys

src=Path(sys.argv[1]).resolve()
ev=Path(sys.argv[2]).resolve(); ev.mkdir(parents=True,exist_ok=True)
p=src/"SP/code/rend2/tr_texture_ai_b2_v2.inc"
before=p.read_text()
old='Com_sprintf(pk3Name, sizeof(pk3Name), "zz_dwtr_%08x.pk3", hash);'
new='Com_sprintf(pk3Name, sizeof(pk3Name), "zzz_dwtr_%08x.pk3", hash);'
assert before.count(old)==1, before.count(old)
after=before.replace(old,new,1)
old2='ri.Printf(PRINT_ALL,\n              "DWTR AI B2 V2: SAVED %s variant=%s. It will override %s after restart.\\n",\n              pk3Name, cand->label, internal);'
new2='ri.Printf(PRINT_ALL,\n              "DWTR AI B2 V2.1: SAVED %s variant=%s. It will override %s after restart.\\n",\n              pk3Name, cand->label, internal);\\n    ri.Printf(PRINT_ALL, "DWTR AI B2 V2.1: physical PK3=%s\\n", pk3Physical);'
assert before.count(old2)==1, before.count(old2)
after=after.replace(old2,new2,1)
marker='/* DARKWOLF_TEXTURE_AI_B2_V21_PK3_AUTOLOAD_FIX */'
assert marker not in after
after += "\\n"+marker+"\\n"
p.write_text(after)

proof={
 "version":"DarkWolf Local AI Texture Restoration B2 V2.1",
 "base":"B2 V2 Run #42574596120",
 "fix":"PK3 autoload filename collision with RTCW SP sorting kludge",
 "old_prefix":"zz_dwtr_",
 "old_problem":"FS_AddGameDirectory rewrites any real zz_* pak name to sp_* before FS_LoadZipFile",
 "new_prefix":"zzz_dwtr_",
 "why_safe":"zzz_ does not match the engine's exact zz_ rewrite and sorts after ordinary paks",
 "save_root":"fs_homepath/<game> (engine search path, highest-priority home game directory)",
 "prints_exact_physical_path":True,
 "before_sha256":hashlib.sha256(before.encode()).hexdigest(),
 "after_sha256":hashlib.sha256(after.encode()).hexdigest()
}
(ev/"DW_TEXTURE_AI_B2_V21_SOURCE_PROOF.json").write_text(json.dumps(proof,indent=2)+"\\n")
print(json.dumps(proof,indent=2))
