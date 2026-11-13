#!/usr/bin/env python3
from pathlib import Path
import zipfile,sys,hashlib,json

pk3=Path(sys.argv[1])
out=Path(sys.argv[2])
if not pk3.exists():
    raise SystemExit(f"missing {pk3}")

wanted=[
    "models/darkwolf/switches/toggle_off.md3",
    "models/darkwolf/switches/toggle_on.md3",
    "models/darkwolf/switches/knife_off.md3",
    "models/darkwolf/switches/knife_on.md3",
    "models/darkwolf/switches/rotary_off.md3",
    "models/darkwolf/switches/rotary_on.md3",
    "models/darkwolf/switches/toggle.tga",
    "models/darkwolf/switches/knife.tga",
    "models/darkwolf/switches/rotary.tga",
    "gfx/darkwolf/dlv14_lamp_off.tga",
    "scripts/dw_destructible_switches_v12.shader",
    "scripts/dw_destructible_visuals_v14.shader",
]

manifest={}
with zipfile.ZipFile(pk3) as z:
    names=set(z.namelist())
    for name in wanted:
        if name not in names:
            raise SystemExit(f"missing PK3 entry {name}")
        data=z.read(name)
        dst=out/name
        dst.parent.mkdir(parents=True,exist_ok=True)
        dst.write_bytes(data)
        manifest[name]=hashlib.sha256(data).hexdigest()

(out/"docs").mkdir(parents=True,exist_ok=True)
(out/"docs/DW_DLV16_LOOSE_ASSETS.json").write_text(
    json.dumps({
      "feature":"DarkWolf Destructible Lights V1.6 loose VFS safety copy",
      "source_pk3":pk3.name,
      "files":manifest
    },indent=2)+"\n"
)
print("DW_DLV16_LOOSE_ASSETS_PASS",len(wanted))
