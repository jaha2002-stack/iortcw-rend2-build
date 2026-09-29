#!/usr/bin/env python3
import argparse, math, re
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument("log")
p.add_argument("out")
p.add_argument("--settle-frames",type=int,default=45)
args=p.parse_args()

text=Path(args.log).read_text(errors="replace")
origins={}
for line in text.splitlines():
    if "TESTLAB_FIXTURE_ORIGIN " not in line:
        continue
    fm=re.search(r"fixture=(-?\d+)",line)
    om=re.search(r"origin=([-+0-9.eE]+),([-+0-9.eE]+),([-+0-9.eE]+)",line)
    if fm and om:
        origins[int(fm.group(1))]=tuple(float(om.group(i)) for i in range(1,4))

required=(741,742,743,744)
missing=[x for x in required if x not in origins]
if missing:
    raise SystemExit(f"missing historical table fixture origins: {missing}")

a=origins[742]
b=origins[744]
cx=(a[0]+b[0])*0.5
cy=(a[1]+b[1])*0.5
cz=(a[2]+b[2])*0.5
dx=a[0]-b[0]
dy=a[1]-b[1]
dl=math.hypot(dx,dy)
if dl < 1.0:
    raise SystemExit("742/744 XY separation too small")
ux,uy=dx/dl,dy/dl

# Traverse the historical score-crossing axis in both directions. The repeated
# far endpoint gives the selector one settled frame block before the reverse.
offsets=[180,130,80,30,-30,-80,-130,-180,-180,-130,-80,-30,30,80,130,180]
z=cz-64.0
target_z=z-48.0
lines=[
    "set developer 1",
    "set logfile 2",
    "set r_staticPromoteMaxLights 32",
    "set r_dlightShadowMaxLights 3",
    "set r_staticPromoteUnifiedDiag 1",
    "set r_staticPromoteRootCauseDiag 1",
    "set r_staticPromoteRootCauseFocus 742",
    "set r_staticPromoteRootCauseSampleMs 100",
    "set r_staticPromotePhysicalGroupDiag 1",
    "set r_testlabExcludeShadowFixture -1",
    "set cg_draw2D 0",
    "set cg_drawGun 0",
    "echo TESTLAB_TABLE_CLUSTER_BEGIN count=16 focus=742 challenger=744 budget=3 maxLights=32",
]
for i,off in enumerate(offsets):
    x=cx+ux*off
    y=cy+uy*off
    vx=cx-x
    vy=cy-y
    vz=target_z-z
    yaw=math.degrees(math.atan2(vy,vx))
    pitch=-math.degrees(math.atan2(vz,max(1.0,math.hypot(vx,vy))))
    lines += [
        f"echo TESTLAB_TABLE_CAPTURE_BEGIN index={i} offset={off} x={x:.3f} y={y:.3f} z={z:.3f}",
        f"dw_testView {x:.3f} {y:.3f} {z:.3f} {pitch:.3f} {yaw:.3f} 0",
        f"wait {args.settle_frames}",
        f"dw_testViewState {i}",
        f"set r_testlabCaptureIndex {i}",
        "wait 4",
        f"echo TESTLAB_TABLE_CAPTURE_READY index={i}",
        f"screenshot testlab_table_{i:03d}",
        "wait 4",
        f"echo TESTLAB_TABLE_CAPTURE_DONE index={i}",
    ]
lines += [
    "set r_testlabCaptureIndex -1",
    "echo TESTLAB_TABLE_CLUSTER_COMPLETE count=16 focus=742 challenger=744",
    "wait 10",
    "quit",
]
out=Path(args.out)
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text("\n".join(lines)+"\n")
print(f"generated table traversal around historical fixtures 742/744 center=({cx:.3f},{cy:.3f},{cz:.3f})")
