#!/usr/bin/env python3
from pathlib import Path
import argparse,json,math,re,struct,zipfile

ap=argparse.ArgumentParser()
ap.add_argument("retail_main")
ap.add_argument("--out",required=True)
args=ap.parse_args()
retail=Path(args.retail_main)

bsp=None
source=None
for pk3 in sorted(retail.glob("*.pk3")):
    try:
        with zipfile.ZipFile(pk3) as z:
            if "maps/escape1.bsp" in z.namelist():
                bsp=z.read("maps/escape1.bsp"); source=pk3.name+":maps/escape1.bsp"; break
    except zipfile.BadZipFile:
        pass
if bsp is None: raise SystemExit("escape1.bsp not found")
if bsp[:4]!=b"IBSP": raise SystemExit("not IBSP")
version=struct.unpack_from("<i",bsp,4)[0]

def lump(i):
    return struct.unpack_from("<ii",bsp,8+i*8)

# shaders
off,n=lump(1); shaders=[]
for p in range(off,off+n-71,72):
    name=bsp[p:p+64].split(b"\0",1)[0].decode("latin1","replace")
    sf,cf=struct.unpack_from("<ii",bsp,p+64)
    shaders.append((name,sf,cf))

# planes
off,n=lump(2); planes=[]
for p in range(off,off+n-15,16):
    nx,ny,nz,d=struct.unpack_from("<ffff",bsp,p)
    planes.append(((nx,ny,nz),d))

# nodes
off,n=lump(3); nodes=[]
for p in range(off,off+n-35,36):
    vals=struct.unpack_from("<9i",bsp,p)
    nodes.append({"plane":vals[0],"children":(vals[1],vals[2]),"mins":vals[3:6],"maxs":vals[6:9]})

# leaves
off,n=lump(4); leaves=[]
for p in range(off,off+n-47,48):
    vals=struct.unpack_from("<12i",bsp,p)
    leaves.append({"cluster":vals[0],"area":vals[1],"mins":vals[2:5],"maxs":vals[5:8],"firstLeafSurface":vals[8],"numLeafSurfaces":vals[9],"firstLeafBrush":vals[10],"numLeafBrushes":vals[11]})

# leafbrushes
off,n=lump(6)
leafbrushes=[struct.unpack_from("<i",bsp,p)[0] for p in range(off,off+n-3,4)]

# brushes
off,n=lump(8); brushes=[]
for p in range(off,off+n-11,12):
    fs,ns,sh=struct.unpack_from("<iii",bsp,p)
    brushes.append((fs,ns,sh))

# brush sides
off,n=lump(9); brushsides=[]
for p in range(off,off+n-7,8):
    brushsides.append(struct.unpack_from("<ii",bsp,p))

CONTENTS_SOLID=1

def point_leaf(pt):
    idx=0
    guard=0
    while idx>=0:
        guard+=1
        if guard>10000 or idx>=len(nodes): return None
        nd=nodes[idx]
        pn=nd["plane"]
        if pn<0 or pn>=len(planes): return None
        normal,d=planes[pn]
        v=pt[0]*normal[0]+pt[1]*normal[1]+pt[2]*normal[2]-d
        idx=nd["children"][0 if v>=0 else 1]
    li=-1-idx
    return li if 0<=li<len(leaves) else None

def point_in_brush(pt,bi,eps=0.5):
    if bi<0 or bi>=len(brushes): return False
    first,count,sh=brushes[bi]
    if sh<0 or sh>=len(shaders): return False
    if not (shaders[sh][2] & CONTENTS_SOLID): return False
    for si in range(first,first+count):
        if si<0 or si>=len(brushsides): return False
        pn,_=brushsides[si]
        if pn<0 or pn>=len(planes): return False
        normal,d=planes[pn]
        if pt[0]*normal[0]+pt[1]*normal[1]+pt[2]*normal[2]-d > eps:
            return False
    return True

def point_valid(pt):
    li=point_leaf(pt)
    if li is None: return False
    lf=leaves[li]
    if lf["cluster"]<0: return False
    a=lf["firstLeafBrush"]; b=a+lf["numLeafBrushes"]
    if a<0 or b>len(leafbrushes): return False
    for k in range(a,b):
        if point_in_brush(pt,leafbrushes[k]):
            return False
    return True

def clear_segment(a,b):
    # stop before the target surface itself; reject solid points along 0..0.86
    for i in range(1,22):
        t=0.86*i/22.0
        p=[a[k]+(b[k]-a[k])*t for k in range(3)]
        if not point_valid(p):
            return False
    return True

def yaw_to(a,b):
    return math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))

targets=[
  {"id":"torch_wall","target":[-1600.0,1118.0,186.0],"shader":"textures/castle_wall/castle_grid_c19m","category":"torch"},
  {"id":"torch_flame5000","target":[-1274.1,1337.1,37.2],"shader":"textures/sfx/xflame2_5000","category":"torch"},
  {"id":"guard_metal","target":[-1004.0,750.0,-177.5],"shader":"textures/metal_misc/ametal_m03","category":"guard"},
  {"id":"outdoor_wall","target":[-2088.0,-64.0,1035.2],"shader":"textures/snow/s_cathedrale_c06","category":"outdoor"},
]

# known spawn must be valid as a parser sanity check
spawn=[1808.0,1600.0,-760.0]
spawn_valid=point_valid(spawn)

for t in targets:
    target=t["target"]
    candidates=[]
    for r in (96,128,160,192,224,256,320,384,448,512):
        for deg in range(0,360,30):
            a=math.radians(deg)
            for zoff in (-96,-64,-32,0,32,64,96,128):
                cam=[target[0]+r*math.cos(a),target[1]+r*math.sin(a),target[2]+zoff]
                if not point_valid(cam):
                    continue
                los=clear_segment(cam,target)
                score=(0 if los else 10000)+r+abs(zoff)*0.35
                candidates.append({
                    "camera":[round(x,2) for x in cam],
                    "yaw":round(yaw_to(cam,target),2),
                    "radius":r,
                    "zoff":zoff,
                    "clear_segment":los,
                    "leaf":point_leaf(cam),
                    "score":round(score,2),
                })
    candidates.sort(key=lambda x:x["score"])
    # spatially diverse top candidates
    chosen=[]
    for c in candidates:
        if all(math.dist(c["camera"],q["camera"])>=96 for q in chosen):
            chosen.append(c)
        if len(chosen)>=12: break
    t["candidates"]=chosen
    t["valid_candidate_count"]=len(candidates)

report={"bsp_source":source,"version":version,"spawn_sanity":{"point":spawn,"valid":spawn_valid},"targets":targets}
Path(args.out).write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
if not spawn_valid:
    raise SystemExit("BSP collision parser sanity failed: known player spawn classified invalid")
for t in targets:
    if not t["candidates"]:
        raise SystemExit("no safe camera candidates for "+t["id"])
