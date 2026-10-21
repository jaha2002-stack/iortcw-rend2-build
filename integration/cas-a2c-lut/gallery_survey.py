#!/usr/bin/env python3
"""Read protected RTCW map data in CI and export camera planning metadata only.
Never copy retail BSP/PK3 into artifacts.
"""
import json, sys, zipfile, collections, re
from pathlib import Path
sys.path.insert(0,str(Path("testlab/scripts").resolve()))
from rc4_assault_camera import World

targets=("factory","escape1","assault","crypt1","church","boss1","swf","crypt2","village1","forest")
markers=("torch","fire","flame","candle","lamp","light","burn","brazier","stove","furnace","gate","iron","door","grate","fence","grill","radar","tower","church")
retail=Path(sys.argv[1]);output=Path(sys.argv[2]);out={}
for mapname in targets:
    bsp=None
    for pk3 in retail.glob("*.pk3"):
        with zipfile.ZipFile(pk3) as z:
            key=next((n for n in z.namelist() if n.lower()==f"maps/{mapname}.bsp"),None)
            if key:bsp=z.read(key);break
    if not bsp:
        out[mapname]={"present":False};continue
    w=World(bsp)
    classes=collections.Counter(e.get("classname","<none>") for e in w.entities)
    candidates=[]
    for idx,e in enumerate(w.entities):
        joined=" ".join(str(v) for k,v in e.items() if k not in ("message","scriptname")).lower()
        kind=e.get("classname","")
        if not any(p in joined for p in markers) and kind not in ("info_player_start","light","func_door","func_static","misc_model","func_explosive","script_mover"):
            continue
        if kind=="light" and len(candidates)>90:continue
        candidates.append({"id":idx,"classname":kind,"origin":e.get("origin"),"model":e.get("model"),
                           "targetname":e.get("targetname"),"scriptName":e.get("scriptName",e.get("scriptname")),
                           "spawnflags":e.get("spawnflags"),
                           "hint":next((p for p in markers if p in joined),None)})
    matched_materials=[]
    for shader,flags,contents in w.shaders:
        name=shader.split(b"\\0")[0].decode("latin1","replace")
        if any(p in name.lower() for p in markers):
            matched_materials.append(name)
    out[mapname]={"present":True,"entity_count":len(w.entities),"bounds":list(w.bounds),
                  "classes":classes.most_common(30),
                  "candidates":candidates[:120],
                  "matched_materials":matched_materials[:100]}
    print(mapname,"entities",len(w.entities),"targets",len(candidates),"materials",len(matched_materials),flush=True)
output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\\n")
print("SURVEY_COMPLETE",sum(bool(x.get("present")) for x in out.values()),flush=True)
