#!/usr/bin/env python3
"""Compile real RC4 fidelity cutout helpers in an ASan/UBSan C harness."""
from pathlib import Path
import subprocess,sys,json,re
root=Path(sys.argv[1]).resolve()
out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
src=(root/"SP/code/rend2/tr_image.c").read_text()
def extract(name):
    m=re.search(r"(?m)^static (?:qboolean|void)\s+"+re.escape(name)+r"\([^;]*?\)\s*\{",src)
    if not m:raise RuntimeError("Missing actual C helper "+name)
    start=m.start();a=src.index("{",m.start());depth=1;b=a+1
    while depth:
        depth+=(src[b]=="{")-(src[b]=="}")
        b+=1
    return src[start:b]
code=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
typedef unsigned char byte;
typedef int qboolean;
#define qtrue 1
#define qfalse 0
#define MAX(a,b) ((a)>(b)?(a):(b))
#define MIN(a,b) ((a)<(b)?(a):(b))
#define CLAMP(x,lo,hi) ((x)<(lo)?(lo):((x)>(hi)?(hi):(x)))
''' + "\n"+extract("DW_IsBinaryCutout")+"\n"+extract("DW_MipMapCutout")+r'''
int main(void)
{
    int i;
    byte p[64] = {
        240,30,15,255, 0,0,240,0,
        0,0,240,0, 0,0,240,0
    };
    if(!DW_IsBinaryCutout(p,2,2)) return 1;
    DW_MipMapCutout(p,2,2);
    if(!(p[0]>=239 && p[1]>=29 && p[2]>=14 && p[3]==64)) {
       fprintf(stderr,"Unexpected premultiplied output %u,%u,%u,%u\n",p[0],p[1],p[2],p[3]);
       return 2;
    }
    {
      byte linearAlpha[16] = {240,2,20,128, 20,30,40,255, 0,0,0,0, 0,0,0,0};
      if(DW_IsBinaryCutout(linearAlpha,2,2)) return 3;
    }
    {
      byte solid[16]={255,0,0,255, 0,255,0,255, 0,0,255,255, 255,255,255,255};
      if(DW_IsBinaryCutout(solid,2,2)) return 4;
    }
    {
      byte thin[16]={200,30,10,255, 0,0,200,0, 255,20,20,255, 0,0,200,0};
      if(!DW_IsBinaryCutout(thin,1,4)) return 5;
      DW_MipMapCutout(thin,1,4);
      if(thin[3]!=128 || thin[7]!=128 || thin[0]<190 || thin[4]<245) return 6;
    }
    {
      byte transparent[64]={0};
      if(DW_IsBinaryCutout(transparent,4,4)) return 7;
      DW_MipMapCutout(transparent,4,4);
      for(i=0;i<16;i++) if(transparent[i]!=0) return 8;
    }
    printf("PASS: real cutout helper ASan+UBSan four scenario classes, alpha premultiplication, thin mip tail\n");
    return 0;
}
'''
(out/"fidelity_cutout_harness.c").write_text(code)
exe=out/"cutout-test"
cc=["cc","-std=c11","-O1","-g","-fsanitize=address,undefined",
    "-fno-omit-frame-pointer",str(out/"fidelity_cutout_harness.c"),"-lm","-o",str(exe)]
subprocess.run(cc,check=True)
r=subprocess.run([str(exe)],capture_output=True,text=True)
(out/"cutout-tests.log").write_text(r.stdout+r.stderr)
if r.returncode:
    print(r.stdout+r.stderr,flush=True)
    raise SystemExit(r.returncode)
print(r.stdout,flush=True)
report={"status":"PASS","tests":["binary RGBA edge","nonbinary alpha exclusion","fully opaque exclusion","1x4 thin mip tail","transparent zero alpha"],"compiler_flags":"ASan/UBSan","real_source_functions":["DW_IsBinaryCutout","DW_MipMapCutout"]}
(out/"cutout-tests.json").write_text(json.dumps(report,indent=2)+"\n")
