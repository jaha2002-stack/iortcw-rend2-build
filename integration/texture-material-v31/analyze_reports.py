#!/usr/bin/env python3
"""Compare two DW V3.1 reports; no unsupported GPU/visual-quality claims."""
import argparse, json, re
from pathlib import Path

KV=re.compile(r"(\w+)=([^\s]+)")
ROW_FIELDS=("class","policy","source","uploaded","srcFormat","gpuFormat","compressed",
            "mip","v3eligible","v3NoCompFlagAdded","originalNoCompFlag",
            "NPOTinput","NPOTretained","name")
def extract(path):
    lines=Path(path).read_text(encoding="utf-8",errors="replace").splitlines()
    rows={}
    headers=[]
    for line in lines:
        if line.startswith("[DWV31] scope="): headers.append(dict(KV.findall(line)))
        if not line.startswith("[DWV31] class="): continue
        r=dict(KV.findall(line))
        missing=[k for k in ROW_FIELDS if k not in r]
        if missing: raise ValueError(f"Missing fields {missing}: {line}")
        rows[r["name"].lower().replace("\\","/")]=r
    if not headers: raise ValueError(f"No DWV31 scope header in {path}; run console command first")
    return rows,headers[-1]

def compare(off,on):
    before,bh=extract(off)
    after,ah=extract(on)
    if bh.get("scope")!="0" or ah.get("scope")!="1":
        raise ValueError("Expected scope0 first and scope1 second: "+str((bh.get("scope"),ah.get("scope"))))
    names=sorted(set(before)|set(after))
    changes=[]
    for name in names:
        a=before.get(name)
        b=after.get(name)
        if a is None or b is None:
            changes.append({"name":name,"kind":"LOAD_SET_DIFF","scope0_loaded":bool(a),"scope1_loaded":bool(b)})
            continue
        altered={k:{"scope0":a[k],"scope1":b[k]}
                 for k in ("uploaded","gpuFormat","compressed","mip","source","policy","v3NoCompFlagAdded")
                 if a[k]!=b[k]}
        if altered:changes.append({"name":name,"kind":"POLICY_OR_FORMAT_CHANGE","fields":altered})
    results={
      "status":"DIAGNOSTIC_COMPARISON_ONLY",
      "scope0_total":len(before),
      "scope1_total":len(after),
      "scope1_newly_added_no_compression_flags":sorted(n for n,r in after.items()
            if r["v3NoCompFlagAdded"]=="1"),
      "scope1_gpu_format_differences":sorted(n for n in before.keys() & after.keys()
            if before[n]["gpuFormat"]!=after[n]["gpuFormat"]),
      "scope1_upload_dimension_differences":sorted(n for n in before.keys() & after.keys()
            if before[n]["uploaded"]!=after[n]["uploaded"]),
      "unmatched_or_modified_records":changes,
      "note":"This measures actual load policy and GPU internal format, not whether visual quality improved."
    }
    return results

def selftest(tmp):
    p=tmp/"off.txt";q=tmp/"on.txt"
    h="[DWV31] scope=0 textureFidelity=1 picmip=0 picmip2=0 minFilter=0x1 magFilter=0x1 anisoConfigured=2\n"
    row="[DWV31] class=V3 policy=NO_NEW_FLAG source=128x128 uploaded=128x128 srcFormat=0x8058 gpuFormat=0x8051 compressed=0 mip=1 v3eligible=0 v3NoCompFlagAdded=0 originalNoCompFlag=0 NPOTinput=0 NPOTretained=0 name=models/powerups/health/health_l.tga\n"
    p.write_text(h+row)
    q.write_text(h.replace("scope=0","scope=1")+row.replace("policy=NO_NEW_FLAG","policy=FLAG_ADDED").replace("v3eligible=0","v3eligible=1").replace("v3NoCompFlagAdded=0","v3NoCompFlagAdded=1"))
    x=compare(p,q)
    assert x["scope0_total"]==x["scope1_total"]==1
    assert x["scope1_newly_added_no_compression_flags"]==["models/powerups/health/health_l.tga"]
    assert not x["scope1_gpu_format_differences"]
    print("DW_V31_REPORT_PAIR_PARSER_NEGATIVE_QUALITY_CLAIM_TEST_PASS")

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--scope0",type=Path)
    a.add_argument("--scope1",type=Path)
    a.add_argument("--out",type=Path)
    a.add_argument("--selftest",action="store_true")
    args=a.parse_args()
    if args.selftest:
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:selftest(Path(tmp))
        return
    if not args.scope0 or not args.scope1:a.error("--scope0 and --scope1 required")
    out=compare(args.scope0,args.scope1)
    s=json.dumps(out,indent=2,ensure_ascii=False)+"\n"
    if args.out:args.out.write_text(s)
    else:print(s)
if __name__=="__main__":main()
