/* Contract assertions for functions extracted from the current renderer source. */
static void eq(float a,float b){assert(fabsf(a-b)<1e-6f);}
static void colorEq(const vec3_t a,const vec3_t b){for(int j=0;j<3;j++)eq(a[j],b[j]);}
int main(void){
 FBO_t input={1},quarter={2};image_t depth={64},cube={128};ivec4_t box={0};
 dlight_t light={0};vec3_t flame={1,2,3};
 tr.quarterFbo[0]=&quarter;tr.renderDepthImage=&depth;tr.volumetricLocalShader.program=1;tr.shadowCubemaps[0]=&cube;
 tr.volumetricFullresFbo=NULL;tr.screenScratchFbo=NULL;tr.quarterFbo[1]=NULL;
 backEnd.viewParms.zFar=1024;backEnd.refdef.viewaxis[0][0]=1;
 r_znear->value=4;s_rVolumetricFireUpscale->integer=0;r_volumetricLocalSpotUpscale->integer=0;
 s_rVolumetricFireStrength->value=1;r_volumetricLocalStrength->value=1;
 light.radius=200;light.color[0]=1;light.color[1]=.52f;light.color[2]=.16f;
 light.origin[0]=10;light.origin[1]=20;light.origin[2]=30;
 float baselineScore=RB_LocalVolumetricDlightScore(&light);
 RB_LocalVolumetricRenderEx(&input,box,6,&light,0,NULL,.5f,200,flame,NULL,NULL,1);
 vec4_t baselineColor,baselineSource,baselineVolume,baselineInfo;
 VectorCopy4(values[UNIFORM_PRIMARYLIGHTCOLOR],baselineColor);
 VectorCopy4(values[UNIFORM_PRIMARYLIGHTORIGIN],baselineSource);
 VectorCopy4(values[UNIFORM_CUBEMAPINFO],baselineVolume);
 VectorCopy4(values[UNIFORM_DLIGHTINFO],baselineInfo);
 eq(capturedParams[0],.5f);
 light.iflcActive=1;light.iflcBaseRadius=200;VectorCopy(light.color,light.iflcBaseColor);light.iflcVolumeGain=1;
 float directs[]={0,.5f,2,3};
 for(int i=0;i<4;i++){
  VectorScale(light.iflcBaseColor,directs[i],light.color);
  eq(RB_LocalVolumetricDlightScore(&light),baselineScore);
  RB_LocalVolumetricRenderEx(&input,box,6,&light,0,NULL,.5f,RB_IFLC_BaseRadius(&light),flame,NULL,RB_IFLC_BaseColor(&light),RB_IFLC_FireVolumeGain(&light));
  colorEq(values[UNIFORM_PRIMARYLIGHTCOLOR],baselineColor);
  colorEq(values[UNIFORM_PRIMARYLIGHTORIGIN],baselineSource);eq(values[UNIFORM_PRIMARYLIGHTORIGIN][3],baselineSource[3]);
  colorEq(values[UNIFORM_CUBEMAPINFO],baselineVolume);eq(values[UNIFORM_CUBEMAPINFO][3],baselineVolume[3]);
  eq(values[UNIFORM_DLIGHTINFO][2],baselineInfo[2]);eq(capturedParams[0],.5f);
 }
 light.radius=400;eq(RB_LocalVolumetricDlightScore(&light),baselineScore);
 RB_LocalVolumetricRenderEx(&input,box,6,&light,0,NULL,.5f,RB_IFLC_BaseRadius(&light),flame,NULL,RB_IFLC_BaseColor(&light),1);
 eq(values[UNIFORM_CUBEMAPINFO][3],200);eq(values[UNIFORM_DLIGHTINFO][2],400);eq(values[UNIFORM_PRIMARYLIGHTORIGIN][3],400);
 for(int mode=2;mode<=8;mode++){
  if(mode==4)continue;
  RB_LocalVolumetricRenderEx(&input,box,mode,&light,0,NULL,.5f,200,flame,NULL,RB_IFLC_BaseColor(&light),3);
  eq(capturedParams[0],1.5f);colorEq(values[UNIFORM_PRIMARYLIGHTCOLOR],light.iflcBaseColor);
  RB_LocalVolumetricRenderEx(&input,box,mode,&light,0,NULL,.5f,200,flame,NULL,RB_IFLC_BaseColor(&light),0);
  eq(capturedParams[0],0);
 }
 // Cached synthetic capture retains its own radius; gain lives outside its fade.
 dlight_t cached=light;cached.iflcActive=0;cached.radius=375;VectorCopy(light.iflcBaseColor,cached.color);
 RB_LocalVolumetricRenderEx(&input,box,6,&cached,-1,NULL,.5f,200,flame,&cube,NULL,3);
 eq(values[UNIFORM_DLIGHTINFO][2],375);eq(values[UNIFORM_CUBEMAPINFO][3],200);eq(capturedParams[0],1.5f);
 // Generic LocalVol gets original RGB, never FireVol's independent gain.
 light.localVolumetricLamp=1;light.iflcVolumeGain=3;
 RB_LocalVolumetricRender(&input,box,3,&light,0,NULL,.5f,0);
 eq(capturedParams[0],.5f);colorEq(values[UNIFORM_PRIMARYLIGHTCOLOR],light.iflcBaseColor);
 puts("IFLC_BACKEND_CPU_PASS score/base snapshot inputs, direct-zero/full independence, volume-gain fade, capture-vs-plume radius, cached fallback, generic local RGB");return 0;
}
