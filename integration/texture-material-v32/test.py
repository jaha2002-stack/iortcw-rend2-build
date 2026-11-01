#!/usr/bin/env python3
"""Test the literal V3.2 model-select predicate compiled natively (positive + negative)."""
from pathlib import Path
import argparse,json,subprocess,re

def function(source,name):
    token="static qboolean "+name+"("
    i=source.index(token)
    p=source.index("{",i)
    depth=0
    for j in range(p,len(source)):
        if source[j]=="{": depth+=1
        elif source[j]=="}":
            depth-=1
            if depth==0:return source[i:j+1]+"\n"
    raise ValueError("unclosed "+name)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("root",type=Path)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    r=a.root/"SP/code/rend2"
    source=(r/"tr_image.c").read_text()
    init=(r/"tr_init.c").read_text()
    for p in ("tr_backend.c","tr_shade.c","tr_shader.c","tr_fbo.c",
              "glsl/dwfinal_fp.glsl","glsl/lightall_fp.glsl"):
        assert "DARKWOLF_V32_MODEL_SAMPLING_20261101" not in (r/p).read_text(),p
    assert 'r_dwModelMipBias = ri.Cvar_Get("r_dwModelMipBias", "0", CVAR_ARCHIVE | CVAR_LATCH);' in init
    assert 'ri.Cvar_CheckRange(r_dwModelMipBias, -0.50f, 0.00f, qfalse);' in init
    assert source.count("GL_TEXTURE_LOD_BIAS, applied") == 1
    assert source.count("r_dwModelMipBias->value < -0.0001f") == 1
    assert "qglTextureParameterfEXT(image->texnum, GL_TEXTURE_2D" in source
    assert "r_dwModelTextureScope && r_dwModelTextureScope->integer" in source
    assert "DW_MipMapCutout" not in source
    assert "dwV31ImageTrace[tr.numImages - 1].actualMipBiasRequest = applied;" in source

    parts=[function(source,n) for n in
           ("DW_IsModelTextureName","DW_IsExtendedModelTextureName","DW_V32_ModelMipEligible")]
    cases=[
      ("models/players/axis/head.tga","IMGTYPE_COLORALPHA","IMGFLAG_MIPMAP",1,0,1),
      ("models/weapons2/mp40/mp40.tga","IMGTYPE_COLORALPHA","IMGFLAG_MIPMAP",1,0,1),
      ("models/weapons/stg44/mag.tga","IMGTYPE_COLORALPHA","IMGFLAG_MIPMAP",1,0,1),
      ("models/powerups/health/health_l.tga","IMGTYPE_COLORALPHA","IMGFLAG_MIPMAP",1,0,0),
      ("models/powerups/health/health_l.tga","IMGTYPE_COLORALPHA","IMGFLAG_MIPMAP",1,1,1),
      ("models/powerups/ammo/am792mm.tga","IMGTYPE_COLORALPHA","IMGFLAG_MIPMAP",1,1,1),
      ("models/monsters/zombie/body.tga","IMGTYPE_COLORALPHA","IMGFLAG_MIPMAP",1,1,1),
      ("models/mapobjects/shield/shield.tga","IMGTYPE_COLORALPHA","IMGFLAG_MIPMAP",1,1,0),
      ("textures/metal/grate.tga","IMGTYPE_COLORALPHA","IMGFLAG_MIPMAP",1,1,0),
      ("textures/rock/wall.tga","IMGTYPE_COLORALPHA","IMGFLAG_MIPMAP",1,1,0),
      ("gfx/2d/icons.tga","IMGTYPE_COLORALPHA","IMGFLAG_MIPMAP",1,1,0),
      ("models/players/axis/head.tga","IMGTYPE_NORMAL","IMGFLAG_MIPMAP",1,1,0),
      ("models/powerups/health/health_l.tga","IMGTYPE_NORMAL","IMGFLAG_MIPMAP",1,1,0),
      ("models/powerups/health/health_l.tga","IMGTYPE_COLORALPHA","0",1,1,0),
      ("models/powerups/health/health_l.tga","IMGTYPE_COLORALPHA","(IMGFLAG_MIPMAP|IMGFLAG_CUBEMAP)",1,1,0),
      ("models/players/axis/head.tga","IMGTYPE_COLORALPHA","IMGFLAG_MIPMAP",0,1,0),
      ("models/powerups/health/health_l.tga","IMGTYPE_COLORALPHA","IMGFLAG_MIPMAP",0,1,0),
      ("models/characters/companion/body.tga","IMGTYPE_COLORALPHA","IMGFLAG_MIPMAP",1,0,0),
      ("models/characters/companion/body.tga","IMGTYPE_COLORALPHA","IMGFLAG_MIPMAP",1,1,1),
      ("models/charactersFake/companion/body.tga","IMGTYPE_COLORALPHA","IMGFLAG_MIPMAP",1,1,0),
      ("MODELS/POWERUPS/AMMO/AMTESLA.TGA","IMGTYPE_COLORALPHA","IMGFLAG_MIPMAP",1,1,1)
    ]
    prelude=r'''#include <stdio.h>
#include <ctype.h>
#include <string.h>
typedef int qboolean;
typedef int imgType_t;
typedef int imgFlags_t;
enum {qfalse=0,qtrue=1,IMGTYPE_COLORALPHA=1,IMGTYPE_NORMAL=2};
enum {IMGFLAG_MIPMAP=1,IMGFLAG_CUBEMAP=2};
static int Q_stricmpn(const char *a,const char *b,int n) {
    for(int i=0;i<n;i++){
        int c=tolower((unsigned char)a[i]),d=tolower((unsigned char)b[i]);
        if(c!=d)return c-d;
        if(!a[i]||!b[i])break;
    } return 0;
}
'''
    s=prelude+"\n".join(parts)+"\nint main(void){\n"
    for i,(name,typ,flags,fidelity,scope,want) in enumerate(cases):
        s+=f' if (DW_V32_ModelMipEligible("{name}",{typ},{flags},{fidelity},{scope})!={want}) {{puts("CASE_{i}_FAIL");return {i+1};}}\n'
    s+=' if (DW_V32_ModelMipEligible(NULL,IMGTYPE_COLORALPHA,IMGFLAG_MIPMAP,1,1)) return 100;\n'
    s+=' puts("DW_V32_NATIVE_MODEL_ONLY_SAMPLING_PREDICATE_PASS");return 0;}\n'
    c=a.out/"dw_v32_select.c";c.write_text(s)
    binary=a.out/"dw_v32_select"
    subprocess.run(["gcc","-std=c99","-O2","-Wall","-Wextra","-Werror",str(c),"-o",str(binary)],check=True)
    r=subprocess.run([str(binary)],capture_output=True,text=True,check=True)
    assert "DW_V32_NATIVE_MODEL_ONLY_SAMPLING_PREDICATE_PASS" in r.stdout,r.stdout
    print(r.stdout.strip())
    test={"test_count":len(cases)+1,"pass":True,
          "source_compiled":True,
          "negative_cases_included":["world BSP","mapobjects","UI","normal map","nonmip","cubemap","fidelity off","scope off"],
          "config_default_zero":True,
          "no_gl_call_for_zero_bias":True,
          "bounded_bias":[-0.50,0],
          "real_gpu_test":"PENDING"}
    (a.out/"DW_V32_NATIVE_TEST.json").write_text(json.dumps(test,indent=2)+"\n")
    print("DW_V32_STATIC_AND_NATIVE_TEST_PASS")
if __name__=="__main__":main()
