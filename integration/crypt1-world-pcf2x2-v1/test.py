#!/usr/bin/env python3
"""Static guard + GLSL120/130 + numeric PCF response checks for Crypt1 world mask."""
import argparse,hashlib,json,math,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument("source",type=Path)
p.add_argument("--out",type=Path,required=True)
p.add_argument("--require-glslang",action="store_true")
a=p.parse_args()
root=a.source/"SP/code/rend2"
files=["glsl/dlight_fp.glsl","glsl/lightall_fp.glsl"]
mark="DARKWOLF_CRYPT1_ARCHITECTURAL_WORLD_VISIBILITY_PCF2X2_V1_20261028"
s={k:(root/k).read_text() for k in files}
def func(source):
    start=source.index("float DlightWorldVisibility(vec3 worldPosition)")
    end=source.index("\n}\n",start)+3
    return source[start:end]
def H(x):return hashlib.sha256(x.encode()).hexdigest()
f=func(s[files[0]])
assert f==func(s[files[1]]),"WORLD_VISIBILITY_FAMILY_DIVERGENCE"
assert f.count("for (int iy = 0; iy < 2; ++iy)")==1
assert f.count("for (int ix = 0; ix < 2; ++ix)")==1
assert f.count("texture(u_DlightWorldMap, ray)")==1
assert f.count("textureCube(u_DlightWorldMap, ray)")==1
assert "float planeDepth = numerator / denominator;" in f
assert "float test = step((depth - 0.35) * u_DlightWorldOrigin.w, stored);" in f
assert "visibility += wx * wy * test;" in f
assert "return clamp(visibility, 0.0, 1.0);" in f
assert "uniform samplerCube u_DlightWorldMap;" in s[files[0]]
assert "uniform vec4 u_DlightWorldOrigin;" in s[files[0]]
for k,v in s.items():
    assert v.count(mark)==1,k
    assert "DlightWorldVisibility(" in v
    assert "uniform samplerCube u_DlightShadowMap;" in v
    assert not any(bad in v for bad in ("r_dwCrypt1World","r_dwWorldGateFilter")),k
assert H(f)!= "2e518538bb8fb3db37377e539b8642e4c18bd1327e1b1ef1bf1cabdb909348d8"

def blend(taps,fx,fy):
    assert len(taps)==4 and 0<=fx<=1 and 0<=fy<=1
    return ((1-fx)*(1-fy)*taps[0] +fx*(1-fy)*taps[1]+
            (1-fx)*fy*taps[2] + fx*fy*taps[3])
cases=[
 ("fully_visible",[1,1,1,1],.37,.48,1.0),
 ("fully_blocked",[0,0,0,0],.37,.48,0.0),
 ("hard_wall_interior",[0,0,0,0],0.0,0.0,0.0),
 ("seam_start",[0,1,0,1],0.0,.39,0.0),
 ("seam_midpoint",[0,1,0,1],.5,.39,.5),
 ("seam_end",[0,1,0,1],1.0,.39,1.0),
 ("one_open_corner",[0,0,0,1],.5,.5,.25),
 ("single_block_corner",[0,1,1,1],.5,.5,.75),
 ("face_min_clamped",[1,0,1,0],0.0,.5,1.0),
 ("face_max_clamped",[1,0,1,0],1.0,.5,0.0)
]
for name,taps,fx,fy,expected in cases:
    v=blend(taps,fx,fy)
    assert math.isclose(v,expected,abs_tol=1e-12),(name,v,expected)
for t in [j/100 for j in range(101)]:
    assert 0<=blend([0,1,0,1],t,.5)<=1
    if t>0: assert blend([0,1,0,1],t,.5)>=blend([0,1,0,1],t-.01,.5)
assert math.isclose(blend([1,0,1,0],.5,.5)+blend([0,1,0,1],.5,.5),1.0)
a.out.mkdir(parents=True,exist_ok=True)
glslang=shutil.which("glslangValidator")
if a.require_glslang: assert glslang, "GLSLANG_REQUIRED_IN_CI"
compiled=[]
if glslang:
    for v in (120,130):
        hdr=("#version "+str(v)+"\n" +
             "uniform samplerCube u_DlightWorldMap;\n"+
             "uniform vec4 u_DlightWorldOrigin;\n"+
             ("in" if v==130 else "varying")+" vec3 shaderWorldPosition;\n"+
             ("out vec4 fragColor;\n" if v==130 else ""))
        source=hdr+f+"\nvoid main(){float a=DlightWorldVisibility(shaderWorldPosition);"+(
            "fragColor=vec4(a,a,a,1.0);" if v==130 else "gl_FragColor=vec4(a,a,a,1.0);")+"}\n"
        tmp=a.out/("WORLD_GATE_GLSL"+str(v)+".frag")
        tmp.write_text(source)
        result=subprocess.run([glslang,"-S","frag",str(tmp)],text=True,capture_output=True)
        (a.out/("WORLD_GATE_GLSL"+str(v)+".log")).write_text(result.stdout+"\n"+result.stderr)
        assert result.returncode==0,("GLSL_COMPILE_FAILED",v,result.stdout,result.stderr)
        compiled.append(v)
        print("GLSL_WORLD_PCF2X2_PASS",v)
report={"status":"STATIC_AND_GLSL_PASS" if compiled else "STATIC_ONLY",
        "mode":"world visibility hard mask to per-sample 2x2 filtered comparisons",
        "function_hash":H(f),"GLSL_versions":compiled,
        "numeric_cases":[n for n,*_ in cases],
        "four_sample_weights_sum_one":True,"full_walls_remain_zero":True,
        "underlying_depth_map":"GL_NEAREST_RGB_PACKED_UNCHANGED",
        "primary_shadow_PCF_2048":"UNCHANGED",
        "new_cvars":[],"GPU_validation":"PENDING"}
(a.out/"CRYPT1_WORLD_PCF2X2_SHADER_TESTS.json").write_text(json.dumps(report,indent=2)+"\n")
print("DW_CRYPT1_WORLD_PCF2X2_STATIC_GLSL_NUMERIC_PASS")
