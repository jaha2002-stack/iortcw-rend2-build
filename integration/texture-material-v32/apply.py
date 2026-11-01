#!/usr/bin/env python3
"""DarkWolf V3.2: real, strictly opt-in per-model texture LOD bias.

Patches the exact reconstructed V3.1 #41283547717 renderer. At bias=0 (default)
NO GL sampler changes occur. The sole runtime effect when opted in is setting
GL_TEXTURE_LOD_BIAS on specific 2D mipmapped model color textures.
No global filtering/anisotropy settings, no BSP/mapobjects, no GLSL changes.
"""
import argparse,hashlib,json,shutil,tempfile
from pathlib import Path
R=Path("SP/code/rend2")
MARK="DARKWOLF_V32_MODEL_SAMPLING_20261101"
V31="DARKWOLF_MODEL_FIDELITY_V31_REPORT_20261101"
V3="DARKWOLF_TEXTURE_MATERIAL_V3_OPTIN_MODELS_20261031"

def once(s,old,new,label):
    n=s.count(old)
    if n!=1:raise RuntimeError("%s expected=1 found=%d; anchor=%r"%(label,n,old[:110]))
    return s.replace(old,new,1)
def sha(x):return hashlib.sha256(x).hexdigest()

SELECTOR=r"""
// DARKWOLF_V32_MODEL_SAMPLING_20261101
// This is NOT a "models/" wildcard. No BSP textures, mapobjects or render targets.
static qboolean DW_V32_ModelMipEligible(const char *name, imgType_t type,
    imgFlags_t flags, qboolean fidelityOn, qboolean extendedScopeOn)
{
    if (!name || !fidelityOn || type != IMGTYPE_COLORALPHA ||
        !(flags & IMGFLAG_MIPMAP) || (flags & IMGFLAG_CUBEMAP))
        return qfalse;
    if (DW_IsModelTextureName(name))
        return qtrue;
    return extendedScopeOn && DW_IsExtendedModelTextureName(name);
}

"""

def init(s):
    assert V31 in s and MARK not in s
    s=once(s,"cvar_t *r_dwModelTextureScope;",
           "cvar_t *r_dwModelTextureScope;\n// "+MARK+"\ncvar_t *r_dwModelMipBias;",
           "CVar global declaration")
    old='\tri.Cvar_CheckRange(r_dwModelTextureScope, 0, 1, qtrue);'
    new=(old+'\n\t// '+MARK+': opt-in only; -0.50..0.00 levels, default 0 == V3.1.\n'
        '\tr_dwModelMipBias = ri.Cvar_Get("r_dwModelMipBias", "0", CVAR_ARCHIVE | CVAR_LATCH);\n'
        '\tri.Cvar_CheckRange(r_dwModelMipBias, -0.50f, 0.00f, qfalse);')
    return once(s,old,new,"CVar registration")

def header(s):
    assert V31 in s and MARK not in s
    return once(s,"extern cvar_t *r_dwModelTextureScope;",
                "extern cvar_t *r_dwModelTextureScope;\n// "+MARK+"\nextern cvar_t *r_dwModelMipBias;",
                "CVar extern")

def image(s):
    assert V31 in s and V3 in s and MARK not in s
    s=once(s,
       "typedef struct {\n\tchar *name;",
       SELECTOR+"typedef struct {\n\tchar *name;",
       "pure model/mipmap selector")
    s=once(s,
       "    qboolean noCompressionFlagAddedByV3;\n} DW_V31ImageTrace_t;",
       "    qboolean noCompressionFlagAddedByV3;\n    float actualMipBiasRequest; // "+MARK+"\n} DW_V31ImageTrace_t;",
       "trace field")
    # Extend the load trace only; old V3.1 command is still compatible.
    s=once(s,
       'if (image && DW_IsExtendedModelTextureName(name) && tr.numImages > 0 &&',
       'if (image && (DW_IsExtendedModelTextureName(name) || DW_IsModelTextureName(name)) &&\n'
       '\t    tr.numImages > 0 &&',
       "extend report trace to V2 model classes")
    old=("\t\tev->noCompressionFlagAddedByV3 = dwV31AddedNoComp;\n"
         "\t}\n"
         "\tri.Free( pic );")
    new=("\t\tev->noCompressionFlagAddedByV3 = dwV31AddedNoComp;\n"
         "\t}\n"
         "\t// "+MARK+": independent per-texture LOD request. The 0.0 default is no-op.\n"
         "\t// Only model color images with authored mipmaps; never cubemaps/world/UI/normal maps.\n"
         "\tif (image && r_dwModelMipBias && r_dwModelMipBias->value < -0.0001f &&\n"
         "\t    DW_V32_ModelMipEligible(name, type, image->flags,\n"
         "\t        r_dwTextureFidelity && r_dwTextureFidelity->integer,\n"
         "\t        r_dwModelTextureScope && r_dwModelTextureScope->integer)) {\n"
         "\t\tfloat applied = Com_Clamp(-0.50f, 0.00f, r_dwModelMipBias->value);\n"
         "\t\tqglTextureParameterfEXT(image->texnum, GL_TEXTURE_2D, GL_TEXTURE_LOD_BIAS, applied);\n"
         "\t\tif (tr.numImages > 0 && tr.images[tr.numImages - 1] == image)\n"
         "\t\t\tdwV31ImageTrace[tr.numImages - 1].actualMipBiasRequest = applied;\n"
         "\t}\n"
         "\tri.Free( pic );")
    s=once(s,old,new,"apply bias after actual model image upload")
    # Render diagnostic reports record the request actually made for each GPU object.
    old2=("[DWV31] ix=%i gpu=0x%x raw=0x%x cmp=%i npot=%i kept=%i traced=%i\\n")
    new2=("[DWV31] ix=%i gpu=0x%x raw=0x%x cmp=%i npot=%i kept=%i traced=%i bias=%.2f\\n")
    s=once(s,old2,new2,"diagnostic line, compact")
    s=once(s,
       "           tracked ? 1 : 0);\n        ri.Printf(PRINT_ALL, \"[DWV31] ix=%i name=%s\\n\", i, im->imgName);",
       "           tracked ? 1 : 0,\n           tracked ? ev->actualMipBiasRequest : 0.0f);\n"
       "        ri.Printf(PRINT_ALL, \"[DWV31] ix=%i name=%s\\n\", i, im->imgName);",
       "diagnostic value")
    s=once(s,
       "    for (i = 0; i < tr.numImages; ++i) {",
       "    // "+MARK+": report configured value separately from actual per-image requests.\n"
       "    ri.Printf(PRINT_ALL, \"[DWV32] configBias=%.2f scope=%i (zero means sampler untouched)\\n\",\n"
       "      r_dwModelMipBias ? r_dwModelMipBias->value : 0.0f,\n"
       "      r_dwModelTextureScope ? r_dwModelTextureScope->integer : -1);\n"
       "    for (i = 0; i < tr.numImages; ++i) {",
       "header bias info")
    # Compatibility: if older include omits enum, use OpenGL 1.4 constant; no behavior change.
    s=once(s,
       "#include \"tr_local.h\"\n",
       "#include \"tr_local.h\"\n"
       "#ifndef GL_TEXTURE_LOD_BIAS\n#define GL_TEXTURE_LOD_BIAS 0x8501\n#endif\n",
       "OpenGL LOD bias enum")
    return s

def apply(root,dry=False):
    root=Path(root)
    funcs={"tr_init.c":init,"tr_local.h":header,"tr_image.c":image}
    protected=("tr_backend.c","tr_shade.c","tr_shader.c","tr_fbo.c",
               "glsl/dwfinal_fp.glsl","glsl/lightall_fp.glsl")
    if dry:
        with tempfile.TemporaryDirectory() as td:
            dst=Path(td)
            for n in tuple(funcs)+protected:
                path=dst/R/n
                path.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(root/R/n,path)
            return apply(dst,False)
    changed={}
    for name,fn in funcs.items():
        p=root/R/name
        before=p.read_bytes()
        after=fn(before.decode("utf-8")).encode()
        assert after!=before and MARK.encode() in after
        p.write_bytes(after)
        changed[str(R/name)]={"before":sha(before),"after":sha(after)}
    im=(root/R/"tr_image.c").read_text()
    init_text=(root/R/"tr_init.c").read_text()
    assert "r_dwModelMipBias" in im
    assert 'ri.Cvar_Get("r_dwModelMipBias", "0", CVAR_ARCHIVE | CVAR_LATCH)' in init_text
    assert im.count("GL_TEXTURE_LOD_BIAS, applied") == 1
    assert im.count("DW_V32_ModelMipEligible(") == 2
    assert im.count("DW_IsModelTextureName(name)") >= 2
    assert "DW_MipMapCutout" not in im
    for f in protected:
        assert MARK not in (root/R/f).read_text()
    report={
      "parent_run":41283547717,"original_clean_base_run":41019985033,
      "changed_source_files":changed,
      "new_cvar":{"r_dwModelMipBias":{"default":"0","minimum":-0.50,"maximum":0.0,"latched":True}},
      "only_new_gl_change":"GL_TEXTURE_LOD_BIAS for allowlisted, mipmapped 2D color model images when value is negative",
      "excluded":["textures/ BSP","models/mapobjects/","particle","sky","UI",
                  "render targets","cubemaps","normal maps","images without mipmaps"],
      "no_global_texture_filter_change":True,"anisotropy_unchanged":True,
      "renderer_cvar_defaults_preserved":True,"new_cvar_default_noop":True,
      "no_shader_or_postprocess_files_modified":True,
      "real_windows_gpu_image_test":"PENDING"}
    print("DW_V32_MODEL_PER_TEXTURE_LOD_BIAS_PATCH_PASS",len(changed))
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("root",type=Path)
    p.add_argument("--check-only",action="store_true")
    p.add_argument("--proof",type=Path)
    a=p.parse_args()
    result=apply(a.root,a.check_only)
    if a.proof:a.proof.write_text(json.dumps(result,indent=2)+"\n")
