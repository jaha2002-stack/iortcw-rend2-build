#!/usr/bin/env python3
import re, sys, json
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit("usage: analyze_fixture905_toggle.py LOG OUT")

lines=Path(sys.argv[1]).read_text(errors="replace").splitlines()
marker=re.compile(r"TESTLAB_SHADOW_ELIGIBILITY map=escape1 fixture=905 capture=(-?\d+) exclude905=([01])")
direct=re.compile(r"SPR_FIXV1_FRAME map=escape1 entity=905\b.*sourceRoute=promoted\b.*addedDlightIndex=(-?\d+)")
rows=[]
for line in lines:
    m=marker.search(line)
    if m:
        rows.append({"capture":int(m.group(1)),"exclude905":int(m.group(2))})
result={"schema":1,"test":"escape1_fixture905_shadow_toggle","markers":rows,
        "direct905_present":any(direct.search(x) and int(direct.search(x).group(1))>=0 for x in lines)}
Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2))
