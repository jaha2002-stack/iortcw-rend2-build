#!/usr/bin/env python3
from pathlib import Path
import argparse, json, math, re, struct, zipfile

ap=argparse.ArgumentParser()
ap.add_argument("retail_main")
ap.add_argument("--out", required=True)
ap.add_argument("--shots", required=True)
args=ap.parse_args()

retail=Path(args.retail_main)
out=Path(args.out)
shots_path=Path(args.shots)
out.parent.mkdir(parents=True,exist_ok=True)
shots_path.parent.mkdir(parents=True,exist_ok=True)

bsp_bytes=None
bsp_source=None
for pk3 in sorted(retail.glob("*.pk3")):
    try:
        with zipfile.ZipFile(pk3) as z:
            for name in z.namelist():
                if name.lower()=="maps/escape1.bsp":
                    bsp_bytes=z.read(name)
                    bsp_source=f"{pk3.name}:{name}"
                    break
    except zipfile.BadZipFile:
        pass
    if bsp_bytes is not None:
        break
if bsp_bytes is None:
    raise SystemExit("maps/escape1.bsp not found")

magic=bsp_bytes[:4]
version=struct.unpack_from("<i",bsp_bytes,4)[0]
if magic!=b"IBSP":
    raise SystemExit(f"unexpected BSP magic {magic!r}")

def lump(i):
    off,length=struct.unpack_from("<ii",bsp_bytes,8+i*8)
    return off,length

ent_off,ent_len=lump(0)
entities_text=bsp_bytes[ent_off:ent_off+ent_len].split(b"\0",1)[0].decode("latin1","replace")
entities=[]
for block in re.findall(r"\{(.*?)\}", entities_text, flags=re.S):
    kv=dict(re.findall(r'"([^"]*)"\s+"([^"]*)"',block))
    if kv:
        entities.append(kv)

def origin(e):
    s=e.get("origin")
    if not s:
        return None
    try:
        vals=[float(x) for x in s.split()]
        return vals[:3] if len(vals)>=3 else None
    except Exception:
        return None

def dist(a,b):
    return math.sqrt(sum((a[i]-b[i])**2 for i in range(3)))

lights=[(i,e,origin(e)) for i,e in enumerate(entities) if e.get("classname")=="light" and origin(e)]
interesting=[]
rx=re.compile(r"torch|flame|fire|lamp|sconce|lantern",re.I)
for i,e in enumerate(entities):
    o=origin(e)
    hay=" ".join([e.get("classname",""),e.get("model",""),e.get("targetname",""),e.get("scriptName",""),e.get("name","")])
    if o and rx.search(hay):
        interesting.append((i,e,o,hay))

# Dense light clusters: every light can seed a cluster; dedupe nearby centroids.
clusters=[]
for i,e,o in lights:
    neigh=[x for x in lights if dist(o,x[2])<=520]
    if len(neigh)<3:
        continue
    c=[sum(x[2][k] for x in neigh)/len(neigh) for k in range(3)]
    clusters.append((len(neigh),c,[x[0] for x in neigh]))
clusters.sort(reverse=True,key=lambda x:x[0])
dedup=[]
for item in clusters:
    if all(dist(item[1],x[1])>320 for x in dedup):
        dedup.append(item)
    if len(dedup)>=8:
        break

# Player/spawn/high-Z candidates for exterior reconnaissance.
spawn_classes={"info_player_start","info_player_deathmatch","info_player_checkpoint","info_player_intermission","info_player_axis","info_player_allied"}
spawns=[]
for i,e in enumerate(entities):
    o=origin(e)
    if o and e.get("classname","") in spawn_classes:
        spawns.append((i,e,o))
high_entities=sorted([(i,e,origin(e)) for i,e in enumerate(entities) if origin(e)], key=lambda x:x[2][2], reverse=True)[:20]

# Parse shaders, vertices, draw surfaces for nearest material lookup.
sh_off,sh_len=lump(1)
shader_rec=72
shaders=[]
for p in range(sh_off,sh_off+sh_len-shader_rec+1,shader_rec):
    name=bsp_bytes[p:p+64].split(b"\0",1)[0].decode("latin1","replace")
    surfaceFlags,contentFlags=struct.unpack_from("<ii",bsp_bytes,p+64)
    shaders.append({"name":name,"surfaceFlags":surfaceFlags,"contentFlags":contentFlags})

v_off,v_len=lump(10)
verts=[]
for p in range(v_off,v_off+v_len-44+1,44):
    verts.append(struct.unpack_from("<fff",bsp_bytes,p))

s_off,s_len=lump(13)
surf_rec=104
surfaces=[]
for p in range(s_off,s_off+s_len-surf_rec+1,surf_rec):
    shaderNum,fogNum,surfaceType,firstVert,numVerts=struct.unpack_from("<iiiii",bsp_bytes,p)
    if numVerts<=0 or firstVert<0 or firstVert+numVerts>len(verts):
        continue
    pts=verts[firstVert:firstVert+numVerts]
    mn=[min(v[k] for v in pts) for k in range(3)]
    mx=[max(v[k] for v in pts) for k in range(3)]
    center=[(mn[k]+mx[k])*0.5 for k in range(3)]
    name=shaders[shaderNum]["name"] if 0<=shaderNum<len(shaders) else f"<shader:{shaderNum}>"
    surfaces.append({"shader":name,"center":center,"mins":mn,"maxs":mx,"surfaceType":surfaceType,"firstVert":firstVert,"numVerts":numVerts})

def point_box_distance(p,mn,mx):
    d=0.0
    for k in range(3):
        if p[k]<mn[k]: d+=(mn[k]-p[k])**2
        elif p[k]>mx[k]: d+=(p[k]-mx[k])**2
    return math.sqrt(d)

def nearest_surfaces(p,n=12):
    arr=sorted(surfaces,key=lambda s:point_box_distance(p,s["mins"],s["maxs"]))
    return [{"shader":s["shader"],"distance":round(point_box_distance(p,s["mins"],s["maxs"]),2),"center":[round(x,1) for x in s["center"]]} for s in arr[:n]]

# Camera shots: four cardinal offsets around each target, yaw aimed at target.
shots=[]
def add_ring(prefix,target,category,metadata,dist_xy=150,zoff=0):
    offsets=[(dist_xy,0),(-dist_xy,0),(0,dist_xy),(0,-dist_xy)]
    for idx,(dx,dy) in enumerate(offsets):
        cam=[target[0]+dx,target[1]+dy,target[2]+zoff]
        yaw=math.degrees(math.atan2(target[1]-cam[1],target[0]-cam[0]))
        shots.append({
            "name":f"{prefix}_{idx}",
            "camera":[round(x,1) for x in cam],
            "target":[round(x,1) for x in target],
            "yaw":round(yaw,1),
            "category":category,
            "metadata":metadata,
            "nearest_surfaces":nearest_surfaces(target,8)
        })

for rank,(i,e,o,hay) in enumerate(interesting[:8]):
    add_ring(f"torch{rank}",o,"torch",{"entity_index":i,"classname":e.get("classname"),"model":e.get("model"),"targetname":e.get("targetname"),"hay":hay},120,0)

for rank,(count,c,ids) in enumerate(dedup[:6]):
    add_ring(f"cluster{rank}",c,"light_cluster",{"light_count":count,"entity_indices":ids},180,0)

# High-Z / spawn reconnaissance, one ring each for a limited set.
for rank,(i,e,o) in enumerate(spawns[:4]):
    add_ring(f"spawn{rank}",o,"spawn",{"entity_index":i,"classname":e.get("classname")},180,0)
for rank,(i,e,o) in enumerate(high_entities[:4]):
    add_ring(f"high{rank}",o,"high_z",{"entity_index":i,"classname":e.get("classname"),"model":e.get("model")},220,0)

report={
    "bsp_source":bsp_source,
    "magic":magic.decode("ascii"),
    "version":version,
    "entity_count":len(entities),
    "light_count":len(lights),
    "interesting_count":len(interesting),
    "interesting":[{"index":i,"origin":o,"classname":e.get("classname"),"model":e.get("model"),"targetname":e.get("targetname"),"scriptName":e.get("scriptName"),"nearest_surfaces":nearest_surfaces(o,10)} for i,e,o,hay in interesting[:20]],
    "dense_light_clusters":[{"count":count,"center":[round(x,1) for x in c],"entity_indices":ids,"nearest_surfaces":nearest_surfaces(c,10)} for count,c,ids in dedup],
    "spawns":[{"index":i,"origin":o,"classname":e.get("classname"),"nearest_surfaces":nearest_surfaces(o,8)} for i,e,o in spawns],
    "high_entities":[{"index":i,"origin":o,"classname":e.get("classname"),"model":e.get("model"),"nearest_surfaces":nearest_surfaces(o,8)} for i,e,o in high_entities],
    "shot_count":len(shots),
}
out.write_text(json.dumps(report,indent=2)+"\n")
shots_path.write_text(json.dumps(shots,indent=2)+"\n")
print(json.dumps({"report":str(out),"shots":str(shots_path),"shot_count":len(shots),"interesting":len(interesting),"clusters":len(dedup)},indent=2))
