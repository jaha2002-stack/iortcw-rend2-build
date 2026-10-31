#!/usr/bin/env python3
"""Native scope/negative-case tests for the exact compiled V3 classifier."""
from pathlib import Path
import argparse,subprocess,tempfile,json,re,hashlib

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("root",type=Path)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    p=a.root/"SP/code/rend2"
    image=(p/"tr_image.c").read_text()
    init=(p/"tr_init.c").read_text()
    shader=(p/"tr_shader.c").read_text()
    shade=(p/"tr_shade.c").read_text()
    backend=(p/"tr_backend.c").read_text()
    beg=image.index("static qboolean DW_IsExtendedModelTextureName(")
    end=image.index("\ntypedef struct {\n\tchar *name;",beg)
    func=image[beg:end]
    assert func.count("static qboolean")==1
    # No wildcard "models/" or BSP/world admitted by the new helper.
    tests=[
      ("models/characters/axis.tga",1),
      ("models/enemies/guard.tga",1),
      ("models/monsters/beast.tga",1),
      ("models/items/medkit.tga",1),
      ("models/powerups/pack.tga",1),
      ("MODELS/ITEMS/MEDKIT.TGA",1),
      ("models/mapobjects/grate.tga",0),
      ("models/mapobjects/lamp.tga",0),
      ("textures/metal/grate.tga",0),
      ("textures/brick/wall.tga",0),
      ("models/players/axis/body.tga",0),
      ("models/weapons2/mp40/mp40.tga",0),
      ("models/itemsFake/test.tga",0),
      ("models/charactersFake/test.tga",0),
      ("ui/assets/icon.tga",0),
      ("gfx/2d/crosshair.tga",0),
      ("models/props/largewall.tga",0),
      ("models/items",0),
      ("",0),
    ]
    c=r'''#include <stdio.h>
#include <ctype.h>
#include <string.h>
typedef int qboolean;
enum { qfalse=0, qtrue=1 };
static int Q_stricmpn(const char *a,const char *b,int n) {
    int i;
    for (i=0;i<n;i++){
       unsigned char ca=(unsigned char)a[i],cb=(unsigned char)b[i];
       int x=tolower(ca),y=tolower(cb);
       if(x!=y)return x-y;
       if(!ca||!cb)break;
    }
    return 0;
}
''' +func+'\nint main(void){\n'
    for n,(path,expected) in enumerate(tests):
        c+='  if (DW_IsExtendedModelTextureName("'+path+'")!='+str(expected)+') {printf("FAIL '+str(n)+'\\n");return '+str(n+1)+';}\n'
    c+='  if (DW_IsExtendedModelTextureName(NULL)) return 99;\n'
    c+='  puts("DW_V3_NATIVE_MODEL_SCOPE_POSITIVE_NEGATIVE_PASS");\n  return 0;\n}\n'
    f=a.out/"DW_MODEL_V3_class_test.c";f.write_text(c)
    binary=a.out/"DW_MODEL_V3_class_test"
    subprocess.run(["gcc","-std=c99","-Wall","-Wextra","-Werror","-O2",str(f),"-o",str(binary)],check=True)
    run=subprocess.run([str(binary)],capture_output=True,text=True,check=True)
    print(run.stdout.strip())
    assert "DW_V3_NATIVE_MODEL_SCOPE_POSITIVE_NEGATIVE_PASS" in run.stdout
    assert 'r_dwModelTextureScope = ri.Cvar_Get("r_dwModelTextureScope", "0", CVAR_ARCHIVE | CVAR_LATCH);' in init
    assert "r_dwModelTextureScope->integer && type == IMGTYPE_COLORALPHA" in image
    assert "(flags & IMGFLAG_MIPMAP) && DW_IsExtendedModelTextureName(name)" in image
    assert "characterMIP = qtrue;" in image
    assert "if (r_dwTextureFidelity->integer && DW_IsModelTextureName(name))" in image
    assert "DARKWOLF_TEXTURE_MATERIAL_QUALITY_V2_41019985033" in init
    assert "DARKWOLF_SUN_HDR16F_PRECISION_V1_40878732886" in backend
    assert "DARKWOLF_PORTAL_SKY_SINGLE_SAMPLE_UNIVERSAL_V1" in backend
    assert "DW_MipMapCutout" not in image
    assert 'DW_IsExtendedModelTextureName' not in shader
    assert 'DW_IsExtendedModelTextureName' not in shade
    result={"tests":len(tests)+1,"native_binary_compiled":True,
            "world_BSP_negative":["textures/metal/grate.tga","models/mapobjects/grate.tga"],
            "V2_default_scope_zero":True,"source_reference":"V2 -> V3 exact postpatch",
            "shader_and_global_fx_paths_unmodified":True,"visual_approval":"PENDING"}
    (a.out/"DW_MODEL_V3_TEST_REPORT.json").write_text(json.dumps(result,indent=2)+"\n")
    print("DW_MODEL_FIDELITY_V3_STATIC_SCOPE_AUDIT_PASS")
if __name__=="__main__":
    main()
