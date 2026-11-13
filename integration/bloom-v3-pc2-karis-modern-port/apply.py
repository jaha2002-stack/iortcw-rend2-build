#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
from pathlib import Path

V2="REND2_BLOOM_V2_HDR_MULTI_SCALE_PYRAMID"
V3="REND2_BLOOM_V3_HDR_SCATTER_PYRAMID"
V31="REND2_BLOOM_V3_1_HDR_INPUT_VALIDATION_SCATTER_STABILITY"
PC2="REND2_BLOOM_V3_22_LIGHTALL_NONFINITE_OUTPUT_FIREWALL_PC2"
KARIS="REND2_BLOOM_PC2_KARIS_ANTIFIREFLY_PRODUCTION_CANDIDATE_V2"
PORT="DW_BLOOM_V3_PC2_KARIS_MODERN_PORT_43189244002"
BLOOM_V2_SHA="80f9c017788db5296f804d5165432b5d788f4f252abe30eceac1006536ae0dd5"
ALLOW={
 "SP/code/rend2/glsl/bloom_fp.glsl",
 "SP/code/rend2/glsl/lightall_fp.glsl",
 "SP/code/rend2/tr_backend.c",
 "SP/code/rend2/tr_init.c",
 "SP/code/rend2/tr_local.h",
}
FROZEN={
 "SP/code/rend2/tr_fbo.c","SP/code/rend2/tr_image.c","SP/code/rend2/tr_postprocess.c",
 "SP/code/rend2/glsl/tonemap_fp.glsl","SP/code/rend2/glsl/bloom_vp.glsl",
 "SP/code/rend2/glsl/ssgi_fp.glsl","SP/code/rend2/glsl/ssgi_vp.glsl",
}

def h(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def snap(root):
 b=Path(root)/"SP/code/rend2"
 return {p.relative_to(root).as_posix():h(p) for p in b.rglob("*") if p.is_file()}
def one(s,a,b,label):
 n=s.count(a)
 if n!=1: raise SystemExit(f"{label}: expected 1 anchor, got {n}")
 return s.replace(a,b,1)
def run(p,root,label):
 if not Path(p).is_file(): raise SystemExit(f"{label} patcher missing: {p}")
 subprocess.run([sys.executable,str(p),"--root",str(root)],check=True)

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("root",type=Path); ap.add_argument("--v3-patcher",required=True,type=Path)
 ap.add_argument("--v31-patcher",required=True,type=Path); ap.add_argument("--proof",required=True,type=Path)
 a=ap.parse_args(); root=a.root.resolve(); r=root/"SP/code/rend2"
 f={"bloom":r/"glsl/bloom_fp.glsl","light":r/"glsl/lightall_fp.glsl","be":r/"tr_backend.c","init":r/"tr_init.c","local":r/"tr_local.h"}
 for p in f.values():
  if not p.is_file(): raise SystemExit(f"missing {p}")
 pre=snap(root); frozen={x:h(root/x) for x in FROZEN}; pret={k:h(v) for k,v in f.items()}
 if h(f["bloom"])!=BLOOM_V2_SHA: raise SystemExit("Bloom V2 fragment base SHA drift")
 for k in ("be","init","local"):
  if V2 not in f[k].read_text(encoding="utf-8"): raise SystemExit(f"{k}: V2 marker missing")
 for marker in (V3,V31,PC2,KARIS,PORT):
  if any(marker in p.read_text(encoding="utf-8",errors="ignore") for p in f.values()): raise SystemExit(f"repeat/drift: {marker}")

 # Exact historical V3 and V3.1 transforms.
 run(a.v3_patcher,root,"V3")
 run(a.v31_patcher,root,"V3.1")
 fp=f["bloom"].read_text(encoding="utf-8"); be=f["be"].read_text(encoding="utf-8")
 if V3 not in fp or V3 not in be or V31 not in fp or V31 not in be: raise SystemExit("historical V3/V3.1 markers missing")

 # Modern PC2: only helper + final RGB firewall; finite PBR path must round-trip exactly.
 light0=f["light"].read_text(encoding="utf-8")
 for x in ("USE_PBR2","DW_LinearToSRGB","USE_PBR2_IBL_V31","USE_PBR_PHYSICAL_RELIEF_V32"):
  if x not in light0: raise SystemExit(f"modern LightAll prerequisite missing: {x}")
 helper=f"""// {PORT}: production-only helper preserving the #32847437364 PC2 contract.
bool DW_BloomPC2Bad3(vec3 v) {{ return any(isnan(v)) || any(isinf(v)); }}

"""
 fw=f"\tif (DW_BloomPC2Bad3(gl_FragColor.rgb)) {{ gl_FragColor.rgb = vec3(0.0); }} // {PC2}\n"
 light=one(light0,"void main()\n{\n",helper+"void main()\n{\n","PC2 helper")
 light=one(light,"\tgl_FragColor.a = alpha;\n",fw+"\tgl_FragColor.a = alpha;\n","PC2 final firewall")
 if light.replace(helper,"",1).replace(fw,"",1)!=light0: raise SystemExit("PC2 finite-path round trip failed")
 f["light"].write_text(light,encoding="utf-8",newline="\n")

 # Exact Karis candidate-v2 fragment branch from accepted #328 package.
 fp=f["bloom"].read_text(encoding="utf-8")
 karis="""\t// REND2_BLOOM_PC2_KARIS_ANTIFIREFLY_PRODUCTION_CANDIDATE_V2
\t// Mode 7: center-preserving Karis-style 3x3 resolve on the already extracted 1/2-res bright source.
\tif (u_Color.w > 6.5 && u_Color.w < 7.5)
\t{
\t\tfloat safeMax = max(u_Color.x, 8.0);
\t\tvec2 d = u_InvTexRes;
\t\tvec3 c0 = BloomSafeColor(texture2D(u_TextureMap, var_TexCoords + d * vec2(-1.0, -1.0)).rgb, safeMax);
\t\tvec3 c1 = BloomSafeColor(texture2D(u_TextureMap, var_TexCoords + d * vec2( 0.0, -1.0)).rgb, safeMax);
\t\tvec3 c2 = BloomSafeColor(texture2D(u_TextureMap, var_TexCoords + d * vec2( 1.0, -1.0)).rgb, safeMax);
\t\tvec3 c3 = BloomSafeColor(texture2D(u_TextureMap, var_TexCoords + d * vec2(-1.0,  0.0)).rgb, safeMax);
\t\tvec3 c4 = BloomSafeColor(texture2D(u_TextureMap, var_TexCoords).rgb, safeMax);
\t\tvec3 c5 = BloomSafeColor(texture2D(u_TextureMap, var_TexCoords + d * vec2( 1.0,  0.0)).rgb, safeMax);
\t\tvec3 c6 = BloomSafeColor(texture2D(u_TextureMap, var_TexCoords + d * vec2(-1.0,  1.0)).rgb, safeMax);
\t\tvec3 c7 = BloomSafeColor(texture2D(u_TextureMap, var_TexCoords + d * vec2( 0.0,  1.0)).rgb, safeMax);
\t\tvec3 c8 = BloomSafeColor(texture2D(u_TextureMap, var_TexCoords + d * vec2( 1.0,  1.0)).rgb, safeMax);
\t\tconst vec3 luma = vec3(0.2126, 0.7152, 0.0722);
\t\tfloat w0=1.0/(1.0+max(dot(c0,luma),0.0)), w1=1.0/(1.0+max(dot(c1,luma),0.0)), w2=1.0/(1.0+max(dot(c2,luma),0.0));
\t\tfloat w3=1.0/(1.0+max(dot(c3,luma),0.0)), w4=1.0/(1.0+max(dot(c4,luma),0.0)), w5=1.0/(1.0+max(dot(c5,luma),0.0));
\t\tfloat w6=1.0/(1.0+max(dot(c6,luma),0.0)), w7=1.0/(1.0+max(dot(c7,luma),0.0)), w8=1.0/(1.0+max(dot(c8,luma),0.0));
\t\tfloat wsum=w0+w1+w2+w3+w4+w5+w6+w7+w8;
\t\tvec3 karis=(c0*w0+c1*w1+c2*w2+c3*w3+c4*w4+c5*w5+c6*w6+c7*w7+c8*w8)/max(wsum,0.0001);
\t\tfloat centerPeak=max(max(c4.r,c4.g),c4.b), localPeak=max(max(karis.r,karis.g),karis.b);
\t\tfloat isolation=clamp((centerPeak-localPeak)/max(centerPeak,0.0001),0.0,1.0);
\t\tisolation*=isolation;
\t\tgl_FragColor=vec4(BloomSafeColor(mix(c4,karis,isolation),safeMax),1.0);
\t\treturn;
\t}

"""
 fp=one(fp,"void main()\n{\n","void main()\n{\n"+karis,"Karis shader")
 f["bloom"].write_text(fp,encoding="utf-8",newline="\n")

 be=f["be"].read_text(encoding="utf-8")
 be=one(be,"\tvec4_t blurParams;\n\tvec4_t safeCopyParams;\n",
        "\tvec4_t blurParams;\n\tvec4_t safeCopyParams;\n\tvec4_t antiFireflyParams; // "+KARIS+"\n","Karis params")
 block="""\t// REND2_BLOOM_PC2_KARIS_ANTIFIREFLY_PRODUCTION_CANDIDATE_V2
\tif (s_bloomV1.scatterSafety >= 3)
\t{
\t\tVectorSet4(antiFireflyParams, s_bloomV1.scatterSafeMax, 1.0f, 0.0f, 7.0f);
\t\tFBO_Blit(tr.bloomPyramidFbo[0][0], s_bloomV1.pyramidBox[0], NULL,
\t\t\ttr.bloomPyramidFbo[0][1], s_bloomV1.pyramidBox[0], &tr.bloomShader, antiFireflyParams, 0);
\t\tVectorSet4(safeCopyParams, s_bloomV1.scatterSafeMax, 1.0f, 0.0f, 5.0f);
\t\tFBO_Blit(tr.bloomPyramidFbo[0][1], s_bloomV1.pyramidBox[0], NULL,
\t\t\ttr.bloomPyramidFbo[0][0], s_bloomV1.pyramidBox[0], &tr.bloomShader, safeCopyParams, 0);
\t}

"""
 gate="\t// Safety 2+ sanitizes every Gaussian tap and output. Safety 0/1 keep exact v3.0 blur math.\n"
 be=one(be,gate,block+gate,"Karis pre-pyramid")
 f["be"].write_text(be,encoding="utf-8",newline="\n")

 post=snap(root); changed=sorted(x for x in set(pre)|set(post) if pre.get(x)!=post.get(x))
 if set(changed)!=ALLOW: raise SystemExit(f"changed-file allowlist violation: {changed}")
 for rel,d in frozen.items():
  if h(root/rel)!=d: raise SystemExit(f"frozen file changed: {rel}")

 fp=f["bloom"].read_text(encoding="utf-8"); be=f["be"].read_text(encoding="utf-8")
 init=f["init"].read_text(encoding="utf-8"); local=f["local"].read_text(encoding="utf-8"); light=f["light"].read_text(encoding="utf-8")
 checks={
  "v3":V3 in fp and V3 in be, "v31":V31 in fp and V31 in be,
  "pc2":light.count(PC2)==1 and light.count("DW_BloomPC2Bad3")==2,
  "karis":fp.count(KARIS)==1 and be.count(KARIS)==2,
  "mode3":'r_bloomMode, 1, 3, qtrue' in init,
  "v2fallback":'#define REND2_BLOOM_V2_LEVELS 3' in local and 'RB_BloomV2Prepare' in be and 'RB_BloomV2Composite' in be,
  "fivelevels":'#define REND2_BLOOM_PYRAMID_LEVELS 5' in local,
  "safety3":'r_bloomScatterSafety = ri.Cvar_Get( "r_bloomScatterSafety", "3"' in init,
  "levels5":'r_bloomScatterMaxLevels = ri.Cvar_Get( "r_bloomScatterMaxLevels", "5"' in init,
  "safe64":'r_bloomScatterSafeMax = ri.Cvar_Get( "r_bloomScatterSafeMax", "64.0"' in init,
  "pbr":'USE_PBR2' in light and 'DW_LinearToSRGB' in light,
  "ggx":'USE_PBR2_IBL_V31' in light, "pom":'USE_PBR_PHYSICAL_RELIEF_V32' in light,
  "candidatev1absent":'hdrEligibility' not in fp,
 }
 bad=[k for k,v in checks.items() if not v]
 if bad: raise SystemExit("contract failures: "+",".join(bad))
 proof={"port":PORT,"source_reference_run":32847437364,"target_base_run":43189244002,
        "target_base_renderer_sha256":"4d9a01bc0edbfcf9fa5540ed6ad5ec74fe4a8cf4c61fc79d38bfc90f4f0e23d0",
        "changed_files":changed,"pre_target_sha256":pret,"post_target_sha256":{k:h(v) for k,v in f.items()},
        "frozen_sha256":frozen,"checks":checks}
 a.proof.parent.mkdir(parents=True,exist_ok=True); a.proof.write_text(json.dumps(proof,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(json.dumps(proof,indent=2,sort_keys=True)); print("DW_BLOOM_V3_PC2_KARIS_MODERN_PORT_APPLY_PASS")
if __name__=="__main__": main()
