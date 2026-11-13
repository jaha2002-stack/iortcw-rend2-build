#!/usr/bin/env python3
from pathlib import Path
import zipfile,sys,hashlib

pk3=Path(sys.argv[1])
if not pk3.exists():
    raise SystemExit(f"missing {pk3}")

def make_tga(kind,w=128,h=128):
    # Much darker RTCW/WWII palette than V1.2, with restrained wear.
    palettes={
      "toggle":[(46,50,43),(31,22,18),(88,84,72),(18,20,18)],
      "knife":[(49,54,45),(33,23,18),(94,87,70),(20,22,19)],
      "rotary":[(44,48,43),(29,21,17),(84,82,73),(17,19,18)],
    }
    seed={"toggle":13,"knife":29,"rotary":41}[kind]
    hdr=bytearray(18);hdr[2]=2;hdr[12]=w&255;hdr[13]=w>>8
    hdr[14]=h&255;hdr[15]=h>>8;hdr[16]=24;hdr[17]=0x20
    pix=bytearray()
    for y in range(h):
        for x in range(w):
            patch=(1 if x>=64 else 0)+(2 if y>=64 else 0)
            base=list(palettes[kind][patch])
            lx=x&63;ly=y&63
            edge=min(lx,ly,63-lx,63-ly)
            grain=((x*19+y*23+seed*11)%13)-6
            if edge<2: base=[min(255,int(v*1.10)+3) for v in base]
            elif edge<6: base=[max(0,int(v*0.91)) for v in base]
            # Sparse worn metal flecks, not high-frequency noise.
            if ((x*7+y*5+seed)%149)==0:
                base=[min(255,int(v*1.20)+5) for v in base]
            if ((x*11+y*13+seed)%193)==0:
                base=[max(0,int(v*0.76)) for v in base]
            base=[max(0,min(255,v+grain//2)) for v in base]
            pix.extend((base[2],base[1],base[0]))
    return bytes(hdr)+bytes(pix)

with zipfile.ZipFile(pk3,"r") as z:
    data={n:z.read(n) for n in z.namelist()}

for kind in ("toggle","knife","rotary"):
    data[f"models/darkwolf/switches/{kind}.tga"]=make_tga(kind)

tmp=pk3.with_suffix(".v17.tmp.pk3")
with zipfile.ZipFile(tmp,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for n,b in sorted(data.items()):
        z.writestr(n,b)
tmp.replace(pk3)

with zipfile.ZipFile(pk3) as z:
    assert z.testzip() is None
    for kind in ("toggle","knife","rotary"):
        b=z.read(f"models/darkwolf/switches/{kind}.tga")
        assert len(b)==18+128*128*3
print("DW_DLV17_SWITCH_ART_REFINED_PASS")
print("SHA256",hashlib.sha256(pk3.read_bytes()).hexdigest())
