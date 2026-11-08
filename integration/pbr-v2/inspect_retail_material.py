#!/usr/bin/env python3
from pathlib import Path
import argparse, json, re, zipfile

ap=argparse.ArgumentParser()
ap.add_argument("retail_main")
ap.add_argument("--shader",required=True)
ap.add_argument("--out",required=True)
a=ap.parse_args()
root=Path(a.retail_main)
target=a.shader.strip().lower()
hits=[]
images=[]
for pk3 in sorted(root.glob("*.pk3")):
    try:
        with zipfile.ZipFile(pk3) as z:
            for name in z.namelist():
                low=name.lower().replace("\\","/")
                if low.startswith("scripts/") and (low.endswith(".shader") or low.endswith(".mtr")):
                    try:
                        text=z.read(name).decode("latin1","replace")
                    except Exception:
                        continue
                    # exact material block: material name followed by balanced braces.
                    for m in re.finditer(r'(?mi)^\s*([^\s/{][^\r\n{]*)\s*\{',text):
                        mat=m.group(1).strip().lower().replace("\\","/")
                        if mat!=target:
                            continue
                        start=m.start()
                        brace=text.find("{",m.start())
                        depth=0; end=None
                        for i in range(brace,len(text)):
                            if text[i]=="{": depth+=1
                            elif text[i]=="}":
                                depth-=1
                                if depth==0:
                                    end=i+1; break
                        block=text[start:end] if end else text[start:start+4000]
                        maps=re.findall(r'(?mi)^\s*(?:map|clampmap)\s+([^\s}]+)',block)
                        stages=re.findall(r'(?mi)^\s*stage\s+([^\s}]+)',block)
                        hits.append({"pk3":pk3.name,"script":name,"block":block,"maps":maps,"stages":stages})
                if low.startswith(target) and low.rsplit(".",1)[-1] in ("jpg","jpeg","tga","png"):
                    images.append({"pk3":pk3.name,"path":name})
    except zipfile.BadZipFile:
        pass
out={"shader":a.shader,"definitions":hits,"matching_images":images}
Path(a.out).write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps(out,indent=2))
