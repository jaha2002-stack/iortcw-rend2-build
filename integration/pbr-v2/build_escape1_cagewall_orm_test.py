#!/usr/bin/env python3
from pathlib import Path
import argparse, io, json, math, re, struct, zipfile
from PIL import Image, ImageFilter, ImageStat

ap=argparse.ArgumentParser()
ap.add_argument("retail_main")
ap.add_argument("--outdir", required=True)
args=ap.parse_args()

retail=Path(args.retail_main)
outdir=Path(args.outdir)
outdir.mkdir(parents=True,exist_ok=True)

# Find Escape1 BSP.
bsp=None
bsp_source=None
pk3s=sorted(retail.glob("*.pk3"))
for pk3 in pk3s:
    try:
        with zipfile.ZipFile(pk3) as z:
            if "maps/escape1.bsp" in z.namelist():
                bsp=z.read("maps/escape1.bsp")
                bsp_source=f"{pk3.name}:maps/escape1.bsp"
                break
    except zipfile.BadZipFile:
        pass
if bsp is None:
    raise SystemExit("escape1.bsp not found")

if bsp[:4] != b"IBSP":
    raise SystemExit("bad BSP")
version=struct.unpack_from("<i",bsp,4)[0]

def lump(i):
    return struct.unpack_from("<ii",bsp,8+i*8)

# Entities.
off,n=lump(0)
ent_text=bsp[off:off+n].split(b"\0",1)[0].decode("latin1","replace")
entities=[]
for block in re.findall(r"\{(.*?)\}",ent_text,re.S):
    kv=dict(re.findall(r'"([^"]*)"\s+"([^"]*)"',block))
    if kv:
        entities.append(kv)

def vec3(s):
    try:
        v=[float(x) for x in s.split()]
        return v[:3] if len(v)>=3 else None
    except Exception:
        return None

cages=[]
for i,e in enumerate(entities):
    model=e.get("model","").lower()
    o=vec3(e.get("origin",""))
    if o and ("cagelighta.md3" in model or "cagelighta5k.md3" in model):
        cages.append((i,e,o))
if len(cages)<2:
    raise SystemExit(f"expected at least two cage lights, found {len(cages)}")
# Select the physical pair of adjacent hanging cages, not arbitrary cage lights elsewhere
# on Escape1. Require a plausible pair separation and prefer the closest pair with
# similar height; this resolves the start-area pair around (-160, 328..468, 8xx).
pairs=[]
for a in range(len(cages)):
    for b in range(a+1,len(cages)):
        oa,ob=cages[a][2],cages[b][2]
        dd=math.sqrt(sum((oa[k]-ob[k])**2 for k in range(3)))
        dz=abs(oa[2]-ob[2])
        # The user-described start/torture-area ceiling fixtures are the unique
        # very close pair: two cagelighta models 56 units apart at the same height.
        if 30.0 <= dd <= 100.0 and dz <= 20.0:
            pairs.append((dd + dz*0.5,a,b))
if not pairs:
    raise SystemExit("requested close ceiling cage-light pair not found")
pairs.sort()
_,ia,ib=pairs[0]
cages=[cages[ia],cages[ib]]
mid=[sum(x[2][k] for x in cages)/len(cages) for k in range(3)]

# Shaders.
off,n=lump(1)
shaders=[]
for p in range(off,off+n-72+1,72):
    name=bsp[p:p+64].split(b"\0",1)[0].decode("latin1","replace").replace("\\","/")
    sf,cf=struct.unpack_from("<ii",bsp,p+64)
    shaders.append((name,sf,cf))

# Drawverts.
off,n=lump(10)
verts=[]
for p in range(off,off+n-44+1,44):
    verts.append(struct.unpack_from("<fff",bsp,p))

# Drawindexes.
off,n=lump(11)
indexes=[struct.unpack_from("<i",bsp,p)[0] for p in range(off,off+n-3,4)]

# Drawsurfaces.
off,n=lump(13)
surfs=[]
for p in range(off,off+n-104+1,104):
    vals=struct.unpack_from("<12i12f2i",bsp,p)
    shaderNum,fogNum,surfaceType,firstVert,numVerts,firstIndex,numIndexes=vals[:7]
    if not (0 <= shaderNum < len(shaders)) or numVerts<=0 or firstVert<0 or firstVert+numVerts>len(verts):
        continue
    pts=verts[firstVert:firstVert+numVerts]
    mn=[min(v[k] for v in pts) for k in range(3)]
    mx=[max(v[k] for v in pts) for k in range(3)]
    center=[(mn[k]+mx[k])*0.5 for k in range(3)]
    normal=None
    if numIndexes>=3 and 0<=firstIndex and firstIndex+numIndexes<=len(indexes):
        for q in range(firstIndex,firstIndex+numIndexes-2,3):
            ia,ib,ic=indexes[q:q+3]
            if not (0<=ia<numVerts and 0<=ib<numVerts and 0<=ic<numVerts):
                continue
            a,b,c=pts[ia],pts[ib],pts[ic]
            u=[b[k]-a[k] for k in range(3)]
            v=[c[k]-a[k] for k in range(3)]
            cr=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
            l=math.sqrt(sum(x*x for x in cr))
            if l>1e-5:
                normal=[x/l for x in cr]
                break
    surfs.append({
        "shader":shaders[shaderNum][0],
        "type":surfaceType,
        "firstVert":firstVert,
        "numVerts":numVerts,
        "mins":mn,"maxs":mx,"center":center,"normal":normal,
    })

def boxdist(p,s):
    d=0.0
    for k in range(3):
        if p[k]<s["mins"][k]: d+=(s["mins"][k]-p[k])**2
        elif p[k]>s["maxs"][k]: d+=(p[k]-s["maxs"][k])**2
    return math.sqrt(d)

def area_proxy(s):
    spans=sorted([max(0.0,s["maxs"][k]-s["mins"][k]) for k in range(3)],reverse=True)
    return spans[0]*spans[1]

cand=[]
for s in surfs:
    name=s["shader"].lower()
    d=boxdist(mid,s)
    if d>240:
        continue
    if not name.startswith("textures/"):
        continue
    if any(x in name for x in ("/decals/","/sfx/","/common/","/metal_","/wood/","/props/")):
        continue
    nrm=s["normal"]
    vertical=bool(nrm and abs(nrm[2])<0.35)
    score=0.0
    if "/castle_wall/" in name: score+=180
    if vertical: score+=120
    if s["type"]==1: score+=30
    score+=min(80,area_proxy(s)/5000.0)
    score-=d*0.6
    cand.append((score,d,s))
if not cand:
    raise SystemExit("no nearby wall surface candidates")
cand.sort(key=lambda x:x[0],reverse=True)
score,d,target=cand[0]
shader=target["shader"]
normal=target["normal"]
if not normal or abs(normal[2])>=0.7:
    raise SystemExit(f"chosen surface is not vertical enough: {target}")

# Find original diffuse texture from protected retail pk3s.
exts=[".tga",".jpg",".jpeg",".png"]
tex_bytes=None
tex_ext=None
tex_source=None
lookup=[shader+e for e in exts]
for pk3 in reversed(pk3s):
    try:
        with zipfile.ZipFile(pk3) as z:
            names={n.lower():n for n in z.namelist()}
            for candidate in lookup:
                key=candidate.lower()
                if key in names:
                    real=names[key]
                    tex_bytes=z.read(real)
                    tex_ext=Path(real).suffix.lower()
                    tex_source=f"{pk3.name}:{real}"
                    break
    except zipfile.BadZipFile:
        pass
    if tex_bytes is not None:
        break
if tex_bytes is None:
    raise SystemExit(f"diffuse texture not found for {shader}")

img=Image.open(io.BytesIO(tex_bytes)).convert("RGB")
w,h=img.size
gray=img.convert("L")
blur=gray.filter(ImageFilter.GaussianBlur(radius=max(1.0,min(w,h)/96.0)))
edge=gray.filter(ImageFilter.FIND_EDGES)

# Build a conservative stone ORM from the original diffuse.
# R = AO: darker/local recessed-looking regions get modestly lower AO.
# G = roughness: stone remains broadly rough with micro-detail modulation.
# B = metallic: 0 for masonry.
ao=Image.new("L",(w,h))
rough=Image.new("L",(w,h))
gpx=gray.load(); bpx=blur.load(); epx=edge.load(); apx=ao.load(); rpx=rough.load()
for y in range(h):
    for x in range(w):
        g=gpx[x,y]/255.0
        b=bpx[x,y]/255.0
        e=epx[x,y]/255.0
        local=max(-0.25,min(0.25,g-b))
        a=max(0.55,min(1.0,0.78 + 0.20*g + 0.20*local))
        r=max(0.62,min(0.96,0.78 + 0.12*(1.0-g) + 0.10*e))
        apx[x,y]=round(a*255)
        rpx[x,y]=round(r*255)
metal=Image.new("L",(w,h),0)
orm=Image.merge("RGB",(ao,rough,metal))
orm_path=outdir/(Path(shader).name+"_orm.tga")
orm.save(orm_path)

# Build a tangent-space normal map from the original stone texture.
# The source is first lightly blurred so JPEG noise does not become false geometry,
# then a Sobel gradient is converted to an OpenGL-style normal (X right, Y up, Z out).
height=gray.filter(ImageFilter.GaussianBlur(radius=max(0.8,min(w,h)/220.0)))
hpx=height.load()
normal_img=Image.new("RGB",(w,h))
npx=normal_img.load()
strength=2.25
for y in range(h):
    ym=max(0,y-1); yp=min(h-1,y+1)
    for x in range(w):
        xm=max(0,x-1); xp=min(w-1,x+1)
        # Sobel derivative in texture space.
        gx=(hpx[xp,ym] + 2*hpx[xp,y] + hpx[xp,yp] -
            hpx[xm,ym] - 2*hpx[xm,y] - hpx[xm,yp]) / (8.0*255.0)
        gy=(hpx[xm,yp] + 2*hpx[x,yp] + hpx[xp,yp] -
            hpx[xm,ym] - 2*hpx[x,ym] - hpx[xp,ym]) / (8.0*255.0)
        nx=-gx*strength
        ny= gy*strength
        nz=1.0
        ll=math.sqrt(nx*nx+ny*ny+nz*nz)
        nx/=ll; ny/=ll; nz/=ll
        npx[x,y]=(round((nx*0.5+0.5)*255),
                  round((ny*0.5+0.5)*255),
                  round((nz*0.5+0.5)*255))
normal_path=outdir/(Path(shader).name+"_n.tga")
normal_img.save(normal_path)

# Two additive packages are emitted so A/B can be run in fresh processes:
# A: no package (original material only)
# B: full PBR package with Normal + ORM.
pk3_full=outdir/"zzz_dw_escape1_cage_wall_pbr_full.pk3"
with zipfile.ZipFile(pk3_full,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    z.writestr(shader+"_n.tga",normal_path.read_bytes())
    z.writestr(shader+"_orm.tga",orm_path.read_bytes())

# Camera: build two legal candidates on either side; first points at wall center.
# Keep camera around eye height relative to the wall center and close enough to inspect material.
nxy=[normal[0],normal[1],0.0]
nl=math.hypot(nxy[0],nxy[1])
nxy=[nxy[0]/nl,nxy[1]/nl,0.0]
target_pt=list(target["center"])
cam_z=max(target["mins"][2]+48,min(target["maxs"][2]-24,mid[2]-55))
target_pt[2]=cam_z
# Place the camera on the same room side, below the hanging cages and offset
# laterally so neither cage blocks the wall.  This emulates a player standing
# beside the wall rather than a camera floating at ceiling height.
toward_cages=[mid[0]-target_pt[0],mid[1]-target_pt[1],0.0]
sign=1 if toward_cages[0]*nxy[0] + toward_cages[1]*nxy[1] >= 0.0 else -1
tangent=[-nxy[1],nxy[0],0.0]
cam_z=mid[2]-55.0
cam=[
    target_pt[0]+sign*nxy[0]*176+tangent[0]*112,
    target_pt[1]+sign*nxy[1]*176+tangent[1]*112,
    cam_z
]
yaw=math.degrees(math.atan2(target_pt[1]-cam[1],target_pt[0]-cam[0]))
camera={"camera":[round(v,2) for v in cam],"yaw":round(yaw,2),"side":sign}

cfg=['set g_cheats 1','set cg_draw2D 0','set cg_drawGun 0','set cg_drawCrosshair 0']
x,y,z=camera["camera"]
cfg += [f'setviewpos {x} {y} {z} {camera["yaw"]}','wait 45','screenshot cagewall_orm_real','wait 15','quit']
(outdir/"cagewall_orm_capture.cfg").write_text("\n".join(cfg)+"\n")

report={
    "bsp_source":bsp_source,
    "bsp_version":version,
    "cages":[{"entity":i,"model":e.get("model"),"origin":o} for i,e,o in cages],
    "cage_midpoint":[round(v,2) for v in mid],
    "selected_wall_shader":shader,
    "selected_wall_score":round(score,2),
    "selected_wall_distance":round(d,2),
    "selected_wall_center":[round(v,2) for v in target["center"]],
    "selected_wall_mins":[round(v,2) for v in target["mins"]],
    "selected_wall_maxs":[round(v,2) for v in target["maxs"]],
    "selected_wall_normal":[round(v,5) for v in normal],
    "original_texture_source":tex_source,
    "original_texture_size":[w,h],
    "normal_path":str(normal_path.name),
    "normal_mean_rgb":[round(v,2) for v in ImageStat.Stat(normal_img).mean],
    "normal_strength":strength,
    "orm_path":str(orm_path.name),
    "orm_channel_mean":{"AO":round(ImageStat.Stat(ao).mean[0]/255.0,4),"Roughness":round(ImageStat.Stat(rough).mean[0]/255.0,4),"Metallic":0.0},
    "pk3_full":pk3_full.name,
    "camera":camera,
    "top_wall_candidates":[{"shader":s["shader"],"score":round(sc,2),"distance":round(dd,2),"center":[round(v,1) for v in s["center"]],"normal":None if not s["normal"] else [round(v,3) for v in s["normal"]]} for sc,dd,s in cand[:12]]
}
(outdir/"cagewall_orm_proof.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
