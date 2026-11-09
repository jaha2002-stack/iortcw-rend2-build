#!/usr/bin/env python3
from pathlib import Path
import json,sys
root=Path(sys.argv[1]); ev=Path(sys.argv[2]); ev.mkdir(parents=True,exist_ok=True)
v2=(root/"tr_texture_ai_b2_v2.inc").read_text()
fs=(Path(sys.argv[3])/"SP/code/qcommon/files.c").read_text() if len(sys.argv)>3 else ""
checks={}
def ck(k,v):
    checks[k]=bool(v); assert v,k
ck("new_prefix",'\"zzz_dwtr_%08x.pk3\"' in v2)
ck("old_prefix_removed",'\"zz_dwtr_%08x.pk3\"' not in v2)
ck("physical_path_logged","physical PK3=%s" in v2 and "pk3Physical" in v2)
ck("still_atomic","MoveFileExA(tmpPath, finalPath" in v2)
ck("still_physical_write","CreateFileA(tmpPath" in v2)
ck("engine_sp_kludge_present",'!Q_strncmp( sorted[i],"zz_",3 )' in fs)
ck("engine_rewrites_to_sp",'memcpy( sorted[i],"sp",2 )' in fs)
ck("zzz_does_not_match_kludge", not "zzz_dwtr_".startswith("zz_"))
(ev/"DW_TEXTURE_AI_B2_V21_TESTS.json").write_text(json.dumps(checks,indent=2)+"\\n")
print("DW_TEXTURE_AI_B2_V21_STATIC_TESTS_PASS",len(checks))
