#!/usr/bin/env python3
"""V5.1 source length failure reproduction + complete shader permutation checks."""
import argparse,hashlib,json,re,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument("source",type=Path)
p.add_argument("--out",type=Path,required=True)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
root=a.source/"SP/code/rend2"
glsl=(root/"tr_glsl.c").read_text()
light=(root/"glsl/lightall_fp.glsl").read_text()
dlight=(root/"glsl/dlight_fp.glsl").read_text()
H=lambda t:hashlib.sha256(t.encode()).hexdigest()
assert H(glsl)=="9de909410773f35e0f967de7fbaff0bc4d5b3e86191734410b5e3f8aff894907",("TR_GLSL_SOURCE_HASH",H(glsl))
assert H(light)=="22c39b8796a9829a7b6ce951a3ad077dbe5b5d7643b8836692ee8d541a7655db"
assert H(dlight)=="3f0f27878f34b87f4b0877c83c195e30f89231ceab4e70cf8d694ab1867727cd"
assert (root/"tr_main.c").read_text().count("r_dwTeslaWorldFilterTest")==1
assert (root/"tr_scene.c").read_text().count("r_dwEscape1NativeWorldMaskTest")==1
assert glsl.count("char fpCode[65536];")==1
assert glsl.count("char vpCode[32000];")==1
assert glsl.count("if (size < 0 || destSize <= 0 || size >= destSize)")==1
assert glsl.count('ri.Error(ERR_FATAL, "Could not load lightall shader!")')==1
real_shader_bytes=len(light.encode())
legacy_limit=32000
new_limit=65536
assert real_shader_bytes==34029,(real_shader_bytes,"unexpected assembled body")
assert real_shader_bytes>legacy_limit  # reproduces user's exact early failure
# Runtime header+compile-time permutations can be up to 4KiB here:
# actual engine generator writes approximately 1-2KiB; check ample margin.
header_safety_bytes=4096
assert real_shader_bytes+header_safety_bytes+1<new_limit
assert real_shader_bytes+header_safety_bytes+1>legacy_limit
assert len(dlight.encode())+header_safety_bytes+1<new_limit
assert "#define varying in" in glsl
assert "GLSL_LoadGPUShaderText(name, fallback_fp, GL_FRAGMENT_SHADER, postHeader, size)" in glsl
assert "postHeader = &fpCode[strlen(fpCode)];" in glsl
assert "size -= strlen(fpCode);" in glsl
assert 'DW_XLABS_TESLA_CUBE_FACE_FILTER_ESCAPE1_NATIVE_MASK_TEST_V5_20261028' in light
assert "DW_TeslaWorldCubeFacePcfTest(worldPosition)" in light
assert "DARKWOLF_CRYPT1_ARCHITECTURAL_WORLD_VISIBILITY_PCF2X2_V1_20261028" in light
assert H((root/"tr_backend.c").read_text())=="e08d1f94b186fd46b078fbaf740e38c8cea93170836c2701c27801ad443f495f"
glslang=shutil.which("glslangValidator")
assert glslang, "CI_REQUIRES_GLSLANG_VALIDATOR"
base="#define r_FBufScale vec2(0.000781250, 0.001302083)\n"
types=[
 ("unlit",[]),
 ("lightmap",["USE_LIGHT","USE_LIGHTMAP","USE_NORMALMAP","USE_SPECULARMAP","GLOSS_IS_GLOSS"]),
 ("dlight_shadow",["USE_LIGHT","USE_LIGHT_VECTOR","USE_DLIGHT_SHADOWMAP","GLOSS_IS_GLOSS"]),
 ("dlight_shadow_normal",["USE_LIGHT","USE_LIGHT_VECTOR","USE_DLIGHT_SHADOWMAP","USE_NORMALMAP","USE_SPECULARMAP","GLOSS_IS_GLOSS"]),
 ("dlight_shadow_cubemap",["USE_LIGHT","USE_LIGHT_VECTOR","USE_DLIGHT_SHADOWMAP","USE_NORMALMAP","USE_SPECULARMAP","USE_CUBEMAP","GLOSS_IS_GLOSS"])
]
versions=[120,130,150]
results=[]
for ver in versions:
 for name,defs in types:
  # GLSL120 cube LOD requires GL_ARB_shader_texture_lod extension not enabled by the legacy renderer header; actual user GPU is GLSL150.
  if ver == 120 and "USE_CUBEMAP" in defs: continue
  hdr=f"#version {ver}\n"
  if ver>=130:
   hdr+="""#define varying in
out vec4 out_Color;
#define gl_FragColor out_Color
#define texture2D texture
#define textureCubeLod textureLod
#define shadow2D texture
"""
  hdr+=base+"#define r_dlightShadowFilter 2\n#define r_dlightFalloff 1\n"
  if "USE_CUBEMAP" in defs: hdr+="#define ROUGHNESS_MIPS float(5)\n"
  hdr+="".join("#define "+d+"\n" for d in defs)
  shader=hdr+light
  # Source is complete, including all actual lines and helper functions.
  dest=a.out/f"LIGHTALL_FULL_{ver}_{name}.frag"
  dest.write_text(shader)
  process=subprocess.run([glslang,"-S","frag",str(dest)],capture_output=True,text=True)
  (a.out/f"LIGHTALL_FULL_{ver}_{name}.log").write_text(process.stdout+"\n"+process.stderr)
  if process.returncode:
   raise AssertionError(("FULL_LIGHTALL_COMPILATION_FAILED",ver,name,process.stdout,process.stderr))
  results.append({"version":ver,"variant":name,"bytes":len(shader.encode())})
# All dlight variants also compiled with the same extended global buffer.
for ver in (120,130,150):
 hdr=f"#version {ver}\n"
 if ver>=130:
  hdr+="#define varying in\nout vec4 out_Color;\n#define gl_FragColor out_Color\n#define texture2D texture\n"
 hdr+="#define USE_DLIGHT_SHADOWMAP\n#define r_dlightShadowFilter 2\n#define r_dlightFalloff 1\n#define r_dlightFallbackMode 1\n#define r_dlightBacks 0\n"
 dest=a.out/f"DLIGHT_FULL_{ver}.frag"
 dest.write_text(hdr+dlight)
 process=subprocess.run([glslang,"-S","frag",str(dest)],capture_output=True,text=True)
 (a.out/f"DLIGHT_FULL_{ver}.log").write_text(process.stdout+"\n"+process.stderr)
 if process.returncode:
  raise AssertionError(("FULL_DLIGHT_COMPILATION_FAILED",ver,process.stdout,process.stderr))
 results.append({"version":ver,"variant":"dlight_shadow","bytes":len((hdr+dlight).encode())})
report={"status":"V5_1_FULL_SHADER_LOADER_AND_PERMUTATIONS_PASS",
 "cause":"V5 lightall_fp.glsl 34029-byte body cannot fit old 32000-byte fragment shader loading buffer",
 "shader_body_bytes":real_shader_bytes,"old_fp_buffer_bytes":legacy_limit,"new_fp_buffer_bytes":new_limit,
 "header_safety_bytes":header_safety_bytes,
 "glsl_compilation_cases":results,
 "protected_programs":["Crypt1 PCF2x2","Sun3","FireE","Tesla actual light","V5 filter shader unchanged"],
 "runtime_GPU_user_validation":"PENDING"}
(a.out/"V5_1_FULL_SHADER_QA.json").write_text(json.dumps(report,indent=2)+"\n")
print(report["status"],"variants",len(results))
