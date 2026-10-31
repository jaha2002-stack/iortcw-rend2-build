#!/usr/bin/env python3
"""V3 opt-in model texture class extension, strictly on V2 exact 41019985033 source.

Only R_Register cvar registration, tr_local extern and tr_image model-image
classification may change. Default 0 retains V2 image code behavior.
No BSP, world-shader, mapobjects, A2C, LUT, CAS, sky, HDR or shadow changes.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,tempfile

R=Path("SP/code/rend2")
V2="DARKWOLF_TEXTURE_MATERIAL_QUALITY_V2_41019985033"
V3="DARKWOLF_TEXTURE_MATERIAL_V3_OPTIN_MODELS_20261031"

def repl(s,old,new,label):
    count=s.count(old)
    if count!=1: raise RuntimeError("%s expected=1 found=%s : %s"%(label,count,old[:120]))
    return s.replace(old,new,1)

def sha(data):
    return hashlib.sha256(data).hexdigest()

# Explicit allowlist rather than "models/" wildcard: authored BSP model/prop
# surfaces may otherwise change unexpectedly. This is intentionally conservative.
HELPER=r"""
// DARKWOLF_TEXTURE_MATERIAL_V3_OPTIN_MODELS_20261031
// Independent model-asset whitelist, not a BSP or arbitrary models/ wildcard.
// Original players/weapons continue to be classified by DW_IsModelTextureName.
static qboolean DW_IsExtendedModelTextureName(const char *name)
{
    if (!name) return qfalse;
    return !Q_stricmpn(name, "models/characters/", sizeof("models/characters/") - 1) ||
           !Q_stricmpn(name, "models/enemies/", sizeof("models/enemies/") - 1) ||
           !Q_stricmpn(name, "models/monsters/", sizeof("models/monsters/") - 1) ||
           !Q_stricmpn(name, "models/items/", sizeof("models/items/") - 1) ||
           !Q_stricmpn(name, "models/powerups/", sizeof("models/powerups/") - 1);
}

"""

def init(s):
    assert V2 in s and V3 not in s
    s=repl(s,"cvar_t *r_dwMaterialFidelity;",
          "cvar_t *r_dwMaterialFidelity;\n// "+V3+"\ncvar_t *r_dwModelTextureScope;",
          "new standalone CVar global")
    start='r_dwMaterialFidelity = ri.Cvar_Get("r_dwMaterialFidelity", "1", CVAR_ARCHIVE | CVAR_LATCH);'
    assert start in s,"source must preserve accepted V2 material default ON"
    s=repl(s,start,
        start+'\n\t// '+V3+': 0=V2 exact; 1=additional curated nonworld model assets.\n'
        '\tr_dwModelTextureScope = ri.Cvar_Get("r_dwModelTextureScope", "0", CVAR_ARCHIVE | CVAR_LATCH);\n'
        '\tri.Cvar_CheckRange(r_dwModelTextureScope, 0, 1, qtrue);',
        "new CVar registration after material toggle")
    return s

def header(s):
    assert V2 not in s or V3 not in s
    return repl(s,"extern cvar_t *r_dwMaterialFidelity;",
                "extern cvar_t *r_dwMaterialFidelity;\n// "+V3+"\nextern cvar_t *r_dwModelTextureScope;",
                "renderer extern")

def image(s):
    assert V3 not in s and "static qboolean DW_IsModelTextureName" in s
    # Use a bounded, unique struct anchor immediately after the V2 classifier.
    # No edits to DW_IsModelTextureName, so the V2 path stays bit-for-bit stable.
    s=repl(s,"typedef struct {\n\tchar *name;",HELPER+"typedef struct {\n\tchar *name;",
           "extended asset classifier")
    old="(r_dwTextureFidelity->integer && DW_IsModelTextureName(name)), &resampledBuffer)"
    new=("(r_dwTextureFidelity->integer &&\n"
         "               (DW_IsModelTextureName(name) ||\n"
         "               (r_dwModelTextureScope && r_dwModelTextureScope->integer &&\n"
         "                type == IMGTYPE_COLORALPHA && DW_IsExtendedModelTextureName(name)))),\n"
         "               &resampledBuffer)")
    s=repl(s,old,new,"NPOT eligibility only for opted-in model image")
    old="""if (r_dwTextureFidelity->integer && DW_IsModelTextureName(name))
	{
		characterMIP = qtrue;
		flags |= IMGFLAG_NO_COMPRESSION;
	}
"""
    new="""if (r_dwTextureFidelity->integer && DW_IsModelTextureName(name))
	{
		characterMIP = qtrue;
		flags |= IMGFLAG_NO_COMPRESSION;
	}
	// """+V3+""": optional extension, no character picmip override.
	// Existing authored mip flags and r_picmip remain untouched for other models.
	else if (r_dwTextureFidelity->integer && r_dwModelTextureScope &&
	         r_dwModelTextureScope->integer && type == IMGTYPE_COLORALPHA &&
	         (flags & IMGFLAG_MIPMAP) && DW_IsExtendedModelTextureName(name))
	{
		flags |= IMGFLAG_NO_COMPRESSION;
	}
"""
    s=repl(s,old,new,"V2 image lookup compression remains intact")
    assert s.count("DW_IsExtendedModelTextureName(name)") == 2
    assert s.count("DW_IsModelTextureName(name)") >= 2
    return s

def apply(root,dry=False):
    root=Path(root)
    patchers={"tr_init.c":init,"tr_local.h":header,"tr_image.c":image}
    if dry:
        with tempfile.TemporaryDirectory() as td:
            sample=Path(td)
            for filename in patchers:
                target=sample/R/filename
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(root/R/filename,target)
            return apply(sample,False)
    observed={}
    for filename,fn in patchers.items():
        p=root/R/filename
        previous=p.read_bytes()
        assert V3.encode() not in previous,filename+" already patched"
        current=fn(previous.decode("utf-8")).encode("utf-8")
        assert current!=previous
        p.write_bytes(current)
        observed[str(R/filename)]={"previous_sha256":sha(previous),
                                   "patched_sha256":sha(current)}
    source=(root/R/"tr_image.c").read_text()
    assert 'models/mapobjects/' not in source.split("// "+V3,1)[1].split("typedef struct",1)[0]
    assert "r_dwModelTextureScope" in source
    assert "characterMIP = qtrue" in source
    assert "DW_MipMapCutout" not in source
    # There should be no source changes outside these three files.
    proof={"base":"exact V2 source built from Clean Production 41019985033",
           "v2_run":41200040113,
           "defaults":{"r_dwModelTextureScope":"0"},
           "allowed_extensions":["models/characters/","models/enemies/","models/monsters/","models/items/","models/powerups/"],
           "excluded_by_default":["all BSP textures","textures/","models/mapobjects/","UI","sky","particle"],
           "material_algorithm":"unchanged from V2",
           "cas_a2c_lut":"unchanged from V2",
           "all_unrelated_effects":"unchanged",
           "changed_files":observed,
           "local_gpu_validation":"PENDING"}
    print("DW_MODEL_FIDELITY_V3_SAFE_SCOPE_PATCH_PASS",len(observed),flush=True)
    return proof

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("root",type=Path)
    ap.add_argument("--check-only",action="store_true")
    ap.add_argument("--proof",type=Path)
    args=ap.parse_args()
    result=apply(args.root,args.check_only)
    if args.proof: args.proof.write_text(json.dumps(result,indent=2)+"\n")
if __name__=="__main__":
    main()
