#!/usr/bin/env python3
"""Audit exact glass auto-probe sources across REAL licensed RTCW SP BSP maps."""
from pathlib import Path
import json,re,struct,zipfile,collections,hashlib,argparse
EXCLUDED=("water","lava","ice","blood","mirror","frame","trim","shutter","shudder","panel","border")
def main(root,out):
    maps={}
    for pak in sorted(Path(root).glob("*.pk3")):
        with zipfile.ZipFile(pak) as f:
            for path in f.namelist():
                if path.lower().startswith("maps/") and path.lower().endswith(".bsp"):
                    maps[Path(path).stem.lower()]=(pak,path)
    result=[]
    for name,(pak,path) in sorted(maps.items()):
        with zipfile.ZipFile(pak) as z:b=z.read(path)
        if b[:4]!=b"IBSP": continue
        lumps=[struct.unpack_from("<ii",b,8+i*8) for i in range(17)]
        def lp(i):
            off,n=lumps[i];return b[off:off+n]
        entitytxt=lp(0).decode("latin1")
        entitynames=collections.Counter(n.lower() for n in re.findall(r'"classname"\s+"([^"]+)"',entitytxt,re.I))
        s=lp(1);face=lp(13)
        shnames=[s[i:i+64].split(b"\x00",1)[0].decode("latin1").lower()
                 for i in range(0,len(s),72)]
        matches=collections.Counter()
        for i in range(0,len(face),104):
            tex=struct.unpack_from("<i",face,i)[0]
            if tex<0 or tex>=len(shnames):continue
            full=shnames[tex];base=full.rsplit("/",1)[-1]
            if any(w in base for w in ("glass","window")) and not any(w in base for w in EXCLUDED):
                matches[full]+=1
        authored=entitynames["misc_cubemap"];ai=entitynames["ai_marker"];sp=entitynames["info_player_start"]
        fallthrough=bool(matches) and not (authored or ai or sp)
        result.append({"map":name,"glass_named_surfaces":sum(matches.values()),"glass_material_names":list(matches),
        "author_probes":authored,"ai_markers":ai,"sp_starts":sp,"other_player_spawns":sum(v for k,v in entitynames.items() if k.startswith("info_player_") and k!="info_player_start"),
        "requires_fallback_beyond_current_v1":fallthrough,"sha256_bsp":hashlib.sha256(b).hexdigest()})
    flagged=[x for x in result if x["requires_fallback_beyond_current_v1"]]
    data={"retail_assets_not_exported":True,"map_count":len(result),"glass_named_maps":sum(x["glass_named_surfaces"]>0 for x in result),
    "glass_maps_missing_known_probe_source":len(flagged),"flagged_maps":[x["map"] for x in flagged],"maps":result}
    Path(out).parent.mkdir(parents=True,exist_ok=True)
    Path(out).write_text(json.dumps(data,indent=2)+"\n")
    print("REAL_RTCW_GLOBALLY_INVENTORIED",data["map_count"],"GLASS_MAPS",data["glass_named_maps"])
    print("MISSING_PROBE_SOURCE",data["flagged_maps"])
    if flagged:raise SystemExit("UNIVERSAL_GLASS_PROBE_FALLBACK_INCOMPLETE")
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("retail",type=Path);p.add_argument("--out",required=True,type=Path);a=p.parse_args();main(a.retail,a.out)
