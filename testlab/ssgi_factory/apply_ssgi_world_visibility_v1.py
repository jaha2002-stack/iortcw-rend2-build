#!/usr/bin/env python3
"""Source-grounded geometry fix candidate for the real v4.4.6 SSGI path.

Unlike previous bright-source modes, tests physically meaningful visibility:
0 = unchanged mode-3; 1 = depth-ray line-of-sight; 2 = depth-ray + two-sided
geometry orientation. No per-map rectangle or donor brightness threshold.
Defaults OFF. Used ONLY on the isolated TestLab branch.
"""
from pathlib import Path
import sys
r=Path(sys.argv[1] if len(sys.argv)>1 else 'source')/'SP/code/rend2'
shader=r/'glsl/ssgi_fp.glsl'
def one(s,a,b,name):
    assert s.count(a)==1, f'{name}: expected 1 exact anchor, got {s.count(a)}'
    return s.replace(a,b)

s=shader.read_text()
s=one(s,'uniform vec4 u_ViewInfo; // x=zFar/zNear, y=zFar, z=entity guard mode, w=reserved',
    'uniform vec4 u_ViewInfo; // x=zFar/zNear, y=zFar, z=entity guard, w=brightfix\n'
    'uniform vec3 u_ViewLeft; // SSGI_VISIBILITY_V1: tanHalfFovX, tanHalfFovY, geomMode','view')
s=one(s,'void SsgiAccumulate(const vec2 offset,',"""
// SSGI_VISIBILITY_V1: perspective-correct positions from REAL scene depth.
vec3 SsgiPositionAt(const vec2 uv, const float normDepth)
{
    float z = max(normDepth * u_ViewInfo.y, 0.0001);
    return vec3((2.0*uv.x - 1.0)*u_ViewLeft.x*z,
                (2.0*uv.y - 1.0)*u_ViewLeft.y*z, z);
}

// Finite-difference geometric normals using the nearer-in-depth neighbor,
// never interpolate a normal through foreground/background silhouettes.
vec3 SsgiSurfaceNormal(const vec2 uv, const float d, const vec2 texel)
{
    vec2 t = max(texel*0.5, vec2(0.00001));
    vec2 lo = vec2(0.001), hi = vec2(0.999);
    vec2 xp = clamp(uv+vec2(t.x,0.0),lo,hi);
    vec2 xm = clamp(uv-vec2(t.x,0.0),lo,hi);
    vec2 yp = clamp(uv+vec2(0.0,t.y),lo,hi);
    vec2 ym = clamp(uv-vec2(0.0,t.y),lo,hi);
    float dxp=SsgiLinearDepth(xp), dxm=SsgiLinearDepth(xm);
    float dyp=SsgiLinearDepth(yp), dym=SsgiLinearDepth(ym);
    vec3 p = SsgiPositionAt(uv,d);
    vec3 tx = abs(dxp-d)<=abs(dxm-d) ?
        (SsgiPositionAt(xp,dxp)-p) : (p-SsgiPositionAt(xm,dxm));
    vec3 ty = abs(dyp-d)<=abs(dym-d) ?
        (SsgiPositionAt(yp,dyp)-p) : (p-SsgiPositionAt(ym,dym));
    vec3 n = cross(tx,ty);
    float area = length(n);
    if (area<0.000001) return vec3(0.0,0.0,-1.0);
    n=-n/area;
    return n.z>0.0 ? -n:n;
}

// Perspective-correct screen ray. A foreground depth fragment between the
// receiver and donor is an occluder, not a legitimate light bounce.
float SsgiLineOfSight(const vec2 fromUv,const vec2 toUv,
    const float fromDepth,const float toDepth)
{
    float z0=max(fromDepth*u_ViewInfo.y,0.01);
    float z1=max(toDepth*u_ViewInfo.y,0.01);
    for (int i=1;i<=3;++i)
    {
        float t=float(i)*0.25;
        float expected=1.0/mix(1.0/z0,1.0/z1,t);
        float scene=SsgiLinearDepth(mix(fromUv,toUv,t))*u_ViewInfo.y;
        float tolerance=max(1.5,expected*0.002);
        if (scene+tolerance<expected) return 0.0;
    }
    return 1.0;
}

void SsgiAccumulate(const vec2 offset,""",'functions')
s=one(s,'\tconst vec3 centerColor,\n\tinout vec3 sumColor,',
  '\tconst vec3 centerColor,\n\tconst vec3 receiverNormal,\n\tinout vec3 sumColor,','argument')
anchor='\tfloat geometryWeight = separated * residualNear * localDepth;\n\tif (geometryWeight <= 0.0001)\n\t\treturn;'
new="""\tfloat geometryWeight = separated * residualNear * localDepth;
\tif (geometryWeight <= 0.0001)
\t\treturn;

\t// SSGI_VISIBILITY_V1: reject screen-space donors that the receiving
\t// surface cannot physically see. No luminance or map-specific gating.
\tif (u_ViewLeft.z > 0.5)
\t{
\t\tif (SsgiLineOfSight(var_ScreenTex,uv,centerDepth,sampleDepth)<0.5)
\t\t\treturn;
\t\tif (u_ViewLeft.z > 1.5)
\t\t{
\t\t\tvec3 donorNormal=SsgiSurfaceNormal(uv,sampleDepth,maskTexel);
\t\t\tvec3 receiverPos=SsgiPositionAt(var_ScreenTex,centerDepth);
\t\t\tvec3 donorPos=SsgiPositionAt(uv,sampleDepth);
\t\t\tvec3 v=donorPos-receiverPos;
\t\t\tfloat travel=length(v);
\t\t\tif (travel<1.0) return;
\t\t\tv/=travel;
\t\t\tfloat emitFacing=max(dot(donorNormal,-v),0.0);
\t\t\tfloat receiveFacing=max(dot(receiverNormal,v),0.0);
\t\t\tgeometryWeight*=emitFacing*receiveFacing;
\t\t\tif (geometryWeight<=0.0001) return;
\t\t}
\t}"""
s=one(s,anchor,new,'geomweight')
s=one(s,'\tvec3 sumColor = vec3(0.0);\n\tfloat accepted = 0.0;\n\tfloat centerWorld',
   '\tvec3 sumColor = vec3(0.0);\n\tfloat accepted = 0.0;\n'
   '\tvec3 receiverNormal = u_ViewLeft.z > 1.5 ? '
   'SsgiSurfaceNormal(var_ScreenTex,centerDepth,maskTexel) : vec3(0.0,0.0,-1.0);\n'
   '\tfloat centerWorld','receivernormal')
a='maskTexel, centerColor, sumColor, accepted);'
assert s.count(a)==12, f'expected 12 donor samples, got {s.count(a)}'
s=s.replace(a,'maskTexel, centerColor, receiverNormal, sumColor, accepted);')
shader.write_text(s)
init=r/'tr_init.c';s=init.read_text()
a='cvar_t *r_ssgiBrightSourceFix; // DARKWOLF_SSGI_BRIGHT_SOURCE_HALO_FIX_V0_2'
s=one(s,a,a+'\ncvar_t *r_ssgiGeometryVisibility; // SSGI_VISIBILITY_V1','declaration')
a='ri.Cvar_CheckRange( r_ssgiBrightSourceFix, 0, 4, qtrue ); // FACTORY_TESTLAB_MODES_3_4_ONLY'
s=one(s,a,a+'''
\tr_ssgiGeometryVisibility = ri.Cvar_Get( "r_ssgiGeometryVisibility", "0", CVAR_ARCHIVE );
\tri.Cvar_CheckRange( r_ssgiGeometryVisibility, 0, 2, qtrue );''','registration')
init.write_text(s)
local=r/'tr_local.h';s=local.read_text()
a='extern cvar_t *r_ssgiBrightSourceFix; // DARKWOLF_SSGI_BRIGHT_SOURCE_HALO_FIX_V0_2'
local.write_text(one(s,a,a+'\nextern cvar_t *r_ssgiGeometryVisibility; // SSGI_VISIBILITY_V1','extern'))
backend=r/'tr_backend.c';s=backend.read_text()
a='GLSL_SetUniformVec4(&tr.ssgiShader, UNIFORM_VIEWINFO, giViewInfo);'
n='''GLSL_SetUniformVec4(&tr.ssgiShader, UNIFORM_VIEWINFO, giViewInfo);
\t\t\t\t// Preserve FOV independently from existing guard and brightfix uniforms.
\t\t\t\t{
\t\t\t\t\tvec3_t ssgiGeometry;
\t\t\t\t\tVectorSet(ssgiGeometry,
\t\t\t\t\t\ttan(backEnd.viewParms.fovX * M_PI / 360.0f),
\t\t\t\t\t\ttan(backEnd.viewParms.fovY * M_PI / 360.0f),
\t\t\t\t\t\t(float)(r_ssgiGeometryVisibility ? r_ssgiGeometryVisibility->integer : 0));
\t\t\t\t\tGLSL_SetUniformVec3(&tr.ssgiShader, UNIFORM_VIEWLEFT, ssgiGeometry);
\t\t\t\t}'''
backend.write_text(one(s,a,n,'backenduniform'))
print('SSGI_VISIBILITY_V1_PATCH_PASS controls=0,1,2 no_screen_ROI=1 ray_samples=3 donors=12')
