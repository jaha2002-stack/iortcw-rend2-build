#!/usr/bin/env python3
from pathlib import Path
import zipfile, sys, struct, math, json, hashlib

p=Path(sys.argv[1])
if not p.exists():
    raise SystemExit(f"missing pk3 {p}")

def tga_rgba_circle(size=64):
    w=h=size
    hdr=bytearray(18)
    hdr[2]=2
    hdr[12]=w&255; hdr[13]=w>>8
    hdr[14]=h&255; hdr[15]=h>>8
    hdr[16]=32
    hdr[17]=0x28  # top-left + 8 alpha bits
    pix=bytearray()
    cx=(w-1)/2.0; cy=(h-1)/2.0
    r=size*0.44
    for y in range(h):
        for x in range(w):
            d=math.sqrt((x-cx)**2+(y-cy)**2)
            # dark warm glass/metal center; soft 3px edge
            if d <= r-3:
                a=248
            elif d < r:
                a=int(248*(r-d)/3.0)
            else:
                a=0
            # slightly lighter center gives a dead-glass rather than black-hole look
            f=max(0.0,min(1.0,d/r))
            rr=int(48 + 18*(1.0-f))
            gg=int(45 + 14*(1.0-f))
            bb=int(39 + 10*(1.0-f))
            pix.extend((bb,gg,rr,a))
    return bytes(hdr)+bytes(pix)

shader=r'''darkwolf/dlv14_lamp_off
{
    cull disable
    {
        map gfx/darkwolf/dlv14_lamp_off.tga
        blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
        rgbGen vertex
        alphaGen vertex
    }
}
'''

files={
    "gfx/darkwolf/dlv14_lamp_off.tga":tga_rgba_circle(),
    "scripts/dw_destructible_visuals_v14.shader":shader.encode("ascii"),
    "docs/DW_DLV14_VISUAL_STATE.json":(json.dumps({
        "feature":"DarkWolf Destructible Lights V1.4 Visual State",
        "switch_render":"direct cgame trap_R_RegisterModel + guaranteed sprite fallback",
        "lamp_off_visual":"per-proxy circular dark mask; no global shader remap",
        "exact_fixture_destruction":"id:<fixtureId> with xyz backward compatibility"
    },indent=2)+"\n").encode("utf-8")
}

# Rebuild rather than append duplicate central directory entries.
existing={}
with zipfile.ZipFile(p,"r") as z:
    for n in z.namelist():
        existing[n]=z.read(n)
existing.update(files)

tmp=p.with_suffix(".tmp.pk3")
with zipfile.ZipFile(tmp,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for n,d in sorted(existing.items()):
        z.writestr(n,d)
tmp.replace(p)

with zipfile.ZipFile(p) as z:
    assert z.testzip() is None
    assert "scripts/dw_destructible_visuals_v14.shader" in z.namelist()
    b=z.read("gfx/darkwolf/dlv14_lamp_off.tga")
    assert b[2]==2 and b[16]==32
    assert len(b)==18+64*64*4
print("DW_DLV14_VISUAL_ASSETS_PASS",p)
print("SHA256",hashlib.sha256(p.read_bytes()).hexdigest())
