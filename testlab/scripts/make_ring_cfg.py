#!/usr/bin/env python3
import argparse
import json
import math
import re
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("log")
parser.add_argument("scenario")
parser.add_argument("out")
parser.add_argument("--batch-index", type=int, default=0)
parser.add_argument("--batch-count", type=int, default=1)
parser.add_argument("--settle-frames", type=int)
args = parser.parse_args()

log = Path(args.log).read_text(errors="replace")
scenario = json.loads(Path(args.scenario).read_text())
out = Path(args.out)

m = {}
for line in log.splitlines():
    if "TESTLAB_FIXTURE_ORIGIN " not in line:
        continue
    fm = re.search(r"fixture=(-?\d+)", line)
    om = re.search(r"origin=([-+0-9.eE]+),([-+0-9.eE]+),([-+0-9.eE]+)", line)
    if fm and om:
        m[int(fm.group(1))] = tuple(float(om.group(i)) for i in range(1, 4))
if not m:
    raise SystemExit("no fixture origins discovered")

fixture = int(scenario["fixtures"][0]["fixture"])
if fixture not in m:
    raise SystemExit(f"fixture {fixture} origin missing")
if args.batch_count < 1:
    raise SystemExit("batch-count must be >= 1")
if not 0 <= args.batch_index < args.batch_count:
    raise SystemExit("batch-index outside batch-count")

fx, fy, fz = m[fixture]
d = scenario["discovery"]
settle_frames = int(args.settle_frames if args.settle_frames is not None else d["settle_frames"])
if settle_frames < 1:
    raise SystemExit("settle-frames must be >= 1")

positions = []
idx = 0
for vertical_offset in d["vertical_offsets"]:
    for radius in d["ring_radii"]:
        for k in range(d["ring_samples"]):
            a = 2 * math.pi * k / d["ring_samples"]
            x = fx + radius * math.cos(a)
            y = fy + radius * math.sin(a)
            z = fz + vertical_offset
            dx, dy, dzv = fx - x, fy - y, fz - z
            yaw = math.degrees(math.atan2(dy, dx))
            h = math.hypot(dx, dy)
            pitch = -math.degrees(math.atan2(dzv, h))
            positions.append((idx, x, y, z, pitch, yaw))
            idx += 1

total = len(positions)
start = total * args.batch_index // args.batch_count
end = total * (args.batch_index + 1) // args.batch_count
selected = positions[start:end]
if not selected:
    raise SystemExit("selected batch is empty")

first_idx = selected[0][0]
last_idx = selected[-1][0]
lines = [
    "set developer 1",
    "set logfile 2",
    "set r_staticPromoteMaxLights 32",
    "set r_dlightShadowMaxLights 3",
    "set r_staticPromoteUnifiedDiag 1",
    "set r_staticPromoteRootCauseDiag 1",
    f"set r_staticPromoteRootCauseFocus {fixture}",
    "set r_staticPromoteRootCauseSampleMs 100",
    "set r_staticPromotePhysicalGroupDiag 1",
    (
        f"echo TESTLAB_RING_BATCH_BEGIN batch={args.batch_index} "
        f"count={len(selected)} first={first_idx} last={last_idx} settleFrames={settle_frames}"
    ),
]

# DARKWOLF_TESTLAB_TABLE_SHADOW_ISOLATION_V0_1
# Run 59 already proved the complete 128-view continuity ring.  For the next
# diagnostic run only, reuse the final eight capture IDs as a controlled A/B
# at two already-validated guard-room views while keeping the exact 0..127
# capture contract and screenshot names expected by the workflow/analyzer.
+table_isolation = {}
+if fixture == 918 and total == 128 and args.batch_count == 4 and args.batch_index == 3:
+    table_isolation = {
+        120: ("front", 0, (384.0, 416.0, 520.0, 0.0, -90.0)),
+        121: ("front", 1, (384.0, 416.0, 520.0, 0.0, -90.0)),
+        122: ("front", 2, (384.0, 416.0, 520.0, 0.0, -90.0)),
+        123: ("front", 3, (384.0, 416.0, 520.0, 0.0, -90.0)),
+        124: ("side",  0, (608.0, 192.0, 520.0, 0.0, 180.0)),
+        125: ("side",  1, (608.0, 192.0, 520.0, 0.0, 180.0)),
+        126: ("side",  2, (608.0, 192.0, 520.0, 0.0, 180.0)),
+        127: ("side",  3, (608.0, 192.0, 520.0, 0.0, 180.0)),
+    }
+
+for capture_idx, x, y, z, pitch, yaw in selected:
+    table_case = table_isolation.get(capture_idx)
+    if table_case:
+        label, budget, override = table_case
+        x, y, z, pitch, yaw = override
+        lines += [
+            f"set r_dlightShadowMaxLights {budget}",
+            (
+                f"echo TESTLAB_TABLE_PHASE label={label} budget={budget} "
+                f"capture={capture_idx} state=BEGIN"
+            ),
+        ]
+    lines += [
+        f"echo TESTLAB_CAPTURE_BEGIN index={capture_idx}",
+        f"dw_testView {x:.3f} {y:.3f} {z:.3f} {pitch:.3f} {yaw:.3f} 0",
+        f"wait {settle_frames}",
+        f"dw_testViewState {capture_idx}",
+        f"set r_testlabCaptureIndex {capture_idx}",
+        "wait 3",
+        f"echo TESTLAB_CAPTURE_READY index={capture_idx}",
+    ]
+    if table_case:
+        label, budget, _ = table_case
+        lines += [
+            (
+                f"echo TESTLAB_TABLE_PHASE label={label} budget={budget} "
+                f"capture={capture_idx} state=READY"
+            ),
+        ]
+    lines += [
+        f"screenshot testlab_{fixture}_{capture_idx:03d}",
+        "wait 3",
+        f"echo TESTLAB_CAPTURE_DONE index={capture_idx}",
+    ]
+    if table_case:
+        label, budget, _ = table_case
+        lines += [
+            (
+                f"echo TESTLAB_TABLE_PHASE label={label} budget={budget} "
+                f"capture={capture_idx} state=DONE"
+            ),
+        ]
+
+if table_isolation:
+    lines += [
+        "set r_dlightShadowMaxLights 3",
+        "echo TESTLAB_TABLE_ISOLATION_COMPLETE captures=8",
+    ]
+
+lines += [
    (
        f"echo TESTLAB_RING_BATCH_COMPLETE batch={args.batch_index} "
        f"count={len(selected)} first={first_idx} last={last_idx}"
    ),
    "wait 10",
    "quit",
]

out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(lines) + "\n")
print(
    f"generated {len(selected)}/{total} camera captures around fixture {fixture} "
    f"at {m[fixture]} batch={args.batch_index}/{args.batch_count} "
    f"range={first_idx}-{last_idx} settle={settle_frames}"
)
