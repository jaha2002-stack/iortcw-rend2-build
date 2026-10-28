#!/usr/bin/env python3
"""V5.1: reproduce actual >=32k fragment loader overflow; compile entire shaders."""
import hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
assert len(sys.argv)==3,"usage qa.py SOURCE OUT"
root=Path(sys.argv[1])/"SP/code/rend2"
out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
loader=(root/"tr_glsl.c").read_text()
shader={(name): (root/"glsl"/f"{name}_fp.glsl").read_text()
        for name in ("lightall","dlight")}
sizes={name:len(s.encode("utf-8")) for name,s in shader.items()}
assert sizes=={"lightall":34029,"dlight":15350},("UNEXPECTED_SHADER_SIZES",sizes)
assert sha(loader.encode())=="61be71110ad88bc58c9a61dc19fdb1650b0b70d240c547ccfd56131c5d02e508"
assert len(re.findall(r"char fpCode\[65536\]",loader))==1
assert "char fpCode[32000]" not in loader
assert loader.count("char vpCode[32000]")==1
assert "size = sizeof(fpCode);" in loader
assert "GLSL_GetShaderHeader(GL_FRAGMENT_SHADER, extra, fpCode, size);" in loader
assert "size -= strlen(fpCode);" in loader
assert "GLSL_LoadGPUShaderText(name, fallback_fp, GL_FRAGMENT_SHADER, postHeader, size)" in loader
assert "size >= destSize" in loader
assert sizes["lightall"]>=32000, "V5_ORIGINAL_BUG_NOT_REPRODUCED"
assert sizes["lightall"]+4096<65536,"INSUFFICIENT_SAFE_HEADER_CAPACITY"
assert "DW_XLABS_TESLA_CUBE_FACE_FILTER_ESCAPE1_NATIVE_MASK_TEST_V5_20261028" in shader["lightall"]
assert "DW_XLABS_TESLA_CUBE_FACE_FILTER_ESCAPE1_NATIVE_MASK_TEST_V5_20261028" in shader["dlight"]
# Verify all the bytes of the GPU logic remain exactly as the already-built V5.
assert sha(shader["lightall"].encode())=="22c39b8796a9829a7b6ce951a3ad077dbe5b5d7643b8836692ee8d541a7655db"
assert sha(shader["dlight"].encode())=="3f0f27878f34b87f4b0877c83c195e30f89231ceab4e70cf8d694ab1867727cd"
glslang=shutil.which("glslangValidator")
assert glslang,"MISSING_GLSLANG_IN_CI"
variants=[
 ("lightall",120,["USE_LIGHT","USE_LIGHT_VECTOR","USE_DLIGHT_SHADOWMAP","r_dlightShadowFilter 2","r_dlightFalloff 0","GLOSS_IS_GLOSS"]),
 ("lightall",130,["USE_LIGHT","USE_LIGHT_VECTOR","USE_DLIGHT_SHADOWMAP","r_dlightShadowFilter 2","r_dlightFalloff 0","USE_NORMALMAP","GLOSS_IS_GLOSS"]),
 ("lightall",150,["USE_LIGHT","USE_LIGHT_VECTOR","USE_DLIGHT_SHADOWMAP","r_dlightShadowFilter 2","r_dlightFalloff 0","USE_NORMALMAP","USE_SPECULARMAP","GLOSS_IS_GLOSS"]),
 ("lightall",150,["USE_LIGHT","USE_LIGHTMAP","USE_NORMALMAP","GLOSS_IS_GLOSS"]),
 ("dlight",120,["USE_DLIGHT_SHADOWMAP","r_dlightShadowFilter 2"]),
 ("dlight",130,["USE_DLIGHT_SHADOWMAP","r_dlightShadowFilter 2"]),
 ("dlight",150,["USE_DLIGHT_SHADOWMAP","r_dlightShadowFilter 2"]),
]
compiled=[]
for name,ver,defs in variants:
 header=f"#version {ver}\n"
 if ver>=130:
  header+="#define varying in\nout vec4 out_Color;\n#define gl_FragColor out_Color\n"
  header+="#define texture2D texture\n#define textureCubeLod textureLod\n#define shadow2D texture\n"
 else:header+="#define shadow2D(a,b) shadow2D(a,b).r\n"
 header+="#ifndef M_PI\n#define M_PI 3.14159265358979323846\n#endif\n"
 header+="#define r_FBufScale vec2(0.000781250,0.001302083)\n"
 header+="\n".join("#define "+x for x in defs)+"\n#line 0\n"
 full=header+shader[name]
 assert len(full.encode("utf-8"))<65536
 label=name+"_"+str(ver)+"_"+("normal" if "USE_NORMALMAP" in defs else "basic")+"_"+("shadow" if "USE_DLIGHT_SHADOWMAP" in defs else "baked")
 filename=out/(label+".frag")
 filename.write_text(full)
 proc=subprocess.run([glslang,"-S","frag",str(filename)],capture_output=True,text=True)
 (out/(label+".log")).write_text(proc.stdout+"\n"+proc.stderr)
 if proc.returncode:
  raise RuntimeError(f"FULL_SHADER_COMPILE_FAIL {label}\n{proc.stdout}\n{proc.stderr}")
 compiled.append(label)
report={
 "status":"FULL_SHADER_GLSL_120_130_150_PASS",
 "root_cause":"V5 lightall source size 34029 > 32000-byte fpCode loader buffer",
 "frozen_production_run":40640998083,
 "previous_v5_run":40668719725,
 "shader_source_sizes":sizes,
 "previous_fragment_loader_capacity":32000,
 "repaired_fragment_loader_capacity":65536,
 "fragment_shader_header_safety_margin":65536-sizes["lightall"]-4096,
 "header_max_budget_assumed":4096,
 "full_shader_variants_compiled":compiled,
 "shaders_modified_by_v5_1":False,
 "new_gpu_logic":False,
 "GPU_runtime":"PENDING_USER_TEST",
}
(out/"V5_1_FULL_GLSL_QA.json").write_text(json.dumps(report,indent=2)+"\n")
print("DW_V5_1_FULL_SHADER_SIZE_AND_COMPILE_7_VARIANTS_PASS")
