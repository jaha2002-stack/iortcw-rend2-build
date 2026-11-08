#!/usr/bin/env python3
from pathlib import Path
import argparse,json,math,re,struct,zipfile
ap=argparse.ArgumentParser(); ap.add_argument("retail_main"); ap.add_argument("--out",required=True)
a=ap.parse_args(); retail=Path(a.retail_main)
bsp=None; src=None
for pk3 in sorted(retail.glob("*.pk3")):
    try:
        with zipfile.ZipFile(pk3) as z:
            if "maps/escape1.bsp" in z.namelist():
                bsp=z.read("maps/escape1.bsp"); src=f"{pk3.name}:maps/escape1.bsp"; break
    except: pass
if bsp is None: raise SystemExit("no bsp")
def lump(i): return struct.unpack_from("<ii",bsp,8+i*8)
o,n=lump(0); txt=bsp[o:o+n].split(b"\0",1)[0].decode("latin1","replace")
ents=[]
for block in re.findall(r"\{(.*?)\}",txt,re.S):
    kv=dict(re.findall(r'"([^"]*)"\s+"([^"]*)"',block))
    if kv: ents.append(kv)
def org(e):
    try:
        v=[float(x) for x in e.get("origin","").split()]; return v[:3] if len(v)>=3 else None
    except: return None
starts=[(i,e,org(e)) for i,e in enumerate(ents) if e.get("classname")=="info_player_start" and org(e)]
if not starts: raise SystemExit("no info_player_start")
si,se,start=starts[0]
def d(p): return math.sqrt(sum((p[k]-start[k])**2 for k in range(3)))
rows=[]
rx=re.compile(r"cage|grate|iron|torture|hang|chain|basket|cell|bar|lamp|light",re.I)
for i,e in enumerate(ents):
    p=org(e)
    if not p: continue
    model=e.get("model",""); cn=e.get("classname",""); tn=e.get("targetname",""); sn=e.get("scriptName","")
    hay=" ".join([cn,model,tn,sn])
    dist=d(p)
    if dist<=1800 or rx.search(hay):
        rows.append({"index":i,"distance":round(dist,1),"origin":p,"classname":cn,"model":model,"targetname":tn,"scriptName":sn,"matched":bool(rx.search(hay))})
rows.sort(key=lambda x:x["distance"])
out={"bsp_source":src,"player_start":{"index":si,"origin":start},"nearby":rows[:350],"matched_anywhere":[r for r in rows if r["matched"]][:250]}
Path(a.out).write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps(out,indent=2))
