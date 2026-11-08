#!/usr/bin/env python3
from pathlib import Path
import argparse, json, math, re, struct, zipfile

ap=argparse.ArgumentParser()
ap.add_argument("retail_main")
ap.add_argument("--out",required=True)
ap.add_argument("--cfg",required=True)
args=ap.parse_args()

retail=Path(args.retail_main)
bsp=None; source=None
for pk3 in sorted(retail.glob("*.pk3")):
    try:
        with zipfile.ZipFile(pk3) as z:
            names={n.lower():n for n in z.namelist()}
            if "maps/escape1.bsp" in names:
                real=names["maps/escape1.bsp"]
                bsp=z.read(real); source=f"{pk3.name}:{real}"
                break
    except zipfile.BadZipFile:
        pass
if bsp is None: raise SystemExit("maps/escape1.bsp not found")
if bsp[:4]!=b"IBSP": raise SystemExit("bad BSP magic")

def lump(i): return struct.unpack_from("<ii",bsp,8+i*8)

# shaders
off,n=lump(1)
shaders=[]
for p in range(off,off+n-72+1,72):
    name=bsp[p:p+64].split(b"\0",1)[0].decode("latin1","replace").replace("\\","/")
    sf,cf=struct.unpack_from("<ii",bsp,p+64)
    shaders.append((name,sf,cf))

# drawverts
off,n=lump(10)
verts=[struct.unpack_from("<fff",bsp,p) for p in range(off,off+n-44+1,44)]

# drawindexes
off,n=lump(11)
idx=[struct.unpack_from("<i",bsp,p)[0] for p in range(off,off+n-3,4)]

# surfaces
off,n=lump(13)
surfs=[]
for p in range(off,off+n-104+1,104):
    vals=struct.unpack_from("<12i12f2i",bsp,p)
    shaderNum,fogNum,surfaceType,firstVert,numVerts,firstIndex,numIndexes=vals[:7]
    if not (0<=shaderNum<len(shaders)) or numVerts<3 or firstVert<0 or firstVert+numVerts>len(verts):
        continue
    pts=verts[firstVert:firstVert+numVerts]
    mn=[min(v[k] for v in pts) for k in range(3)]
    mx=[max(v[k] for v in pts) for k in range(3)]
    center=[(mn[k]+mx[k])*0.5 for k in range(3)]
    normal=None
    if 0<=firstIndex and firstIndex+numIndexes<=len(idx):
        for q in range(firstIndex,firstIndex+numIndexes-2,3):
            ia,ib,ic=idx[q:q+3]
            if not (0<=ia<numVerts and 0<=ib<numVerts and 0<=ic<numVerts): continue
            a,b,c=pts[ia],pts[ib],pts[ic]
            u=[b[k]-a[k] for k in range(3)]
            v=[c[k]-a[k] for k in range(3)]
            cr=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
            ll=math.sqrt(sum(x*x for x in cr))
            if ll>1e-4:
                normal=[x/ll for x in cr]; break
    surfs.append({"shader":shaders[shaderNum][0],"type":surfaceType,"mins":mn,"maxs":mx,"center":center,"normal":normal})

def boxdist(a,b):
    # center-to-box distance of a point a to surface b bounds
    d=0.0
    for k in range(3):
        if a[k]<b["mins"][k]: d+=(b["mins"][k]-a[k])**2
        elif a[k]>b["maxs"][k]: d+=(a[k]-b["maxs"][k])**2
    return math.sqrt(d)

sky=[s for s in surfs if "/sky" in s["shader"].lower() or s["shader"].lower().startswith("textures/skies/")]

candidates=[]
for s in surfs:
    name=s["shader"].lower()
    nrm=s["normal"]
    if not nrm or abs(nrm[2])>0.35: continue
    spans=[max(0.0,s["maxs"][k]-s["mins"][k]) for k in range(3)]
    vertical_area=max(spans[0],spans[1])*spans[2]
    if vertical_area<18000: continue
    # Strong preference for known exterior/snow material namespaces.
    material=0
    if name.startswith("textures/snow/"): material+=220
    if "/castle_" in name or "/cathedrale_" in name: material+=70
    if name.startswith("textures/castle_wall/"): material+=25
    if material==0: continue
    if any(x in name for x in ("step","floor","roof","trim","wood","metal","light","grate","grid")): material-=80
    nearest_sky=None; sky_d=99999.0
    for sk in sky:
        d=boxdist(s["center"],sk)
        if d<sky_d:
            sky_d=d; nearest_sky=sk
    if sky_d>900: continue
    # Prefer high/open exterior areas and large uncluttered walls.
    score=material + min(180,vertical_area/5000.0) + max(0,160-sky_d*0.2) + max(0,(s["center"][2]+200)/12.0)
    candidates.append((score,sky_d,vertical_area,s,nearest_sky))

candidates.sort(key=lambda x:x[0],reverse=True)
selected=[]
for item in candidates:
    s=item[3]
    if any(math.dist(s["center"],x[3]["center"])<320 for x in selected): continue
    selected.append(item)
    if len(selected)>=3: break
if not selected: raise SystemExit("no outdoor wall candidates")

shots=[]
for rank,(score,sky_d,area,s,sk) in enumerate(selected):
    n=s["normal"]
    # Pick the wall side facing the closest sky surface.
    tosky=[sk["center"][k]-s["center"][k] for k in range(3)] if sk else n
    sign=1.0 if sum(tosky[k]*n[k] for k in range(3))>=0 else -1.0
    outward=[n[k]*sign for k in range(3)]
    # Camera close to wall, with small tangent offset so the texture fills most of frame.
    tangent=[-outward[1],outward[0],0.0]
    point=list(s["center"])
    # Avoid top/bottom edge if this is a very tall wall.
    point[2]=max(s["mins"][2]+72,min(s["maxs"][2]-72,s["center"][2]))
    cam=[point[0]+outward[0]*58+tangent[0]*18,
         point[1]+outward[1]*58+tangent[1]*18,
         point[2]]
    yaw=math.degrees(math.atan2(point[1]-cam[1],point[0]-cam[0]))
    shots.append({
        "name":f"outdoor_candidate_{rank}",
        "shader":s["shader"],
        "camera":[round(v,2) for v in cam],
        "target":[round(v,2) for v in point],
        "yaw":round(yaw,2),
        "score":round(score,2),
        "sky_distance":round(sky_d,2),
        "area_proxy":round(area,2),
        "normal":[round(v,5) for v in n],
        "bounds":{"mins":[round(v,1) for v in s["mins"]],"maxs":[round(v,1) for v in s["maxs"]]},
        "nearest_sky":None if not sk else sk["shader"],
    })

report={
    "bsp_source":source,
    "candidate_count":len(candidates),
    "shots":shots,
    "top_candidates":[{
        "score":round(sc,2),"sky_distance":round(sd,2),"area":round(ar,2),
        "shader":s["shader"],"center":[round(v,1) for v in s["center"]],
        "normal":[round(v,4) for v in s["normal"]]
    } for sc,sd,ar,s,sk in candidates[:20]]
}
Path(args.out).write_text(json.dumps(report,indent=2)+"\n")

lines=["set g_cheats 1","set cg_draw2D 0","set cg_drawGun 0","set cg_drawCrosshair 0"]
for s in shots:
    x,y,z=s["camera"]
    lines += [f'setviewpos {x} {y} {z} {s["yaw"]}','wait 4',f'screenshot {s["name"]}','wait 2']
lines += ["quit"]
Path(args.cfg).write_text("\n".join(lines)+"\n")
print(json.dumps(report,indent=2))
