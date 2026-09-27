#!/usr/bin/env python3
import json,re,sys
from pathlib import Path

log=Path(sys.argv[1])
scenario=Path(sys.argv[2])
out=Path(sys.argv[3])
cfg=json.loads(scenario.read_text())
text=log.read_text(errors="replace") if log.exists() else ""

kv_re=re.compile(r"(\w+)=([^\s]+)")
front=[]
shadow=[]
origins={}
for line in text.splitlines():
    if "TESTLAB_FIXTURE_ORIGIN " in line:
        kv=dict(kv_re.findall(line))
        try:
            origins[int(kv["fixture"])]=[float(x) for x in kv["origin"].split(",")]
        except Exception: pass
    if "TESTLAB_RUNTIME_FRAME " in line:
        kv=dict(kv_re.findall(line)); front.append(kv)
    if "USLRD_SHADOW_GROUP " in line:
        kv=dict(kv_re.findall(line)); shadow.append(kv)

fixtures=[int(x["fixture"]) for x in cfg["fixtures"]]
result={"schema":1,"scenario":cfg["id"],"fixtures":{},"shadow_records":len(shadow),"status":"FAIL","failures":[]}
for fixture in fixtures:
    rows=[r for r in front if int(r.get("fixture","-999"))==fixture]
    direct=any(int(r.get("addedDlightIndex","-1")) >= 0 for r in rows)
    resident=any(
        int(r.get("selectedSlot","-1")) >= 0 or
        r.get("unifiedResident","0") == "1" or
        r.get("held","0") == "1"
        for r in rows
    )
    expected=next((x for x in cfg["fixtures"] if int(x["fixture"])==fixture),{})
    result["fixtures"][str(fixture)]={
        "records":len(rows),
        "origin":origins.get(fixture),
        "direct_seen":direct,
        "resident_seen":resident,
        "physical_seen":any(r.get("physical","0")=="1" for r in rows),
        "max_selected_count":max([int(r.get("selectedCount","0")) for r in rows] or [0]),
        "max_active_count":max([int(r.get("activeCount","0")) for r in rows] or [0])
    }
    if not rows:
        result["failures"].append(f"fixture {fixture}: no TESTLAB_RUNTIME_FRAME telemetry")
    if expected.get("require_direct", False) and not direct:
        result["failures"].append(f"fixture {fixture}: direct light never observed")
    if expected.get("require_resident", False) and not resident:
        result["failures"].append(f"fixture {fixture}: residency never observed")
    for r in rows:
        if int(r.get("maxLights","-1")) != int(cfg["assertions"].get("max_static_promote_lights",32)):
            result["failures"].append(f"fixture {fixture}: runtime maxLights contract mismatch")
            break
        if int(r.get("selectedCount","0")) > int(cfg["assertions"].get("max_static_promote_lights",32)):
            result["failures"].append(f"fixture {fixture}: selectedCount exceeded StaticPromote budget")
            break

badslots=[]
for r in shadow:
    try:
        slot=int(r.get("slot","-1"))
        if slot<0 or slot>=int(cfg["assertions"]["max_shadow_slot_exclusive"]):
            badslots.append(slot)
    except Exception: pass
if badslots:
    result["failures"].append(f"persistent StaticPromote shadow slot outside 0..{cfg['assertions']['max_shadow_slot_exclusive']-1}: {sorted(set(badslots))}")

if not result["failures"]: result["status"]="PASS"
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print(json.dumps(result,indent=2,sort_keys=True))
raise SystemExit(0 if result["status"]=="PASS" else 2)
