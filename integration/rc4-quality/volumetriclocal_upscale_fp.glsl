// RC4_QUALITY_VOLUMETRIC_RECONSTRUCTION_V1
// Four *unmixed* half-resolution samples are classified against matching
// full-resolution scene depth BEFORE interpolation. Never filter the scene.
uniform sampler2D u_DiffuseMap;
uniform sampler2D u_ScreenDepthMap;
uniform vec2 u_InvTexRes;
uniform vec4 u_ViewInfo;
uniform vec4 u_Color;
uniform vec4 u_EnableTextures; // scene viewport x,y,w,h in full-depth UVs
varying vec2 var_DepthTex;
#define DEPTH_MAX_ERROR 0.000000059604644775390625
vec2 sceneUv(vec2 uv)
{
 vec2 t=u_EnableTextures.xy + vec2(uv.x,1.0-uv.y)*u_EnableTextures.zw;
 // Same canonical depth pixel as the producer, including half/full-grid ties.
 return (floor(t/u_ViewInfo.zw+vec2(0.001))+vec2(0.5))*u_ViewInfo.zw;
}
float getLinearDepth(sampler2D d, vec2 t, float z)
{
 float v=texture2D(d,sceneUv(t)).r-DEPTH_MAX_ERROR;
 return 1.0/mix(z,1.0,v);
}
float depthWeight(float c,float d,float r)
{
 float q=abs(d-c)/max(min(c,d),0.0005);
 return exp(-q*max(r,0.0));
}
void addReconstructionTap(vec2 uv,float spatial,float cd,vec2 lo,vec2 hi,
                          inout vec3 sum,inout float weight)
{
 uv=clamp(uv,lo,hi);
 float sd=getLinearDepth(u_ScreenDepthMap,uv,u_ViewInfo.x);
 float w=spatial*depthWeight(cd,sd,max(u_Color.x,32.0));
 // Exact texel centres prevent implicit linear mixing across a silhouette.
 sum+=texture2D(u_DiffuseMap,uv).rgb*w;
 weight+=w;
}
void main()
{
 vec2 texel=u_InvTexRes,lo=texel*0.5,hi=vec2(1.0)-lo;
 vec2 uv=clamp(var_DepthTex,vec2(0.0),vec2(1.0));
 float cd=getLinearDepth(u_ScreenDepthMap,uv,u_ViewInfo.x);
 int mode=int(floor(u_Color.y+0.5));
 vec3 sum=vec3(0.0);float sumW=0.0;
 if(mode>=4)
 {
  vec2 p=uv/texel-vec2(0.5),base=floor(p),f=fract(p);
  vec2 a=(base+vec2(0.5))*texel;
  addReconstructionTap(a,(1.0-f.x)*(1.0-f.y),cd,lo,hi,sum,sumW);
  addReconstructionTap(a+vec2(texel.x,0.0),f.x*(1.0-f.y),cd,lo,hi,sum,sumW);
  addReconstructionTap(a+vec2(0.0,texel.y),(1.0-f.x)*f.y,cd,lo,hi,sum,sumW);
  addReconstructionTap(a+texel,f.x*f.y,cd,lo,hi,sum,sumW);
  // Unsupported thin foreground pixels must not inherit background radiance.
  gl_FragColor=vec4(sumW>0.00001 ? max(sum/sumW,vec3(0.0)) : vec3(0.0),0.0);
  return;
 }
 // Preserve the optional historical 3x3/5x5 kernels, correcting their depth UVs.
 uv=clamp(uv,lo,hi);
 if(mode>=2)
 {
  for(int y=-2;y<=2;++y)for(int x=-2;x<=2;++x)
  {
   vec2 s=clamp(uv+vec2(float(x),float(y))*texel,lo,hi);
   float w=depthWeight(cd,getLinearDepth(u_ScreenDepthMap,s,u_ViewInfo.x),u_Color.x)*exp(-0.22*float(x*x+y*y));
   sum+=texture2D(u_DiffuseMap,s).rgb*w;sumW+=w;
  }
 }
 else
 {
  for(int y=-1;y<=1;++y)for(int x=-1;x<=1;++x)
  {
   vec2 s=clamp(uv+vec2(float(x),float(y))*texel,lo,hi);
   float r2=float(x*x+y*y),spatial=r2<0.5?1.0:(r2<1.5?0.70:0.45);
   float w=depthWeight(cd,getLinearDepth(u_ScreenDepthMap,s,u_ViewInfo.x),u_Color.x)*spatial;
   sum+=texture2D(u_DiffuseMap,s).rgb*w;sumW+=w;
  }
 }
 gl_FragColor=vec4(sum/max(sumW,0.0001),0.0);
}
