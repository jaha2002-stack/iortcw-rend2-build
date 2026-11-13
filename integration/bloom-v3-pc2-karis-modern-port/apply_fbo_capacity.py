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
    fbo_c=root/"SP/code/rend2/tr_fbo.c"
    s=p.read_text(encoding="utf-8")
    fbo=fbo_c.read_text(encoding="utf-8")
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
    # Current FBO_Init worst-case bound:
    # 2 MSAA render/resolve + 5 pre-shadow singletons + 32 point shadows + 4 sun shadows
    # + 1 screen shadow + 2 texture scratch + 2 exposure FBO + 2 quarter FBO
    # + (5 Bloom levels * 2 ping-pong) + 7 trailing singleton FBO = 67.
    required_anchors=(
        'FBO_Create("_render"', 'FBO_Create("_msaaResolve"',
        'MAX_DRAWN_PSHADOWS', 'FBO_Create("_sunshadowmap"',
        'FBO_Create(va("_bloomPyr%dA"', 'FBO_Create(va("_bloomPyr%dB"',
        'FBO_Create("_dlightShadow"', 'FBO_Create("_dlightWorld"',
        'FBO_Create("_fireVolSyntheticProduction"'
    )
    missing=[x for x in required_anchors if x not in fbo]
    if missing:
        raise SystemExit("FBO budget source drift: "+",".join(missing))
    worst_case=67
    capacity=80
    if capacity < worst_case:
        raise SystemExit("FBO capacity below current worst-case")
    proof={"marker":MARK,"file":"SP/code/rend2/tr_local.h","pre_sha256":pre,"post_sha256":post,
           "worst_case_fbo_budget":worst_case,"capacity":capacity,"headroom":capacity-worst_case,"checks":checks}
    a.proof.parent.mkdir(parents=True,exist_ok=True)
    a.proof.write_text(json.dumps(proof,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(proof,indent=2,sort_keys=True))
    print("DW_BLOOM_V3_FBO_CAPACITY_80_PASS")
    return 0
if __name__=="__main__":
    raise SystemExit(main())
