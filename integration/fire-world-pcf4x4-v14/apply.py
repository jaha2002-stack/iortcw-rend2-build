#!/usr/bin/env python3
"""Quality-only V1.4 from exact Clean #41297344177; only renderer tr_main.c."""
import argparse,hashlib,json
from pathlib import Path
BASE="a304b1e0a30b9d834c9180e15e9275dd40fc08e939f38e675815f4cadca4da59"
AFTER="0a17db572b5bf4ee9c5523a47dabf3302a36e23ec2e5fe0d0d3febb300fe7303"
MARK="DARKWOLF_FIRE_WORLD_PCF4X4_V14_PRODUCTION_CANDIDATE_20261102"
FILE="SP/code/rend2/tr_main.c"
def sha(s): return hashlib.sha256(s).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument("root",type=Path)
    ap.add_argument("--check-only",action="store_true");ap.add_argument("--proof",type=Path)
    a=ap.parse_args(); p=a.root/FILE; old=p.read_bytes()
    assert sha(old)==BASE,("WRONG_CLEAN_SOURCE",sha(old),BASE)
    s=old.decode("utf-8")
    assert MARK not in s and "r_dwFireShadowMotion" not in s
    assert "r_dwFireWorldMaskProbe" not in s
    orig="""\t\tif (R_DWIsStationaryXlabsTeslaWorldLight(dl))
\t\t\ttr.refdef.dlightWorldOrigin[i][3] = -2.0f - 1.0f / cache->radius;

\t}
}

static qboolean R_FireVolProductionCacheMatchesHint"""
    target="""\t\tif (R_DWIsStationaryXlabsTeslaWorldLight(dl))
\t\t\ttr.refdef.dlightWorldOrigin[i][3] = -2.0f - 1.0f / cache->radius;
\t\t// """+MARK+"""
\t\t// Reuse the existing signed face-corrected 4x4 tent PCF for STRICT
\t\t// real authored persistent fire ONLY. Original world-only cubemap,
\t\t// 6-face depth capture, exact-origin cache and Tesla remain unchanged.
\t\telse if (dl->worldOcclusion && dl->nativeAuthoredDlight &&
\t\t\tdl->fireVolumetricSource &&
\t\t\tdl->shadowSourceClass == DWSHADOW_SOURCE_PERSISTENT_FIRE &&
\t\t\tdl->staticPromoteFixtureId < 0 &&
\t\t\tdl->fireVolumetricNativeOrdinal >= 0)
\t\t\ttr.refdef.dlightWorldOrigin[i][3] = -2.0f - 1.0f / cache->radius;

\t}
}

static qboolean R_FireVolProductionCacheMatchesHint"""
    assert s.count(orig)==1,("WRONG_ANCHOR",s.count(orig))
    final=s.replace(orig,target,1).encode("utf-8")
    assert sha(final)==AFTER,("UNEXPECTED_PATCH_SHA",sha(final),AFTER)
    assert "r_dwFireWorldMaskProbe" not in final.decode()
    if not a.check_only:p.write_bytes(final)
    proof={"status":"PRODUCTION_CANDIDATE_GPU_UNVERIFIED","base_run":41297344177,
        "modified_files":[FILE],"source_sha256_before":BASE,"source_sha256_after":AFTER,
        "new_cvars":[],"changed_capture":False,"changed_shadow_cache":False,
        "changed_light_motion":False,"changed_shader_sources":False,
        "world_containment_default":2,"gpu_regressions":"UNTESTED"}
    if a.proof:a.proof.parent.mkdir(parents=True,exist_ok=True);a.proof.write_text(json.dumps(proof,indent=2)+"\n")
    print("DW_FIRE_WORLD_PCF4x4_V14_EXACT_CLEAN_SINGLE_FILE_PASS")
if __name__=="__main__":main()
