#!/usr/bin/env python3
from pathlib import Path
import argparse, json

ap=argparse.ArgumentParser()
ap.add_argument("source")
ap.add_argument("--proof")
args=ap.parse_args()

root=Path(args.source)/"SP/code/rend2"
changed=[]

def rw(rel):
    p=root/rel
    return p,p.read_text()

def one(s,old,new,label):
    n=s.count(old)
    if n!=1:
        raise SystemExit(f"{label}: expected 1 anchor, found {n}")
    return s.replace(old,new,1)

# ---------------------------------------------------------------------------
# Public command prototype.
# ---------------------------------------------------------------------------
p,s=rw("tr_local.h")
s=one(s,
'''void		R_ShaderList_f( void );
void    R_RemapShader(const char *oldShader, const char *newShader, const char *timeOffset);
''',
'''void		R_ShaderList_f( void );
void		R_PbrMaterialAudit_f( void );
void    R_RemapShader(const char *oldShader, const char *newShader, const char *timeOffset);
''',"audit prototype")
p.write_text(s); changed.append("SP/code/rend2/tr_local.h")

# ---------------------------------------------------------------------------
# Runtime audit reads the already-collapsed shader stage. This reports what
# LightAll actually received, not what a PK3 author intended to bind.
# ---------------------------------------------------------------------------
p,s=rw("tr_shader.c")
anchor='''/*
===============
R_ShaderList_f

Dump information on all valid shaders to the console
A second parameter will cause it to print in sorted order
===============
*/
'''
audit=r'''static const char *R_PbrAuditImageName(const shaderStage_t *stage, int bundle)
{
	image_t *image;

	if (!stage || bundle < 0 || bundle >= NUM_TEXTURE_BUNDLES)
		return "<none>";

	image = stage->bundle[bundle].image[0];
	return image ? image->imgName : "<none>";
}

static const char *R_PbrAuditImageTypeName(const image_t *image)
{
	if (!image)
		return "NONE";

	switch (image->type)
	{
	case IMGTYPE_NORMAL:
		return "NORMAL";
	case IMGTYPE_NORMALHEIGHT:
		return "NORMALHEIGHT";
	case IMGTYPE_DELUXE:
		return "DELUXE";
	case IMGTYPE_COLORALPHA:
	default:
		return "COLORALPHA";
	}
}

/*
====================
R_PbrMaterialAudit_f

Usage:
  r_pbrMaterialAudit <shaderName>

Reports the material response after Rend2 stage collapse:
Diffuse / NormalHeight / packed ORM / lightmap / parallaxDepth / POM V3.2.
====================
*/
void R_PbrMaterialAudit_f(void)
{
	shader_t *sh;
	const char *name;
	int i;
	int lightallCount = 0;

	if (ri.Cmd_Argc() != 2)
	{
		ri.Printf(PRINT_ALL, "usage: r_pbrMaterialAudit <shaderName>\n");
		ri.Printf(PRINT_ALL, "example: r_pbrMaterialAudit textures/snow/s_cathedrale_c06\n");
		return;
	}

	name = ri.Cmd_Argv(1);
	sh = R_FindShaderByName(name);

	if (!sh || sh == tr.defaultShader || sh->defaultShader)
	{
		ri.Printf(PRINT_ALL, "[DW_PBR_AUDIT] shader=%s status=NOT_LOADED_OR_DEFAULTED\n", name);
		return;
	}

	ri.Printf(PRINT_ALL,
		"[DW_PBR_AUDIT] shader=%s status=FOUND index=%d explicit=%d lightmapIndex=%d passes=%d r_pbr=%d r_parallaxMapping=%d\n",
		sh->name, sh->index, sh->explicitlyDefined ? 1 : 0, sh->lightmapIndex,
		sh->numUnfoggedPasses, r_pbr->integer, r_parallaxMapping->integer);

	ri.Printf(PRINT_ALL,
		"[DW_PBR_AUDIT] pomConfig minLayers=%d maxLayers=%d refine=%d maxOffset=%.6f depthScale=%.3f grazingFade=%.3f..%.3f shadows=%d shadowStrength=%.3f\n",
		r_pomMinLayers->integer, r_pomMaxLayers->integer, r_pomRefineSteps->integer,
		r_pomMaxOffset->value, r_pomDepthScale->value,
		r_pomGrazingFadeStart->value, r_pomGrazingFadeEnd->value,
		r_parallaxMapShadows->integer, r_pomShadowStrength->value);

	for (i = 0; i < sh->numUnfoggedPasses; ++i)
	{
		shaderStage_t *stage = sh->stages[i];
		image_t *normalImage;
		image_t *specularImage;
		qboolean lightall;
		qboolean parallax;
		qboolean normalHeight;
		qboolean packedOrm;
		qboolean pomActive;

		if (!stage || !stage->active)
			continue;

		lightall = (stage->type == ST_GLSL && stage->glslShaderGroup == tr.lightallShader);
		normalImage = stage->bundle[TB_NORMALMAP].image[0];
		specularImage = stage->bundle[TB_SPECULARMAP].image[0];
		parallax = lightall && ((stage->glslShaderIndex & LIGHTDEF_USE_PARALLAXMAP) != 0);
		normalHeight = normalImage && normalImage->type == IMGTYPE_NORMALHEIGHT;
		packedOrm = specularImage && stage->specularScale[2] < 0.0f;
		pomActive = lightall && parallax && normalHeight &&
			r_pbr->integer >= 3 && r_parallaxMapping->integer > 1;

		if (lightall)
			lightallCount++;

		ri.Printf(PRINT_ALL,
			"[DW_PBR_AUDIT] stage=%d lightall=%d glslIndex=0x%X diffuse=%s normal=%s normalType=%s heightAlpha=%d orm=%s packedORM=%d lightmap=%s parallax=%d parallaxDepth=%.6f pomV32=%s\n",
			i,
			lightall ? 1 : 0,
			stage->glslShaderIndex,
			R_PbrAuditImageName(stage, TB_DIFFUSEMAP),
			R_PbrAuditImageName(stage, TB_NORMALMAP),
			R_PbrAuditImageTypeName(normalImage),
			normalHeight ? 1 : 0,
			R_PbrAuditImageName(stage, TB_SPECULARMAP),
			packedOrm ? 1 : 0,
			R_PbrAuditImageName(stage, TB_LIGHTMAP),
			parallax ? 1 : 0,
			stage->normalScale[3],
			pomActive ? "ACTIVE" : "INACTIVE");
	}

	if (lightallCount == 0)
	{
		ri.Printf(PRINT_ALL,
			"[DW_PBR_AUDIT] shader=%s result=NO_LIGHTALL_STAGE POM cannot be active for this material path\n",
			sh->name);
	}
}


'''
if anchor not in s:
    raise SystemExit("R_ShaderList_f anchor missing")
s=s.replace(anchor,audit+anchor,1)
p.write_text(s); changed.append("SP/code/rend2/tr_shader.c")

# ---------------------------------------------------------------------------
# Register/unregister the audit command.
# ---------------------------------------------------------------------------
p,s=rw("tr_init.c")
s=one(s,
'''	ri.Cmd_AddCommand( "shaderlist", R_ShaderList_f );
	ri.Cmd_AddCommand( "skinlist", R_SkinList_f );
''',
'''	ri.Cmd_AddCommand( "shaderlist", R_ShaderList_f );
	ri.Cmd_AddCommand( "r_pbrMaterialAudit", R_PbrMaterialAudit_f );
	ri.Cmd_AddCommand( "skinlist", R_SkinList_f );
''',"audit command register")

s=one(s,
'''	ri.Cmd_RemoveCommand( "shaderlist" );
	ri.Cmd_RemoveCommand( "skinlist" );
''',
'''	ri.Cmd_RemoveCommand( "shaderlist" );
	ri.Cmd_RemoveCommand( "r_pbrMaterialAudit" );
	ri.Cmd_RemoveCommand( "skinlist" );
''',"audit command unregister")
p.write_text(s); changed.append("SP/code/rend2/tr_init.c")

proof={
    "base_run":42614562240,
    "base":"PBR V3.2 Physical Relief / POM",
    "feature":"Material Binding Audit",
    "command":"r_pbrMaterialAudit <shaderName>",
    "reports":[
        "loaded/defaulted status",
        "explicit material flag",
        "collapsed LightAll stage",
        "diffuse image",
        "normal/normalheight image and IMGTYPE",
        "height-in-alpha eligibility",
        "specular/ORM image and packed-ORM marker",
        "lightmap image",
        "LIGHTDEF_USE_PARALLAXMAP",
        "parallaxDepth from normalScale.a",
        "POM V3.2 ACTIVE/INACTIVE",
        "active POM quality cvars"
    ],
    "pom_algorithm_changed":False,
    "ggx_ibl_changed":False,
    "changed_files":changed
}
if args.proof:
    q=Path(args.proof); q.parent.mkdir(parents=True,exist_ok=True); q.write_text(json.dumps(proof,indent=2)+"\n")
print(json.dumps(proof,indent=2))
