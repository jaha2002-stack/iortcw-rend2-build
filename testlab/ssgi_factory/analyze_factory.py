#!/usr/bin/env python3
import argparse,json,re
from pathlib import Path
from PIL import Image,ImageStat,ImageChops
p=argparse.ArgumentParser()
for v in ("manifest","log","screenshots","out"):p.add_argument("--"+v,type=Path,required=True)
a=p.parse_args()
m=json.loads(a.manifest.read_text());log=a.log.read_text(errors="replace")
names=[v["name"] for v in m["screenshots"]]
files={p.name:p for p in a.screenshots.glob("*.tga")}
missing=sorted(set(names)-set(files))
extra=sorted(set(files)-set(names))
if missing or extra:raise SystemExit(f"CAPTURE_MISMATCH missing={missing[:12]} extra={extra[:12]}")
if "FACTORY_SSGI_REAL_GAMEPLAY_CAPTURE_COMPLETE" not in log:raise SystemExit("NO_COMPLETE_MARKER")
traces=re.findall(r"SSGITRACE[^\n]+",log)
if not traces or not any("reason=active" in row for row in traces):raise SystemExit("SSGI_NEVER_ACTIVE")
# Per-capture case gating: timestamped capture windows must show SSGI active
# in each ON mode and disabled when OFF. The run cannot pass merely because
# one unrelated trace happened earlier in the map.
previous_cut=0
for capture in m["screenshots"]:
 tag=f'FACTORY_CAPTURE_READY view={capture["view"]} case={capture["case"]}'
 # The trace occurs while the mode is settled *before* this marker.
 begin=f'FACTORY_VIEW_BEGIN index={capture["view"]}'
 assert begin in log and tag in log,(begin,tag)
 end=log.index(tag,previous_cut)+len(tag)
 window=log[previous_cut:end]
 previous_cut=end
 case=capture["case"]
 traces_window=re.findall(r"SSGITRACE[^\\n]+",window)
 if case == "off":
  if not any("active=0" in x for x in traces_window):raise SystemExit(f"OFF_TRACE_MISSING view={capture['view']}")
 else:
  if not any("active=1" in x and f"brightfix={3 if case=='experimental' else 2}" in x for x in traces_window):
   raise SystemExit(f"ACTIVE_TRACE_MISSING view={capture['view']} case={case}")
summary={}
for name,f in files.items():
 im=Image.open(f).convert("RGB")
 s=ImageStat.Stat(im)
 summary[name]={"size":im.size,"mean_luma":round(sum(s.mean)/3,3),"variance":round(sum(s.var)/3,3)}
 if min(im.size)<600:raise SystemExit(f"INVALID_RESOLUTION {name}")
byview={}
for shot in m["screenshots"]:
 byview.setdefault(shot["view"],{})[shot["case"]]=shot["name"]
for i,cases in byview.items():
 if set(cases)!={"off","on","requested","bilateral","experimental"}:raise SystemExit(f"MISSING_VIEW_CASES {i}")
 diffs={}
 base=Image.open(files[cases["off"]]).convert("RGB")
 for case in ("on","requested","bilateral","experimental"):
  candidate=Image.open(files[cases[case]]).convert("RGB")
  d=ImageStat.Stat(ImageChops.difference(base,candidate))
  diffs[case]=round(sum(d.mean)/3,3)
 summary[f"view_{i}_comparison"]=diffs
data={"status":"CAPTURE_COMPLETE_PENDING_VISUAL_ACCEPTANCE","notes":"SSGI active confirmed by trace; pixel metrics alone cannot prove lamp artifact resolved.","total":len(names),"views":len(byview),"traces":traces[-16:],"images":summary,"manifest":m}
a.out.write_text(json.dumps(data,indent=2)+"\n")
print("FACTORY_SSGI_CAPTURE_ANALYSIS",data["status"],"shots",len(names),"views",len(byview))
