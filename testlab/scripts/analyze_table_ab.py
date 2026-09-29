#!/usr/bin/env python3
import argparse
import json
import re
import statistics
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("root")
p.add_argument("out")
args = p.parse_args()
root = Path(args.root)

labels = ("baseline", "exclude742", "exclude744")
for label in labels:
    qlog = root / label / "qconsole.log"
    if not qlog.is_file():
        raise SystemExit(f"missing qconsole for {label}: {qlog}")
    text = qlog.read_text(errors="replace")
    if f"TESTLAB_TABLE_CLUSTER_COMPLETE label={label} count=16 focus=742 challenger=744" not in text:
        raise SystemExit(f"missing completion marker for {label}")
    for fixture in (742, 744):
        if not re.search(rf"TESTLAB_RUNTIME_FRAME map=escape1 fixture={fixture} .*addedDlightIndex=[0-9]+", text):
            raise SystemExit(f"direct light fixture {fixture} missing in {label}")
    shots = sorted((root / label / "screenshots").glob(f"testlab_table_{label}_*.tga"))
    if len(shots) != 16:
        raise SystemExit(f"{label}: expected 16 screenshots, got {len(shots)}")

if "TESTLAB_SHADOW_ELIGIBILITY map=escape1 fixture=742" not in (root/"exclude742"/"qconsole.log").read_text(errors="replace"):
    raise SystemExit("exclude742 shadow eligibility gate was not exercised")
if "TESTLAB_SHADOW_ELIGIBILITY map=escape1 fixture=744" not in (root/"exclude744"/"qconsole.log").read_text(errors="replace"):
    raise SystemExit("exclude744 shadow eligibility gate was not exercised")

def read_tga(path):
    data = path.read_bytes()
    if len(data) < 18:
        raise ValueError(f"short TGA: {path}")
    idlen = data[0]
    cmap = data[1]
    image_type = data[2]
    cmap_len = int.from_bytes(data[5:7], "little")
    cmap_bits = data[7]
    width = int.from_bytes(data[12:14], "little")
    height = int.from_bytes(data[14:16], "little")
    bpp = data[16]
    if cmap:
        raise ValueError(f"color-mapped TGA unsupported: {path}")
    if image_type not in (2, 10) or bpp not in (24, 32):
        raise ValueError(f"unsupported TGA type={image_type} bpp={bpp}: {path}")
    px = bpp // 8
    pos = 18 + idlen + cmap_len * ((cmap_bits + 7) // 8)
    count = width * height
    if image_type == 2:
        raw = bytearray(data[pos:pos + count * px])
        if len(raw) != count * px:
            raise ValueError(f"truncated TGA: {path}")
    else:
        raw = bytearray()
        while len(raw) < count * px:
            header = data[pos]
            pos += 1
            n = (header & 0x7f) + 1
            if header & 0x80:
                pixel = data[pos:pos + px]
                pos += px
                raw.extend(pixel * n)
            else:
                nbytes = n * px
                raw.extend(data[pos:pos+nbytes])
                pos += nbytes
        raw = raw[:count * px]
    lum = []
    for i in range(0, len(raw), px):
        b, g, r = raw[i], raw[i+1], raw[i+2]
        lum.append((54*r + 183*g + 19*b) / 256.0)
    return width, height, lum

def compare(a, b):
    wa, ha, la = read_tga(a)
    wb, hb, lb = read_tga(b)
    if (wa, ha) != (wb, hb):
        raise ValueError(f"image size mismatch: {a} vs {b}")
    diffs = [y-x for x, y in zip(la, lb)]
    med = statistics.median(diffs)
    residual = [d-med for d in diffs]
    return {
        "median_global_shift": med,
        "residual_abs_mean": sum(abs(x) for x in residual)/len(residual),
        "residual_brightening_mean": sum(x for x in residual if x > 0)/len(residual),
        "residual_darkening_mean": -sum(x for x in residual if x < 0)/len(residual),
        "changed_fraction_ge3": sum(1 for x in residual if abs(x) >= 3.0)/len(residual),
    }

rows = []
for i in range(16):
    base = root/"baseline"/"screenshots"/f"testlab_table_baseline_{i:03d}.tga"
    e742 = root/"exclude742"/"screenshots"/f"testlab_table_exclude742_{i:03d}.tga"
    e744 = root/"exclude744"/"screenshots"/f"testlab_table_exclude744_{i:03d}.tga"
    rows.append({
        "index": i,
        "exclude742": compare(base, e742),
        "exclude744": compare(base, e744),
    })

summary = {
    "schema": 1,
    "method": "same-camera TGA residual comparison after subtracting median whole-frame luminance shift",
    "rows": rows,
    "exclude742_total_brightening": sum(r["exclude742"]["residual_brightening_mean"] for r in rows),
    "exclude744_total_brightening": sum(r["exclude744"]["residual_brightening_mean"] for r in rows),
    "exclude742_total_changed": sum(r["exclude742"]["changed_fraction_ge3"] for r in rows),
    "exclude744_total_changed": sum(r["exclude744"]["changed_fraction_ge3"] for r in rows),
}
Path(args.out).write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({k: summary[k] for k in (
    "exclude742_total_brightening",
    "exclude744_total_brightening",
    "exclude742_total_changed",
    "exclude744_total_changed",
)}, indent=2))
