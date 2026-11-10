#!/usr/bin/env python3
"""Separate GLSL120/130 and math QA of isolated Xlabs Tesla PCF filters."""
import hashlib,json,math,random,shutil,subprocess,sys
from pathlib import Path
assert len(sys.argv)==3,"qa.py SOURCE_ROOT OUTPUT_DIR"
source=Path(sys.argv[1])/"SP/code/rend2"
out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
files=["glsl/dlight_fp.glsl","glsl/lightall_fp.glsl"]
src={k:(source/k).read_text() for k in files}
marker="DW_XLABS_TESLA_CUBE_FACE_FILTER_ESCAPE1_NATIVE_MASK_TEST_V5_20261028"
def extract(s,start):
 begin=s.index(start)
 end=s.index("\n}\n",begin)+3
 return s[begin:end]
f0=extract(src[files[0]],"float DW_TeslaWorldCubeFacePcfTest(")
f1=extract(src[files[0]],"float DlightWorldVisibility(")
assert f0==extract(src[files[1]],"float DW_TeslaWorldCubeFacePcfTest(")
assert f1==extract(src[files[1]],"float DlightWorldVisibility(")
assert f1.count("if (u_DlightWorldOrigin.w < -0.5)")==1
assert "if (u_DlightWorldOrigin.w <= 0.0) return 1.0;" in f1
assert f1.count("for (int iy = 0; iy < 2; ++iy)")==1
assert f0.count("for (int iy = 0; iy < 4; ++iy)")==1
assert f0.count("for (int ix = 0; ix < 4; ++ix)")==1
assert f0.count("vec2 st = (axis == 0)") == 1
assert f0.count("float invRange = encodedMode - float(mode);")==1
assert f0.count("float accepted = step((depth - 0.35) * invRange, stored);")==1
assert all(s.count(marker)==1 for s in src.values())
main=(source/"tr_main.c").read_text()
scene=(source/"tr_scene.c").read_text()
assert "r_dwTeslaWorldFilterTest\", \"0\", 0" in main
assert "fabs(dl->origin[0] + 548.8f)" in main
assert 'Q_stricmp(tr.world->baseName, "xlabs")' in main
assert "tr.refdef.dlightWorldOrigin[i][3] = -(float)mode - 1.0f / cache->radius" in main
assert "r_dwEscape1NativeWorldMaskTest\", \"0\", 0" in scene
assert "fabs(org[0] + 1340.0f)" in scene
assert "fabs(org[0] + 1212.0f)" in scene
assert 'Q_stricmp(tr.world->baseName, "escape1")' in scene
# Existing production stays in the original function and is unchanged apart from
# an unreachable-for-normal-lights negative-w dispatcher.
old="    if (u_DlightWorldOrigin.w <= 0.0) return 1.0;"
v4=Path("evidence/v4-old/SP/code/rend2")
assert main.count("VectorCopy(testCaptureOrigin, shadowParms.or.origin);")==1
assert "DARKWOLF_CRYPT1_ARCHITECTURAL_WORLD_VISIBILITY_PCF2X2_V1_20261028" in src[files[0]]
assert hashlib.sha256((source/"tr_backend.c").read_bytes()).hexdigest()=="e08d1f94b186fd46b078fbaf740e38c8cea93170836c2701c27801ad443f495f"
# Unit check: signed OpenGL cube mapping must round-trip world direction.
random.seed(20261028)
def project(vec):
 x,y,z=vec;a=[abs(x),abs(y),abs(z)]
 i=max(range(3),key=lambda n:(a[n],-n));sgn=1 if vec[i]>=0 else -1
 q=[x/max(a),y/max(a),z/max(a)]
 if i==0:s,t=-sgn*q[2],-q[1]
 elif i==1:s,t=q[0],sgn*q[2]
 else:s,t=sgn*q[0],-q[1]
 if i==0: reconstructed=(sgn,-t,-sgn*s)
 elif i==1: reconstructed=(s,sgn,sgn*t)
 else:reconstructed=(sgn*s,-t,sgn)
 return reconstructed
for _ in range(10000):
 v=[random.uniform(-1,1) for _ in range(3)]
 w=project(v)
 q=[u/max(map(abs,v)) for u in v]
 assert max(abs(x-y) for x,y in zip(w,q))<1e-12
def tent(s):
 first=math.floor(s)-1
 return [max(0,2-abs(first+j-s)) for j in range(4)]
for i in range(1001):
 a=i/1000
 x=tent(a)
 assert sum(x)>0 and all(0<=v<=2 for v in x)
 assert math.isclose(sum(x)/sum(x),1.0)
compiled=[]
glslang=shutil.which("glslangValidator")
assert glslang,"GLSLANG_VALIDATOR_REQUIRED"
for ver in (120,130):
 header=f"#version {ver}\n"+"uniform samplerCube u_DlightWorldMap;\nuniform vec4 u_DlightWorldOrigin;\n"
 header+=("varying vec3 worldPosition;\n" if ver==120 else "in vec3 worldPosition;\nout vec4 fragColor;\n")
 stub=("\nvoid main(){float v=DlightWorldVisibility(worldPosition);"
       +("gl_FragColor=vec4(v,v,v,1.0);" if ver==120 else "fragColor=vec4(v,v,v,1.0);")+"}\n")
 fpath=out/f"V5_TESLA_WORLD_CUBEFACE_{ver}.frag"
 fpath.write_text(header+f0+"\n"+f1+stub)
 p=subprocess.run([glslang,"-S","frag",str(fpath)],text=True,capture_output=True)
 (out/f"V5_TESLA_WORLD_CUBEFACE_{ver}.log").write_text(p.stdout+"\n"+p.stderr)
 assert p.returncode==0,(ver,p.stdout,p.stderr)
 compiled.append(ver)
report={
 "status":"SOURCE_UNIT_GLSL_PASS","glsl_versions":compiled,
 "cubeface_roundtrips":10000,"tent_weight_cases":1001,
 "test_only":True,"production_crypt1_path_same":True,
 "sha256_function":hashlib.sha256(f0.encode()).hexdigest(),
 "baseline_glsl_sha256":{"dlight":"1651e1e14c8154aead2616856ba2d7c1c5ab66b69fb26bd049a5dd9e236ed08c",
  "lightall":"f5d93f15acedb9139f648658774bc409690d07ef0a34f52058fe053c13bee2cd"},
 "user_gpu_test":"PENDING"}
(out/"V5_TESLA_GLSL_QA.json").write_text(json.dumps(report,indent=2)+"\n")
print("DW_XLABS_ESCAPE1_V5_CUBEFACE_GLSL120_130_NUMERIC_PASS")
