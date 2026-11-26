#!/usr/bin/env python3
from pathlib import Path
import json, re, sys
import numpy as np
from PIL import Image

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("evidence/screenshots")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("evidence/vaa3-image-analysis.json")

pat = re.compile(r"^(vaa3_(?:local|sun)_[^_]+(?:_p\d+)?)_(off1|base1|fix|base2|off2)\.tga$", re.I)
groups = {}
for p in sorted(ROOT.glob("vaa3_*.tga")):
    m = pat.match(p.name)
    if m:
        groups.setdefault(m.group(1), {})[m.group(2).lower()] = p
required = {"off1","base1","fix","base2","off2"}
valid = {k:v for k,v in groups.items() if required.issubset(v)}
if not valid:
    raise SystemExit("no complete VAA3 groups")

WEAPON_ROI=(0.48,0.42,1.00,1.00)
WORLD_ROI=(0.03,0.08,0.82,0.86)

def load(p):
    return np.asarray(Image.open(p).convert("RGB"),dtype=np.float32)/255.0

def luma(x):
    return x[...,0]*0.2126+x[...,1]*0.7152+x[...,2]*0.0722

def crop(x,roi):
    if roi is None: return x
    h,w=x.shape[:2]; x0,y0,x1,y1=roi
    return x[int(y0*h):int(y1*h),int(x0*w):int(x1*w)]

def mae(a,b,roi=None):
    a=crop(a,roi); b=crop(b,roi)
    return float(np.mean(np.abs(a-b)))

def edge_band(scene, roi=None):
    g=luma(crop(scene,roi))
    gx=np.zeros_like(g); gy=np.zeros_like(g)
    gx[:,:-1]=np.abs(g[:,1:]-g[:,:-1]); gy[:-1,:]=np.abs(g[1:,:]-g[:-1,:])
    grad=gx+gy
    thr=max(float(np.percentile(grad,78.0)),0.002)
    m=grad>=thr
    d=m.copy()
    d[1:,:]|=m[:-1,:]; d[:-1,:]|=m[1:,:]; d[:,1:]|=m[:,:-1]; d[:,:-1]|=m[:,1:]
    return d

def contribution_metrics(vol, scene, roi=None):
    c=luma(crop(vol,roi))
    m=edge_band(scene,roi)
    if min(c.shape)<6 or not np.any(m):
        return {"signal_mean":float(c.mean()),"edge_grad":0.0,"edge_lap":0.0,"edge_hf_ratio":0.0,"edge_pixels":int(m.sum())}
    gx=np.zeros_like(c); gy=np.zeros_like(c)
    gx[:,:-1]=np.abs(c[:,1:]-c[:,:-1]); gy[:-1,:]=np.abs(c[1:,:]-c[:-1,:])
    grad=gx+gy
    lap=np.zeros_like(c)
    core=c[1:-1,1:-1]
    lap[1:-1,1:-1]=np.abs(4*core-c[1:-1,:-2]-c[1:-1,2:]-c[:-2,1:-1]-c[2:,1:-1])
    eg=float(np.mean(grad[m])); el=float(np.mean(lap[m]))
    return {"signal_mean":float(c.mean()),"edge_grad":eg,"edge_lap":el,"edge_hf_ratio":el/(eg+1e-7),"edge_pixels":int(m.sum())}

def energy(vol,roi=None):
    return float(np.mean(luma(crop(vol,roi))))

rows=[]
for name, files in sorted(valid.items()):
    im={k:load(v) for k,v in files.items()}
    shapes={x.shape for x in im.values()}
    if len(shapes)!=1: raise SystemExit(f"shape mismatch {name}: {shapes}")
    off=(im['off1']+im['off2'])*0.5
    base=(im['base1']+im['base2'])*0.5
    fix=im['fix']
    vb=np.maximum(base-off,0.0)
    vf=np.maximum(fix-off,0.0)
    stable_off=mae(im['off1'],im['off2'])<=0.010 and mae(im['off1'],im['off2'],WEAPON_ROI)<=0.015
    stable_base=mae(im['base1'],im['base2'])<=0.010 and mae(im['base1'],im['base2'],WEAPON_ROI)<=0.015
    bm={"global":contribution_metrics(vb,off,None),"weapon":contribution_metrics(vb,off,WEAPON_ROI),"world":contribution_metrics(vb,off,WORLD_ROI)}
    fm={"global":contribution_metrics(vf,off,None),"weapon":contribution_metrics(vf,off,WEAPON_ROI),"world":contribution_metrics(vf,off,WORLD_ROI)}
    base_energy=energy(vb); fix_energy=energy(vf)
    ratio=fix_energy/max(base_energy,1e-8)
    weapon_delta=fm['weapon']['edge_hf_ratio']-bm['weapon']['edge_hf_ratio']
    world_delta=fm['world']['edge_hf_ratio']-bm['world']['edge_hf_ratio']
    global_delta=fm['global']['edge_hf_ratio']-bm['global']['edge_hf_ratio']
    combined=0.5*(weapon_delta+world_delta)
    signal_ok=base_energy>0.00015
    energy_ok=0.88<=ratio<=1.12
    edge_ok=(combined < -0.0010 and weapon_delta < 0.004 and world_delta < 0.004)
    row={
      "group":name,"files":{k:v.name for k,v in files.items()},
      "off_stability_global_mae":mae(im['off1'],im['off2']),
      "base_stability_global_mae":mae(im['base1'],im['base2']),
      "off_stability_weapon_mae":mae(im['off1'],im['off2'],WEAPON_ROI),
      "base_stability_weapon_mae":mae(im['base1'],im['base2'],WEAPON_ROI),
      "stable":bool(stable_off and stable_base),"signal_ok":bool(signal_ok),
      "base_energy":base_energy,"fix_energy":fix_energy,"energy_ratio":ratio,"energy_ok":bool(energy_ok),
      "baseline":bm,"candidate":fm,
      "weapon_edge_hf_delta":weapon_delta,"world_edge_hf_delta":world_delta,
      "global_edge_hf_delta":global_delta,"combined_edge_hf_delta":combined,
      "edge_ok":bool(edge_ok),
      "pass":bool(stable_off and stable_base and signal_ok and energy_ok and edge_ok)
    }
    rows.append(row)

bykind={}
for kind in ('local','sun'):
    rr=[r for r in rows if r['group'].startswith('vaa3_'+kind+'_')]
    bykind[kind]={
      "groups":len(rr),"passed":sum(1 for r in rr if r['pass']),
      "median_combined_edge_hf_delta":float(np.median([r['combined_edge_hf_delta'] for r in rr])) if rr else None,
      "median_energy_ratio":float(np.median([r['energy_ratio'] for r in rr])) if rr else None,
      "all_stable":bool(rr and all(r['stable'] for r in rr)),
    }

result={"schema":3,"weapon_roi_normalized":WEAPON_ROI,"world_roi_normalized":WORLD_ROI,"summary":bykind,"groups":rows,
"notes":[
 "metrics operate on isolated positive volumetric contribution (volume-on minus frozen volume-off frame)",
 "negative edge_hf_delta means less high-frequency staircase energy at scene/weapon edges",
 "energy_ratio guards against hiding aliasing by simply dimming the volumetric effect"
]}
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({"summary":bykind,"groups":[{"group":r['group'],"pass":r['pass'],"combined":r['combined_edge_hf_delta'],"weapon":r['weapon_edge_hf_delta'],"world":r['world_edge_hf_delta'],"energy_ratio":r['energy_ratio']} for r in rows]},indent=2))
