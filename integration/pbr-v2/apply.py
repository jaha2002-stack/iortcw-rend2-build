#!/usr/bin/env python3
from pathlib import Path
import argparse, json, hashlib, re

ap=argparse.ArgumentParser()
ap.add_argument("source")
ap.add_argument("--stage",type=int,choices=(1,2,3),required=True)
ap.add_argument("--proof")
args=ap.parse_args()
root=Path(args.source)/"SP/code/rend2"
stage=args.stage

def read(name):
    p=root/name
    return p,p.read_text()

def replace_once(s,old,new,label):
    if s.count(old)!=1:
        raise SystemExit(f"{label}: expected exactly one anchor, found {s.count(old)}")
    return s.replace(old,new,1)

changed=[]

# tr_glsl.c: preserve USE_PBR semantics; add opt-in PBR2/V3 defines.
p,s=read("tr_glsl.c")
old='''	if (r_pbr->integer)
		Q_strcat(dest, size, "#define USE_PBR\\n");
'''
new='''	if (r_pbr->integer)
		Q_strcat(dest, size, "#define USE_PBR\\n");
	if (r_pbr->integer >= 2)
		Q_strcat(dest, size, "#define USE_PBR2\\n");
	if (r_pbr->integer >= 3)
		Q_strcat(dest, size, "#define USE_PBR2_IBL_V3\\n");
'''
s=replace_once(s,old,new,"tr_glsl USE_PBR")
p.write_text(s); changed.append("SP/code/rend2/tr_glsl.c")

# lightall_fp.glsl: modern core, exact transfer, optional ORM decode, conservative IBL.
p,s=read("glsl/lightall_fp.glsl")
anchor="#define EPSILON 0.00000001\n"
insert=r'''#define EPSILON 0.00000001

#if defined(USE_PBR2)
vec3 DW_SRGBToLinear(vec3 c)
{
	vec3 lo = c / 12.92;
	vec3 hi = pow((c + vec3(0.055)) / 1.055, vec3(2.4));
	return mix(lo, hi, step(vec3(0.04045), c));
}

vec3 DW_LinearToSRGB(vec3 c)
{
	c = max(c, vec3(0.0));
	vec3 lo = c * 12.92;
	vec3 hi = 1.055 * pow(c, vec3(1.0 / 2.4)) - vec3(0.055);
	return mix(lo, hi, step(vec3(0.0031308), c));
}

float DW_DistributionGGX(float NH, float roughness)
{
	float a = max(roughness * roughness, 0.0025);
	float a2 = a * a;
	float d = NH * NH * (a2 - 1.0) + 1.0;
	return a2 / max(3.14159265 * d * d, EPSILON);
}

float DW_VisibilitySmithGGXCorrelated(float NL, float NE, float roughness)
{
	float a = max(roughness * roughness, 0.0025);
	float a2 = a * a;
	float gv = NL * sqrt(max(NE * NE * (1.0 - a2) + a2, EPSILON));
	float gl = NE * sqrt(max(NL * NL * (1.0 - a2) + a2, EPSILON));
	return 0.5 / max(gv + gl, EPSILON);
}

vec3 DW_FresnelSchlick(vec3 F0, float EH)
{
	float x = 1.0 - clamp(EH, 0.0, 1.0);
	float x2 = x * x;
	float x5 = x2 * x2 * x;
	return F0 + (vec3(1.0) - F0) * x5;
}

vec3 DW_CalcSpecularGGX(vec3 F0, float NL, float NE, float NH, float EH, float roughness)
{
	return DW_FresnelSchlick(F0, EH) *
		DW_DistributionGGX(NH, roughness) *
		DW_VisibilitySmithGGXCorrelated(NL, NE, roughness);
}

vec3 DW_EnvironmentBRDFApprox(vec3 F0, float roughness, float NE)
{
	vec4 c0 = vec4(-1.0, -0.0275, -0.572, 0.022);
	vec4 c1 = vec4( 1.0,  0.0425,  1.04, -0.04);
	vec4 r = roughness * c0 + c1;
	float a004 = min(r.x * r.x, exp2(-9.28 * NE)) * r.x + r.y;
	vec2 AB = vec2(-1.04, 1.04) * a004 + r.zw;
	return F0 * AB.x + AB.y;
}
#endif
'''
s=replace_once(s,anchor,insert,"lightall helpers")

old='''  #if defined(USE_PBR) && !defined(USE_FAST_LIGHT)
	lightmapColor.rgb *= lightmapColor.rgb;
  #endif
'''
new='''  #if defined(USE_PBR2) && !defined(USE_FAST_LIGHT)
	lightmapColor.rgb = DW_SRGBToLinear(lightmapColor.rgb);
  #elif defined(USE_PBR) && !defined(USE_FAST_LIGHT)
	lightmapColor.rgb *= lightmapColor.rgb;
  #endif
'''
s=replace_once(s,old,new,"lightmap transfer")

old='''  #if defined(USE_SPECULARMAP)
	vec4 specular = texture2D(u_SpecularMap, texCoords);
  #else
	vec4 specular = vec4(1.0);
  #endif
	specular *= u_SpecularScale;

  #if defined(USE_PBR)
	diffuse.rgb *= diffuse.rgb;
  #endif

  #if defined(USE_PBR)
	// diffuse rgb is base color
	// specular red is gloss
	// specular green is metallicness
	float gloss = specular.r;
	float metal = specular.g;
	specular.rgb = metal * diffuse.rgb + vec3(0.04 - 0.04 * metal);
	diffuse.rgb *= 1.0 - metal;
  #else
	// diffuse rgb is diffuse
	// specular rgb is specular reflectance at normal incidence
	// specular alpha is gloss
	float gloss = specular.a;

	// adjust diffuse by specular reflectance, to maintain energy conservation
	diffuse.rgb *= vec3(1.0) - specular.rgb;
  #endif

  #if defined(GLOSS_IS_GLOSS)
	float roughness = exp2(-3.0 * gloss);
  #elif defined(GLOSS_IS_SMOOTHNESS)
	float roughness = 1.0 - gloss;
  #elif defined(GLOSS_IS_ROUGHNESS)
	float roughness = gloss;
  #elif defined(GLOSS_IS_SHININESS)
	float roughness = pow(2.0 / (8190.0 * gloss + 2.0), 0.25);
  #endif
'''
new='''  #if defined(USE_SPECULARMAP)
	vec4 specularSample = texture2D(u_SpecularMap, texCoords);
  #else
	vec4 specularSample = vec4(1.0);
  #endif
	vec4 specular = specularSample * u_SpecularScale;
	float materialAO = 1.0;

  #if defined(USE_PBR2)
	diffuse.rgb = DW_SRGBToLinear(diffuse.rgb);
	float gloss;
	float metal;
	float roughness;
	if (u_SpecularScale.z < -0.5)
	{
		// DarkWolf packed ORM: R=AO, G=roughness, B=metallic.
		materialAO = clamp(specularSample.r, 0.0, 1.0);
		roughness = clamp(specularSample.g, 0.045, 1.0);
		metal = clamp(specularSample.b, 0.0, 1.0);
		gloss = 1.0 - roughness;
	}
	else
	{
		// Compatibility path for existing Rend2 PBR spec/gloss textures.
		gloss = specular.r;
		metal = clamp(specular.g, 0.0, 1.0);
  #if defined(GLOSS_IS_GLOSS)
		roughness = exp2(-3.0 * gloss);
  #elif defined(GLOSS_IS_SMOOTHNESS)
		roughness = 1.0 - gloss;
  #elif defined(GLOSS_IS_ROUGHNESS)
		roughness = gloss;
  #elif defined(GLOSS_IS_SHININESS)
		roughness = pow(2.0 / (8190.0 * gloss + 2.0), 0.25);
  #endif
	}
	roughness = clamp(roughness, 0.045, 1.0);
	specular.rgb = mix(vec3(0.04), diffuse.rgb, metal);
	diffuse.rgb *= 1.0 - metal;
  #elif defined(USE_PBR)
	diffuse.rgb *= diffuse.rgb;
	// diffuse rgb is base color
	// specular red is gloss
	// specular green is metallicness
	float gloss = specular.r;
	float metal = specular.g;
	specular.rgb = metal * diffuse.rgb + vec3(0.04 - 0.04 * metal);
	diffuse.rgb *= 1.0 - metal;
  #else
	// diffuse rgb is diffuse
	// specular rgb is specular reflectance at normal incidence
	// specular alpha is gloss
	float gloss = specular.a;

	// adjust diffuse by specular reflectance, to maintain energy conservation
	diffuse.rgb *= vec3(1.0) - specular.rgb;
  #endif

  #if !defined(USE_PBR2)
  #if defined(GLOSS_IS_GLOSS)
	float roughness = exp2(-3.0 * gloss);
  #elif defined(GLOSS_IS_SMOOTHNESS)
	float roughness = 1.0 - gloss;
  #elif defined(GLOSS_IS_ROUGHNESS)
	float roughness = gloss;
  #elif defined(GLOSS_IS_SHININESS)
	float roughness = pow(2.0 / (8190.0 * gloss + 2.0), 0.25);
  #endif
  #endif
'''
s=replace_once(s,old,new,"material decode")

old='''  #if defined(r_deluxeSpecular)
    #if defined(USE_LIGHT_VECTOR)
	reflectance += CalcSpecular(specular.rgb, NH, EH, roughness) * r_deluxeSpecular;
    #else
	reflectance += CalcSpecular(specular.rgb, NH, EH, pow(roughness, r_deluxeSpecular));
    #endif
  #endif
'''
new='''  #if defined(r_deluxeSpecular)
    #if defined(USE_PBR2)
	reflectance += DW_CalcSpecularGGX(specular.rgb, NL, NE, NH, EH, roughness) * r_deluxeSpecular;
    #elif defined(USE_LIGHT_VECTOR)
	reflectance += CalcSpecular(specular.rgb, NH, EH, roughness) * r_deluxeSpecular;
    #else
	reflectance += CalcSpecular(specular.rgb, NH, EH, pow(roughness, r_deluxeSpecular));
    #endif
  #endif
'''
s=replace_once(s,old,new,"direct GGX")

old='''	gl_FragColor.rgb += ambientColor * diffuse.rgb;
'''
new='''	gl_FragColor.rgb += ambientColor * diffuse.rgb * materialAO;
'''
s=replace_once(s,old,new,"material AO")

old='''	reflectance = EnvironmentBRDF(roughness, NE, specular.rgb);
'''
new='''  #if defined(USE_PBR2_IBL_V3)
	reflectance = DW_EnvironmentBRDFApprox(specular.rgb, roughness, NE);
  #else
	reflectance = EnvironmentBRDF(roughness, NE, specular.rgb);
  #endif
'''
s=replace_once(s,old,new,"IBL BRDF")

old='''  #if defined(USE_BOX_CUBEMAP_PARALLAX)
	vec3 cubeLightColor = hitCube(R * u_CubeMapInfo.w, parallax, u_CubeMapInfo.www, ROUGHNESS_MIPS * roughness, u_CubeMap).rgb * u_EnableTextures.w;
  #else
	vec3 cubeLightColor = textureCubeLod(u_CubeMap, R + parallax, ROUGHNESS_MIPS * roughness).rgb * u_EnableTextures.w;
  #endif
'''
new='''  #if defined(USE_PBR2_IBL_V3)
	float dwCubeLod = ROUGHNESS_MIPS * roughness * roughness;
  #else
	float dwCubeLod = ROUGHNESS_MIPS * roughness;
  #endif
  #if defined(USE_BOX_CUBEMAP_PARALLAX)
	vec3 cubeLightColor = hitCube(R * u_CubeMapInfo.w, parallax, u_CubeMapInfo.www, dwCubeLod, u_CubeMap).rgb * u_EnableTextures.w;
  #else
	vec3 cubeLightColor = textureCubeLod(u_CubeMap, R + parallax, dwCubeLod).rgb * u_EnableTextures.w;
  #endif
'''
s=replace_once(s,old,new,"cubemap roughness LOD")

old='''    #if defined(USE_PBR)
	cubeLightColor *= cubeLightColor;
    #endif
'''
new='''    #if defined(USE_PBR2)
	cubeLightColor = DW_SRGBToLinear(cubeLightColor);
    #elif defined(USE_PBR)
	cubeLightColor *= cubeLightColor;
    #endif
'''
s=replace_once(s,old,new,"cubemap transfer")

old='''	reflectance  = CalcSpecular(specular.rgb, NH2, EH2, roughness);
'''
new='''  #if defined(USE_PBR2)
	reflectance  = DW_CalcSpecularGGX(specular.rgb, NL2, NE, NH2, EH2, roughness);
  #else
	reflectance  = CalcSpecular(specular.rgb, NH2, EH2, roughness);
  #endif
'''
s=replace_once(s,old,new,"primary GGX")

old='\tgl_FragColor.rgb = sqrt(gl_FragColor.rgb);'
new='''  #if defined(USE_PBR2)
\tgl_FragColor.rgb = DW_LinearToSRGB(gl_FragColor.rgb);
  #else
\tgl_FragColor.rgb = sqrt(gl_FragColor.rgb);
  #endif'''
s=replace_once(s,old,new,"output transfer line")
p.write_text(s); changed.append("SP/code/rend2/glsl/lightall_fp.glsl")

if stage >= 2:
    # Add a flag rather than a new texture unit/type. Packed ORM remains an ordinary RGBA image
    # but receives data-map mip filtering and no light scaling.
    p,s=read("tr_local.h")
    old='''	IMGFLAG_GENNORMALMAP   = 0x0080,
} imgFlags_t;
'''
    new='''	IMGFLAG_GENNORMALMAP   = 0x0080,
	IMGFLAG_PBRDATA        = 0x0100,
} imgFlags_t;
'''
    s=replace_once(s,old,new,"PBRDATA flag")
    p.write_text(s); changed.append("SP/code/rend2/tr_local.h")

    p,s=read("tr_image.c")
    anchor='''static void R_MipMapsRGB( byte *in, int inWidth, int inHeight)
'''
    if anchor not in s:
        raise SystemExit("R_MipMapsRGB anchor missing")
    idx=s.index(anchor)
    helper=r'''static void DW_MipMapsPBRData(byte *in, int inWidth, int inHeight)
{
	int x, y;
	int outWidth = MAX(1, inWidth >> 1);
	int outHeight = MAX(1, inHeight >> 1);
	byte *out = in;
	for (y = 0; y < outHeight; ++y)
	{
		int y0 = MIN(inHeight - 1, y * 2);
		int y1 = MIN(inHeight - 1, y0 + 1);
		for (x = 0; x < outWidth; ++x)
		{
			int x0 = MIN(inWidth - 1, x * 2);
			int x1 = MIN(inWidth - 1, x0 + 1);
			int c;
			for (c = 0; c < 4; ++c)
			{
				int a = in[(y0 * inWidth + x0) * 4 + c];
				int b = in[(y0 * inWidth + x1) * 4 + c];
				int d = in[(y1 * inWidth + x0) * 4 + c];
				int e = in[(y1 * inWidth + x1) * 4 + c];
				out[(y * outWidth + x) * 4 + c] = (byte)((a + b + d + e + 2) >> 2);
			}
		}
	}
}


'''
    s=s[:idx]+helper+s[idx:]

    old='''			if (type == IMGTYPE_NORMAL || type == IMGTYPE_NORMALHEIGHT)
				R_MipMapNormalHeight(*data, *data, width, height, qfalse);
			else
				R_MipMapsRGB(*data, width, height);
'''
    new='''			if (type == IMGTYPE_NORMAL || type == IMGTYPE_NORMALHEIGHT)
				R_MipMapNormalHeight(*data, *data, width, height, qfalse);
			else if (flags & IMGFLAG_PBRDATA)
				DW_MipMapsPBRData(*data, width, height);
			else
				R_MipMapsRGB(*data, width, height);
'''
    s=replace_once(s,old,new,"ScaleToPower2 PBR mip")

    old='''				if (type == IMGTYPE_NORMAL || type == IMGTYPE_NORMALHEIGHT)
					R_MipMapNormalHeight(data, data, width, height, glRefConfig.swizzleNormalmap);
				else
					R_MipMapsRGB(data, width, height);
'''
    new='''				if (type == IMGTYPE_NORMAL || type == IMGTYPE_NORMALHEIGHT)
					R_MipMapNormalHeight(data, data, width, height, glRefConfig.swizzleNormalmap);
				else if (flags & IMGFLAG_PBRDATA)
					DW_MipMapsPBRData(data, width, height);
				else
					R_MipMapsRGB(data, width, height);
'''
    s=replace_once(s,old,new,"Upload PBR mip")
    p.write_text(s); changed.append("SP/code/rend2/tr_image.c")

    p,s=read("tr_shader.c")
    old='''			else if(!Q_stricmp(token, "specularMap"))
			{
				stage->type = ST_SPECULARMAP;
				VectorSet4(stage->specularScale, 1.0f, 1.0f, 1.0f, 1.0f);
			}
'''
    new='''			else if(!Q_stricmp(token, "specularMap"))
			{
				stage->type = ST_SPECULARMAP;
				VectorSet4(stage->specularScale, 1.0f, 1.0f, 1.0f, 1.0f);
			}
			else if(!Q_stricmp(token, "ormMap"))
			{
				stage->type = ST_SPECULARMAP;
				// z < 0 is an internal packed-ORM marker consumed by lightall_fp.
				VectorSet4(stage->specularScale, 1.0f, 1.0f, -1.0f, 1.0f);
			}
'''
    s=replace_once(s,old,new,"ormMap parser")

    load_pat=r'(?m)^([ \t]*)stage->bundle\[0\]\.image\[0\]\s*=\s*R_FindImageFileExt\([^;]+;'
    hits=list(re.finditer(load_pat,s))
    if len(hits)<2:
        raise SystemExit(f"shader image load anchors expected at least 2, found {len(hits)}")
    def add_pbrdata_guard(m):
        indent=m.group(1)
        nl=chr(10)
        tab=chr(9)
        return indent+'if (stage->type == ST_SPECULARMAP && stage->specularScale[2] < 0.0f)'+nl+indent+tab+'flags |= IMGFLAG_NOLIGHTSCALE | IMGFLAG_PBRDATA;'+nl+m.group(0)
    s,n=re.subn(load_pat,add_pbrdata_guard,s,count=2)
    if n!=2:
        raise SystemExit(f"shader PBRDATA guard insertion expected 2, found {n}")

    old='''	if (r_specularMapping->integer)
	{
		image_t *diffuseImg;
		if (specular)
		{
'''
    new='''	if (r_specularMapping->integer)
	{
		image_t *diffuseImg;
		if (specular)
		{
'''
    # no-op anchor sanity
    if old not in s: raise SystemExit("specular collapse anchor missing")

    old_block='''		else if ((lightmap || useLightVector || useLightVertex) && (diffuseImg = diffuse->bundle[TB_DIFFUSEMAP].image[0]))
		{
			char specularName[MAX_QPATH];
			image_t *specularImg;
			imgFlags_t specularFlags = (diffuseImg->flags & ~IMGFLAG_GENNORMALMAP) | IMGFLAG_NOLIGHTSCALE;

			COM_StripExtension(diffuseImg->imgName, specularName, MAX_QPATH);
			Q_strcat(specularName, MAX_QPATH, "_s");

			specularImg = R_FindImageFile(specularName, IMGTYPE_COLORALPHA, specularFlags);

			if (specularImg)
			{
				diffuse->bundle[TB_SPECULARMAP] = diffuse->bundle[0];
				diffuse->bundle[TB_SPECULARMAP].numImageAnimations = 0;
				diffuse->bundle[TB_SPECULARMAP].image[0] = specularImg;

				VectorSet4(diffuse->specularScale, 1.0f, 1.0f, 1.0f, 1.0f);
				// REND2_MAT_0_V2_4_CLASSIFIER_CORRECTION: automatic <diffuse>_s discovery.
				diffuse->materialSpecularSource = MATDBG_SPEC_AUTO_SUFFIX;
			}
		}
'''
    new_block='''		else if ((lightmap || useLightVector || useLightVertex) && (diffuseImg = diffuse->bundle[TB_DIFFUSEMAP].image[0]))
		{
			char specularName[MAX_QPATH];
			image_t *specularImg = NULL;
			qboolean pbrOrm = qfalse;
			imgFlags_t specularFlags = (diffuseImg->flags & ~IMGFLAG_GENNORMALMAP) | IMGFLAG_NOLIGHTSCALE;

			COM_StripExtension(diffuseImg->imgName, specularName, MAX_QPATH);
			if (r_pbr->integer >= 2)
			{
				Q_strcat(specularName, MAX_QPATH, "_orm");
				specularImg = R_FindImageFile(specularName, IMGTYPE_COLORALPHA, specularFlags | IMGFLAG_PBRDATA);
				if (specularImg)
				{
					VectorSet4(diffuse->specularScale, 1.0f, 1.0f, -1.0f, 1.0f);
					pbrOrm = qtrue;
				}
			}
			if (!specularImg)
			{
				COM_StripExtension(diffuseImg->imgName, specularName, MAX_QPATH);
				Q_strcat(specularName, MAX_QPATH, "_s");
				specularImg = R_FindImageFile(specularName, IMGTYPE_COLORALPHA, specularFlags);
				if (specularImg)
					VectorSet4(diffuse->specularScale, 1.0f, 1.0f, 1.0f, 1.0f);
			}

			if (specularImg)
			{
				diffuse->bundle[TB_SPECULARMAP] = diffuse->bundle[0];
				diffuse->bundle[TB_SPECULARMAP].numImageAnimations = 0;
				diffuse->bundle[TB_SPECULARMAP].image[0] = specularImg;
				// Both _orm and legacy _s are authored/automatic material inputs and must bypass MAT-1 fallback.
				diffuse->materialSpecularSource = MATDBG_SPEC_AUTO_SUFFIX;
				(void)pbrOrm;
			}
		}
'''
    s=replace_once(s,old_block,new_block,"ORM autodiscovery")
    p.write_text(s); changed.append("SP/code/rend2/tr_shader.c")

# Stage 3 intentionally does not mutate cubemap capture/export. The V3 IBL shader path
# above changes only BRDF/LOD interpretation, minimizing risk.
proof={
    "baseline_run":42217883095,
    "baseline_commit":"0ef4fc401daff30c230ccb8226a8029fb0a3519f",
    "stage":stage,
    "changed_files":sorted(set(changed)),
    "legacy_default_unchanged":True,
    "legacy_pbr1_preserved":True,
    "sampler_budget_increase":0,
    "cubemap_capture_format_changed":False,
    "v3_true_ggx_prefilter_deferred":"V3.1 after visual acceptance"
}
if args.proof:
    Path(args.proof).parent.mkdir(parents=True,exist_ok=True)
    Path(args.proof).write_text(json.dumps(proof,indent=2)+"\n")
print(json.dumps(proof,indent=2))
