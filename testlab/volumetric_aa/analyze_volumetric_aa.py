#!/usr/bin/env python3
from pathlib import Path
import json, sys
import numpy as np
from PIL import Image

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("evidence/screenshots")
out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("evidence/vaa-image-analysis.json")

pairs = []
for base in sorted(root.glob("*_base.tga")):
    fix = base.with_name(base.name.replace("_base.tga", "_fix.tga"))
    if not fix.exists():
        continue
    a = np.asarray(Image.open(base).convert("RGB"), dtype=np.float32) / 255.0
    b = np.asarray(Image.open(fix).convert("RGB"), dtype=np.float32) / 255.0
    if a.shape != b.shape:
        raise SystemExit(f"shape mismatch: {base.name} {a.shape} vs {fix.name} {b.shape}")

    def metrics(img):
        gray = img[...,0] * 0.2126 + img[...,1] * 0.7152 + img[...,2] * 0.0722
        gx = np.abs(gray[:,1:] - gray[:,:-1])
        gy = np.abs(gray[1:,:] - gray[:-1,:])
        g = np.zeros_like(gray)
        g[:,:-1] += gx
        g[:-1,:] += gy
        core = gray[1:-1,1:-1]
        lap = np.abs(
            4.0 * core
            - gray[1:-1,:-2] - gray[1:-1,2:]
            - gray[:-2,1:-1] - gray[2:,1:-1]
        )
        gc = g[1:-1,1:-1]
        thresh = float(np.percentile(gc, 85.0))
        mask = gc >= max(thresh, 1e-4)
        if not np.any(mask):
            hf = 0.0
            edge = 0.0
        else:
            hf = float(np.mean(lap[mask]) / (np.mean(gc[mask]) + 1e-6))
            edge = float(np.mean(gc[mask]))
        return {
            "mean_luma": float(np.mean(gray)),
            "edge_strength_p85": edge,
            "edge_hf_ratio": hf,
        }

    ma = metrics(a)
    mb = metrics(b)
    mae = float(np.mean(np.abs(a - b)))
    pair = {
        "base": base.name,
        "fix": fix.name,
        "base_metrics": ma,
        "fix_metrics": mb,
        "edge_hf_delta": mb["edge_hf_ratio"] - ma["edge_hf_ratio"],
        "mean_luma_delta": mb["mean_luma"] - ma["mean_luma"],
        "rgb_mae": mae,
    }
    pairs.append(pair)

if not pairs:
    raise SystemExit("no *_base.tga / *_fix.tga pairs found")

deltas = np.array([p["edge_hf_delta"] for p in pairs], dtype=np.float64)
luma = np.array([abs(p["mean_luma_delta"]) for p in pairs], dtype=np.float64)
mae = np.array([p["rgb_mae"] for p in pairs], dtype=np.float64)
summary = {
    "pair_count": len(pairs),
    "median_edge_hf_delta": float(np.median(deltas)),
    "pairs_edge_hf_improved": int(np.sum(deltas < 0.0)),
    "median_abs_luma_delta": float(np.median(luma)),
    "median_rgb_mae": float(np.median(mae)),
    "interpretation": "negative edge_hf_delta means less high-frequency staircase energy around strong image edges",
}
result = {"schema": 1, "summary": summary, "pairs": pairs}
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2))
