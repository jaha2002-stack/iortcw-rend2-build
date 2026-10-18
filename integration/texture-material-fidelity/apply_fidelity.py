#!/usr/bin/env python3
"""DW texture/material fidelity opt-in patch, restricted to exact RC4+CSM tree.

Both quality feature toggles default OFF. Reject unexpected source drift.
Never modify lighting, shadow cache, Bloom, volumetrics, SSGI or release assets.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

MARK = "DARKWOLF_TEXTURE_MATERIAL_FIDELITY_V01"
ROOT = Path("SP/code/rend2")

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def change(text: str, old: str, new: str, context: str, count: int = 1) -> str:
    found = text.count(old)
    if found != count:
        raise RuntimeError(f"{context}: expected {count} anchors, found {found}: {old[:100]!r}")
    return text.replace(old, new)

def apply(root: Path, out: Path | None = None) -> dict:
    changes: dict[str,dict[str,str]] = {}

    def edit(rel: str, update):
        path = root / ROOT / rel
        before = path.read_bytes()
        old = before.decode("utf-8")
        if MARK in old:
            raise RuntimeError(f"{rel}: candidate already applied")
        new = update(old)
        if new == old:
            raise RuntimeError(f"{rel}: no effective changes")
        path.write_bytes(new.encode("utf-8"))
        changes[str(ROOT / rel)] = {"old_sha256": sha(before), "new_sha256": sha(path.read_bytes())}

    def init(txt):
        txt=change(txt, 'cvar_t  *r_genNormalMaps;',
             'cvar_t  *r_genNormalMaps;\n// '+MARK+'\ncvar_t *r_dwTextureFidelity;\ncvar_t *r_dwAdaptiveUpsample;\ncvar_t *r_dwCutoutMip;\ncvar_t *r_dwMaterialFidelity;',
             "cvar globals")
        txt=change(txt, 'r_genNormalMaps = ri.Cvar_Get( "r_genNormalMaps", "0", CVAR_ARCHIVE | CVAR_LATCH );',
            '''r_genNormalMaps = ri.Cvar_Get( "r_genNormalMaps", "0", CVAR_ARCHIVE | CVAR_LATCH );
	// DARKWOLF_TEXTURE_MATERIAL_FIDELITY_V01: OFF by default until real GPU acceptance.
	r_dwTextureFidelity = ri.Cvar_Get("r_dwTextureFidelity", "0", CVAR_ARCHIVE | CVAR_LATCH);
	r_dwAdaptiveUpsample = ri.Cvar_Get("r_dwAdaptiveUpsample", "1", CVAR_ARCHIVE | CVAR_LATCH);
	r_dwCutoutMip = ri.Cvar_Get("r_dwCutoutMip", "1", CVAR_ARCHIVE | CVAR_LATCH);
	r_dwMaterialFidelity = ri.Cvar_Get("r_dwMaterialFidelity", "0", CVAR_ARCHIVE | CVAR_LATCH);
	ri.Cvar_CheckRange(r_dwTextureFidelity, 0, 1, qtrue);
	ri.Cvar_CheckRange(r_dwAdaptiveUpsample, 0, 1, qtrue);
	ri.Cvar_CheckRange(r_dwCutoutMip, 0, 1, qtrue);
	ri.Cvar_CheckRange(r_dwMaterialFidelity, 0, 1, qtrue);''', "init cvars")
        return txt

    def header(txt):
        pat=r'(?m)^([ \t]*extern[ \t]+cvar_t[ \t]+\*r_picmip2;[^\n]*\n)'
        hits=list(re.finditer(pat,txt))
        if len(hits)!=1: raise RuntimeError("tr_local.h: r_picmip2 declaration not unique")
        return txt[:hits[0].end()]+("// "+MARK+"\nextern cvar_t *r_dwTextureFidelity;\nextern cvar_t *r_dwAdaptiveUpsample;\nextern cvar_t *r_dwCutoutMip;\nextern cvar_t *r_dwMaterialFidelity;\n")+txt[hits[0].end():]

    model_helper = r'''
// DARKWOLF_TEXTURE_MATERIAL_FIDELITY_V01: textures intentionally scoped to
// player and gun assets.  Exclude world BSP, particles, skies and post-FX.
static qboolean DW_IsModelTextureName(const char *name)
{
	if (!name) return qfalse;
	return !Q_stricmpn(name, "models/players/", 15) ||
	       !Q_stricmpn(name, "models/weapons2/", 16) ||
	       !Q_stricmpn(name, "models/weapons/", 15);
}

'''

    def image(txt):
        txt=change(txt, 'typedef struct {\n\tchar *name;',
                   model_helper+'typedef struct {\n\tchar *name;', "model texture classifier")
        if txt.count('static qboolean RawImage_ScaleToPower2( byte **data, int *inout_width, int *inout_height, imgType_t type, imgFlags_t flags, qboolean characterMip, byte **resampledBuffer)') != 1:
            raise RuntimeError("Expected RC4 characterMip-capable scaling signature")
        txt=change(txt,'\tqboolean scaled;\n#if 0',
            '''	qboolean scaled;
	// DARKWOLF_TEXTURE_MATERIAL_FIDELITY_V01: select only small diffuse maps.
	int dwUpsampleLevel = r_imageUpsample->integer;
	if (r_dwTextureFidelity->integer && r_dwAdaptiveUpsample->integer &&
	    dwUpsampleLevel == 0 && type == IMGTYPE_COLORALPHA &&
	    picmip && width >= 64 && height >= 64 && width <= 256 && height <= 256 &&
	    !(flags & IMGFLAG_CLAMPTOEDGE))
		dwUpsampleLevel = 1;
#if 0''', "adaptive scaling initializer")
        txt=change(txt,'if (!mipmap)\n\t{\n\t\tscaled_width = width;',
            '''if (!mipmap || (r_dwTextureFidelity->integer && QGL_VERSION_ATLEAST(2, 0)))
	{
		// Modern GL supports NPOT mipmapped images; do not discard original texels.
		scaled_width = width;''',"NPOT guard")
        txt=change(txt,'if ( r_roundImagesDown->integer && scaled_width > width )',
            'if ( !r_dwTextureFidelity->integer && r_roundImagesDown->integer && scaled_width > width )',"rounding X")
        txt=change(txt,'if ( r_roundImagesDown->integer && scaled_height > height )',
            'if ( !r_dwTextureFidelity->integer && r_roundImagesDown->integer && scaled_height > height )',"rounding Y")
        txt=change(txt,'scaled_width < r_imageUpsampleMaxSize->integer && scaled_height < r_imageUpsampleMaxSize->integer)',
            'scaled_width < r_imageUpsampleMaxSize->integer && scaled_height < r_imageUpsampleMaxSize->integer)',"noop placeholder") if False else txt
        txt=change(txt,'picmip && data && resampledBuffer && r_imageUpsample->integer &&',
            'picmip && data && resampledBuffer && dwUpsampleLevel &&',"upscale gate")
        txt=change(txt,'finalwidth = scaled_width << r_imageUpsample->integer;',
            'finalwidth = scaled_width << dwUpsampleLevel;',"upscale X")
        txt=change(txt,'finalheight = scaled_height << r_imageUpsample->integer;',
            'finalheight = scaled_height << dwUpsampleLevel;',"upscale Y")
        # RC4 already fixed characterMip/r_picmip2 selection for ordinary
        # images and DDS; preserve it byte-for-byte instead of reapplying.
        if 'scaled_width >>= r_picmip2->integer;' not in txt or \
           'picmipLevel = characterMip ? r_picmip2->integer : r_picmip->integer;' not in txt:
            raise RuntimeError("RC4 corrected separate character mip selection absent")
        txt=change(txt,'image->flags = flags;',
            'image->flags = flags;\n\timage->characterMIP = characterMip; // '+MARK,"store real character flag",count=1)
        txt=change(txt,'if (!name) {\n\t\treturn NULL;\n\t}\n\n\thash = generateHashValue(name);',
            '''if (!name) {
		return NULL;
	}
	// DARKWOLF_TEXTURE_MATERIAL_FIDELITY_V01: avoid lossy compression
	// and honor separate mip bias for tagged players and weapon textures.
	if (r_dwTextureFidelity->integer && (characterMIP || DW_IsModelTextureName(name)))
	{
		characterMIP = qtrue;
		flags |= IMGFLAG_NO_COMPRESSION;
	}

	hash = generateHashValue(name);''',"image lookup model class")

        helper=r'''
// DARKWOLF_TEXTURE_MATERIAL_FIDELITY_V01: only 1-bit cutouts.
// Avoid averaging RGB from invisible pixels into grate/foliage edges.
static qboolean DW_IsBinaryCutout(const byte *p, int width, int height)
{
	int i, transparent = 0, opaque = 0;
	if (!p || width <= 0 || height <= 0) return qfalse;
	for (i = 0; i < width * height; ++i)
	{
		int a = p[i*4+3];
		if (a == 0) ++transparent;
		else if (a == 255) ++opaque;
		else return qfalse;
	}
	return transparent > 0 && opaque > 0;
}

// Alpha-weighted linear-light RGB; alpha retains the original 2x2 average.
// Software mipmaps are scoped to opt-in RGBA textures, never HDR/depth/DDS.
static void DW_MipMapCutout(byte *p, int width, int height)
{
	int w = MAX(1, width >> 1), h = MAX(1, height >> 1), x, y, c, k;
	for (y=0; y<h; ++y) for (x=0; x<w; ++x)
	{
		const byte *s[4];
		const int x0 = MIN(width - 1, 2*x), x1 = MIN(width - 1, 2*x+1);
		const int y0 = MIN(height - 1, 2*y), y1 = MIN(height - 1, 2*y+1);
		float alpha = 0.0f;
		byte *o = p + 4*(y*w+x);
		s[0] = p + 4*(y0*width+x0);
		s[1] = p + 4*(y0*width+x1);
		s[2] = p + 4*(y1*width+x0);
		s[3] = p + 4*(y1*width+x1);
		for (k=0; k<4; ++k) alpha += s[k][3] / 255.0f;
		for (c=0; c<3; ++c)
		{
			float rgb = 0.0f;
			if (alpha > 0.0f)
			{
				for (k=0; k<4; ++k)
					rgb += powf(s[k][c] / 255.0f, 2.2f) * (s[k][3] / 255.0f);
				o[c] = (byte)CLAMP(255.0f * powf(rgb/alpha, 1.0f/2.2f), 0.0f, 255.0f);
			}
			else o[c] = 0;
		}
		o[3] = (byte)CLAMP(alpha * (255.0f/4.0f) + 0.5f, 0.0f, 255.0f);
	}
}

'''
        txt=change(txt,'static void RawImage_UploadTexture(GLuint texture, byte *data,',
            helper+'static void RawImage_UploadTexture(GLuint texture, byte *data,',"cutout helper")
        txt=change(txt,'qboolean lastMip = qfalse;\n\n\tdataFormat = PixelDataFormatFromInternalFormat(internalFormat);',
            '''qboolean lastMip = qfalse;
	qboolean dwCutout = qfalse;

	if (r_dwTextureFidelity->integer && r_dwCutoutMip->integer &&
	    rgba8 && type == IMGTYPE_COLORALPHA && !(flags & IMGFLAG_CUBEMAP))
		dwCutout = DW_IsBinaryCutout(data, width, height);

	dataFormat = PixelDataFormatFromInternalFormat(internalFormat);''',"cutout detect")
        txt=change(txt,'if (glRefConfig.framebufferObject)\n\t\t\t{\n\t\t\t\tqglGenerateTextureMipmapEXT(texture, target);',
            '''if (glRefConfig.framebufferObject && !(r_dwTextureFidelity->integer && rgba8))
			{
				qglGenerateTextureMipmapEXT(texture, target);''',"prefer linear-light CPU mips")
        txt=change(txt,'else\n\t\t\t\t\tR_MipMapsRGB(data, width, height);',
            '''else if (dwCutout)
					DW_MipMapCutout(data, width, height);
				else
					R_MipMapsRGB(data, width, height);''',"alpha-aware color mip")
        txt=txt.replace('dwUpsampleLevel && \\n', 'dwUpsampleLevel &&\\n')
        return txt

    def shader(txt):
        txt=change(txt,'static char *s_shaderText;',model_helper+'static char *s_shaderText;',"shader material classifier")
        for ntabs in (6, 5):
            txt=change(txt, 'if (r_genNormalMaps->integer)\n' + '\t'*ntabs + 'flags |= IMGFLAG_GENNORMALMAP;',
                '''if (r_genNormalMaps->integer ||
				    (r_dwMaterialFidelity->integer &&
				     (DW_IsModelTextureName(shader.name) || DW_IsModelTextureName(token))))
'''+('\t'*ntabs)+'''flags |= IMGFLAG_GENNORMALMAP;''',"authored material normalmap",count=1)
        txt=change(txt,'if (r_genNormalMaps->integer)\n\t\t\t\tflags |= IMGFLAG_GENNORMALMAP;',
            '''if (r_genNormalMaps->integer ||
			    (r_dwMaterialFidelity->integer && DW_IsModelTextureName(name)))
				flags |= IMGFLAG_GENNORMALMAP;''',"implicit material normals")
        return txt

    def glsl_c(txt):
        # Scope injection strictly to the lightall shader permutation loop.
        begin=txt.find('for (i = 0; i < LIGHTDEF_COUNT; i++)')
        if begin<0: raise RuntimeError("lightall permutation loop not found")
        end=txt.find('if (glRefConfig.swizzleNormalmap)',begin)
        if end<0 or end-begin>2500: raise RuntimeError("lightall shader insertion scope drift")
        anchor='extradefines[0] = \'\\0\';'
        section=txt[begin:end]
        if section.count(anchor)!=1: raise RuntimeError("ambiguous lightall define initialization")
        section=section.replace(anchor,anchor+'''
        // DARKWOLF_TEXTURE_MATERIAL_FIDELITY_V01: isolate animated lightall.
        if (r_dwMaterialFidelity->integer &&
            (i & (LIGHTDEF_ENTITY_VERTEX_ANIMATION | LIGHTDEF_ENTITY_BONE_ANIMATION)))
            Q_strcat(extradefines, 1024, "#define DW_MATERIAL_FIDELITY\\n");''',1)
        return txt[:begin]+section+txt[end:]

    def glsl_vp(txt):
        txt=change(txt,'''#if defined(USE_LIGHT) && !defined(USE_FAST_LIGHT)
	vec3 bitangent = cross(normal, tangent) * attr_Tangent.w;''',
            '''#if defined(USE_LIGHT) && !defined(USE_FAST_LIGHT)
	// DARKWOLF_TEXTURE_MATERIAL_FIDELITY_V01: animation mixes non-unit normals.
	// Build an orthonormal TBN only for opted-in animated entity lightall.
  #if defined(DW_MATERIAL_FIDELITY) && (defined(USE_VERTEX_ANIMATION) || defined(USE_BONE_ANIMATION))
	normal = dot(normal, normal) > 0.000001 ? normalize(normal) : vec3(0.0, 0.0, 1.0);
	tangent -= normal * dot(normal, tangent);
	if (dot(tangent, tangent) > 0.000001)
		tangent = normalize(tangent);
	else
		tangent = normalize(cross(abs(normal.z) < 0.9 ? vec3(0.0, 0.0, 1.0) : vec3(0.0, 1.0, 0.0), normal));
  #endif
	vec3 bitangent = cross(normal, tangent) * attr_Tangent.w;''',"animated orthonormal TBN")
        return txt

    def glsl_fp(txt):
        anchor = 'reflectance  = CalcDiffuse(diffuse.rgb, NH, EH, roughness);'
        patch = '''// DARKWOLF_TEXTURE_MATERIAL_FIDELITY_V01:
  #if defined(DW_MATERIAL_FIDELITY) && defined(USE_NORMALMAP)
    float dwNormalFootprint = max(dot(dFdx(N), dFdx(N)), dot(dFdy(N), dFdy(N)));
    roughness = clamp(max(roughness, 0.04 + 0.30 * sqrt(max(dwNormalFootprint, 0.0))), 0.04, 1.0);
  #endif
    '''
        return change(txt,anchor,patch+anchor,"normalmap specular antialias")

    if not (root/"SP/code/rend2/tr_scene.c").exists():
        raise RuntimeError("Not an unpacked RC4 game source tree")
    scene = (root/"SP/code/rend2/tr_scene.c").read_text(encoding="utf-8")
    if "DARKWOLF_RC4_FORCE_SUN_CSM_REPRIME_V1" not in scene:
        raise RuntimeError("CSM guard missing; refuse to patch an older release")
    for rel,fn in (
        ("tr_init.c",init),("tr_local.h",header),("tr_image.c",image),
        ("tr_shader.c",shader),("tr_glsl.c",glsl_c),
        ("glsl/lightall_vp.glsl",glsl_vp),("glsl/lightall_fp.glsl",glsl_fp)
    ): edit(rel,fn)
    manifest={
        "candidate":"DARKWOLF_TEXTURE_MATERIAL_FIDELITY_V01",
        "parent":"run 38798189322 + verified RC4 CSM guard",
        "fail_closed":True,
        "default_enabled":False,
        "source_files":changes,
        "unchanged":["tr_scene.c","tr_backend.c","tr_fbo.c","tr_image_dds.c","volumetric GLSL","Bloom GLSL","SSGI GLSL"],
        "gpu_visual_acceptance":"PENDING"
    }
    if out: out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps(manifest,indent=2))
    return manifest

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("root",type=Path)
    parser.add_argument("--manifest",type=Path)
    args=parser.parse_args()
    apply(args.root,args.manifest)
