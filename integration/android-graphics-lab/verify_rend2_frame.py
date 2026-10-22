#!/usr/bin/env python3
"""Conservative visual gate for Android's 3D viewport, not merely a PNG capture."""
from PIL import Image
from collections import Counter
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: verify_rend2_frame.py screenshot.png")
path = Path(sys.argv[1])
im = Image.open(path).convert("RGB")
w, h = im.size
if w < 300 or h < 180:
    print(f"FRAME_VISUAL=FAIL reason=small_frame width={w} height={h}", flush=True)
    raise SystemExit(1)
pixels = [
    im.getpixel((x, y))
    for y in range(int(h * .18), int(h * .79), 2)
    for x in range(int(w * .22), int(w * .78), 2)
]
if not pixels:
    raise SystemExit("FRAME_VISUAL=FAIL reason=empty_region")
bins = Counter(tuple(v >> 4 for v in rgb) for rgb in pixels)
dominant = bins.most_common(1)[0][1] / len(pixels)
colored = sum(max(p) - min(p) > 14 for p in pixels) / len(pixels)
lit = sum(max(p) > 30 for p in pixels) / len(pixels)
# A flat black frame and the Android "Viewing full screen" dialog must FAIL.
# SDL/Gboard and launcher dialogs can occupy most of the viewport.
# The false-positive in Run 39709755979 had lower_pale=0.952.
lower = [im.getpixel((x, y))
         for y in range(int(h * .34), h, 3)
         for x in range(0, w, 3)]
lower_pale = sum(min(p) > 175 and max(p)-min(p) < 30 for p in lower) / len(lower)
ok = (len(bins) >= 65 and dominant < .76 and colored >= .025 and
      lit >= .04 and lower_pale < .69)
print(
    f"FRAME_VISUAL={'PASS' if ok else 'FAIL'} image={path.name} "
    f"size={w}x{h} bins={len(bins)} dominant={dominant:.3f} "
    f"colored={colored:.3f} lit={lit:.3f} lower_pale={lower_pale:.3f}",
    flush=True
)
if not ok:
    raise SystemExit(1)

# Pure image diversity is only a preliminary smoke condition, not scene proof.
