#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

MARK="DW_BLOOM_V3_FBO_CAPACITY_80"
OLD="#define\tMAX_FBOS      64"
NEW="#define\tMAX_FBOS      80 // "+MARK+": V3 adds 4 FBOs; keep HDR/MSAA headroom"

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--proof", required=True, type=Path)
    a=ap.parse_args()
    root=a.root.resolve()
    p=root/"SP/code/rend2/tr_local.h"
    s=p.read_text(encoding="utf-8")
    if MARK in s:
        raise SystemExit("capacity patch already present")
    if s.count(OLD)!=1:
        raise SystemExit(f"expected one MAX_FBOS=64 anchor, got {s.count(OLD)}")
    for req in ("REND2_BLOOM_V3_HDR_SCATTER_PYRAMID","#define REND2_BLOOM_PYRAMID_LEVELS 5","#define REND2_BLOOM_V2_LEVELS 3"):
        if req not in s:
            raise SystemExit("missing prerequisite: "+req)
    pre=sha(p)
    s=s.replace(OLD,NEW,1)
    p.write_text(s,encoding="utf-8",newline="\n")
    post=sha(p)
    t=p.read_text(encoding="utf-8")
    checks={
        "max_fbos_80": NEW in t,
        "max_fbos_64_absent": OLD not in t,
        "v3_five_levels": "#define REND2_BLOOM_PYRAMID_LEVELS 5" in t,
        "v2_three_levels": "#define REND2_BLOOM_V2_LEVELS 3" in t,
    }
    bad=[k for k,v in checks.items() if not v]
    if bad:
        raise SystemExit("capacity contract failed: "+",".join(bad))
    proof={"marker":MARK,"file":"SP/code/rend2/tr_local.h","pre_sha256":pre,"post_sha256":post,"checks":checks}
    a.proof.parent.mkdir(parents=True,exist_ok=True)
    a.proof.write_text(json.dumps(proof,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(proof,indent=2,sort_keys=True))
    print("DW_BLOOM_V3_FBO_CAPACITY_80_PASS")
    return 0
if __name__=="__main__":
    raise SystemExit(main())
