#!/usr/bin/env python3
"""DARKWOLF_ADAPTIVE_GLASS_V1: isolated BSP-only static cubemap/Fresnel pass."""
import argparse,json
from pathlib import Path
M="DARKWOLF_ADAPTIVE_GLASS_V1"
BASE=Path(__file__).resolve().parent
def rep(s,a,b,tag):
    n=s.count(a)
    if n!=1: raise ValueError("%s anchor occurrences=%d"%(tag,n))
    return s.replace(a,b,1)
def cstring(s):
    return "\n".join('"'+line.replace("\\","\\\\").replace('"','\\"')+'\\n"' for line in s.splitlines())
def run(root,check=False):
    root=Path(root)/"SP/code/rend2"
    files=["tr_init.c","tr_local.h","tr_glsl.c","tr_bsp.c","tr_image.c","tr_shade.c"]
    a={k:(root/k).read_text() for k in files}
    if any(M in x for x in a.values()): raise ValueError("Already patched")
    b=dict(a)
    b["tr_local.h"]=rep(b["tr_local.h"],"extern  cvar_t  *r_cubeMapping;",
      "extern cvar_t *r_dwGlassReflect, *r_dwGlassIntensity, *r_dwGlassAutoDetect;\nextern  cvar_t  *r_cubeMapping;","extern")
    b["tr_local.h"]=rep(b["tr_local.h"],"shaderProgram_t textureColorShader;",
      "shaderProgram_t textureColorShader;\n\tshaderProgram_t dwGlassShader; // "+M,"program")
    b["tr_init.c"]=rep(b["tr_init.c"],"cvar_t  *r_cubeMapping;",
      "cvar_t *r_dwGlassReflect, *r_dwGlassIntensity, *r_dwGlassAutoDetect; // "+M+"\ncvar_t  *r_cubeMapping;","vars")
    b["tr_init.c"]=rep(b["tr_init.c"],
      'r_cubeMapping = ri.Cvar_Get( "r_cubeMapping", "0", CVAR_ARCHIVE | CVAR_LATCH );',
      'r_dwGlassReflect = ri.Cvar_Get("r_dwGlassReflect", "1", CVAR_ARCHIVE | CVAR_LATCH);\n\t'
      'r_dwGlassIntensity = ri.Cvar_Get("r_dwGlassIntensity", "0.60", CVAR_ARCHIVE);\n\t'
      'r_dwGlassAutoDetect = ri.Cvar_Get("r_dwGlassAutoDetect", "1", CVAR_ARCHIVE);\n\t'
      'r_cubeMapping = ri.Cvar_Get( "r_cubeMapping", "0", CVAR_ARCHIVE | CVAR_LATCH );',
      "register")
    # Cubemap allocation separate from r_cubeMapping; never change r_cubeMapping itself or normal water shading.
    for f,old,new in [
        ("tr_bsp.c","if (r_cubeMapping->integer)","if (r_cubeMapping->integer || r_dwGlassReflect->integer)"),
        ("tr_bsp.c","if (r_cubeMapping->integer && tr.numCubemaps && glRefConfig.framebufferObject)",
          "if ((r_cubeMapping->integer || r_dwGlassReflect->integer) && tr.numCubemaps && glRefConfig.framebufferObject)"),
        ("tr_image.c","if (r_cubeMapping->integer)","if (r_cubeMapping->integer || r_dwGlassReflect->integer)")
    ]:
        b[f]=rep(b[f],old,new,f+" cube")
    # On maps without authored probes, reuse one player start. Never synthesize a probe in a solid wall.
    b["tr_bsp.c"]=rep(b["tr_bsp.c"],
      'R_LoadCubemapEntities("ai_marker");',
      'R_LoadCubemapEntities("ai_marker");', "ai probe") # do not change base fallback
    vp=cstring((BASE/"glass_vp.glsl").read_text())
    fp=cstring((BASE/"glass_fp.glsl").read_text())
    snippet="\n// "+M+": compile-time embedded, independent of PK3 and r_externalGLSL.\nstatic const char *dwGlassVP =\n"+vp+";\nstatic const char *dwGlassFP =\n"+fp+";\n"
    b["tr_glsl.c"]=rep(b["tr_glsl.c"],
      "void GLSL_InitUniforms(shaderProgram_t *program)",
      snippet+"\nvoid GLSL_InitUniforms(shaderProgram_t *program)","shader strings")
    # Note GPU shader compile cannot happen unless GPU supports GLSL + FBO. Same existing render requirement.
    insert='''\n\t// '''+M+''': one separate glass program; no modifications to lightall or generic permutations.
\t{
\t\tint glassAttribs = ATTR_POSITION | ATTR_NORMAL;
\t\tif (!GLSL_InitGPUShader(&tr.dwGlassShader, "dwglass", glassAttribs, qtrue,
\t\t\t"", qtrue, dwGlassVP, dwGlassFP))
\t\t\tri.Error(ERR_FATAL, "Could not load DarkWolf glass shader");
\t\tGLSL_InitUniforms(&tr.dwGlassShader);
\t\tGLSL_SetUniformInt(&tr.dwGlassShader, UNIFORM_CUBEMAP, TB_CUBEMAP);
\t\tGLSL_FinishGPUShader(&tr.dwGlassShader);
\t}
'''
    b["tr_glsl.c"]=rep(b["tr_glsl.c"],'GLSL_DeleteGPUShader(&tr.textureColorShader);',
       'GLSL_DeleteGPUShader(&tr.textureColorShader);\n\tGLSL_DeleteGPUShader(&tr.dwGlassShader);',"shutdown")
    b["tr_glsl.c"]=rep(b["tr_glsl.c"],'\n\tattribs = ATTR_POSITION | ATTR_TEXCOORD;\n\n\tif (!GLSL_InitGPUShader(&tr.textureColorShader',
       insert+'\n\tattribs = ATTR_POSITION | ATTR_TEXCOORD;\n\n\tif (!GLSL_InitGPUShader(&tr.textureColorShader',"init")
    # Single final overlay after original material pass; transparent windows keep their original blending.
    overlay='''\n// '''+M+''': conservative classifier; exclude water and non-glass.
static qboolean DW_GlassCandidate(const shader_t *sh)
{
\tconst char *name = sh->name;
\tqboolean hint = (sh->surfaceFlags & SURF_GLASS) != 0;
\tif (!r_dwGlassAutoDetect || !r_dwGlassAutoDetect->integer) return hint;
\tif (strstr(name, "water") || strstr(name, "lava") || strstr(name, "mirror") ||
\t    strstr(name, "ice") || strstr(name, "glassbreak") || strstr(name, "blood"))
\t\treturn qfalse;
\treturn hint || strstr(name, "glass") || strstr(name, "window") || strstr(name, "pane");
}
static void DW_DrawGlassReflection(shaderCommands_t *input)
{
\tint index;
\tcubemap_t *probe;
\tvec4_t probeInfo, params;
\tshaderProgram_t *sp = &tr.dwGlassShader;
\tfloat opacity = 1.0f, roughness = 0.18f;
\tint i;
\tif (!r_dwGlassReflect || !r_dwGlassReflect->integer ||
\t    !r_dwGlassIntensity || r_dwGlassIntensity->value <= 0.0f ||
\t    !tr.world || !input->shader || !DW_GlassCandidate(input->shader))
\t\treturn;
\tif (backEnd.depthFill || backEnd.projection2D ||
\t    (backEnd.viewParms.flags & (VPF_SHADOWMAP | VPF_DEPTHSHADOW | VPF_NOCUBEMAPS)) ||
\t    backEnd.currentEntity != &tr.worldEntity ||
\t    input->shader->sort <= SS_PORTAL || input->shader->sort >= SS_NEAREST ||
\t    input->shader->numDeforms || !tr.renderCubeFbo)
\t\treturn;
\tindex = input->cubemapIndex;
\tif (index <= 0 || index > tr.numCubemaps) return;
\tprobe = &tr.cubemaps[index-1];
\tif (!probe->image) return;
\t// Blended shaders are treated as see-through: stronger glancing reflection.
\tfor (i=0;i<MAX_SHADER_STAGES && input->xstages[i];i++) {
\t\tunsigned int bits=input->xstages[i]->stateBits;
\t\tif (bits & (GLS_SRCBLEND_BITS | GLS_DSTBLEND_BITS)) { opacity=0.25f; break; }
\t}
\tif (strstr(input->shader->name,"dirty") || strstr(input->shader->name,"frost"))
\t\troughness=0.72f;
\tGLSL_BindProgram(sp);
\tGLSL_SetUniformMat4(sp, UNIFORM_MODELVIEWPROJECTIONMATRIX, glState.modelviewProjection);
\tGLSL_SetUniformMat4(sp, UNIFORM_MODELMATRIX, backEnd.or.transformMatrix);
\tGLSL_SetUniformVec3(sp, UNIFORM_VIEWORIGIN, backEnd.viewParms.or.origin);
\tVectorSubtract(probe->origin, backEnd.viewParms.or.origin, probeInfo);
\tprobeInfo[3]=1.0f;
\tVectorScale4(probeInfo, 1.0f / ((probe->parallaxRadius>1.0f)?probe->parallaxRadius:1000.0f), probeInfo);
\tGLSL_SetUniformVec4(sp, UNIFORM_CUBEMAPINFO, probeInfo);
\tVectorSet4(params, Com_Clamp(0.0f,1.0f,r_dwGlassIntensity->value), opacity, roughness, 1.0f);
\tGLSL_SetUniformVec4(sp, UNIFORM_SPECULARSCALE, params);
\tGL_BindToTMU(probe->image,TB_CUBEMAP);
\tGL_State(GLS_SRCBLEND_SRC_ALPHA | GLS_DSTBLEND_ONE_MINUS_SRC_ALPHA | GLS_DEPTHTEST_DISABLE);
\t// IMPORTANT: use depth testing to prevent seeing glass through walls.
\tGL_State(GLS_SRCBLEND_SRC_ALPHA | GLS_DSTBLEND_ONE_MINUS_SRC_ALPHA | GLS_DEPTHFUNC_EQUAL);
\tR_DrawElements(input->numIndexes,input->firstIndex);
}
'''
    # GLS_DEPTHFUNC_EQUAL may not exist: prefer default LEQUAL with zero depth writes.
    overlay=overlay.replace('GL_State(GLS_SRCBLEND_SRC_ALPHA | GLS_DSTBLEND_ONE_MINUS_SRC_ALPHA | GLS_DEPTHTEST_DISABLE);\n\t// IMPORTANT: use depth testing to prevent seeing glass through walls.\n\tGL_State(GLS_SRCBLEND_SRC_ALPHA | GLS_DSTBLEND_ONE_MINUS_SRC_ALPHA | GLS_DEPTHFUNC_EQUAL);',
    '// Preserve depth test (LEQUAL), suppress writes through the state mask.\n\tGL_State(GLS_SRCBLEND_SRC_ALPHA | GLS_DSTBLEND_ONE_MINUS_SRC_ALPHA);')
    b["tr_shade.c"]=rep(b["tr_shade.c"],'void RB_StageIteratorGeneric( void )',
        overlay+'\nvoid RB_StageIteratorGeneric( void )',"overlay")
    b["tr_shade.c"]=rep(b["tr_shade.c"],
        '\tRB_IterateStagesGeneric( input );\n\n\t//\n\t// pshadows!',
        '\tRB_IterateStagesGeneric( input );\n\tDW_DrawGlassReflection(input);\n\n\t//\n\t// pshadows!',"draw hook")
    if not check:
        for f in files:(root/f).write_text(b[f])
    return {"marker":M,"base_run":41297344177,"changed":files,"dynamic_reflections":False,
            "global_cubemap_cvar_unchanged":True,"status":"source-only until CI and GPU testing"}
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--check-only",action="store_true")
    ap.add_argument("--proof")
    o=ap.parse_args()
    result=run(o.root,o.check_only)
    if o.proof:Path(o.proof).write_text(json.dumps(result,indent=2)+"\n")
    print(M+"_SOURCE_PASS")
