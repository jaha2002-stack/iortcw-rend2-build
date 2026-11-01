#!/usr/bin/env python3
"""Inspect genuine id Tech 3 BSP from an ORIGINAL RTCW demo .pk3; no image synthesis."""
import argparse,json,struct,zipfile,hashlib,math
from pathlib import Path
EXCLUDE=("water","lava","ice","mirror","blood")
INCLUDE=("glass","window","/pane")
def inspect(path):
    with zipfile.ZipFile(path) as z:
        maps=[n for n in z.namelist() if n.lower().startswith("maps/") and n.lower().endswith(".bsp")]
        result=[]
        for mapname in sorted(maps):
            b=z.read(mapname)
            if len(b)<144 or b[:4]!=b"IBSP": continue
            version=struct.unpack_from("<i",b,4)[0]
            # Q3/RTCW SP BSP lumps 0..16 (offset,length each).
            lumps=[struct.unpack_from("<ii",b,8+8*i) for i in range(17)]
            shoff,shlen=lumps[1]
            suroff,surlen=lumps[13]
            if shlen%72 or surlen%104: continue
            shader=[]
            for off in range(shoff,shoff+shlen,72):
                name=b[off:off+64].split(b"\0",1)[0].decode("ascii","replace").lower()
                surfaceflags,contentflags=struct.unpack_from("<ii",b,off+64)
                # Never assume one shader name identifies an entire glass surface.
                ok=(any(x in name for x in INCLUDE) and not any(x in name for x in EXCLUDE))
                shader.append((name,ok,surfaceflags,contentflags))
            counts={}
            for off in range(suroff,suroff+surlen,104):
                shadernum=struct.unpack_from("<i",b,off)[0]
                if shadernum<0 or shadernum>=len(shader):continue
                name,ok,*_=shader[shadernum]
                if ok:counts[name]=counts.get(name,0)+1
            result.append({"map":mapname,"bsp_version":version,
                           "total_shader_entries":len(shader),
                           "candidate_materials":counts,
                           "candidate_surface_count":sum(counts.values()),
                           "source_bsp_sha256":hashlib.sha256(b).hexdigest()})
        return {"asset_sha256":hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                "maps":result,"map_count":len(result),
                "total_glass_named_surfaces":sum(m["candidate_surface_count"] for m in result)}
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("pk3",type=Path);p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    out=inspect(a.pk3)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(out,indent=2)+"\n")
    print("REAL_RTCW_BSP_GLASS_MAP_AUDIT",out["map_count"],out["total_glass_named_surfaces"])
