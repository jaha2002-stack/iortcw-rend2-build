#!/usr/bin/env python3
"""Bounded RC4 quality patch. No retail assets, quality-cvar changes or telemetry."""
from pathlib import Path
import argparse, hashlib, json


def apply(root: Path, shader_path: Path):
    changed = {}
    def edit(rel, old, new, count=1):
        p = root / rel
        s = p.read_text()
        if s.count(old) != count:
            raise RuntimeError(f'{rel}: expected {count} anchors, got {s.count(old)}: {old[:90]!r}')
        changed.setdefault(rel, hashlib.sha256(p.read_bytes()).hexdigest())
        p.write_text(s.replace(old, new))

    prefix = 'SP/code/rend2/'
    edit(prefix+'tr_local.h', '\tqboolean\texplicitlyDefined;',
         '\tqboolean\tssgiEmitter; // RC4_QUALITY: authored surface emitter, not reflected brightness\n\tqboolean\texplicitlyDefined;')
    edit(prefix+'tr_shader.c', '\t\t// skip stuff that only the q3map needs', '''        // RC4_QUALITY_SSGI_EMITTER_IDENTITY: retain authored emission metadata.
        // Previously this directive was discarded; a world-space lamp then
        // bypassed the scene-entity rejection and became twelve displaced donors.
        // This flag does not change its material, direct light, bloom or shadows.
        else if (!Q_stricmp(token, "q3map_surfacelight"))
        {
            token = COM_ParseExt(text, qfalse);
            if (token[0] && atof(token) > 0.0f)
                shader.ssgiEmitter = qtrue;
            SkipRestOfLine(text);
            continue;
        }
\t\t// skip stuff that only the q3map needs''')
    edit(prefix+'tr_backend.c', 'if (backEnd.ssgiEntityDepthFill && entityNum == REFENTITYNUM_WORLD)',
         '''// RC4_QUALITY_SSGI_EMITTER_IDENTITY: reuse the existing depth mask.
        // Only authored, non-sky emitting world surfaces join scene entities.
        if (backEnd.ssgiEntityDepthFill && entityNum == REFENTITYNUM_WORLD &&
            !(shader && shader->ssgiEmitter && !shader->isSky))''')
    edit(prefix+'tr_backend.c',
         'if (r_softParticles && r_softParticles->integer && r_depthPrepass && r_depthPrepass->integer &&',
         '''// RC4_QUALITY_SHARED_DEPTH: SSGI owns a valid snapshot independently
            // of shadow blur / SSAO / soft-particle enable state. Reuse one copy.
            if (((r_softParticles && r_softParticles->integer) || (r_ssgi && r_ssgi->integer)) &&
                r_depthPrepass && r_depthPrepass->integer &&''')
    edit(prefix+'tr_backend.c', '\t\tqboolean ssgiActive = qfalse;', '''        image_t *ssgiDepth = tr.softParticleDepthImage ? tr.softParticleDepthImage : tr.hdrDepthImage;
\t\tqboolean ssgiActive = qfalse;''')
    edit(prefix+'tr_backend.c', 'else if (!tr.hdrDepthImage)\n\t\t\t\tssgiReason = "no-hdr-depth";',
         'else if (!ssgiDepth)\n\t\t\t\tssgiReason = "no-independent-depth";')
    # Only the two bindings inside SSGI, not SSAO/blur uses of the HDR image.
    p=root/(prefix+'tr_backend.c');s=p.read_text();a=s.index('image_t *ssgiDepth =');b=s.index('RB_USLRDRootCauseSampleStage(srcFbo, dstBox, s_uslrdRcHdrAfterSsgi);',a)
    middle=s[a:b];assert middle.count('GL_BindToTMU(tr.hdrDepthImage, TB_LIGHTMAP);')==2
    p.write_text(s[:a]+middle.replace('GL_BindToTMU(tr.hdrDepthImage, TB_LIGHTMAP);','GL_BindToTMU(ssgiDepth, TB_LIGHTMAP);')+s[b:])
    # Supply the same explicit scene-UV contract to every shared upscale caller.
    helper='''// RC4_QUALITY_VOLUMETRIC_RECONSTRUCTION: quarter color is vertically
// inverted by the accepted generator blit; scene depth is not. Keep the
// producer/world-ray contract unchanged and transform only reconstruction UVs.
static void RB_VolumetricUpscaleInputs(FBO_t *srcFbo, const ivec4_t srcBox, const vec4_t viewInfo)
{
    vec4_t depthRect, depthInfo;
    Vector4Copy(viewInfo, depthInfo);
    depthInfo[2] = 1.0f / tr.renderDepthImage->width;
    depthInfo[3] = 1.0f / tr.renderDepthImage->height;
    VectorSet4(depthRect, srcBox[0] / (float)srcFbo->width,
        srcBox[1] / (float)srcFbo->height,
        srcBox[2] / (float)srcFbo->width, srcBox[3] / (float)srcFbo->height);
    GL_BindToTMU(tr.renderDepthImage, TB_NORMALMAP);
    GLSL_BindProgram(&tr.volumetricLocalUpscaleShader);
    GLSL_SetUniformVec4(&tr.volumetricLocalUpscaleShader, UNIFORM_VIEWINFO, depthInfo);
    GLSL_SetUniformVec4(&tr.volumetricLocalUpscaleShader, UNIFORM_ENABLETEXTURES, depthRect);
}

'''
    edit(prefix+'tr_backend.c','static void RB_VolumetricSun(FBO_t *srcFbo, ivec4_t srcBox)',
         helper+'static void RB_VolumetricSun(FBO_t *srcFbo, ivec4_t srcBox)')
    for tabs,count in [('\t\t',1),('\t\t\t',3)]:
        old=(tabs+'GL_BindToTMU(tr.renderDepthImage, TB_NORMALMAP);\n'+tabs+'GLSL_BindProgram(&tr.volumetricLocalUpscaleShader);\n'+tabs+'GLSL_SetUniformVec4(&tr.volumetricLocalUpscaleShader, UNIFORM_VIEWINFO, viewInfo);')
        edit(prefix+'tr_backend.c',old,tabs+'RB_VolumetricUpscaleInputs(srcFbo, srcBox, viewInfo);',count)
    # A half-resolution centre lands on a full-depth texel boundary at 2x.
    # Canonicalise those ties identically on both producer and reconstruction.
    for filename in ('volumetriclocal_fp.glsl', 'volumetricsun_fp.glsl'):
        rel=prefix+'glsl/'+filename
        edit(rel, 'uniform sampler2D u_ScreenDepthMap;',
             'uniform sampler2D u_ScreenDepthMap;\nuniform vec2 u_InvTexRes; // RC4_QUALITY canonical full-resolution depth sample')
        edit(rel, 'texture2D(depthMap, tex).r - DEPTH_MAX_ERROR',
             'texture2D(depthMap, (floor(tex / u_InvTexRes + vec2(0.001)) + vec2(0.5)) * u_InvTexRes).r - DEPTH_MAX_ERROR')
    shader_rel=prefix+'glsl/volumetriclocal_upscale_fp.glsl'
    p=root/shader_rel
    changed[shader_rel]=hashlib.sha256(p.read_bytes()).hexdigest()
    p.write_bytes(shader_path.read_bytes())
    return {rel:{'before':before,'after':hashlib.sha256((root/rel).read_bytes()).hexdigest()} for rel,before in changed.items()}

if __name__ == '__main__':
    ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);ap.add_argument('--manifest',type=Path);args=ap.parse_args()
    changes=apply(args.root,Path(__file__).with_name('volumetriclocal_upscale_fp.glsl'))
    text=json.dumps({'patch':'RC4_QUALITY_SSGI_EMITTER_AND_VOLUME_JBU_V1','changed_files':changes},indent=2)+'\n'
    if args.manifest: args.manifest.write_text(text)
    print(text)
