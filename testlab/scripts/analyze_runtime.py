#!/usr/bin/env python3
import json,math,re,sys
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
view_states={}
render_views={}
render_re=re.compile(
    r"TESTLAB_RENDER_VIEW index=(\d+) "
    r"origin=([-+0-9.eE]+),([-+0-9.eE]+),([-+0-9.eE]+) "
    r"forward=([-+0-9.eE]+),([-+0-9.eE]+),([-+0-9.eE]+) "
    r"rdflags=(-?\d+)"
)
state_re=re.compile(
    r"TESTLAB_VIEW_STATE index=(\d+) "
    r"origin=([-+0-9.eE]+),([-+0-9.eE]+),([-+0-9.eE]+) "
    r"angles=([-+0-9.eE]+),([-+0-9.eE]+),([-+0-9.eE]+) "
    r"velocity=([-+0-9.eE]+),([-+0-9.eE]+),([-+0-9.eE]+) "
    r"noclip=(\d+) pmNoClip=(\d+)"
)
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
    sm=state_re.search(line)
    if sm:
        idx=int(sm.group(1))
        row={
            "origin":[float(sm.group(i)) for i in range(2,5)],
            "angles":[float(sm.group(i)) for i in range(5,8)],
            "velocity":[float(sm.group(i)) for i in range(8,11)],
            "noclip":int(sm.group(11)),
            "pmNoClip":int(sm.group(12)),
        }
        view_states.setdefault(idx,[]).append(row)
    rm=render_re.search(line)
    if rm:
        idx=int(rm.group(1))
        row={
            "origin":[float(rm.group(i)) for i in range(2,5)],
            "forward":[float(rm.group(i)) for i in range(5,8)],
            "rdflags":int(rm.group(8)),
        }
        render_views.setdefault(idx,[]).append(row)

# Correlate runtime telemetry with each deterministic capture window so the
# analyzer can detect transient direct-light/residency drops instead of only
# proving that a fixture was seen at least once somewhere in the run.
capture_runtime={}
current_capture=None
suppressed_startcams=0
for line in text.splitlines():
    if "TESTLAB_STARTCAM_SUPPRESSED " in line:
        suppressed_startcams+=1
    bm=re.search(r"TESTLAB_CAPTURE_BEGIN index=(\d+)",line)
    if bm:
        current_capture=int(bm.group(1))
        capture_runtime.setdefault(current_capture,[])
        continue
    if current_capture is not None and "TESTLAB_RUNTIME_FRAME " in line:
        capture_runtime.setdefault(current_capture,[]).append(dict(kv_re.findall(line)))
    dm=re.search(r"TESTLAB_CAPTURE_DONE index=(\d+)",line)
    if dm and current_capture==int(dm.group(1)):
        current_capture=None

d=cfg["discovery"]
capture_expected=len(d["vertical_offsets"])*len(d["ring_radii"])*int(d["ring_samples"])

fixtures=[int(x["fixture"]) for x in cfg["fixtures"]]
result={"schema":1,"scenario":cfg["id"],"fixtures":{},"shadow_records":len(shadow),"camera_validation":{},"status":"FAIL","failures":[]}
result["camera_takeover_suppression"]={"suppressed_startcam_count":suppressed_startcams}
if cfg["assertions"].get("require_startcam_suppression_exercised",False) and suppressed_startcams<=0:
    result["failures"].append("scripted startCam suppression was not exercised")

# Deterministic camera contract: every capture index must report a server-side
# noclip view state matching the exact ring geometry that generated its CFG.
focus_fixture=fixtures[0]
focus_origin=origins.get(focus_fixture)
expected_cameras={}
if focus_origin is None:
    result["failures"].append(f"fixture {focus_fixture}: origin unavailable for camera validation")
else:
    fx,fy,fz=focus_origin
    d=cfg["discovery"]
    idx=0
    for vertical_offset in d["vertical_offsets"]:
        for radius in d["ring_radii"]:
            for k in range(d["ring_samples"]):
                a=2*math.pi*k/d["ring_samples"]
                x=fx+radius*math.cos(a); y=fy+radius*math.sin(a); z=fz+vertical_offset
                dx,dy,dzv=fx-x,fy-y,fz-z
                yaw=math.degrees(math.atan2(dy,dx))
                h=math.hypot(dx,dy)
                pitch=-math.degrees(math.atan2(dzv,h))
                expected_cameras[idx]={
                    "origin":[round(x,3),round(y,3),round(z,3)],
                    "angles":[round(pitch,3),round(yaw,3),0.0],
                }
                idx+=1

def angle_error(a,b):
    return abs((a-b+180.0)%360.0-180.0)

camera_bad=[]
camera_missing=[]
camera_duplicate_conflicts=[]
for idx in range(capture_expected):
    rows=view_states.get(idx,[])
    if not rows:
        camera_missing.append(idx)
        continue
    first=rows[0]
    for other in rows[1:]:
        if other != first:
            camera_duplicate_conflicts.append(idx)
            break
    exp=expected_cameras.get(idx)
    if exp is None:
        camera_bad.append({"index":idx,"reason":"expected camera unavailable"})
        continue
    origin_err=max(abs(first["origin"][i]-exp["origin"][i]) for i in range(3))
    angle_err=max(angle_error(first["angles"][i],exp["angles"][i]) for i in range(3))
    velocity_mag=math.sqrt(sum(v*v for v in first["velocity"]))
    if origin_err > 0.05 or angle_err > 0.10 or velocity_mag > 0.05 or first["noclip"] != 1 or first["pmNoClip"] != 1:
        camera_bad.append({
            "index":idx,
            "origin_error":origin_err,
            "angle_error":angle_err,
            "velocity":velocity_mag,
            "noclip":first["noclip"],
            "pmNoClip":first["pmNoClip"],
            "actual":first,
            "expected":exp,
        })

result["camera_validation"]={
    "expected":capture_expected,
    "unique_indices":len(view_states),
    "missing_indices":camera_missing,
    "duplicate_conflicts":sorted(set(camera_duplicate_conflicts)),
    "invalid_count":len(camera_bad),
    "invalid_samples":camera_bad[:8],
}
if camera_missing:
    result["failures"].append(f"camera state missing for indices: {camera_missing[:16]}")
if camera_duplicate_conflicts:
    result["failures"].append(f"camera state duplicate conflict for indices: {sorted(set(camera_duplicate_conflicts))[:16]}")
if camera_bad:
    result["failures"].append(f"camera state mismatch for {len(camera_bad)} captures")

# Renderer-authoritative camera contract. The final refdef may include normal
# first-person eye/bob offsets, so validate proximity to the requested player origin
# and that the renderer forward vector still points at fixture 918.
render_bad=[]
render_missing=[]
render_duplicate_conflicts=[]
for idx in range(capture_expected):
    rows=render_views.get(idx,[])
    if not rows:
        render_missing.append(idx)
        continue
    first=rows[0]
    for other in rows[1:]:
        if other != first:
            render_duplicate_conflicts.append(idx)
            break
    exp=expected_cameras.get(idx)
    if exp is None or focus_origin is None:
        render_bad.append({"index":idx,"reason":"expected render camera unavailable"})
        continue
    delta=[first["origin"][i]-exp["origin"][i] for i in range(3)]
    origin_distance=math.sqrt(sum(v*v for v in delta))
    to_fixture=[focus_origin[i]-first["origin"][i] for i in range(3)]
    to_len=math.sqrt(sum(v*v for v in to_fixture))
    fwd=first["forward"]
    fwd_len=math.sqrt(sum(v*v for v in fwd))
    forward_dot=-1.0
    if to_len > 0.0001 and fwd_len > 0.0001:
        forward_dot=sum((to_fixture[i]/to_len)*(fwd[i]/fwd_len) for i in range(3))
    if origin_distance > 96.0 or forward_dot < 0.90:
        render_bad.append({
            "index":idx,
            "origin_distance":origin_distance,
            "forward_dot":forward_dot,
            "actual":first,
            "expected_player_origin":exp["origin"],
        })

result["render_camera_validation"]={
    "expected":capture_expected,
    "unique_indices":len(render_views),
    "missing_indices":render_missing,
    "duplicate_conflicts":sorted(set(render_duplicate_conflicts)),
    "invalid_count":len(render_bad),
    "invalid_samples":render_bad[:8],
}
if render_missing:
    result["failures"].append(f"renderer camera missing for indices: {render_missing[:16]}")
if render_duplicate_conflicts:
    result["failures"].append(f"renderer camera duplicate conflict for indices: {sorted(set(render_duplicate_conflicts))[:16]}")
if render_bad:
    result["failures"].append(f"renderer camera mismatch for {len(render_bad)} captures")

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
    per_capture={
        idx:[r for r in capture_runtime.get(idx,[]) if int(r.get("fixture","-999"))==fixture]
        for idx in range(capture_expected)
    }
    missing_capture_rows=[idx for idx,caprows in per_capture.items() if not caprows]
    direct_drop_captures=[
        idx for idx,caprows in per_capture.items()
        if caprows and any(int(r.get("addedDlightIndex","-1"))<0 for r in caprows)
    ]
    residency_drop_captures=[
        idx for idx,caprows in per_capture.items()
        if caprows and any(
            int(r.get("selectedSlot","-1"))<0 and
            r.get("unifiedResident","0")!="1" and
            r.get("held","0")!="1"
            for r in caprows
        )
    ]
    direct_drop_records=sum(
        1 for caprows in per_capture.values() for r in caprows
        if int(r.get("addedDlightIndex","-1"))<0
    )
    residency_drop_records=sum(
        1 for caprows in per_capture.values() for r in caprows
        if int(r.get("selectedSlot","-1"))<0 and
           r.get("unifiedResident","0")!="1" and
           r.get("held","0")!="1"
    )
    selected_slot_values=sorted({
        int(r.get("selectedSlot","-1"))
        for caprows in per_capture.values() for r in caprows
    })
    result["fixtures"][str(fixture)]={
        "records":len(rows),
        "origin":origins.get(fixture),
        "direct_seen":direct,
        "resident_seen":resident,
        "physical_seen":any(r.get("physical","0")=="1" for r in rows),
        "max_selected_count":max([int(r.get("selectedCount","0")) for r in rows] or [0]),
        "max_active_count":max([int(r.get("activeCount","0")) for r in rows] or [0]),
        "capture_coverage":capture_expected-len(missing_capture_rows),
        "captures_without_runtime":missing_capture_rows,
        "captures_with_direct_drop":direct_drop_captures,
        "captures_with_residency_drop":residency_drop_captures,
        "direct_drop_records":direct_drop_records,
        "residency_drop_records":residency_drop_records,
        "selected_slot_values":selected_slot_values
    }
    if not rows:
        result["failures"].append(f"fixture {fixture}: no TESTLAB_RUNTIME_FRAME telemetry")
    if expected.get("require_direct", False) and not direct:
        result["failures"].append(f"fixture {fixture}: direct light never observed")
    if expected.get("require_resident", False) and not resident:
        result["failures"].append(f"fixture {fixture}: residency never observed")
    if expected.get("require_direct_every_capture",False):
        if missing_capture_rows:
            result["failures"].append(f"fixture {fixture}: runtime telemetry missing in captures {missing_capture_rows[:16]}")
        if direct_drop_captures:
            result["failures"].append(f"fixture {fixture}: transient direct-light drop in captures {direct_drop_captures[:16]}")
    if expected.get("require_resident_every_capture",False):
        if missing_capture_rows:
            result["failures"].append(f"fixture {fixture}: residency telemetry missing in captures {missing_capture_rows[:16]}")
        if residency_drop_captures:
            result["failures"].append(f"fixture {fixture}: transient residency drop in captures {residency_drop_captures[:16]}")
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
