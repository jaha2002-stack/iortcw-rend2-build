#!/usr/bin/env python3
"""Sun-only FP16 scratch, exact #40878732886 lineage. No GLSL or Local/Fire changes."""
import argparse,hashlib,json
from pathlib import Path
MARK="DARKWOLF_SUN_HDR16F_PRECISION_V1_40878732886"
FILES=["tr_local.h","tr_image.c","tr_fbo.c","tr_backend.c"]
def rep(s,a,b,key):
 n=s.count(a)
 assert n==1,(key,"expected 1",n)
 return s.replace(a,b,1)
def hash_(s):return hashlib.sha256(s.encode()).hexdigest()
def apply(root,check=False):
 p=Path(root)/"SP/code/rend2"
 a={n:(p/n).read_text() for n in FILES}
 assert all(MARK not in s for s in a.values()),"already patched"
 assert "DARKWOLF_VOLUMETRIC_COVERAGE_AA_PRODUCTION_V443" in a["tr_backend.c"]
 assert "DARKWOLF_PORTAL_SKY_SINGLE_SAMPLE_UNIVERSAL_V1" in a["tr_backend.c"]
 assert "DARKWOLF_VOLUMETRIC_COVERAGE_AA_PRODUCTION_V443" in a["tr_image.c"]
 assert "DARKWOLF_VOLUMETRIC_COVERAGE_AA_PRODUCTION_V443" in a["tr_fbo.c"]
 b=dict(a)
 b["tr_local.h"]=rep(b["tr_local.h"],
 "image_t                 *volumetricFullresImage; // DARKWOLF_VOLUMETRIC_COVERAGE_AA_PRODUCTION_V443",
 "image_t                 *volumetricFullresImage; // DARKWOLF_VOLUMETRIC_COVERAGE_AA_PRODUCTION_V443\n\timage_t                 *volumetricSunHalfImage; // "+MARK,
 "sun image field")
 b["tr_local.h"]=rep(b["tr_local.h"],
 "FBO_t                   *volumetricFullresFbo; // DARKWOLF_VOLUMETRIC_COVERAGE_AA_PRODUCTION_V443",
 "FBO_t                   *volumetricFullresFbo; // DARKWOLF_VOLUMETRIC_COVERAGE_AA_PRODUCTION_V443\n\tFBO_t                   *volumetricSunHalfFbo; // "+MARK,
 "sun FBO field")
 src='''\t\t// DARKWOLF_VOLUMETRIC_COVERAGE_AA_PRODUCTION_V443
\t\tif (r_hdr->integer)
\t\t\ttr.volumetricFullresImage = R_CreateImage("*volumetricFullres", NULL, width, height, IMGTYPE_COLORALPHA, IMGFLAG_NO_COMPRESSION | IMGFLAG_CLAMPTOEDGE, hdrFormat);
'''
 dst=src+'''
\t\t// '''+MARK+''': Sun-only RGBA16F; keep shared quarterImage unchanged.
\t\tif (r_hdr->integer && glRefConfig.textureFloat)
\t\t\ttr.volumetricSunHalfImage = R_CreateImage("*dwSunHalfRGBA16F", NULL,
\t\t\t\t(width > 1) ? width / 2 : 1, (height > 1) ? height / 2 : 1,
\t\t\t\tIMGTYPE_COLORALPHA, IMGFLAG_NO_COMPRESSION | IMGFLAG_CLAMPTOEDGE, GL_RGBA16F_ARB);
'''
 b["tr_image.c"]=rep(b["tr_image.c"],src,dst,"sun image allocation")
 src='''\t// DARKWOLF_VOLUMETRIC_COVERAGE_AA_PRODUCTION_V443
\tif (tr.volumetricFullresImage)
\t{
\t\ttr.volumetricFullresFbo = FBO_Create("_volumetricFullres", tr.volumetricFullresImage->width, tr.volumetricFullresImage->height);
\t\tFBO_AttachImage(tr.volumetricFullresFbo, tr.volumetricFullresImage, GL_COLOR_ATTACHMENT0, 0);
\t\tR_CheckFBO(tr.volumetricFullresFbo);
\t}
'''
 dst=src+'''
\t// '''+MARK+''': depth-detached, raymarch samples existing renderDepthImage.
\tif (tr.volumetricSunHalfImage)
\t{
\t\ttr.volumetricSunHalfFbo = FBO_Create("_dwSunHalfRGBA16F", tr.volumetricSunHalfImage->width, tr.volumetricSunHalfImage->height);
\t\tFBO_AttachImage(tr.volumetricSunHalfFbo, tr.volumetricSunHalfImage, GL_COLOR_ATTACHMENT0, 0);
\t\tR_CheckFBO(tr.volumetricSunHalfFbo);
\t}
'''
 b["tr_fbo.c"]=rep(b["tr_fbo.c"],src,dst,"sun FBO allocation")
 b["tr_backend.c"]=rep(b["tr_backend.c"],
 "\tqboolean gateFbo = (glRefConfig.framebufferObject && tr.quarterFbo[0]) ? qtrue : qfalse;",
 "\t// "+MARK+": preserve RGBA8 fallback on non-float hardware.\n\tFBO_t *sunInputFbo = tr.volumetricSunHalfFbo ? tr.volumetricSunHalfFbo : tr.quarterFbo[0];\n\tqboolean gateFbo = (glRefConfig.framebufferObject && sunInputFbo) ? qtrue : qfalse;",
 "sun FBO selection")
 for old,new in [
 ("FBO_Blit(srcFbo, srcBox, NULL, tr.quarterFbo[0], NULL, &tr.volumetricSunShader, params, 0);",
  "FBO_Blit(srcFbo, srcBox, NULL, sunInputFbo, NULL, &tr.volumetricSunShader, params, 0);"),
 ("FBO_Blit(tr.quarterFbo[0], NULL, NULL, tr.volumetricFullresFbo, srcBox, &tr.volumetricLocalUpscaleShader, aaParams, 0);",
  "FBO_Blit(sunInputFbo, NULL, NULL, tr.volumetricFullresFbo, srcBox, &tr.volumetricLocalUpscaleShader, aaParams, 0);"),
 ("FBO_Blit(tr.quarterFbo[0], NULL, NULL, srcFbo, srcBox, NULL, NULL, GLS_SRCBLEND_ONE | GLS_DSTBLEND_ONE);",
  "FBO_Blit(sunInputFbo, NULL, NULL, srcFbo, srcBox, NULL, NULL, GLS_SRCBLEND_ONE | GLS_DSTBLEND_ONE);")]:
  start=b["tr_backend.c"].index("static void RB_VolumetricSun(")
  end=b["tr_backend.c"].index("\n// DARKWOLF_LAMP_VOLUMETRIC",start)
  section=b["tr_backend.c"][start:end]
  assert section.count(old)==1,("wrong sun blit anchor",old)
  b["tr_backend.c"]=b["tr_backend.c"][:start]+section.replace(old,new,1)+b["tr_backend.c"][end:]
 assert b["tr_backend.c"].count("sunInputFbo")==5
 assert "GL_RGBA8" in b["tr_image.c"].split("tr.quarterImage[x] = R_CreateImage",1)[1].split(";",1)[0]
 assert all(a[n]!=b[n] for n in FILES)
 if not check:
  for n in FILES:(p/n).write_text(b[n])
 return {"base_run":40878732886,"marker":MARK,"check_only":check,
  "modified_files":["SP/code/rend2/"+n for n in FILES],
  "sha256_before":{n:hash_(a[n]) for n in FILES},
  "sha256_after":{n:hash_(b[n]) for n in FILES},
  "glsl_modified":False,"local_fire_code_modified":False,
  "new_cvars":[],"new_dither":False,"gpu_test":"PENDING"}
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("root",type=Path)
 p.add_argument("--check-only",action="store_true")
 p.add_argument("--proof",type=Path)
 a=p.parse_args()
 r=apply(a.root,check=a.check_only)
 if a.proof:a.proof.write_text(json.dumps(r,indent=2)+"\n")
 print("DARKWOLF_SUN_HDR16F_PRECISION_V1_SOURCE_PASS")
