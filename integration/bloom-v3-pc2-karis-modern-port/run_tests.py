#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

V3="REND2_BLOOM_V3_HDR_SCATTER_PYRAMID"
V31="REND2_BLOOM_V3_1_HDR_INPUT_VALIDATION_SCATTER_STABILITY"
PC2="REND2_BLOOM_V3_22_LIGHTALL_NONFINITE_OUTPUT_FIREWALL_PC2"
KARIS="REND2_BLOOM_PC2_KARIS_ANTIFIREFLY_PRODUCTION_CANDIDATE_V2"

def h(p: Path) -> str: return hashlib.sha256(p.read_bytes()).hexdigest()

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("root",type=Path); ap.add_argument("--proof",required=True,type=Path); args=ap.parse_args()
    root=args.root.resolve(); proof=json.loads(args.proof.read_text(encoding="utf-8"))
    r=root/"SP/code/rend2"
    fp=(r/"glsl/bloom_fp.glsl").read_text(encoding="utf-8")
    light=(r/"glsl/lightall_fp.glsl").read_text(encoding="utf-8")
    be=(r/"tr_backend.c").read_text(encoding="utf-8")
    init=(r/"tr_init.c").read_text(encoding="utf-8")
    local=(r/"tr_local.h").read_text(encoding="utf-8")
    alltxt="\n".join([fp,light,be,init,local])
    req={
      "v3": V3 in fp and V3 in be,
      "v31": V31 in fp and V31 in be,
      "pc2": light.count(PC2)==1,
      "karis": fp.count(KARIS)==1 and be.count(KARIS)==1,
      "mode3": 'r_bloomMode, 1, 3, qtrue' in init,
      "startup_mode2": 'ri.Cvar_Set( "r_bloomMode", "2" );' in init,
      "no_debug_trace_cvars": 'r_bloomDebug' not in init and 'r_bloomTrace' not in init and 'r_bloomDebug' not in local and 'r_bloomTrace' not in local,
      "mode2_fallback": '#define REND2_BLOOM_V2_LEVELS 3' in local and 'RB_BloomV2Prepare' in be and 'RB_BloomV2Composite' in be,
      "five_levels": '#define REND2_BLOOM_PYRAMID_LEVELS 5' in local,
      "fbo_capacity_80": 'DW_BLOOM_V3_FBO_CAPACITY_80' in local and 'MAX_FBOS      80' in local,
      "full_safety": 'r_bloomScatterSafety' in alltxt and 'r_bloomScatterMaxLevels' in alltxt and 'r_bloomScatterSafeMax' in alltxt,
      "pbr": 'USE_PBR2' in light and 'DW_LinearToSRGB' in light,
      "ggx": 'USE_PBR2_IBL_V31' in light,
      "pom": 'USE_PBR_PHYSICAL_RELIEF_V32' in light,
      "candidate_v1_absent": 'hdrEligibility' not in fp,
    }
    for rel,digest in proof["frozen_sha256"].items():
        req["frozen:"+rel]=(h(root/rel)==digest)
    failed=[k for k,v in req.items() if not v]
    if failed: raise SystemExit("FAILED: "+", ".join(failed))
    print(json.dumps({"checks":req,"failed":[]},indent=2,sort_keys=True))
    print("DW_BLOOM_V3_PC2_KARIS_MODERN_PORT_STATIC_PASS")
    return 0
if __name__=="__main__": raise SystemExit(main())
