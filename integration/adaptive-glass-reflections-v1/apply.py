#!/usr/bin/env python3
"""DARKWOLF_ADAPTIVE_GLASS_V1: isolated BSP-only static cubemap/Fresnel pass."""
import argparse,json,re
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
    files=["tr_init.c","tr_local.h","tr_glsl.c","tr_bsp.c","tr_image.c","tr_shade.c","tr_light.c"]
    a={k:(root/k).read_text() for k in files}
    if any(M in x for x in a.values()): raise ValueError("Already patched")
    b=dict(a)
    b["tr_local.h"]=rep(b["tr_local.h"],"extern  cvar_t  *r_cubeMapping;",
      "extern cvar_t *r_dwGlassReflect, *r_dwGlassIntensity, *r_dwGlassAutoDetect;\nextern  cvar_t  *r_cubeMapping;","extern")
    b["tr_local.h"]=rep(b["tr_local.h"],"shaderProgram_t textureColorShader;",
      "shaderProgram_t textureColorShader;\n\tshaderProgram_t dwGlassShader; // "+M,"program")
    b["tr_init.c"]=rep(b["tr_init.c"],"cvar_t  *r_cubeMapping;",
      "cvar_t *r_dwGlassReflect, *r_dwGlassIntensity, *r_dwGlassAutoDetect; // "+M+"\ncvar_t  *r_cubeMapping;","vars")
    # Register immediately before existing cube mapping without modifying its value.
    # Historical DarkWolf cvars may have altered formatting/defaults.
    patt=r'(?m)^(\s*)r_cubeMapping\s*=\s*ri\.Cvar_Get\(\s*"r_cubeMapping"[^;]*;'
    hits=list(re.finditer(patt,b["tr_init.c"]))
    if len(hits)!=1:raise ValueError("r_cubeMapping registration occurrences "+str(len(hits)))
    m=hits[0]
    reg=('r_dwGlassReflect = ri.Cvar_Get("r_dwGlassReflect", "1", CVAR_ARCHIVE | CVAR_LATCH);\n'
         'r_dwGlassIntensity = ri.Cvar_Get("r_dwGlassIntensity", "0.60", CVAR_ARCHIVE);\n'
         'r_dwGlassAutoDetect = ri.Cvar_Get("r_dwGlassAutoDetect", "1", CVAR_ARCHIVE);\n')
    indent=m.group(1)
    b["tr_init.c"]=b["tr_init.c"][:m.start()]+indent+reg.replace('\n','\n'+indent)+b["tr_init.c"][m.start():]
    # Static cubemap allocation only; legacy lightall / Norway water remain gated by original r_cubeMapping.
    b["tr_image.c"]=rep(b["tr_image.c"],
        "if (r_cubeMapping->integer)",
        "if (r_cubeMapping->integer || r_dwGlassReflect->integer)","glass resource")
    b["tr_light.c"]=rep(b["tr_light.c"],
        "if (r_cubeMapping->integer && tr.numCubemaps)",
        "if ((r_cubeMapping->integer || (r_dwGlassReflect && r_dwGlassReflect->integer)) && tr.numCubemaps)",
        "nearest probe independent from global shading cvar")
    # All maps: preserve authored cubemap path exactly, limit only glass-specific automatic probes.
    # Source-level classifier mirrored in tr_shade; no map-name whitelist anywhere.
    glassSource=r'''
// DARKWOLF_ADAPTIVE_GLASS_V1: map-agnostic, conservative BSP material recognition.
static qboolean DW_MapHasGlass(void)
{
    int i;
    for (i=0; i<s_worldData.numsurfaces; ++i)
    {
        const shader_t *sh=s_worldData.surfaces[i].shader;
        const char *n;
        if (!sh) continue;
        n=strrchr(sh->name,'/');
        n=n?n+1:sh->name; // basename only: avoid false glass on 'castle_window/cashudder'
        if (Q_stristr(n,"water") || Q_stristr(n,"lava") ||
            Q_stristr(n,"mirror") || Q_stristr(n,"blood") || Q_stristr(n,"ice") ||
            Q_stristr(n,"shutter") || Q_stristr(n,"shudder") ||
            Q_stristr(n,"frame") || Q_stristr(n,"trim") ||
            Q_stristr(n,"panel") || Q_stristr(n,"border")) continue;
        if ((sh->surfaceFlags & SURF_GLASS) ||
            (r_dwGlassAutoDetect->integer && (Q_stristr(n,"glass") ||
                Q_stristr(n,"window")))) return qtrue;
    }
    return qfalse;
}
// Select at most 12 evenly spaced map-authored safe AI markers (or player starts).
// No per-frame updates and no uncontrolled hundreds-of-probes startup work.
static void DW_LoadAutoGlassProbes(void)
{
    const int limit=12;
    const char *kind="ai_marker";
    char spawnChars[2048];
    char *vars[MAX_SPAWN_VARS][2];
    int pass, nv, total=0, nselected=0, seen=0, i;
    for (pass=0; pass<2; ++pass)
    {
        int found=0;
        const char *candidate=pass==0?"ai_marker":"info_player_start";
        while(R_ParseSpawnVars(spawnChars,sizeof(spawnChars),&nv,vars))
        {
            qboolean match=qfalse, haveOrigin=qfalse;
            for(i=0;i<nv;i++) {
                if (!Q_stricmp(vars[i][0],"classname") &&
                    !Q_stricmp(vars[i][1],candidate)) match=qtrue;
                if (!Q_stricmp(vars[i][0],"origin")) haveOrigin=qtrue;
            }
            if (match && haveOrigin) found++;
        }
        if (found) {kind=candidate;total=found;break;}
    }
    if (!total) return;
    tr.numCubemaps=total<limit?total:limit;
    tr.cubemaps=ri.Hunk_Alloc(tr.numCubemaps*sizeof(*tr.cubemaps),h_low);
    memset(tr.cubemaps,0,tr.numCubemaps*sizeof(*tr.cubemaps));
    while(R_ParseSpawnVars(spawnChars,sizeof(spawnChars),&nv,vars))
    {
        qboolean match=qfalse, haveOrigin=qfalse;
        vec3_t origin;
        for(i=0;i<nv;i++) {
            if (!Q_stricmp(vars[i][0],"classname") &&
                !Q_stricmp(vars[i][1],kind)) match=qtrue;
            if (!Q_stricmp(vars[i][0],"origin")) {
                haveOrigin=(sscanf(vars[i][1],"%f %f %f",
                                    &origin[0],&origin[1],&origin[2])==3);
            }
        }
        if (!match || !haveOrigin) continue;
        if (nselected < tr.numCubemaps &&
            seen == ((2*nselected+1)*total)/(2*tr.numCubemaps)) {
            VectorCopy(origin,tr.cubemaps[nselected].origin);
            tr.cubemaps[nselected].parallaxRadius=1000.0f;
            nselected++;
        }
        seen++;
    }
    tr.numCubemaps=nselected;
    ri.Printf(PRINT_ALL,"DarkWolf glass: automatic static probes %d from %s\n",nselected,kind);
}
'''
    b["tr_bsp.c"]=rep(b["tr_bsp.c"],
        "void R_AssignCubemapsToWorldSurfaces(void)",
        glassSource+"\nvoid R_AssignCubemapsToWorldSurfaces(void)","auto probe helper")
    b["tr_bsp.c"]=rep(b["tr_bsp.c"],
        "if (r_cubeMapping->integer)\n\t{\n\t\t// Try loading an env.json file first",
        "if (r_cubeMapping->integer || (r_dwGlassReflect && r_dwGlassReflect->integer && DW_MapHasGlass()))\n\t{\n\t\t// Try loading an env.json file first",
        "probe gating")
    b["tr_bsp.c"]=rep(b["tr_bsp.c"],
        'R_LoadCubemapEntities("ai_marker");',
        'if (r_cubeMapping->integer) R_LoadCubemapEntities("ai_marker");\n'
        '            else DW_LoadAutoGlassProbes();',"auto fallback")
    b["tr_bsp.c"]=rep(b["tr_bsp.c"],
        "if (r_cubeMapping->integer && tr.numCubemaps && glRefConfig.framebufferObject)",
        "if ((r_cubeMapping->integer || (r_dwGlassReflect && r_dwGlassReflect->integer)) && tr.numCubemaps && glRefConfig.framebufferObject)",
        "static probe captures")
    vp=cstring((BASE/"glass_vp.glsl").read_text())
    fp=cstring((BASE/"glass_fp.glsl").read_text())
    snippet="\n// "+M+": compile-time embedded, independent of PK3 and r_externalGLSL.\nstatic const char *dwGlassVP =\n"+vp+";\nstatic const char *dwGlassFP =\n"+fp+";\n"
    b["tr_glsl.c"]=rep(b["tr_glsl.c"],
      "void GLSL_InitUniforms(shaderProgram_t *program)",
      snippet+"\nvoid GLSL_InitUniforms(shaderProgram_t *program)","shader strings")
    # Note GPU shader compile cannot happen unless GPU supports GLSL + FBO. Same existing render requirement.
    insert='''\n\t// '''+M+''': one separate glass program; no modifications to lightall or generic permutations.
\t{
\t\tint glassAttribs = ATTR_POSITION | ATTR_NORMAL | ATTR_TEXCOORD;
\t\tif (!GLSL_InitGPUShader(&tr.dwGlassShader, "dwglass", glassAttribs, qtrue,
\t\t\t"", qtrue, dwGlassVP, dwGlassFP))
\t\t\tri.Error(ERR_FATAL, "Could not load DarkWolf glass shader");
\t\tGLSL_InitUniforms(&tr.dwGlassShader);
\t\tGLSL_SetUniformInt(&tr.dwGlassShader, UNIFORM_CUBEMAP, TB_CUBEMAP);
\t\tGLSL_SetUniformInt(&tr.dwGlassShader, UNIFORM_DIFFUSEMAP, TB_DIFFUSEMAP);
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
\tconst char *name = strrchr(sh->name,'/');
\tqboolean hint = (sh->surfaceFlags & SURF_GLASS) != 0;
\tname = name ? name + 1 : sh->name; // shader basename; not directory paths
\tif (Q_stristr(name, "water") || Q_stristr(name, "lava") || Q_stristr(name, "mirror") ||
\t    Q_stristr(name, "ice") || Q_stristr(name, "blood") ||
\t    Q_stristr(name, "shutter") || Q_stristr(name, "shudder") ||
\t    Q_stristr(name, "frame") || Q_stristr(name, "trim") ||
\t    Q_stristr(name, "panel") || Q_stristr(name, "border")) return qfalse;
\tif (!r_dwGlassAutoDetect || !r_dwGlassAutoDetect->integer) return hint;
\treturn hint || Q_stristr(name, "glass") || Q_stristr(name, "window");
}
static void DW_DrawGlassReflection(shaderCommands_t *input)
{
\tint index;
\tcubemap_t *probe;
\tvec4_t probeInfo, params;
\tshaderProgram_t *sp = &tr.dwGlassShader;
\tfloat opacity = 1.0f, roughness = 0.18f;
\tint i, alphaTest = 0;
\tshaderStage_t *firstStage = input->xstages[0];
\tif (!r_dwGlassReflect || !r_dwGlassReflect->integer ||
\t    !r_dwGlassIntensity || r_dwGlassIntensity->value <= 0.0f ||
\t    !tr.world || !input->shader || !DW_GlassCandidate(input->shader))
\t\treturn;
\tif (backEnd.depthFill || backEnd.projection2D ||
\t    (backEnd.viewParms.flags & (VPF_SHADOWMAP | VPF_DEPTHSHADOW | VPF_NOCUBEMAPS)) ||
\t    (backEnd.currentEntity && backEnd.currentEntity != &tr.worldEntity &&
\t     (!tr.currentModel || tr.currentModel->type != MOD_BRUSH)) ||
\t    input->shader->sort <= SS_PORTAL || input->shader->sort >= SS_NEAREST ||
\t    input->shader->numDeforms || !tr.renderCubeFbo)
\t\treturn;
\tindex = input->cubemapIndex;
\t// BSP brush glass (including breakable panes) uses nearest static environment probe.
\tif (index <= 0 && backEnd.currentEntity && backEnd.currentEntity != &tr.worldEntity)
\t\tindex = R_CubemapForPoint(backEnd.currentEntity->e.origin);
\tif (index <= 0 || index > tr.numCubemaps) return;
\tprobe = &tr.cubemaps[index-1];
\tif (!probe->image || !firstStage) return;
\t// Blended shaders are treated as see-through: stronger glancing reflection.
\tfor (i=0;i<MAX_SHADER_STAGES && input->xstages[i];i++) {
\t\tunsigned int bits=input->xstages[i]->stateBits;
\t\tif (bits & (GLS_SRCBLEND_BITS | GLS_DSTBLEND_BITS)) { opacity=0.25f; break; }
\t}
\tif (Q_stristr(input->shader->name,"dirty") || Q_stristr(input->shader->name,"frost"))
\t\troughness=0.72f;
\tGLSL_BindProgram(sp);
\tGLSL_SetUniformMat4(sp, UNIFORM_MODELVIEWPROJECTIONMATRIX, glState.modelviewProjection);
\tGLSL_SetUniformMat4(sp, UNIFORM_MODELMATRIX, backEnd.or.transformMatrix);
\tGLSL_SetUniformVec3(sp, UNIFORM_VIEWORIGIN, backEnd.viewParms.or.origin);
\tVectorSubtract(probe->origin, backEnd.viewParms.or.origin, probeInfo);
\tprobeInfo[3]=1.0f;
\tVectorScale4(probeInfo, 1.0f / ((probe->parallaxRadius>1.0f)?probe->parallaxRadius:1000.0f), probeInfo);
\tGLSL_SetUniformVec4(sp, UNIFORM_CUBEMAPINFO, probeInfo);
\tVectorSet4(params, Com_Clamp(0.0f,1.0f,r_dwGlassIntensity->value), opacity, roughness, opacity < 1.0f ? 1.0f : 0.0f);
\tGLSL_SetUniformVec4(sp, UNIFORM_SPECULARSCALE, params);
\tif ((firstStage->stateBits & GLS_ATEST_BITS) == GLS_ATEST_GT_0) alphaTest=1;
\telse if ((firstStage->stateBits & GLS_ATEST_BITS) == GLS_ATEST_LT_80) alphaTest=2;
\telse if ((firstStage->stateBits & GLS_ATEST_BITS) == GLS_ATEST_GE_80) alphaTest=3;
\tGLSL_SetUniformInt(sp, UNIFORM_ALPHATEST, alphaTest);
\tif (firstStage->bundle[0].image[0])
\t\tR_BindAnimatedImageToTMU(&firstStage->bundle[0], TB_DIFFUSEMAP);
\telse
\t\tGL_BindToTMU(tr.whiteImage,TB_DIFFUSEMAP);
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
    b["tr_shade.c"]=rep(b["tr_shade.c"],
        "\tvertexAttribs = RB_CalcShaderVertexAttribs( input );",
        "\tvertexAttribs = RB_CalcShaderVertexAttribs( input );\n"
        "\t// Glass-only normal attribute for BSP world and brush surfaces.\n"
        "\tif (r_dwGlassReflect && r_dwGlassReflect->integer &&\n"
        "\t    input->shader && DW_GlassCandidate(input->shader)) vertexAttribs |= ATTR_NORMAL;",
        "normal attribute")
    if not check:
        for f in files:(root/f).write_text(b[f])
    return {"marker":M,"base_run":41297344177,"changed":files,"dynamic_reflections":False,"automatic_map_agnostic_probes_limit":12,
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
