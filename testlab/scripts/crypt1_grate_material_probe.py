#!/usr/bin/env python3
"""Report authored Crypt1 grate material/shader properties from LICENSED retail PK3.
Produces metadata only; no images, source assets or original shader text.
"""
from pathlib import Path
import sys,re,json,zipfile,struct,collections
sys.path.insert(0,str(Path("testlab/scripts").resolve()))
from crypt1_grate_bsp_probe import get_bsp

LOOKUP=["textures/broken_castle/wall_c21m","textures/crypt/crypt_d01_step","textures/crypt/crypt_d01"]
def extract_blocks(text,name):
    hits=[]
    for m in re.finditer(r"(?mi)^\s*"+re.escape(name)+r"\s*\{",text):
        start=m.end();level=1;i=start
        while i<len(text) and level:
            if text[i]=="{":level+=1
            if text[i]=="}":level-=1
            i+=1
        hits.append(text[start:i-1])
    return hits

def main():
    retail=Path(sys.argv[1]);out=Path(sys.argv[2])
    data,owner=get_bsp(retail)
    def lump(i):
        pos,size=struct.unpack_from('<ii',data,8+i*8);return data[pos:pos+size]
    shaders=list(struct.iter_unpack('<64sii',lump(1)))
    surfaces=lump(13)
    counts=collections.Counter()
    for i in range(len(surfaces)//104):
        tup=struct.unpack_from('<12i',surfaces,i*104)
        sh=tup[0];numidx=tup[6]
        if 0<=sh<len(shaders):
            name=shaders[sh][0].split(b"\0")[0].decode('latin-1').lower()
            if name in LOOKUP:counts[(name,"surface_count")]+=1;counts[(name,"triangles")]+=numidx//3
    result=dict(map="crypt1",protected_map_owner=owner,materials={})
    for material in LOOKUP:
        item={"bsp_shader":material,"surface_count":counts[(material,"surface_count")],
              "triangles":counts[(material,"triangles")],
              "flags":[{"surfaceFlags":x[1],"contentFlags":x[2]} for x in shaders if x[0].split(b"\0")[0].decode('latin-1').lower()==material],
              "shader_script_matches":[],"texture_candidates":[]}
        for pk3 in sorted(retail.glob("*.pk3")):
            with zipfile.ZipFile(pk3) as z:
                for n in z.namelist():
                    key=n.lower()
                    if key.startswith("scripts/") and key.endswith(".shader"):
                        text=z.read(n).decode("latin-1")
                        # Lightly trim comments before parsing shader block boundaries.
                        text=re.sub(r"/\*.*?\*/","",text,flags=re.S)
                        text=re.sub(r"//[^\r\n]*","",text)
                        for body in extract_blocks(text,material):
                            item["shader_script_matches"].append({
                                "pk3":pk3.name,"file":n,
                                "stages":body.count("{"),
                                "alpha_func":bool(re.search(r"\balphaFunc\b",body,re.I)),
                                "blend_func":bool(re.search(r"\bblendFunc\b",body,re.I)),
                                "alpha_to_coverage":bool(re.search(r"\balphaToCoverage\b",body,re.I)),
                                "surfaceparm_trans":bool(re.search(r"\bsurfaceparm\s+trans\b",body,re.I)),
                                "surfaceparm_alphashadow":bool(re.search(r"\bsurfaceparm\s+alphashadow\b",body,re.I)),
                                "cull_nonsolid":bool(re.search(r"\bcull\s+(none|disable|twosided)\b",body,re.I)),
                            })
                    if key.startswith(material+".") and key.endswith((".tga",".jpg",".jpeg",".png",".dds")):
                        item["texture_candidates"].append({"pk3":pk3.name,"extension":Path(n).suffix.lower()})
        result["materials"][material]=item
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+"\n")
    for k,v in result["materials"].items():
        print(k,"surfaces",v["surface_count"],"triangles",v["triangles"],
              "scripts",v["shader_script_matches"],"textures",v["texture_candidates"][:10],flush=True)
    print("CRYPT1_GRATE_AUTHORED_SHADER_AND_SURFACE_FLAGS_AUDIT_PASS",flush=True)
if __name__=="__main__":main()
