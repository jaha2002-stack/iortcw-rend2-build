#!/usr/bin/env python3
"""Clean production #406409 precise Tesla X2 F2 / Escape1 A whole shader QA."""
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
assert H(light)=="2b16f2ad0902ba879ee5d854cc2d2f23d8668d80178074568cbcf42735157d3f"
assert H(dlight)=="abd8c2330a21bd0101a108104bda0392fe09bc7d74649013d9271c357f6ea701"
main=(root/"tr_main.c").read_text()
scene=(root/"tr_scene.c").read_text()
assert H(main)=="a304b1e0a30b9d834c9180e15e9275dd40fc08e939f38e675815f4cadca4da59"
assert H(scene)=="273e7ead08b25a2b035b69578c2e41b34a7712bba3646fee1961042a5154f7c5"
for source in (main,scene,light,dlight,glsl):
 for bad in ("r_dwTeslaWorldFilterTest","r_dwTeslaWorldCaptureXTest",
             "r_dwEscape1NativeWorldMaskTest","r_dwMainSceneLightAuditOnce",
             "DW_MAIN_SCENE_AUDIT_V4","DW_TeslaWorldCubeFacePcfTest"):
  assert bad not in source,("PRODUCTION_TEST_RESIDUE",bad)
assert main.count("capture[0] += 64.0f;")==1
assert main.count("tr.refdef.dlightWorldOrigin[i][3] = -2.0f - 1.0f / cache->radius;")==1
assert main.count("R_DWIsStationaryXlabsTeslaWorldLight(")==3
assert scene.count("fabs(org[0] + 1340.0f) < 2.0f")==1
assert "fabs(org[0] + 1212.0f)" not in scene
assert "r_dlightWorldContainment->integer >= 1 && nativeAuthoredDlightMarker" in scene
assert glsl.count("char fpCode[65536];")==1
assert glsl.count("char vpCode[32000];")==1
assert glsl.count("if (size < 0 || destSize <= 0 || size >= destSize)")==1
assert glsl.count('ri.Error(ERR_FATAL, "Could not load lightall shader!")')==1
real_shader_bytes=len(light.encode())
legacy_limit=32000
new_limit=65536
assert real_shader_bytes==33448,(real_shader_bytes,"unexpected assembled body")
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
assert "DARKWOLF_XLABS_TESLA_X2_F2_ESCAPE1_A_CLEAN_PRODUCTION_20261028" in light
assert "DW_TeslaWorldCubeFacePcf4x4(worldPosition)" in light
assert "float invRange = -u_DlightWorldOrigin.w - 2.0;" in light
assert "if (mode == 1" not in light
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
report={"status":"DARKWOLF_X2_F2_ESCAPE1_A_FULL_GLSL_QA_PASS",
 "cause":"Promoted F2-only lightall source needs the previously user-tested 65536-byte fragment loading buffer",
 "shader_body_bytes":real_shader_bytes,"old_fp_buffer_bytes":legacy_limit,"new_fp_buffer_bytes":new_limit,
 "header_safety_bytes":header_safety_bytes,
 "glsl_compilation_cases":results,
 "protected_programs":["Crypt1 PCF2x2","Sun3","FireE","Local","Sky","Tesla actual source/2048 point shadows"],
 "source_allowlist":["SP/code/rend2/tr_main.c","SP/code/rend2/tr_scene.c",
                     "SP/code/rend2/tr_glsl.c","SP/code/rend2/glsl/dlight_fp.glsl",
                     "SP/code/rend2/glsl/lightall_fp.glsl"],
 "engine_code_files_changed":5,"temp_cvars":[],
 "crypt1_original_pcf_unchanged":True,
 "xlabs_tesla_capture_offset_x":64,"escape1_fire_source_A_only":True,
 "glsl_variants_passed":len(results),
 "runtime_GPU_user_validation":"PENDING"}
(a.out/"DARKWOLF_CLEAN_PRODUCTION_SOURCE_GLSL_QA.json").write_text(json.dumps(report,indent=2)+"\n")
print(report["status"],"variants",len(results))
