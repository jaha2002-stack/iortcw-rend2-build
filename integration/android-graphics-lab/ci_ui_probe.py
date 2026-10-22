#!/usr/bin/env python3
"""Real Android accessibility UI + renderer command tests. Run after scene smoke."""
from __future__ import annotations
import re
import sys
import time
from pathlib import Path
import xml.etree.ElementTree as ET
import ci_scene_driver as drv

BOUNDS = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")

def nodes(xml, name, prefix=False):
    return [n for n in ET.fromstring(xml).iter("node")
            if (n.get("text", "").startswith(name) if prefix
                else n.get("text", "") == name)]

def center(n):
    b=BOUNDS.fullmatch(n.get("bounds",""))
    if not b: raise RuntimeError("UI element lacks bounds: "+repr(n.attrib))
    x0,y0,x1,y1=map(int,b.groups())
    if x0>=x1 or y0>=y1: raise RuntimeError("Invalid UI hit rectangle")
    return (x0+x1)//2,(y0+y1)//2

def await_node(out,name,prefix=False):
    for i in range(9):
        xml=drv.xml_dump(out,300+i)
        items=nodes(xml,name,prefix)
        if items: return items[0]
        time.sleep(1)
    raise RuntimeError("Android UI node unavailable: "+name)

def tap(out,name,prefix=False):
    x,y=center(await_node(out,name,prefix))
    drv.adb("shell","input","tap",str(x),str(y),timeout=12)
    time.sleep(1)
    print("LAB_UI_TAP="+name,flush=True)

def textinput(out,value):
    xml=drv.xml_dump(out,400)
    edits=[n for n in ET.fromstring(xml).iter("node")
           if n.get("class")=="android.widget.EditText"]
    if len(edits)!=1:
        raise RuntimeError("Expected one text field; found %d"%len(edits))
    x,y=center(edits[0])
    drv.adb("shell","input","tap",str(x),str(y))
    drv.adb("shell","input","text",value,timeout=12)

def await_log(out,needle,min_count=1,seconds=120):
    start=time.monotonic()
    while time.monotonic()-start<seconds:
        s=drv.logcat(out)
        if s.count(needle)>=min_count:
            print("LAB_ENGINE_EVENT="+needle,flush=True)
            return
        time.sleep(2)
    raise RuntimeError("Missing engine event: "+needle)

def record(out,value):
    print(value,flush=True)
    with (out/"ui-functional-audit.txt").open("a") as f:f.write(value+"\n")

def main(out):
    out.mkdir(parents=True,exist_ok=True)
    (out/"ui-functional-status.txt").write_text("FUNCTIONAL_UI=NOT_RUN\n")
    if not (out/"retail-frame.png").is_file():
        raise RuntimeError("Capture the game world before testing its controls")
    drv.current_game_pid()
    tap(out,"GRAPHICS LAB")
    xml=drv.xml_dump(out,250)
    mandatory=["MAP: open any map","CAMERA: free camera (noclip)",
               "ZOOM IN","ZOOM OUT","FULL NATIVE RESOLUTION",
               "ALL CVARS: search & inspect"]
    if any(not nodes(xml,t) for t in mandatory):
        raise RuntimeError("Graphics Lab menu missing one of its core actions")
    record(out,"GRAPHICS_LAB_MENU=PASS")
    tap(out,"ALL CVARS: search & inspect")
    heading=await_node(out,"Runtime CVar catalog (",True).get("text","")
    match=re.fullmatch(r"Runtime CVar catalog \((\d+)\)",heading)
    if not match or int(match.group(1))<100:
        raise RuntimeError("Catalog missing engine Cvars: "+heading)
    record(out,"GRAPHICS_LAB_CVAR_CATALOG=PASS count="+match.group(1))
    textinput(out,"r_dwCas")
    tap(out,"SEARCH")
    item=await_node(out,"r_dwCas =",True)
    if not item.get("text","").endswith("1"):
        raise RuntimeError("CAS effect not enabled: "+item.get("text",""))
    record(out,"GRAPHICS_LAB_CAS_CVAR=PASS")
    drv.adb("shell","input","keyevent","4")
    time.sleep(1)
    tap(out,"GRAPHICS LAB")
    tap(out,"ZOOM IN")
    await_log(out,"GRAPHICS_LAB_CMD_DISPATCH=cg_fov 50",seconds=45)
    record(out,"GRAPHICS_LAB_ZOOM=PASS")
    tap(out,"GRAPHICS LAB")
    tap(out,"CAMERA: free camera (noclip)")
    await_log(out,"GRAPHICS_LAB_CMD_DISPATCH=noclip",seconds=45)
    record(out,"GRAPHICS_LAB_FREE_CAMERA=PASS")
    first=drv.logcat(out).count("DARKWOLF_ANDROID_UI_BRIEFING_AUTOSTART=PASS")
    tap(out,"GRAPHICS LAB")
    tap(out,"MAP: open any map")
    textinput(out,"crypt1")
    tap(out,"LOAD")
    await_log(out,"GRAPHICS_LAB_CMD_DISPATCH=spdevmap crypt1",seconds=60)
    await_log(out,"DARKWOLF_ANDROID_UI_BRIEFING_AUTOSTART=PASS",first+1,seconds=150)
    drv.current_game_pid()
    record(out,"GRAPHICS_LAB_CRYPT1_MAP_SWITCH=PASS")
    if any(term in drv.logcat(out) for term in drv.FATAL):
        raise RuntimeError("Game fatal after map switch")
    (out/"ui-functional-status.txt").write_text(
        "FUNCTIONAL_UI=PASS\nCVARS=PASS\nZOOM=PASS\n"
        "FREE_CAMERA_JNI=PASS\nCRYPT1_SWITCH=PASS\n")

def selftest():
    data=('<hierarchy><node text="GRAPHICS LAB" bounds="[470,0][640,68]"/>'
          '<node text="r_dwCas = 1" bounds="[22,55][615,99]"/></hierarchy>')
    assert center(nodes(data,"GRAPHICS LAB")[0])==(555,34)
    assert nodes(data,"r_dwCas =",True)[0].get("text")=="r_dwCas = 1"
    assert not nodes(data,"MAP: open any map")
    print("GRAPHICS_LAB_UI_PROBE_SELFTEST=PASS",flush=True)

if __name__=="__main__":
    if len(sys.argv)==2 and sys.argv[1]=="--selftest":selftest()
    elif len(sys.argv)==2:
        p=Path(sys.argv[1]);p.mkdir(parents=True,exist_ok=True)
        try:main(p)
        except Exception as e:
            (p/"ui-functional-status.txt").write_text("FUNCTIONAL_UI=FAIL\nREASON=%s\n"%e)
            print("GRAPHICS_LAB_UI_PROBE_FAILED: %s"%e,file=sys.stderr,flush=True)
            raise SystemExit(1)
    else:raise SystemExit("usage: ci_ui_probe.py --selftest | <out>")
