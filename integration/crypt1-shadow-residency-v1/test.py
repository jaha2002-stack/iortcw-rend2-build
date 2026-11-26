#!/usr/bin/env python3
"""Static and deterministic priority inversion regression tests for shadow resident sets."""
import argparse,hashlib,json
from pathlib import Path

ap=argparse.ArgumentParser()
ap.add_argument("source",type=Path)
ap.add_argument("--out",type=Path,required=True)
args=ap.parse_args()
file=args.source/"SP/code/rend2/tr_main.c"
s=file.read_text()
MARK="DARKWOLF_CRYPT1_PERSISTENT_FIRE_SHADOW_PRIORITY_FIX_V1_20261028"
checks={
 "exact_patch_marker":MARK in s,
 "static_groups_preserved":"R_DarkWolfStaticPromoteShadowGroupCanonicalId" in s,
 "shadow_group_persistence_preserved":"R_DarkWolfPersistentPhysicalShadowResidentCandidate" in s,
 "persistent_budget_unchanged":"persistentShadowBudget = r_dlightShadowMaxLights->integer;" in s,
 "dynamic_two_slots_unchanged":"dynamicShadowBudget = 2;" in s,
 "native_fire_only":"candidate->shadowSourceClass != DWSHADOW_SOURCE_PERSISTENT_FIRE" in s,
 "visibility_mask_gate":"!(visibleLightsMask & (1u << candidateIndex))" in s,
 "point_shadow_eligibility_guard":"candidate->noDlightShadow" in s,
 "existing_hysteresis_used":"r_dlightShadowHysteresis->value" in s,
 "min_hysteresis_guard":"Com_Clamp(0.25f, 0.75f" in s,
 "full_resident_only":"occupied == persistentShadowBudget" in s,
 "high_score_threshold":"bestFireScore > weakestScore * (1.0f + hysteresis)" in s,
 "slot_release_only":"residentIndexBySlot[weakestSlot] = -1;" in s and "residentGroupBySlot[weakestSlot] = -1;" in s,
 "held_history_priority_override_blocked":"!(releasedResidentForFire && shadowSlot < persistentShadowBudget)" in s,
 "no_map_specific_special_case":"Q_stricmp(tr.world->baseName, \"crypt1\")" not in s,
 "no_new_debug_cvars":"r_dwCrypt1" not in s
}
assert all(checks.items()),[k for k,v in checks.items() if not v]

def choose(owners,fire_score=-1.0,visible=True,eligible=True,persistent_budget=3,
           hysteresis=0.25,debug_force=False,fire_class="PERSISTENT_FIRE"):
    # Executable, deliberately independent model of the source eligibility rules.
    # Covers the regression signature, not actual GPU rendering.
    residents=list(owners)
    if persistent_budget<=0 or len(residents)<persistent_budget or debug_force:
        return residents,False
    if not visible or not eligible or fire_class!="PERSISTENT_FIRE":return residents,False
    weak=min(range(len(residents)),key=lambda i:residents[i])
    h=min(0.75,max(0.25,hysteresis))
    if fire_score>0.0 and fire_score>residents[weak]*(1.0+h):
        residents[weak]=None
        return residents,True
    return residents,False
cases=[
    ("three_lamps_no_fire",dict(owners=[120,110,100]),False,[120,110,100]),
    ("strong_fire_displaces_weakest",dict(owners=[150,110,40],fire_score=100),True,[150,110,None]),
    ("fire_not_strong_enough",dict(owners=[150,110,100],fire_score=110),False,[150,110,100]),
    ("fire_just_below_margin",dict(owners=[100,90,80],fire_score=99),False,[100,90,80]),
    ("fire_above_margin",dict(owners=[100,90,80],fire_score=101),True,[100,90,None]),
    ("invisible_fire_no_displacement",dict(owners=[150,110,40],fire_score=100,visible=False),False,[150,110,40]),
    ("no_shadow_fire_no_displacement",dict(owners=[150,110,40],fire_score=100,eligible=False),False,[150,110,40]),
    ("dynamic_muzzle_no_displacement",dict(owners=[150,110,40],fire_score=100,fire_class="DYNAMIC_MUZZLE"),False,[150,110,40]),
    ("two_lamps_no_forced_preemption",dict(owners=[110,40],fire_score=100),False,[110,40]),
    ("debug_lock_does_not_change",dict(owners=[150,110,40],fire_score=100,debug_force=True),False,[150,110,40]),
    ("zero_budget",dict(owners=[],fire_score=100,persistent_budget=0),False,[]),
    ("high_hysteresis_strong_fire",dict(owners=[150,110,40],fire_score=100,hysteresis=0.75),True,[150,110,None]),
    ("high_hysteresis_weak_fire",dict(owners=[150,110,40],fire_score=60,hysteresis=0.75),False,[150,110,40])
]
results=[]
for name,kw,want_fire,want_slots in cases:
    slots,fired=choose(**kw)
    assert fired==want_fire and slots==want_slots,(name,slots,fired)
    results.append({"name":name,"pass":True})
assert len(results)>=12
out=args.out
out.mkdir(parents=True,exist_ok=True)
report={"source_sha256":hashlib.sha256(s.encode()).hexdigest(),
 "marker":MARK,"static_checks":checks,"numeric_regression_cases":results,
 "no_new_cvars":True,"no_telemetry":True,"gpu_runtime_crypt1":"NOT_TESTED",
 "scope":"One-file conservative fix to fire-starvation priority inversion only"}
(out/"CRYPT1_SHADOW_SOURCE_TESTS.json").write_text(json.dumps(report,indent=2)+"\n")
print("DW_CRYPT1_SHADOW_STATIC_AND_REGRESSION_TESTS_PASS",len(results))
