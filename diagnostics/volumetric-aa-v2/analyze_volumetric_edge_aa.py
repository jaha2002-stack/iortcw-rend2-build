#!/usr/bin/env python3
from pathlib import Path
import json, re, sys
import numpy as np
from PIL import Image

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("evidence/screenshots")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("evidence/vaa2-image-analysis.json")

pat = re.compile(r"^(vaa2_(?:local|sun)_[^_]+(?:_p\d+)?)_(base1|aa8|aa16|base2)\.tga$", re.I)
groups = {}
for p in sorted(ROOT.glob("vaa2_*.tga")):
    m = pat.match(p.name)
    if m:
        groups.setdefault(m.group(1), {})[m.group(2).lower()] = p

required = {"base1","aa8","aa16","base2"}
valid_groups = {k:v for k,v in groups.items() if required.issubset(v)}
if not valid_groups:
    raise SystemExit("no complete VAA2 baseline/aa8/aa16/baseline2 groups found")

def load(p):
    return np.asarray(Image.open(p).convert("RGB"), dtype=np.float32) / 255.0

def luma(img):
    return img[...,0] * 0.2126 + img[...,1] * 0.7152 + img[...,2] * 0.0722

def edge_metrics(img, roi=None):
    if roi is not None:
        h,w = img.shape[:2]
        x0,y0,x1,y1 = roi
        img = img[int(y0*h):int(y1*h), int(x0*w):int(x1*w)]
    g = luma(img)
    if min(g.shape) < 6:
        return {"edge_hf_ratio":0.0,"edge_strength_p85":0.0,"mean_luma":float(g.mean())}
    gx = np.abs(g[:,1:] - g[:,:-1])
    gy = np.abs(g[1:,:] - g[:-1,:])
    grad = np.zeros_like(g)
    grad[:,:-1] += gx
    grad[:-1,:] += gy
    core = g[1:-1,1:-1]
    lap = np.abs(4*core - g[1:-1,:-2] - g[1:-1,2:] - g[:-2,1:-1] - g[2:,1:-1])
    gc = grad[1:-1,1:-1]
    thr = max(float(np.percentile(gc, 82.0)), 1e-5)
    mask = gc >= thr
    if not np.any(mask):
        hf=edge=0.0
    else:
        hf=float(np.mean(lap[mask])/(np.mean(gc[mask])+1e-6))
        edge=float(np.mean(gc[mask]))
    return {"edge_hf_ratio":hf,"edge_strength_p85":edge,"mean_luma":float(g.mean())}

def mae(a,b,roi=None):
    if roi is not None:
        h,w=a.shape[:2]; x0,y0,x1,y1=roi
        a=a[int(y0*h):int(y1*h),int(x0*w):int(x1*w)]
        b=b[int(y0*h):int(y1*h),int(x0*w):int(x1*w)]
    return float(np.mean(np.abs(a-b)))

# Lower-right player weapon/hand region. It intentionally excludes most horizon/world.
WEAPON_ROI=(0.54,0.46,1.00,1.00)
WORLD_ROI=(0.04,0.08,0.78,0.78)

rows=[]
for name, files in sorted(valid_groups.items()):
    imgs={k:load(v) for k,v in files.items()}
    shapes={x.shape for x in imgs.values()}
    if len(shapes)!=1:
        raise SystemExit(f"shape mismatch in {name}: {shapes}")

    sanity={}
    for k,img in imgs.items():
        lm=float(luma(img).mean())
        sd=float(luma(img).std())
        sanity[k]={"mean_luma":lm,"std_luma":sd,"valid": bool(0.005 < lm < 0.995 and sd > 0.005)}

    base_stability_global=mae(imgs["base1"],imgs["base2"])
    base_stability_weapon=mae(imgs["base1"],imgs["base2"],WEAPON_ROI)
    base=(imgs["base1"]+imgs["base2"])*0.5

    bm_g=edge_metrics(base)
    bm_w=edge_metrics(base,WEAPON_ROI)
    bm_world=edge_metrics(base,WORLD_ROI)

    variants={}
    for vk in ("aa8","aa16"):
        im=imgs[vk]
        mg=edge_metrics(im)
        mw=edge_metrics(im,WEAPON_ROI)
        mworld=edge_metrics(im,WORLD_ROI)
        variants[vk]={
            "global":mg,
            "weapon":mw,
            "world":mworld,
            "global_edge_hf_delta":mg["edge_hf_ratio"]-bm_g["edge_hf_ratio"],
            "weapon_edge_hf_delta":mw["edge_hf_ratio"]-bm_w["edge_hf_ratio"],
            "world_edge_hf_delta":mworld["edge_hf_ratio"]-bm_world["edge_hf_ratio"],
            "global_mean_luma_delta":mg["mean_luma"]-bm_g["mean_luma"],
            "weapon_mean_luma_delta":mw["mean_luma"]-bm_w["mean_luma"],
            "global_rgb_mae_vs_base":mae(im,base),
            "weapon_rgb_mae_vs_base":mae(im,base,WEAPON_ROI),
        }

    stable=base_stability_global <= 0.012 and base_stability_weapon <= 0.018
    row={
        "group":name,
        "files":{k:v.name for k,v in files.items()},
        "sanity":sanity,
        "baseline_stability_global_mae":base_stability_global,
        "baseline_stability_weapon_mae":base_stability_weapon,
        "stable":stable,
        "baseline":{"global":bm_g,"weapon":bm_w,"world":bm_world},
        "variants":variants,
    }
    rows.append(row)

summary={}
for vk in ("aa8","aa16"):
    usable=[r for r in rows if r["stable"] and all(x["valid"] for x in r["sanity"].values())]
    weapon=np.array([r["variants"][vk]["weapon_edge_hf_delta"] for r in usable],dtype=float)
    world=np.array([r["variants"][vk]["world_edge_hf_delta"] for r in usable],dtype=float)
    luma_delta=np.array([abs(r["variants"][vk]["global_mean_luma_delta"]) for r in usable],dtype=float)
    summary[vk]={
        "usable_groups":len(usable),
        "weapon_edge_hf_improved_groups":int(np.sum(weapon<0)) if len(weapon) else 0,
        "median_weapon_edge_hf_delta":float(np.median(weapon)) if len(weapon) else None,
        "median_world_edge_hf_delta":float(np.median(world)) if len(world) else None,
        "median_abs_global_luma_delta":float(np.median(luma_delta)) if len(luma_delta) else None,
        "max_abs_global_luma_delta":float(np.max(luma_delta)) if len(luma_delta) else None,
    }

# Prefer the lower reject if it already cleans the weapon edge and preserves energy;
# otherwise allow reject 16. This is a recommendation, not a hard pass/fail.
def score(v):
    s=summary[v]
    if not s["usable_groups"]: return -1e9
    return (
        s["weapon_edge_hf_improved_groups"] * 3.0
        - (s["median_weapon_edge_hf_delta"] or 0.0) * 12.0
        - (s["median_abs_global_luma_delta"] or 0.0) * 80.0
    )
recommended=max(("aa8","aa16"), key=score)
result={
    "schema":2,
    "weapon_roi_normalized":WEAPON_ROI,
    "world_roi_normalized":WORLD_ROI,
    "summary":summary,
    "recommended_variant":recommended,
    "groups":rows,
    "notes":[
        "negative edge_hf_delta means less high-frequency stair-step energy around strong edges",
        "base1/base2 stability rejects dynamic-scene pairs before judging AA",
        "joint-bilateral kernel is designed to equal ordinary bilinear interpolation when depths agree"
    ]
}
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({"summary":summary,"recommended_variant":recommended},indent=2))
