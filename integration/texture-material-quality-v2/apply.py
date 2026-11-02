#!/usr/bin/env python3
"""V2: world material parity + selective model A2C + analytic LUT, exact #41019985033."""
import argparse,hashlib,json,re,shutil,tempfile
from pathlib import Path
R=Path("SP/code/rend2")
MARK="DARKWOLF_TEXTURE_MATERIAL_QUALITY_V2_41019985033"
changes={}
def sub(s,a,b,label):
 n=s.count(a)
 assert n==1,(label,n,a[:90])
 return s.replace(a,b,1)
def region(s,a,b,replace,label):
 assert s.count(a)==1,(label,'start',s.count(a))
 i=s.index(a);j=s.find(b,i)
 assert j>i,(label,'end')
 return s[:i]+replace+s[j:]
def init(s):
 # Preserve every accepted source default. Retire only two faulty texture subfeatures.
 for k in ('r_dwAdaptiveUpsample','r_dwCutoutMip'):
  s=sub(s,'cvar_t *'+k+';\n','',k+' declaration')
  s=sub(s,'\t'+k+' = ri.Cvar_Get("'+k+'", "1", CVAR_ARCHIVE | CVAR_LATCH);\n','',k+' registration')
  s=sub(s,'\tri.Cvar_CheckRange('+k+', 0, 1, qtrue);\n','',k+' range')
 for k in ('r_dwTextureFidelity','r_dwMaterialFidelity','r_dwA2C',
           'r_dwCas','r_dwCasStrength','r_dwLut','r_dwLutStrength','r_dwLutMode'):
  assert 'ri.Cvar_Get("'+k+'"' in s,k+' preserved'
 return '// '+MARK+': world texture scaling kept original; model fidelity + A2C retained\n'+s

def header(s):
 for k in ('r_dwAdaptiveUpsample','r_dwCutoutMip'):
  s=sub(s,'extern cvar_t *'+k+';\n','',k+' extern')
 return sub(s,'\timage_t *dwColorLutImages[3]; // 16x16x16 RGB 2D atlases, created only when LUT enabled\n','','atlas fields')

def image(s):
 # Remove artificial software upscaling (not real source detail) and fragile cutout CPU mip chain.
 s=region(s,'\t// DARKWOLF_TEXTURE_MATERIAL_FIDELITY_V01: select only small diffuse maps.\n',
          '#if 0\n\tstatic int rmse_saved = 0;',
          '\t// Only user-explicit r_imageUpsample remains; no synthetic default resize.\n\tint dwUpsampleLevel = r_imageUpsample->integer;\n','adaptive upsample')
 s=region(s,'// DARKWOLF_TEXTURE_MATERIAL_FIDELITY_V01: only 1-bit cutouts.',
          'static void RawImage_UploadTexture(',
          '// Original mip generation retained; unsafe binary-cutout CPU chain retired.\n','cutout routines')
 s=sub(s,'\tqboolean dwCutout = qfalse;\n\n\tif (r_dwTextureFidelity->integer && r_dwCutoutMip->integer &&\n\t    rgba8 && type == IMGTYPE_COLORALPHA && !(flags & IMGFLAG_CUBEMAP))\n\t\tdwCutout = DW_IsBinaryCutout(data, width, height);\n','','cutout gating')
 s=sub(s,'if (glRefConfig.framebufferObject && !dwCutout)','if (glRefConfig.framebufferObject)','GPU mip')
 s=sub(s,'\t\t\t\telse if (dwCutout)\n\t\t\t\t\tDW_MipMapCutout(data, width, height);\n','','cutout branch')
 # Original world image sizing: fidelity may use NPOT only for named player and gun textures.
 s=sub(s,
  'qboolean characterMip, byte **resampledBuffer)',
  'qboolean characterMip, qboolean dwFidelityTexture, byte **resampledBuffer)',
  'texture scaling signature')
 s=sub(s,
  'if (!mipmap || (r_dwTextureFidelity->integer && QGL_VERSION_ATLEAST(2, 0)))',
  'if (!mipmap || (dwFidelityTexture && QGL_VERSION_ATLEAST(2, 0)))',
  'scope NPOT to models')
 s=sub(s,'!r_dwTextureFidelity->integer && r_roundImagesDown->integer',
       '!dwFidelityTexture && r_roundImagesDown->integer','round original sizes X/Y') if False else s
 assert s.count('!r_dwTextureFidelity->integer && r_roundImagesDown->integer')==2
 s=s.replace('!r_dwTextureFidelity->integer && r_roundImagesDown->integer',
             '!dwFidelityTexture && r_roundImagesDown->integer')
 s=sub(s,'RawImage_ScaleToPower2(&pic, &width, &height, type, flags, characterMip, &resampledBuffer)',
         'RawImage_ScaleToPower2(&pic, &width, &height, type, flags, characterMip,\n'
         '              (r_dwTextureFidelity->integer && DW_IsModelTextureName(name)), &resampledBuffer)',
         'pass exact image identity')
 s=sub(s,'if (r_dwTextureFidelity->integer && (characterMIP || DW_IsModelTextureName(name)))',
         'if (r_dwTextureFidelity->integer && DW_IsModelTextureName(name))',
         'no compression only player/weapon textures')
 # Eliminate obsolete and fault-prone 16^3 LUT atlas. Only final postprocess LUT shader changes.
 s=region(s,'// DARKWOLF_CAS_A2C_LUT_V01: independent 16^3 look-up-table atlases',
          'void R_CreateBuiltinImages( void )',
          '// No red-prone atlas texture; procedural grade computes directly in final GLSL.\n',
          'GPU LUT atlas')
 s=sub(s,'\tDW_CreateColorLuts(); // DARKWOLF_CAS_A2C_LUT_V01; allocated only with r_dwLut 1 on vid_restart\n',
       '','LUT atlas creation')
 return s

def shade(s):
 # A2C stays implemented and can remain enabled, but only on named model materials.
 # Exclude BSP world, including alpha-tested grates and stairs: preserve depth/coverage parity.
 return sub(s,
   '(!backEnd.currentEntity || !backEnd.currentEntity->e.fadeStartTime)) ? qtrue : qfalse;',
   '(backEnd.currentEntity && backEnd.currentEntity != &tr.worldEntity &&\n'
   '\t\t\t !backEnd.currentEntity->e.fadeStartTime && tess.shader &&\n'
   '\t\t\t !Q_stricmpn(tess.shader->name, "models/", 7))) ? qtrue : qfalse;',
   'A2C model-only scope')



def backend(s):
 s=sub(s,'\tif (!tr.dwColorLutImages[lutIndex])\n\t\tlut = 0.0f;\n','','atlas dependency')
 s=sub(s,'VectorSet4(parms, cas, lut, 0.0f, 0.0f);',
         'VectorSet4(parms, cas, lut, (float)lutIndex, 0.0f);','LUT mode')
 return sub(s,'\t// When CAS runs alone, bind a valid harmless sampler rather than relying on stale GL bindings.\n\tGL_BindToTMU(lut > 0.0f ? tr.dwColorLutImages[lutIndex] : tr.whiteImage, TB_LEVELSMAP);\n','','sampler dependency')
def loader(s):
 s=sub(s,'if ( r_externalGLSL->integer ) {','if ( r_externalGLSL->integer && Q_stricmp(name, "dwfinal") ) {','use audited internal dwfinal')
 return sub(s,'\t\t\tGLSL_SetUniformInt(&tr.dwFinalPolishShader, UNIFORM_LEVELSMAP, TB_LEVELSMAP);\n','','atlas uniform init')
def finalShader(s):
 s=sub(s,'uniform sampler2D u_LevelsMap; // manually trilinearly sampled 16^3 LUT atlas\n','','atlas uniform')
 new="""// Luminance-protected analytical grade. Mode0 identity. No atlas or extra VRAM.
vec3 DW_Lut(vec3 rgb)
{
    vec3 v=clamp(rgb,0.0,1.0);
    if(u_Color.z<0.5) return v;
    vec3 lum=vec3(0.2126,0.7152,0.0722);
    float y=dot(v,lum);
    float sh=clamp((0.70-y)*2.0,0.0,1.0);
    float hi=1.0-sh;
    vec3 g=v;
    if(u_Color.z<1.5) {
        g.r*=1.0+0.055*hi-0.012*sh;
        g.g*=1.0+0.008*sh;
        g.b*=1.0+0.045*sh-0.045*hi;
    } else {
        g.r*=1.0-0.038*sh+0.010*hi;
        g.g*=1.0+0.006*sh;
        g.b*=1.0+0.052*sh-0.016*hi;
    }
    float gy=dot(g,lum);
    if(y>0.000001 && gy>0.000001) g*=y/gy;
    return clamp(g,v*0.90,min(v*1.10,vec3(1.0)));
}

"""
 s=region(s,'vec3 DW_AtlasSlice(vec3 rgb, float sliceIndex)','void main()',new,'analytic LUT')
 return sub(s,'uniform vec4 u_Color;    // x = sharpen [0..0.75]; y = LUT mix [0..1]',
            'uniform vec4 u_Color;    // x CAS; y LUT; z mode 0/1/2','mode documented')
def apply(root,dry):
 changes.clear()
 b=(root/R/'tr_backend.c').read_text()
 assert 'DARKWOLF_SUN_HDR16F_PRECISION_V1_40878732886' in b,'not accepted HDR16F source'
 assert 'DARKWOLF_PORTAL_SKY_SINGLE_SAMPLE_UNIVERSAL_V1' in b,'missing accepted portal-sky'
 edits=[('tr_init.c',init),('tr_local.h',header),('tr_image.c',image),
        ('tr_shade.c',shade),('tr_backend.c',backend),
        ('tr_glsl.c',loader),('glsl/dwfinal_fp.glsl',finalShader)]
 if dry:
  with tempfile.TemporaryDirectory() as t:
   dst=Path(t)
   for rel,_ in edits:
    (dst/R/rel).parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(root/R/rel,dst/R/rel)
   return apply(dst,False)
 for rel,fn in edits:
  f=root/R/rel; before=f.read_text()
  assert MARK not in before
  after=fn(before)
  assert after!=before,rel
  f.write_text(after)
  changes[str(R/rel)]={'before':hashlib.sha256(before.encode()).hexdigest(),
                        'after':hashlib.sha256(after.encode()).hexdigest()}
 sh=(root/R/'tr_shade.c').read_text()
 assert 'backEnd.currentEntity != &tr.worldEntity' in sh
 assert 'GL_SAMPLE_ALPHA_TO_COVERAGE' in sh
 assert 'r_dwA2C' in sh
 assert 'dwFidelityTexture' in (root/R/'tr_image.c').read_text()
 assert 'DW_MipMapCutout' not in (root/R/'tr_image.c').read_text()
 assert 'texture2D(u_LevelsMap' not in (root/R/'glsl/dwfinal_fp.glsl').read_text()
 assert 'r_dwA2C' in (root/R/'tr_init.c').read_text()
 print('DW_TEXTURE_MATERIAL_QUALITY_V2_SOURCE_PASS',len(edits),flush=True)
 return {'accepted_parent_run':41019985033,'changes':changes,
         'retired':['synthetic adaptive upsample','binary-cutout CPU mips','red-prone LUT atlas'],
         'retained':['A2C on named model material only','CAS V03 exact math',
         'Texture Fidelity on player and weapon names only','Material Fidelity on models',
         'bounded analytic LUT opt-in','all unrelated HDR16F, SSGI, shadows, Tesla, volumetric'],
         'world_texture_sizing':'original default paths','source_defaults':'unchanged except retired sub-CVars',
         'real_GPU_accepted':False}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--check-only',action='store_true');p.add_argument('--proof',type=Path)
 a=p.parse_args()
 result=apply(a.root,a.check_only)
 if a.proof:a.proof.write_text(json.dumps(result,indent=2)+'\n')
