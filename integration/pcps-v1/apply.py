#!/usr/bin/env python3
"""Inject opt-in DarkWolf PCPS controls into reconstructed EXACT SAFE source.
Fails CLOSED on any unexpected source layout, with no best-effort global edits.
"""
import argparse, hashlib, json
from pathlib import Path
ROOT=Path("SP/code/rend2")
MARK="DARKWOLF_PCPS_RUNTIME_V1"
def once(s,old,new,label):
    count=s.count(old)
    if count!=1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return s.replace(old,new,1)
def apply(root,check=False):
    p=Path(root)/ROOT
    names=("tr_main.c","tr_init.c","tr_backend.c","tr_local.h")
    original={n:(p/n).read_text(encoding="utf-8") for n in names}
    for n,s in original.items():
        if MARK in s:raise RuntimeError(f"duplicate patch {n}")
    # Release-locked signatures: abort if the signed accepted Boss1 patch is missing.
    assert "DARKWOLF_BOSS1_PROVEN_SOURCE_LOCAL_FIX_CLEAN_PRODUCTION_V1" in original["tr_backend.c"]
    assert "DARKWOLF_CRYPT1_PERSISTENT_FIRE_SHADOW_PRIORITY_FIX_V1_20261028" in original["tr_main.c"]
    assert 'r_dlightShadowMaxLights = ri.Cvar_Get( "r_dlightShadowMaxLights", "3"' in original["tr_init.c"]
    body=Path(__file__).with_name("runtime.inc").read_text(encoding="utf-8")
    assert MARK in body
    out=dict(original)
    m=out["tr_main.c"]
    m=once(m,"void R_RenderDlightCubemaps(const refdef_t *fd)",body+"\nvoid R_RenderDlightCubemaps(const refdef_t *fd)","main runtime definition")
    m=once(m,"pendingLightsMask = R_DarkWolfStaticPromoteShadowExpandPending(pendingLightsMask);",
       "pendingLightsMask = R_DarkWolfStaticPromoteShadowExpandPending(pendingLightsMask);\n"
       "\t/* PCPS: block selected source BEFORE residency/slot assignment, preserve direct light. */\n"
       "\tpendingLightsMask = DWPS_ApplyPendingMask(pendingLightsMask);","source eligibility")
    out["tr_main.c"]=m
    h=out["tr_local.h"]
    anchor="void R_RenderDlightCubemaps(const refdef_t *fd);"
    h=once(h,anchor,
       "void DWPS_Register(void);\nvoid DWPS_Unregister(void);\n"
       "unsigned int DWPS_ApplyPendingMask(unsigned int mask);\n"
       "qboolean DWPS_ShouldSkipCaster(const drawSurf_t *ds);\n"+anchor,
       "local declarations")
    out["tr_local.h"]=h
    init=out["tr_init.c"]
    init=once(init,'ri.Cmd_AddCommand( "imagelist", R_ImageList_f );',
       'DWPS_Register(); /* PCPS opts in only via commands */\n\t'
       'ri.Cmd_AddCommand( "imagelist", R_ImageList_f );',
       "command register")
    init=once(init,'ri.Cmd_RemoveCommand( "imagelist" );',
       'DWPS_Unregister();\n\t'
       'ri.Cmd_RemoveCommand( "imagelist" );',
       "command cleanup")
    out["tr_init.c"]=init
    b=out["tr_backend.c"]
    anchor="if(DW_Boss1CleanSkipSourceLocalCaster(drawSurf))continue;"
    b=once(b,anchor,anchor+"\n\t\tif(DWPS_ShouldSkipCaster(drawSurf))continue;",
       "non destructive world caster guard")
    out["tr_backend.c"]=b
    for n in names:
        assert out[n]!=original[n],f"no changes to {n}"
    assert out["tr_main.c"].count("pendingLightsMask = DWPS_ApplyPendingMask(pendingLightsMask);")==1
    assert out["tr_backend.c"].count("if(DWPS_ShouldSkipCaster(drawSurf))continue;")==1
    if not check:
        for n in names:(p/n).write_text(out[n],encoding="utf-8")
    result={
      "accepted_run":41297344177,
      "scope":"opt-in map-local session-only light shadow slot disable and source-local BSP caster omission",
      "changed":names,
      "source_sha256_before":{n:hashlib.sha256(original[n].encode()).hexdigest() for n in names},
      "source_sha256_after":{n:hashlib.sha256(out[n].encode()).hexdigest() for n in names},
      "preserved":["Sun CSM","Fire/Tesla occlusion","default shadow budgets","Texture Material Fidelity V2","Boss1 guard"],
      "notes":["Original dlight illumination preserved","Caster omit does not release slot; only selected source shadow disable releases slot","No automated physically-correct geometry inference"]
    }
    print(json.dumps(result,indent=2))
    return result
if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("root")
    parser.add_argument("--check-only",action="store_true")
    a=parser.parse_args()
    apply(a.root,a.check_only)
