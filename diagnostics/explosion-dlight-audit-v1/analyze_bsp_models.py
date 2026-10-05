#!/usr/bin/env python3
import json, struct, sys, zipfile
from pathlib import Path

ROOT=Path(sys.argv[1]); OUT=Path(sys.argv[2]); OUT.mkdir(parents=True,exist_ok=True)
for mapname in ("swf","rocket"):
    found=None
    for pk3 in ROOT.rglob("*.pk3"):
        with zipfile.ZipFile(pk3) as z:
            want=f"maps/{mapname}.bsp"
            names={n.lower():n for n in z.namelist()}
            if want in names:
                found=z.read(names[want]); break
        if found: break
    if not found: raise SystemExit(f"missing {mapname}.bsp")
    # Q3/RTCW BSP lump 7 = models; header = magic+version then 17 (offset,length) pairs.
    mo,ml=struct.unpack_from("<ii",found,8+7*8)
    if ml%40: raise SystemExit(f"bad model lump size {mapname}: {ml}")
    models=[]
    for i in range(ml//40):
        off=mo+i*40
        vals=struct.unpack_from("<6f4i",found,off)
        mins=list(vals[0:3]); maxs=list(vals[3:6])
        models.append({"model":f"*{i}","mins":mins,"maxs":maxs,
                       "center":[(mins[j]+maxs[j])*0.5 for j in range(3)],
                       "firstSurface":vals[6],"numSurfaces":vals[7],"firstBrush":vals[8],"numBrushes":vals[9]})
    ents=json.loads((OUT/f"{mapname}-entities-all.json").read_text())
    by={m["model"]:m for m in models}
    matched=[]
    for e in ents:
        m=e.get("model","")
        if m in by:
            row=dict(e); row["__bsp_model"]=by[m]; matched.append(row)
    (OUT/f"{mapname}-bmodel-entities.json").write_text(json.dumps(matched,indent=2),encoding="utf-8")
    print(mapname, "models",len(models),"matched entities",len(matched))
