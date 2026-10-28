#!/usr/bin/env python3
"""Targeted Point Shadow persistent-fire starvation fix over exact #40512393634.

A visible, much-higher-priority persistent fire light can be starved by three
physical groups pinned as residents regardless of priority. This corrects
that priority inversion without reducing the 3+2 budget, changing cubemaps,
touching shaders, or weakening physical residency in lamp-only scenes.
"""
import argparse, hashlib, json
from pathlib import Path

MARK="DARKWOLF_CRYPT1_PERSISTENT_FIRE_SHADOW_PRIORITY_FIX_V1_20261028"
BASE_RUN=40512393634
SRC="SP/code/rend2/tr_main.c"
def H(s): return hashlib.sha256(s.encode()).hexdigest()
def one(s,a,b,key):
    n=s.count(a)
    assert n==1,(key,n)
    return s.replace(a,b,1)

def apply(root):
    file=root/SRC
    before=file.read_text()
    assert MARK not in before,"DUPLICATE_CRYPT1_SHADOW_FIX"
    required=(
      "DARKWOLF_PERSISTENT_PHYSICAL_SHADOW_SET_RESIDENCY_PRODUCTION_V1",
      "DARKWOLF_STAGE11_UNIFIED_ASSET_SHADOW_COVERAGE_CLEAN_PRODUCTION_V1",
      "R_DarkWolfPersistentPhysicalShadowResidentCandidate(",
      "R_DarkWolfStaticPromoteShadowGroupSelectionScore(",
      "R_DarkWolfStaticPromoteShadowExpandPending(",
      "DWSHADOW_SOURCE_PERSISTENT_FIRE",
      "shadowSourceClass",
      "persistentShadowBudget = r_dlightShadowMaxLights->integer;",
      "dynamicShadowBudget = 2;",
      "residentIndexBySlot[residencySlot] = residentIndex;",
      "historyHold[shadowSlot]"
    )
    for marker in required: assert marker in before,("MISSING_EXACT_ACCEPTED_SOURCE_MARKER",marker)
    # Use the unchanged canonical selection code; only add one safe preemption
    # check to a fully occupied resident set.
    out=one(before,
      "\t\tint residencySlot;\n",
      "\t\tint residencySlot;\n"
      "\t\tqboolean releasedResidentForFire = qfalse; // "+MARK+"\n",
      "PERSISTENT_SET_LOCAL_FLAG")
    anchor=(
      "\t\t\tresidentIndexBySlot[residencySlot] = residentIndex;\n"
      "\t\t}\n\n"
      "\t\twhile (pendingLightsMask && renderedLights < maxShadowLights)")
    replacement=(
      "\t\t\tresidentIndexBySlot[residencySlot] = residentIndex;\n"
      "\t\t}\n\n"
      "\t\t// "+MARK+"\n"
      "\t\t// September 8 scored every eligible shadow source. The later resident-set\n"
      "\t\t// policy pins physical groups first; if all three persistent slots are\n"
      "\t\t// occupied it can silently starve a nearer/brighter native flame.\n"
      "\t\t// Release ONLY the weakest physical resident when a visible, eligible\n"
      "\t\t// PERSISTENT_FIRE challenger beats it by the existing hysteresis margin.\n"
      "\t\t// The subsequent canonical selector still chooses the highest score;\n"
      "\t\t// this code does not directly assign any shadow slot.\n"
      "\t\tif (persistentShadowBudget > 0 && !r_dlightDiagForceSelect->integer)\n"
      "\t\t{\n"
      "\t\t\tint occupied = 0, weakestSlot = -1, candidateIndex;\n"
      "\t\t\tfloat weakestScore = 1.0e30f, bestFireScore = -1.0f;\n"
      "\t\t\tfloat hysteresis = r_dlightShadowHysteresis\n"
      "\t\t\t\t? Com_Clamp(0.25f, 0.75f, r_dlightShadowHysteresis->value) : 0.25f;\n"
      "\t\t\tfor (residencySlot = 0; residencySlot < persistentShadowBudget; ++residencySlot)\n"
      "\t\t\t{\n"
      "\t\t\t\tint residentIndex = residentIndexBySlot[residencySlot];\n"
      "\t\t\t\tfloat score;\n"
      "\t\t\t\tif (residentIndex < 0) continue;\n"
      "\t\t\t\t++occupied;\n"
      "\t\t\t\tscore = R_DarkWolfStaticPromoteShadowGroupSelectionScore(residentIndex, fd);\n"
      "\t\t\t\tif (score < weakestScore)\n"
      "\t\t\t\t{\n"
      "\t\t\t\t\tweakestScore = score;\n"
      "\t\t\t\t\tweakestSlot = residencySlot;\n"
      "\t\t\t\t}\n"
      "\t\t\t}\n"
      "\t\t\tif (occupied == persistentShadowBudget && weakestSlot >= 0)\n"
      "\t\t\t{\n"
      "\t\t\t\tfor (candidateIndex = 0; candidateIndex < tr.refdef.num_dlights &&\n"
      "\t\t\t\t\tcandidateIndex < MAX_DLIGHTS; ++candidateIndex)\n"
      "\t\t\t\t{\n"
      "\t\t\t\t\tconst dlight_t *candidate = &tr.refdef.dlights[candidateIndex];\n"
      "\t\t\t\t\tfloat score;\n"
      "\t\t\t\t\tif (!(visibleLightsMask & (1u << candidateIndex)) ||\n"
      "\t\t\t\t\t\t!(pendingLightsMask & (1u << candidateIndex)) ||\n"
      "\t\t\t\t\t\tcandidate->noDlightShadow ||\n"
      "\t\t\t\t\t\tcandidate->shadowSourceClass != DWSHADOW_SOURCE_PERSISTENT_FIRE)\n"
      "\t\t\t\t\t\tcontinue;\n"
      "\t\t\t\t\tscore = R_DlightShadowSelectionScore(candidate, fd);\n"
      "\t\t\t\t\tif (score > bestFireScore) bestFireScore = score;\n"
      "\t\t\t\t}\n"
      "\t\t\t\tif (bestFireScore > 0.0f && bestFireScore > weakestScore * (1.0f + hysteresis))\n"
      "\t\t\t\t{\n"
      "\t\t\t\t\tresidentIndexBySlot[weakestSlot] = -1;\n"
      "\t\t\t\t\tresidentGroupBySlot[weakestSlot] = -1;\n"
      "\t\t\t\t\treleasedResidentForFire = qtrue;\n"
      "\t\t\t\t}\n"
      "\t\t\t}\n"
      "\t\t}\n\n"
      "\t\twhile (pendingLightsMask && renderedLights < maxShadowLights)")
    out=one(out,anchor,replacement,"WEAK_RESIDENT_PREEMPTION")
    # A displaced historical owner must NOT be restored by hold-frame
    # hysteresis in the newly available persistent slot later in this frame.
    out=one(out,
      "\t\tif (!selectedFromResidentSet\n"
      "\t\t\t&& !tr.refdef.dlights[bestLight].transientBlast",
      "\t\tif (!selectedFromResidentSet\n"
      "\t\t\t&& !(releasedResidentForFire && shadowSlot < persistentShadowBudget)\n"
      "\t\t\t&& !tr.refdef.dlights[bestLight].transientBlast",
      "HISTORY_INVERSION_GUARD")
    assert out!=before
    assert out.count(MARK)>=2
    assert out.count("dynamicShadowBudget = 2;")==1
    assert out.count("r_dlightShadowMaxLights->integer")==before.count("r_dlightShadowMaxLights->integer")
    assert "r_dw" not in out[len(before):]  # no diagnostic knobs added
    file.write_text(out)
    return {
      "marker":MARK,"source_base_run":BASE_RUN,"modified_source_files":[SRC],
      "before_sha256":{SRC:H(before)},"after_sha256":{SRC:H(out)},
      "semantic_fix":"full_persistent_set_visible_fire_priority_inversion",
      "hysteresis":"existing r_dlightShadowHysteresis, clamped to 0.25..0.75",
      "preemption_restrictions":[
        "persistent shadow pool fully resident",
        "candidate source is visible eligible PERSISTENT_FIRE",
        "fire score greater than weakest resident by hysteresis",
        "no forced diagnostic selection",
        "no change to dynamic shadow pool"],
      "untouched":["Sun3","FireE","Local","Sky","CSM","caster geometry",
                   "cubemap format","point-shadow PCF","SSGI","Tesla","StaticPromote direct","lamp group capture"],
      "new_cvars":[],"telemetry":False,"GPU_Crypt1_acceptance":"NOT_YET_TESTED"}
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("source",type=Path)
    ap.add_argument("--proof",type=Path)
    a=ap.parse_args()
    proof=apply(a.source)
    if a.proof:
        a.proof.parent.mkdir(parents=True,exist_ok=True)
        a.proof.write_text(json.dumps(proof,indent=2,ensure_ascii=False)+"\n")
    print("DW_CRYPT1_PERSISTENT_FIRE_SHADOW_PRIORITY_SOURCE_PASS")
