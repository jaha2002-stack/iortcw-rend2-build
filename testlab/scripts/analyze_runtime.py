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
    if "USLRD_RC_FRONT " in line:
        kv=dict(kv_re.findall(line)); front.append(kv)
    if "USLRD_SHADOW_GROUP " in line:
        kv=dict(kv_re.findall(line)); shadow.append(kv)

fixtures=[int(x["fixture"]) for x in cfg["fixtures"]]
result={"schema":1,"scenario":cfg["id"],"fixtures":{},"shadow_records":len(shadow),"status":"FAIL","failures":[]}
for fixture in fixtures:
    rows=[r for r in front if int(r.get("fixture","-999"))==fixture]
    direct=any(r.get("directPresent")=="1" for r in rows)
    resident=any(r.get("resident")=="1" for r in rows)
    result["fixtures"][str(fixture)]={"records":len(rows),"origin":origins.get(fixture),"direct_seen":direct,"resident_seen":resident}
    if not rows: result["failures"].append(f"fixture {fixture}: no USLRD_RC_FRONT telemetry")
    if cfg["assertions"].get("require_direct_light_somewhere") and not direct:
        result["failures"].append(f"fixture {fixture}: direct light never observed")
    if cfg["assertions"].get("require_resident_somewhere") and not resident:
        result["failures"].append(f"fixture {fixture}: residency never observed")

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
