#!/usr/bin/env python3
"""Diagnostic-only Caster Scope and Receiver Path for accepted HDR16F Clean #41019985033.

Defaults 0/0: exact original Stage 11 caster/receiver eligibility.
Do NOT ship diagnostic scope narrowing to Clean Production.
"""
import argparse
import hashlib
import json
from pathlib import Path

MARK = "DARKWOLF_POINT_SHADOW_SCOPE_DIAGNOSTIC_V1_41019985033"
FILES = ("tr_local.h", "tr_init.c", "tr_backend.c", "tr_shade.c")

def rep(s, old, new, tag):
    count = s.count(old)
    assert count == 1, (tag, "expected one exact anchor", count)
    return s.replace(old, new, 1)

def digest(s):
    return hashlib.sha256(s.encode()).hexdigest()

def apply(root, check=False, proof=None):
    base = Path(root) / "SP/code/rend2"
    a = {n:(base/n).read_text() for n in FILES}
    assert all(MARK not in s for s in a.values()), "already patched"
    assert "DARKWOLF_STAGE11_UNIFIED_ASSET_SHADOW_COVERAGE_CLEAN_PRODUCTION_V1" in a["tr_shade.c"]
    assert "DARKWOLF_STAGE11_UNIFIED_ASSET_SHADOW_COVERAGE_CLEAN_PRODUCTION_V1" in a["tr_backend.c"]
    assert "DARKWOLF_SUN_HDR16F_PRECISION_V1_40878732886" in a["tr_backend.c"], "not the user-accepted HDR16F source"
    b = dict(a)
    b["tr_local.h"] = rep(b["tr_local.h"],
        "extern cvar_t  *r_dlightShadowStrength;",
        "extern cvar_t  *r_dlightShadowStrength;\n"
        f"extern cvar_t  *r_dwPointCasterScope; // {MARK}: 0 all, 1 BSP world, 2 entities\n"
        f"extern cvar_t  *r_dwPointReceiverPath; // {MARK}: 0 all, 1 legacy without point shadow",
        "extern")
    b["tr_init.c"] = rep(b["tr_init.c"],
        "cvar_t  *r_dlightShadowStrength;",
        "cvar_t  *r_dlightShadowStrength;\n"
        f"cvar_t  *r_dwPointCasterScope; // {MARK}\n"
        f"cvar_t  *r_dwPointReceiverPath; // {MARK}",
        "definitions")
    b["tr_init.c"] = rep(b["tr_init.c"],
        'r_dlightShadowStrength = ri.Cvar_Get( "r_dlightShadowStrength", "0.88", CVAR_ARCHIVE );',
        'r_dlightShadowStrength = ri.Cvar_Get( "r_dlightShadowStrength", "0.88", CVAR_ARCHIVE );\n'
        f'\t// {MARK}: test-only, non-archived. Caster scope latched for cubemap history reset.\n'
        '\tr_dwPointCasterScope = ri.Cvar_Get( "r_dwPointCasterScope", "0", CVAR_LATCH );\n'
        '\tri.Cvar_CheckRange( r_dwPointCasterScope, 0, 2, qtrue );\n'
        '\tr_dwPointReceiverPath = ri.Cvar_Get( "r_dwPointReceiverPath", "0", 0 );\n'
        '\tri.Cvar_CheckRange( r_dwPointReceiverPath, 0, 1, qtrue );',
        "register")
    block = f'''\t\t// {MARK}: point-shadow capture only; does not alter final caster eligibility.
\t\t// World BSP: REFENTITYNUM_WORLD. Others: scene entities, including bmodels.
\t\t// Caster scope is latched: vid_restart rebuilds all shadow cubemap caches.
\t\tif (r_dwPointCasterScope && r_dwPointCasterScope->integer != 0 &&
\t\t\t(backEnd.viewParms.flags & (VPF_SHADOWMAP | VPF_DEPTHSHADOW)) ==
\t\t\t\t(VPF_SHADOWMAP | VPF_DEPTHSHADOW) &&
\t\t\t!(backEnd.viewParms.flags & (VPF_FIREVOL_SYNTHETIC_SHADOW | VPF_DLIGHT_WORLD_OCCLUSION)))
\t\t{{
\t\t\tint dwScopeEntityNum;
\t\t\t// Same entity key decode as R_DecomposeSort (no unsafe NULL parameters).
\t\t\tdwScopeEntityNum = (drawSurf->sort >> QSORT_REFENTITYNUM_SHIFT) & REFENTITYNUM_MASK;
\t\t\tif ((r_dwPointCasterScope->integer == 1 && dwScopeEntityNum != REFENTITYNUM_WORLD) ||
\t\t\t\t(r_dwPointCasterScope->integer == 2 && dwScopeEntityNum == REFENTITYNUM_WORLD))
\t\t\t\tcontinue;
\t\t}}
'''
    b["tr_backend.c"] = rep(b["tr_backend.c"],
        "\tfor (i = 0, drawSurf = drawSurfs ; i < numDrawSurfs ; i++, drawSurf++) {\n"
        "\t\tif ( drawSurf->sort == oldSort && drawSurf->cubemapIndex == oldCubemapIndex && drawSurf->mapLightingKey == oldMapLightingKey) {",
        "\tfor (i = 0, drawSurf = drawSurfs ; i < numDrawSurfs ; i++, drawSurf++) {\n" + block +
        "\t\tif ( drawSurf->sort == oldSort && drawSurf->cubemapIndex == oldCubemapIndex && drawSurf->mapLightingKey == oldMapLightingKey) {",
        "capture only before fast path")
    anchor = """\t\tuseShadow = r_dlightMode->integer >= 2
\t\t\t&& (backEnd.refdef.dlightShadowMask & (1u << l))
\t\t\t&& shadowSlot >= 0 && shadowSlot < MAX_DLIGHT_SHADOWS
\t\t\t&& tr.shadowCubemaps[shadowSlot] != NULL;"""
    start = b["tr_shade.c"].index("static void ProjectDlightTexture( void ) {")
    end = b["tr_shade.c"].index("static void ComputeShaderColors", start)
    section = b["tr_shade.c"][start:end]
    section = rep(section, anchor,
        anchor + f"\n\t\t// {MARK}: legacy ProjectDlightTexture receiver only; forward unchanged.\n"
        "\t\tif (r_dwPointReceiverPath && r_dwPointReceiverPath->integer == 1)\n"
        "\t\t\tuseShadow = qfalse;",
        "legacy receiver only")
    b["tr_shade.c"] = b["tr_shade.c"][:start]+section+b["tr_shade.c"][end:]
    assert b["tr_shade.c"].count("RB_BindDlightWorldOcclusion(sp, l);")==a["tr_shade.c"].count("RB_BindDlightWorldOcclusion(sp, l);")
    assert a["tr_shade.c"].count(anchor)==b["tr_shade.c"].count(anchor)
    assert "DARKWOLF_SUN_HDR16F_PRECISION_V1_40878732886" in b["tr_backend.c"]
    assert all(a[n]!=b[n] for n in FILES)
    if not check:
        for n in FILES:
            (base/n).write_text(b[n])
    summary = {
        "accepted_baseline_run":41019985033,"marker":MARK,"check_only":check,
        "modified_files":["SP/code/rend2/"+n for n in FILES],
        "sha256_before":{n:digest(v) for n,v in a.items()},
        "sha256_after":{n:digest(v) for n,v in b.items()},
        "caster_modes":{"0":"all unchanged","1":"world/BSP only diagnostic","2":"non-world entity incl. bmodels only diagnostic"},
        "receiver_modes":{"0":"all unchanged","1":"legacy ProjectDlightTexture point shadow disabled, other receivers unchanged"},
        "caster_change_requires_vid_restart":True,"sun_hdr16f_untouched":True,
        "stage11_all_casters_receivers_at_defaults":True,
        "point_world_occlusion_untouched":True,"glsl_untouched":True,
        "gpu_test":"PENDING"
    }
    if proof:
        dest=Path(proof);dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(summary,indent=2)+"\n")
    print("DW_POINT_SHADOW_SCOPE_RECEIVER_DIAG_V1_SOURCE_PASS")
    return summary

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("root",type=Path)
    parser.add_argument("--check-only",action="store_true")
    parser.add_argument("--proof",type=Path)
    opts=parser.parse_args()
    apply(opts.root,opts.check_only,opts.proof)
