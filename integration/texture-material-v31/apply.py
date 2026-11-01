#!/usr/bin/env python3
"""V3.1: diagnostic-only instrumentation of accepted V3 model texture policy.

No new rendering decisions, filters, shaders, offsets, mip generation, or cvar defaults.
New explicit command "r_dwModelFidelityReport [powerups|all|substring]"
prints actual model texture load metadata and whether *V3 added* NO_COMPRESSION.
Status for visual benefit is intentionally not inferred from format alone.
"""
from pathlib import Path
import argparse, hashlib, json, shutil, tempfile

ROOT=Path("SP/code/rend2")
MARK="DARKWOLF_MODEL_FIDELITY_V31_REPORT_20261101"
V3="DARKWOLF_TEXTURE_MATERIAL_V3_OPTIN_MODELS_20261031"

def h(s): return hashlib.sha256(s).hexdigest()

def once(text,needle,replacement,label):
    n=text.count(needle)
    if n != 1: raise RuntimeError(f"{label}: expected 1 anchor, got {n}: {needle[:100]}")
    return text.replace(needle,replacement,1)

HELPER=r"""
// DARKWOLF_MODEL_FIDELITY_V31_REPORT_20261101
// Only per-image diagnostic metadata. No rendering or texture allocation changes.
typedef struct {
    const image_t *image;
    int sourceWidth, sourceHeight;
    int originalFlags, originalFormat;
    qboolean noCompressionFlagAddedByV3;
} DW_V31ImageTrace_t;
static DW_V31ImageTrace_t dwV31ImageTrace[MAX_DRAWIMAGES];

static qboolean DW_V31IsPOT(int v) {
    return v > 0 && !(v & (v - 1));
}

static qboolean DW_V31IsCompressedFormat(GLenum fmt) {
    switch (fmt) {
    case GL_COMPRESSED_RGB_S3TC_DXT1_EXT:
    case GL_COMPRESSED_RGBA_S3TC_DXT1_EXT:
    case GL_COMPRESSED_RGBA_S3TC_DXT5_EXT:
    case GL_COMPRESSED_SRGB_ALPHA_S3TC_DXT1_EXT:
    case GL_COMPRESSED_SRGB_ALPHA_S3TC_DXT5_EXT:
    case GL_COMPRESSED_RGB_BPTC_SIGNED_FLOAT_ARB:
    case GL_COMPRESSED_RGBA_BPTC_UNORM_ARB:
    case GL_COMPRESSED_SRGB_ALPHA_BPTC_UNORM_ARB:
    case GL_COMPRESSED_RG_RGTC2:
        return qtrue;
    default:
        return qfalse;
    }
}

// Diagnostic on demand. Importantly, neither this function nor its trace
// touches texture filtering, shaders, FBOs, or world images.
void DW_V31_ModelFidelityReport_f(void) {
    int i, v2 = 0, ext = 0, visible = 0, eligible = 0, added = 0;
    int nonpot = 0, compressed = 0, untraced = 0;
    const char *filter = ri.Cmd_Argc() > 1 ? ri.Cmd_Argv(1) : "";
    qboolean showAll = !Q_stricmp(filter, "all");
    qboolean v3Active = r_dwTextureFidelity && r_dwTextureFidelity->integer &&
                         r_dwModelTextureScope && r_dwModelTextureScope->integer;
    ri.Printf(PRINT_ALL,
       "\n[DWV31] scope=%i textureFidelity=%i picmip=%i picmip2=%i "
       "minFilter=0x%x magFilter=0x%x anisoConfigured=%i "
       "(filters are global settings, not GPU sampling measurements)\n",
       r_dwModelTextureScope ? r_dwModelTextureScope->integer : -1,
       r_dwTextureFidelity ? r_dwTextureFidelity->integer : -1,
       r_picmip ? r_picmip->integer : -1,
       r_picmip2 ? r_picmip2->integer : -1,
       (unsigned int)gl_filter_min, (unsigned int)gl_filter_max,
       r_ext_max_anisotropy ? r_ext_max_anisotropy->integer : -1);

    for (i = 0; i < tr.numImages; ++i) {
        image_t *im = tr.images[i];
        DW_V31ImageTrace_t *ev = &dwV31ImageTrace[i];
        qboolean oldModel, newModel, tracked, isNPOT, elig;
        if (!im) continue;
        oldModel = DW_IsModelTextureName(im->imgName);
        newModel = DW_IsExtendedModelTextureName(im->imgName);
        if (oldModel) ++v2;
        if (newModel) ++ext;
        if (!newModel && !(showAll && oldModel)) continue;
        if (*filter && !showAll && !strstr(im->imgName, filter)) continue;
        tracked = ev->image == im;
        isNPOT = tracked && (!DW_V31IsPOT(ev->sourceWidth) || !DW_V31IsPOT(ev->sourceHeight));
        elig = newModel && tracked && im->type == IMGTYPE_COLORALPHA &&
               (ev->originalFlags & IMGFLAG_MIPMAP) && v3Active;
        if (elig) ++eligible;
        if (tracked && ev->noCompressionFlagAddedByV3) ++added;
        if (isNPOT) ++nonpot;
        if (DW_V31IsCompressedFormat(im->internalFormat)) ++compressed;
        if (newModel && !tracked) ++untraced;
        ++visible;
        // Three compact records per texture avoid console wrapping in condump.
        ri.Printf(PRINT_ALL,
           "[DWV31] ix=%i c=%s e=%i add=%i origNo=%i mip=%i src=%ix%i up=%ix%i\n",
           i, oldModel ? "V2" : "V3", elig ? 1 : 0,
           (tracked && ev->noCompressionFlagAddedByV3) ? 1 : 0,
           (tracked && (ev->originalFlags & IMGFLAG_NO_COMPRESSION)) ? 1 : 0,
           (im->flags & IMGFLAG_MIPMAP) ? 1 : 0,
           tracked ? ev->sourceWidth : im->width,
           tracked ? ev->sourceHeight : im->height,
           im->uploadWidth, im->uploadHeight);
        ri.Printf(PRINT_ALL,
           "[DWV31] ix=%i gpu=0x%x raw=0x%x cmp=%i npot=%i kept=%i traced=%i\n",
           i, (unsigned int)im->internalFormat,
           tracked ? (unsigned int)ev->originalFormat : 0,
           DW_V31IsCompressedFormat(im->internalFormat) ? 1 : 0,
           isNPOT ? 1 : 0,
           (isNPOT && im->uploadWidth == ev->sourceWidth &&
            im->uploadHeight == ev->sourceHeight) ? 1 : 0,
           tracked ? 1 : 0);
        ri.Printf(PRINT_ALL, "[DWV31] ix=%i name=%s\n", i, im->imgName);
    }
    ri.Printf(PRINT_ALL,
      "[DWV31] SUMMARY loadedV2=%i loadedV3=%i shown=%i eligibleV3=%i "
      "newNoCompressionFlags=%i nonPOTshown=%i GPUcompressedShown=%i "
      "untracedV3=%i\n",
      v2,ext,visible,eligible,added,nonpot,compressed,untraced);
    ri.Printf(PRINT_ALL,
      "[DWV31] IMPORTANT: FLAG_ADDED records an actual V3 flag change "
      "at first image load, NOT a proven visual benefit. "
      "Compare TWO reports after separate vid_restart to establish GPU-format differences.\n");
}

"""

def image(t):
    assert V3 in t and MARK not in t
    t=once(t,
       "typedef struct {\n\tchar *name;",
       HELPER+"typedef struct {\n\tchar *name;",
       "diagnostic data and report next to V3 classifier")
    t=once(t,
       "imgFlags_t checkFlagsTrue, checkFlagsFalse;\n",
       "imgFlags_t checkFlagsTrue, checkFlagsFalse;\n"
       "\timgFlags_t dwV31OriginalFlags = flags;\n"
       "\tqboolean dwV31AddedNoComp = qfalse;\n",
       "capture incoming flags")
    t=once(t,
       "else if (r_dwTextureFidelity->integer && r_dwModelTextureScope &&\n"
       "\t         r_dwModelTextureScope->integer && type == IMGTYPE_COLORALPHA &&\n"
       "\t         (flags & IMGFLAG_MIPMAP) && DW_IsExtendedModelTextureName(name))\n"
       "\t{\n"
       "\t\tflags |= IMGFLAG_NO_COMPRESSION;\n"
       "\t}\n",
       "else if (r_dwTextureFidelity->integer && r_dwModelTextureScope &&\n"
       "\t         r_dwModelTextureScope->integer && type == IMGTYPE_COLORALPHA &&\n"
       "\t         (flags & IMGFLAG_MIPMAP) && DW_IsExtendedModelTextureName(name))\n"
       "\t{\n"
       "\t\t// "+MARK+": record policy change without changing condition/behavior.\n"
       "\t\tdwV31AddedNoComp = !(flags & IMGFLAG_NO_COMPRESSION);\n"
       "\t\tflags |= IMGFLAG_NO_COMPRESSION;\n"
       "\t}\n",
       "trace the existing V3 flag decision")
    t=once(t,
       "image = R_CreateImageExt2( ( char * ) name, pic, width, height, picFormat, picNumMips, type, flags, 0, characterMIP );\n"
       "\tri.Free( pic );",
       "image = R_CreateImageExt2( ( char * ) name, pic, width, height, picFormat, picNumMips, type, flags, 0, characterMIP );\n"
       "\t// "+MARK+": trace only loaded extended models, do not alter GPU state.\n"
       "\tif (image && DW_IsExtendedModelTextureName(name) && tr.numImages > 0 &&\n"
       "\t    tr.images[tr.numImages - 1] == image) {\n"
       "\t\tDW_V31ImageTrace_t *ev = &dwV31ImageTrace[tr.numImages - 1];\n"
       "\t\tev->image = image;\n"
       "\t\tev->sourceWidth = width;\n"
       "\t\tev->sourceHeight = height;\n"
       "\t\tev->originalFlags = dwV31OriginalFlags;\n"
       "\t\tev->originalFormat = picFormat;\n"
       "\t\tev->noCompressionFlagAddedByV3 = dwV31AddedNoComp;\n"
       "\t}\n"
       "\tri.Free( pic );",
       "store actual decisions after image upload")
    t=once(t,
       "Com_Memset(hashTable, 0, sizeof(hashTable));",
       "Com_Memset(hashTable, 0, sizeof(hashTable));\n"
       "\t// "+MARK+": fresh snapshot after renderer initialization.\n"
       "\tCom_Memset(dwV31ImageTrace, 0, sizeof(dwV31ImageTrace));",
       "reset traces with normal image init")
    return t

def header(t):
    assert MARK not in t
    return once(t,"void\tR_ImageList_f( void );",
      "void\tR_ImageList_f( void );\n// "+MARK+"\nvoid DW_V31_ModelFidelityReport_f(void);",
      "one exported diagnostic command function")

def init(t):
    assert MARK not in t
    t=once(t,'ri.Cmd_AddCommand( "imagelist", R_ImageList_f );',
        'ri.Cmd_AddCommand( "imagelist", R_ImageList_f );\n'
        '\t// '+MARK+': read-only explicit diagnostic.\n'
        '\tri.Cmd_AddCommand( "r_dwModelFidelityReport", DW_V31_ModelFidelityReport_f );',
        "register report console command")
    t=once(t,'ri.Cmd_RemoveCommand( "imagelist" );',
        'ri.Cmd_RemoveCommand( "imagelist" );\n'
        '\tri.Cmd_RemoveCommand( "r_dwModelFidelityReport" );',
        "unregister report on renderer shutdown")
    return t

def apply(root,dry=False):
    root=Path(root)
    names={"tr_image.c":image,"tr_local.h":header,"tr_init.c":init}
    if dry:
        with tempfile.TemporaryDirectory() as td:
            dst=Path(td)
            protected=("tr_backend.c","tr_shade.c","tr_shader.c",
                       "tr_fbo.c","glsl/dwfinal_fp.glsl")
            for k in tuple(names) + protected:
                out=dst/ROOT/k
                out.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(root/ROOT/k,out)
            return apply(dst,False)
    diffs={}
    for n,fn in names.items():
        p=root/ROOT/n
        old=p.read_bytes()
        new=fn(old.decode("utf-8")).encode("utf-8")
        assert old!=new and MARK.encode() in new
        p.write_bytes(new)
        diffs[str(ROOT/n)]={"sha256_before":h(old),"sha256_after":h(new)}
    image_source=(root/ROOT/"tr_image.c").read_text()
    assert image_source.count("flags |= IMGFLAG_NO_COMPRESSION;") >= 1
    assert "DW_V31_ModelFidelityReport_f" in image_source
    assert "dwV31ImageTrace[tr.numImages - 1]" in image_source
    assert "DW_IsExtendedModelTextureName(name)" in image_source
    assert "r_dwModelTextureScope->integer && type == IMGTYPE_COLORALPHA" in image_source
    assert "DW_MipMapCutout" not in image_source
    assert "r_dwLut" in (root/ROOT/"tr_init.c").read_text()
    for protected in ("tr_backend.c","tr_shade.c","tr_shader.c","tr_fbo.c","glsl/dwfinal_fp.glsl"):
        assert MARK not in (root/ROOT/protected).read_text()
    proof={
       "parent":"V3 Exact V2-derived Actions 41202805738",
       "base_production":41019985033,
       "changed_files":diffs,
       "render_algorithms_modified":False,
       "cvar_defaults_modified":False,
       "diagnostic_command":"r_dwModelFidelityReport [optional substring|all]",
       "first_load_trace":["original_flags","no_compression_flag_added","source_dimensions","source_format",
                            "uploaded_dimensions","GPU internal format","mip flag"],
       "forbidden_claim":"flag added or POT format alone does not imply visual improvement",
       "gpu_acceptance":"PENDING_USER"
    }
    print("DW_MODEL_FIDELITY_V31_READONLY_DIAGNOSTIC_SOURCE_PASS",len(diffs))
    return proof

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("root",type=Path)
    p.add_argument("--check-only",action="store_true")
    p.add_argument("--proof",type=Path)
    a=p.parse_args()
    proof=apply(a.root,a.check_only)
    if a.proof:a.proof.write_text(json.dumps(proof,indent=2)+"\n")
