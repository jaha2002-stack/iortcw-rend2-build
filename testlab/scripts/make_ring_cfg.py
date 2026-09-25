#!/usr/bin/env python3
import json,math,re,sys
from pathlib import Path

log=Path(sys.argv[1]).read_text(errors="replace")
scenario=json.loads(Path(sys.argv[2]).read_text())
out=Path(sys.argv[3])
m={}
for line in log.splitlines():
    if "TESTLAB_FIXTURE_ORIGIN " not in line: continue
    fm=re.search(r"fixture=(-?\d+)",line); om=re.search(r"origin=([-+0-9.eE]+),([-+0-9.eE]+),([-+0-9.eE]+)",line)
    if fm and om: m[int(fm.group(1))]=tuple(float(om.group(i)) for i in range(1,4))
if not m: raise SystemExit("no fixture origins discovered")
fixture=int(scenario["fixtures"][0]["fixture"])
if fixture not in m: raise SystemExit(f"fixture {fixture} origin missing")
fx,fy,fz=m[fixture]
d=scenario["discovery"]
lines=[
"set developer 1",
"set logfile 2",
"set r_staticPromoteMaxLights 32",
"set r_dlightShadowMaxLights 3",
"set r_staticPromoteUnifiedDiag 1",
"set r_staticPromoteRootCauseDiag 1",
f"set r_staticPromoteRootCauseFocus {fixture}",
"set r_staticPromoteRootCauseSampleMs 100",
"set r_staticPromotePhysicalGroupDiag 1",
]
idx=0
for dz in d["vertical_offsets"]:
  for radius in d["ring_radii"]:
    for k in range(d["ring_samples"]):
      a=2*math.pi*k/d["ring_samples"]
      x=fx+radius*math.cos(a); y=fy+radius*math.sin(a); z=fz+dz
      dx,dy,dzv=fx-x,fy-y,fz-z
      yaw=math.degrees(math.atan2(dy,dx))
      h=math.hypot(dx,dy)
      pitch=-math.degrees(math.atan2(dzv,h))
      lines += [f"dw_testView {x:.3f} {y:.3f} {z:.3f} {pitch:.3f} {yaw:.3f} 0",
                f"wait {int(d['settle_frames'])}",
                f"screenshot testlab_{fixture}_{idx:03d}",
                "wait 3"]
      idx+=1
lines += ["echo TESTLAB_RING_COMPLETE","wait 10","quit"]
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text("\n".join(lines)+"\n")
print(f"generated {idx} camera captures around fixture {fixture} at {m[fixture]}")
