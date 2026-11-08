#!/usr/bin/env python3
from pathlib import Path
import argparse, io, json, math, zipfile
from PIL import Image, ImageFilter, ImageStat

ap=argparse.ArgumentParser()
ap.add_argument("retail_main")
ap.add_argument("recon_json")
ap.add_argument("--rank",type=int,default=0)
ap.add_argument("--outdir",required=True)
args=ap.parse_args()

retail=Path(args.retail_main)
recon=json.loads(Path(args.recon_json).read_text())
shot=recon["shots"][args.rank]
shader=shot["shader"].replace("\\","/")
out=Path(args.outdir); out.mkdir(parents=True,exist_ok=True)

# Resolve original diffuse from retail PK3s.
exts=[".tga",".jpg",".jpeg",".png"]
tex_bytes=None; tex_source=None
for pk3 in reversed(sorted(retail.glob("*.pk3"))):
    try:
        with zipfile.ZipFile(pk3) as z:
            names={n.lower().replace("\\","/"):n for n in z.namelist()}
            for ext in exts:
                k=(shader+ext).lower()
                if k in names:
                    real=names[k]; tex_bytes=z.read(real); tex_source=f"{pk3.name}:{real}"; break
    except zipfile.BadZipFile:
        pass
    if tex_bytes is not None: break
if tex_bytes is None: raise SystemExit(f"diffuse not found for {shader}")

base=Image.open(io.BytesIO(tex_bytes)).convert("RGB")
w,h=base.size
gray=base.convert("L")

# Outdoor masonry normal: coarse structure + restrained fine detail.
fine=gray.filter(ImageFilter.GaussianBlur(radius=max(0.65,min(w,h)/320.0)))
coarse=gray.filter(ImageFilter.GaussianBlur(radius=max(2.2,min(w,h)/72.0)))
height=Image.blend(fine,coarse,0.26)
hp=height.load()
normal=Image.new("RGB",(w,h)); np=normal.load()
strength=20.0
angles=[]
for y in range(h):
    ym=max(0,y-1); yp=min(h-1,y+1)
    for x in range(w):
        xm=max(0,x-1); xp=min(w-1,x+1)
        gx=(hp[xp,ym]+2*hp[xp,y]+hp[xp,yp]-hp[xm,ym]-2*hp[xm,y]-hp[xm,yp])/(8.0*255.0)
        gy=(hp[xm,yp]+2*hp[x,yp]+hp[xp,yp]-hp[xm,ym]-2*hp[x,ym]-hp[xp,ym])/(8.0*255.0)
        nx=-gx*strength; ny=gy*strength; nz=1.0
        ll=math.sqrt(nx*nx+ny*ny+nz*nz); nx/=ll; ny/=ll; nz/=ll
        np[x,y]=(round((nx*.5+.5)*255),round((ny*.5+.5)*255),round((nz*.5+.5)*255))
        angles.append(math.degrees(math.acos(max(-1,min(1,nz)))))

# Outdoor stone/snow ORM. Stone stays dielectric; snow/bright mineral areas are
# slightly rougher while darker exposed stone is a bit less rough.
blur=gray.filter(ImageFilter.GaussianBlur(radius=max(1.0,min(w,h)/100.0)))
edge=gray.filter(ImageFilter.FIND_EDGES)
gp=gray.load(); bp=blur.load(); ep=edge.load()
ao=Image.new("L",(w,h)); rough=Image.new("L",(w,h)); metal=Image.new("L",(w,h),0)
apx=ao.load(); rpx=rough.load()
for y in range(h):
    for x in range(w):
        g=gp[x,y]/255.0; b=bp[x,y]/255.0; e=ep[x,y]/255.0
        local=max(-0.30,min(0.30,g-b))
        a=max(0.46,min(1.0,0.72+0.25*g+0.30*local))
        # Exterior stone/snow: rough, but allow visible sun-angle response.
        r=max(0.46,min(0.92,0.60+0.22*g+0.10*e))
        apx[x,y]=round(a*255); rpx[x,y]=round(r*255)
orm=Image.merge("RGB",(ao,rough,metal))

stem=Path(shader).name
normal_path=out/(stem+"_n.tga"); orm_path=out/(stem+"_orm.tga")
normal.save(normal_path); orm.save(orm_path)

baseline=f"""{shader}
{{
    qer_editorimage {shader}.jpg
    {{
        stage diffuseMap
        map {shader}
        rgbGen identity
    }}
    {{
        map $lightmap
        blendFunc GL_DST_COLOR GL_ZERO
    }}
}}
"""
full=f"""{shader}
{{
    qer_editorimage {shader}.jpg
    {{
        stage diffuseMap
        map {shader}
        rgbGen identity
    }}
    {{
        stage normalMap
        map {shader}_n
        normalScale 1 1
    }}
    {{
        stage ormMap
        map {shader}_orm
    }}
    {{
        map $lightmap
        blendFunc GL_DST_COLOR GL_ZERO
    }}
}}
"""

pk3a=out/"zzz_dw_escape1_outdoor_baseline.pk3"
pk3b=out/"zzz_dw_escape1_outdoor_fullpbr.pk3"
with zipfile.ZipFile(pk3a,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    z.writestr("scripts/dw_outdoor_ab.mtr",baseline.encode())
with zipfile.ZipFile(pk3b,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    z.writestr("scripts/dw_outdoor_ab.mtr",full.encode())
    z.writestr(shader+"_n.tga",normal_path.read_bytes())
    z.writestr(shader+"_orm.tga",orm_path.read_bytes())

angles.sort()
def pct(p): return angles[min(len(angles)-1,round((len(angles)-1)*p))]
proof={
    "rank":args.rank,"shader":shader,"original_texture_source":tex_source,
    "texture_size":[w,h],"camera":shot["camera"],"target":shot["target"],"yaw":shot["yaw"],
    "wall_normal":shot["normal"],"sky_distance":shot["sky_distance"],
    "normal_strength":strength,
    "normal_angle_deg":{"mean":round(sum(angles)/len(angles),2),"p50":round(pct(.5),2),"p90":round(pct(.9),2),"p95":round(pct(.95),2)},
    "orm_mean":{"AO":round(ImageStat.Stat(ao).mean[0]/255,4),"Roughness":round(ImageStat.Stat(rough).mean[0]/255,4),"Metallic":0.0},
    "baseline_pk3":pk3a.name,"full_pk3":pk3b.name
}
(out/"outdoor_pbr_proof.json").write_text(json.dumps(proof,indent=2)+"\n")
print(json.dumps(proof,indent=2))
