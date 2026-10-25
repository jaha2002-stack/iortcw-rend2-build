#!/usr/bin/env python3
"""Exact Sep18 stationary Tesla ET_TESLA_EF behavior; preserve all other October code.
No Tesla CVar is made read-only, and no world-lighting optimization is disabled.
"""
import sys,re,json,hashlib
from pathlib import Path
sept,merged,out=(Path(x).resolve() for x in sys.argv[1:4])
H=lambda s:hashlib.sha256(s.encode()).hexdigest()

def branch(s):
    entry=s.index("static void CG_Efx( centity_t *cent ) {")
    begin=s.index("\tif ( cent->currentState.eType == ET_TESLA_EF ) {",entry)
    end=s.index("\t} else if ( cent->currentState.eType == ET_SPOTLIGHT_EF )",begin)
    return begin,end

def function(s,name):
    m=re.search(r"\\b(?:void|int|qboolean|float)\\s+"+re.escape(name)+r"\\s*\\(",s)
    assert m is not None,name
    pos=s.index("{",m.end())
    depth=0
    for i in range(pos,len(s)):
        if s[i]=="{":depth+=1
        elif s[i]=="}":
            depth-=1
            if depth==0:return s[m.start():i+1]
    raise RuntimeError("Unterminated function "+name)

sept_e=(sept/"SP/code/cgame/cg_ents.c").read_text()
newpath=merged/"SP/code/cgame/cg_ents.c"
new_e=newpath.read_text()
a,b=branch(sept_e)
c,d=branch(new_e)
expected_sha="fc79026dcb8923bada3851bfff09ede941292e17e93a27319d22dba268fd7845"
assert H(sept_e[a:b])==expected_sha,"Sep18 Tesla code block identity drift"
assert H(new_e[c:d])!=expected_sha,"Source already has Sep18 Tesla exact block"
assert "DARKWOLF_UNIFIED_PRODUCTION_TESLA_TIMING_V1" in new_e[c:d]
assert "DARKWOLF_UNIFIED_PRODUCTION_TESLA_TIMING_V1" not in sept_e[a:b]
assert "CG_TeslaHoldDuration" in new_e and "CG_TeslaHoldDuration" not in sept_e
first=new_e[:c]+sept_e[a:b]+new_e[d:]
helper_start=first.index("static int CG_TeslaHoldDuration(")
helper_end=first.index("static void CG_Efx(",helper_start)
# Only remove the historical Oct safety wrapper that did not exist in Sep.
assert first[helper_start:helper_end].count("CG_TeslaHoldDuration")==1
repaired=first[:helper_start]+first[helper_end:]
aa,bb=branch(repaired)
assert H(repaired[aa:bb])==expected_sha
assert "CG_TeslaHoldDuration" not in repaired
assert "DARKWOLF_UNIFIED_PRODUCTION_TESLA_TIMING_V1" not in repaired
assert repaired[bb:]==new_e[d:], "Must preserve all non-Tesla rendering after CG_Efx"
assert repaired[:aa]==new_e[:helper_start]+new_e[helper_end:c], "Must preserve all non-Tesla rendering before CG_Efx"
newpath.write_text(repaired)

# The September Tesla server entity, use toggling, map START_ON semantics
# and source-light electric CVar registrations must remain byte-identical.
proven={}
for rel,names in {
 "SP/code/game/g_misc.c":("use_shooter_tesla","shooter_tesla_finish_spawning","SP_shooter_tesla"),
}.items():
    old=(sept/rel).read_text()
    cur=(merged/rel).read_text()
    for name in names:
        o=function(old,name)
        n=function(cur,name)
        assert o==n,(rel,name,"Oct code changed historic Tesla map entity semantics")
        proven[rel+"::"+name]=H(o)

rel="SP/code/cgame/cg_main.c"
assert (sept/rel).read_bytes()==(merged/rel).read_bytes(),"Electric effect light default/registration unexpectedly changed"
proven[rel+"::complete_source"]=hashlib.sha256((sept/rel).read_bytes()).hexdigest()

# Explicit Tesla source classifications and eligibility are the Sep rules.
for rel in ("SP/code/rend2/tr_main.c","SP/code/rend2/tr_scene.c"):
    o=(sept/rel).read_text()
    n=(merged/rel).read_text()
    def tesla_lines(s):
        return [line.strip() for line in s.splitlines() if
                any(word in line for word in ("DWSHADOW_SOURCE_TESLA_","DARKWOLF_REF_SHADOWSRC_TESLA_","allowTeslaMuzzle"))]
    assert tesla_lines(o)==tesla_lines(n),(rel,"Shadow-source classification drift")
    assert len(tesla_lines(o))>=1
    proven[rel+"::Tesla_shadow_classification"]=H("\n".join(tesla_lines(n)))

# No other SP code file is touched by this parity patch.
out.parent.mkdir(parents=True,exist_ok=True)
manifest={
 "baseline":"user-uploaded verified Sep18 Clean Production v1",
 "baseline_run":35361762179,
 "source_gate":"Exact SHA-verified September Tesla block before and after patch",
 "behavior":"SEPTEMBER_ET_TESLA_EF_CG_EFX_BYTE_IDENTICAL",
 "source_file_changed":"SP/code/cgame/cg_ents.c",
 "september_tesla_branch_sha256":expected_sha,
 "october_tesla_branch_sha256_before":H(new_e[c:d]),
 "clean_tesla_branch_sha256_after":H(repaired[aa:bb]),
 "cg_ents_file_sha_before":H(new_e),"cg_ents_file_sha_after":H(repaired),
 "no_other_cgame_logic_changed":True,
 "game_server_tesla_functions_sha256":proven,
 "removed_later_tesla_changes":[
   "DARKWOLF_UNIFIED_PRODUCTION_TESLA_TIMING_V1: intermittent dlight gating",
   "CG_TeslaHoldDuration: changed bolt hold behavior",
   "per-bolt crawl index and zero-time safety revisions after September"],
 "retained_from_september":[
   "CG_Efx stationary ET_TESLA_EF lightning bolt generation and crawl",
   "continuous enhanced Tesla room-light pulse and electric colors",
   "START_ON / triggered shooter_tesla entity semantics",
   "Electric light radius/intensity CVars and Tesla shadow-source classes"],
 "remaining_graphics":"All accepted FourWeek V03 effects plus Sep color default, no Fire/Tesla architectural containment",
 "not_included":"PCF4, Oct SSGI Fire Receiver V04",
 "real_windows_gpu_parity":"NOT_YET_VERIFIED"
}
out.write_text(json.dumps(manifest,indent=2)+"\n")
print("TESLA_EXACT_SEPTEMBER_STATIONARY_RUNTIME_SOURCE_PARITY_PASS",json.dumps({
    "sha":expected_sha,"verified_server_functions":3,
    "Tesla_classes":2,"changed_files":1}),flush=True)
