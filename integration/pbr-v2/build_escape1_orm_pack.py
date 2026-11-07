#!/usr/bin/env python3
from pathlib import Path
import argparse, hashlib, io, json, math, re, statistics, zipfile
from PIL import Image, ImageFilter, ImageOps, ImageStat

ap=argparse.ArgumentParser()
ap.add_argument("retail_main")
ap.add_argument("--out-pk3", required=True)
ap.add_argument("--manifest", required=True)
args=ap.parse_args()

retail=Path(args.retail_main)
outpk3=Path(args.out_pk3)
manifest_path=Path(args.manifest)
outpk3.parent.mkdir(parents=True, exist_ok=True)
manifest_path.parent.mkdir(parents=True, exist_ok=True)

TARGETS=[
    {
        "id":"torch_wall",
        "logical":"textures/castle_wall/castle_grid_c19m",
        "kind":"rough_stone",
        "description":"Escape1 torch-lit castle wall",
        "roughness_range":[188,238],
        "metallic":0,
        "ao_strength":1.9,
    },
    {
        "id":"guard_metal",
        "logical":"textures/metal_misc/ametal_m03",
        "kind":"aged_metal",
        "description":"Escape1 guard-office metal surface under dense lamp cluster",
        "roughness_range":[92,168],
        "metallic":232,
        "ao_strength":1.55,
    },
    {
        "id":"outdoor_wall",
        "logical":"textures/snow/s_cathedrale_c06",
        "kind":"exterior_stone",
        "description":"Escape1 high exterior/sun-facing cathedral wall surface",
        "roughness_range":[172,230],
        "metallic":0,
        "ao_strength":1.75,
    },
]
EXTS=(".tga",".jpg",".jpeg",".png")

# Build deterministic search order. Later pk3s override earlier ones in the engine;
# for our original-source extraction prefer the highest lexical pk3 first.
pk3s=sorted(retail.glob("*.pk3"), key=lambda p:p.name.lower(), reverse=True)
if not pk3s:
    raise SystemExit("No retail PK3s found")

def sha(data): return hashlib.sha256(data).hexdigest()

def all_script_texts():
    docs=[]
    for pk3 in pk3s:
        try:
            with zipfile.ZipFile(pk3) as z:
                for n in z.namelist():
                    if n.lower().startswith("scripts/") and n.lower().endswith(".shader"):
                        try:
                            docs.append((pk3,n,z.read(n).decode("latin1","replace")))
                        except Exception:
                            pass
        except zipfile.BadZipFile:
            pass
    return docs

script_docs=all_script_texts()

def shader_mapped_images(logical):
    out=[]
    # Lightweight block extraction is sufficient for a fallback; direct texture wins.
    name_re=re.escape(logical)
    rx=re.compile(r"(?mis)(?:^|\n)\s*"+name_re+r"\s*\{(.*?)\n\s*\}")
    for pk3,n,text in script_docs:
        m=rx.search(text)
        if not m: continue
        body=m.group(1)
        for mm in re.finditer(r"(?im)^\s*(?:map|clampmap|qer_editorimage)\s+([^\s]+)",body):
            p=mm.group(1).strip()
            if p.startswith("$") or p.startswith("*"):
                continue
            out.append((pk3,n,p))
    return out

def find_image(logical):
    candidates=[logical+e for e in EXTS]
    # Direct authored image.
    for pk3 in pk3s:
        try:
            with zipfile.ZipFile(pk3) as z:
                lower={n.lower():n for n in z.namelist()}
                for c in candidates:
                    if c.lower() in lower:
                        n=lower[c.lower()]
                        return pk3,n,z.read(n),"direct"
        except zipfile.BadZipFile:
            pass
    # Shader fallback.
    for spk3,sname,mapped in shader_mapped_images(logical):
        base=mapped
        if base.lower().endswith(EXTS):
            mapped_candidates=[base]
        else:
            mapped_candidates=[base+e for e in EXTS]
        for pk3 in pk3s:
            try:
                with zipfile.ZipFile(pk3) as z:
                    lower={n.lower():n for n in z.namelist()}
                    for c in mapped_candidates:
                        if c.lower() in lower:
                            n=lower[c.lower()]
                            return pk3,n,z.read(n),f"shader:{spk3.name}:{sname}"
            except zipfile.BadZipFile:
                pass
    raise FileNotFoundError(logical)

def clamp(v,a=0,b=255):
    return max(a,min(b,int(round(v))))

def make_orm(img, cfg):
    rgb=img.convert("RGB")
    gray=ImageOps.grayscale(rgb)
    # Low-frequency neighborhood captures cavities without treating dark albedo
    # as full occlusion. Detail residual only affects AO moderately.
    blur=gray.filter(ImageFilter.GaussianBlur(radius=max(1.5,min(rgb.size)/96.0)))
    g=list(gray.getdata())
    b=list(blur.getdata())
    ao=[]
    rough=[]
    lo,hi=cfg["roughness_range"]
    # Local detail estimator: difference to blur + edge magnitude.
    edges=gray.filter(ImageFilter.FIND_EDGES)
    e=list(edges.getdata())
    for gv,bv,ev in zip(g,b,e):
        cavity=max(0.0, float(bv)-float(gv))
        ao_v=255.0-cavity*cfg["ao_strength"]-min(28.0,ev*0.10)
        ao.append(clamp(max(150.0,ao_v)))

        # Roughness remains material-class driven, with modest microvariation
        # from texture detail. This prevents albedo from being misused as roughness.
        detail=min(1.0, (abs(gv-bv)*0.035 + ev*0.006))
        if cfg["kind"]=="aged_metal":
            rv=lo+(hi-lo)*(0.30+0.55*detail)
        else:
            rv=lo+(hi-lo)*(0.55+0.40*detail)
        rough.append(clamp(rv,lo,hi))

    metal=[int(cfg["metallic"])]*len(ao)
    orm=Image.new("RGB",rgb.size)
    orm.putdata(list(zip(ao,rough,metal)))
    return orm, {"ao":ao,"roughness":rough,"metallic":metal}

def image_to_tga_bytes(img):
    bio=io.BytesIO()
    img.save(bio,format="TGA")
    return bio.getvalue()

manifest={
    "format":"DarkWolf Escape1 PBR V2 ORM validation pack",
    "base_run":42217883095,
    "pbr_build_run":42402994791,
    "channel_layout":{"R":"Ambient Occlusion","G":"Roughness","B":"Metallic"},
    "policy":"Original diffuse textures are NOT replaced. Pack only adds auto-discovered _orm data maps.",
    "materials":[],
}

entries={}
for cfg in TARGETS:
    pk3,n,data,resolution=find_image(cfg["logical"])
    img=Image.open(io.BytesIO(data))
    orm,ch=make_orm(img,cfg)
    orm_bytes=image_to_tga_bytes(orm)
    # Crucial: renderer auto-discovery suffixes the actual diffuse image path.
    source_noext=str(Path(n).with_suffix("")).replace("\\","/")
    orm_path=source_noext+"_orm.tga"
    entries[orm_path]=orm_bytes
    stats={}
    for key,vals in ch.items():
        stats[key]={
            "min":min(vals),"max":max(vals),
            "mean":round(sum(vals)/len(vals),3),
        }
    manifest["materials"].append({
        "id":cfg["id"],
        "logical_shader_or_texture":cfg["logical"],
        "source_pk3":pk3.name,
        "source_image":n,
        "source_resolution":list(img.size),
        "source_sha256":sha(data),
        "resolution_method":resolution,
        "orm_path":orm_path,
        "orm_sha256":sha(orm_bytes),
        "class":cfg["kind"],
        "stats":stats,
        "description":cfg["description"],
    })

manifest_bytes=(json.dumps(manifest,indent=2)+"\n").encode()
entries["dw_pbr_orm_escape1_manifest.json"]=manifest_bytes

with zipfile.ZipFile(outpk3,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for n,data in sorted(entries.items()):
        z.writestr(n,data)

with zipfile.ZipFile(outpk3) as z:
    assert z.testzip() is None
manifest["pack_sha256"]=sha(outpk3.read_bytes())
manifest_path.write_text(json.dumps(manifest,indent=2)+"\n")
print(json.dumps(manifest,indent=2))
