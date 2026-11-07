#!/usr/bin/env python3
from pathlib import Path
import argparse,json,re,zipfile

ap=argparse.ArgumentParser()
ap.add_argument("retail_main")
ap.add_argument("--out",required=True)
args=ap.parse_args()
retail=Path(args.retail_main)
targets=[
 "textures/castle_wall/castle_grid_c19m",
 "textures/metal_misc/ametal_m03",
 "textures/snow/s_cathedrale_c06",
]
results={t:[] for t in targets}
for pk3 in sorted(retail.glob("*.pk3")):
    try:
        with zipfile.ZipFile(pk3) as z:
            for name in z.namelist():
                if not (name.lower().startswith("scripts/") and name.lower().endswith(".shader")):
                    continue
                text=z.read(name).decode("latin1","replace")
                lines=text.splitlines()
                for ti,t in enumerate(targets):
                    for i,line in enumerate(lines):
                        stripped=line.strip()
                        if stripped.lower()!=t.lower():
                            continue
                        # brace-balanced extract from shader name line.
                        j=i+1
                        while j<len(lines) and "{" not in lines[j]:
                            j+=1
                        if j>=len(lines): continue
                        depth=0; block=[lines[i]]
                        started=False
                        for k in range(j,len(lines)):
                            ln=lines[k]
                            block.append(ln)
                            depth+=ln.count("{")-ln.count("}")
                            if "{" in ln: started=True
                            if started and depth<=0:
                                break
                        results[t].append({
                          "pk3":pk3.name,
                          "script":name,
                          "line":i+1,
                          "block":"\n".join(block)
                        })
    except zipfile.BadZipFile:
        pass
Path(args.out).write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps(results,indent=2))
