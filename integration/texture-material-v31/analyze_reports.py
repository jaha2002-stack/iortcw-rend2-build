#!/usr/bin/env python3
"""Compare V3.1 compact three-line per-image console records across two scopes."""
import argparse, json, re
from pathlib import Path

KV=re.compile(r"(\w+)=([^\s]+)")
def extract(path):
    lines=Path(path).read_text(encoding="utf-8",errors="replace").splitlines()
    scopes=[i for i,x in enumerate(lines) if x.startswith("[DWV31] scope=")]
    if not scopes:raise ValueError(f"Missing DWV31 report in {path}; use r_dwModelFidelityReport first.")
    start=scopes[-1]
    header=dict(KV.findall(lines[start]))
    by_index={}
    last_name_index=None
    for line in lines[start+1:]:
        if line.startswith("[DWV31] ix="):
            fields=dict(KV.findall(line))
            ix=fields.pop("ix",None)
            if ix is None:raise ValueError("Bad image record: "+line)
            row=by_index.setdefault(ix,{})
            row.update(fields)
            last_name_index=ix if "name" in fields else None
        elif line.startswith("[DWV31]"):
            last_name_index=None
        elif last_name_index is not None and line.strip() and "name" in by_index[last_name_index]:
            # Engine condump can wrap a long texture path between arbitrary letters.
            by_index[last_name_index]["name"]+=line.strip()
    entries={}
    required=("c","e","add","origNo","mip","src","up","gpu","raw","cmp","npot","kept","traced","name")
    for ix,row in by_index.items():
        missing=[k for k in required if k not in row]
        if missing:raise ValueError(f"Malformed/partial texture entry {ix}: {missing}")
        name=row["name"].lower().replace("\\","/")
        entries[name]=row
    if not entries:raise ValueError(f"No texture records for selected filter in {path}")
    return entries,header

def compare(off,on):
    before,bh=extract(off);after,ah=extract(on)
    if (bh.get("scope"),ah.get("scope"))!=("0","1"):
        raise ValueError("Scope0 then scope1 required; got "+str((bh.get("scope"),ah.get("scope"))))
    common=before.keys()&after.keys()
    edits=[]
    for name in sorted(set(before)|set(after)):
        x=before.get(name);y=after.get(name)
        if x is None or y is None:
            edits.append({"name":name,"reason":"LOADED_IN_ONLY_ONE_SCOPE","in0":bool(x),"in1":bool(y)})
            continue
        diff={k:{"scope0":x[k],"scope1":y[k]} for k in
              ("e","add","up","gpu","cmp","src","mip","npot","kept","origNo")
              if x[k]!=y[k]}
        if diff:edits.append({"name":name,"reason":"REPORTED_POLICY_OR_FORMAT_DIFFERENCE","differences":diff})
    return {
        "mode":"V3.1_DIAGNOSTIC_AB_ONLY",
        "scope0_count":len(before),
        "scope1_count":len(after),
        "newly_injected_no_compression_flags":sorted(k for k,x in after.items() if x["add"]=="1"),
        "actual_gpu_format_changes":sorted(k for k in common if before[k]["gpu"]!=after[k]["gpu"]),
        "actual_uploaded_dimension_changes":sorted(k for k in common if before[k]["up"]!=after[k]["up"]),
        "changes":edits,
        "interpretation":"A policy flag or GPU format difference does not establish any visual-quality improvement."
    }

def selftest(tmp):
    p=tmp/"off.txt";q=tmp/"on.txt"
    def mk(scope,add):
        return (f"[DWV31] scope={scope} textureFidelity=1 picmip=1\n"
                f"[DWV31] ix=23 c=V3 e={scope} add={add} origNo=0 mip=1 src=128x128 up=128x128\n"
                "[DWV31] ix=23 gpu=0x8051 raw=0x8058 cmp=0 npot=0 kept=0 traced=1\n"
                "[DWV31] ix=23 name=models/powerups/health/health_l.tga\n"
                "[DWV31] SUMMARY loadedV2=0 loadedV3=1 shown=1\n")
    p.write_text(mk(0,0));q.write_text(mk(1,1))
    r=compare(p,q)
    assert r["scope0_count"]==r["scope1_count"]==1
    assert len(r["newly_injected_no_compression_flags"])==1
    assert not r["actual_gpu_format_changes"]
    assert "visual-quality" in r["interpretation"]
    print("DW_V31_COMPACT_REPORT_PARSER_AB_SELFTEST_PASS")

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--scope0",type=Path)
    a.add_argument("--scope1",type=Path)
    a.add_argument("--out",type=Path)
    a.add_argument("--selftest",action="store_true")
    x=a.parse_args()
    if x.selftest:
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:selftest(Path(tmp))
    else:
        if not x.scope0 or not x.scope1:a.error("--scope0 and --scope1 required")
        result=json.dumps(compare(x.scope0,x.scope1),indent=2,ensure_ascii=False)+"\n"
        if x.out:x.out.write_text(result)
        else:print(result)
if __name__=="__main__":main()
