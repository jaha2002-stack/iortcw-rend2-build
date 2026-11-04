#!/usr/bin/env python3
from pathlib import Path
import sys,tempfile,shutil,subprocess
src=Path(sys.argv[1]).resolve();ev=Path(sys.argv[2]).resolve();kit=Path(__file__).resolve().parent;root=kit.parent
ev.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory() as d:
 d=Path(d)
 for f in (root/'iflc-v1/tests').iterdir():
  if f.is_file():shutil.copy2(f,d/f.name)
 f=d/'iflc_cpu_tests.c';s=f.read_text();s=s.replace('"DW_IFLC 2\\nmap crypt1','"DW_IFLC 99\\nmap crypt1')
 fixture=(root/'iflc-v11/fixture_tests.inc').read_text();needle='      R_IFLC_ResetFixtures();sh[1].sort=SS_SEE_THROUGH;';assert fixture.count(needle)==1
 fixture=fixture.replace(needle,'      TestSelfRule(&dl,s);\n'+needle)
 shaft=(root/'iflc-v12/shaft_tests.inc').read_text();needle='      dl.iflcOptIn=qfalse;CHECK(R_IFLC_ShadowFixture(&dl)==0,"no native/promoted policy expansion");';assert shaft.count(needle)==1
 shaft=shaft.replace(needle,'''      R_IFLC_ResetFixtures();Q_strncpyz(sh[2].name,"props/torch_ember",sizeof(sh[2].name));
      CHECK(R_IFLC_ShadowFixture(&dl)==1 && s_iflcFixtures[0].count==4,"opaque emissive names remain actual fixture geometry");
      R_IFLC_ResetFixtures();sh[2].sort=SS_SEE_THROUGH;R_IFLC_ShadowFixture(&dl);
      for(i=0;i<s_iflcFixtures[0].count;++i)CHECK(s_iflcFixtures[0].surfaces[i]!=2,"transparent stage not adopted");
      R_IFLC_ResetFixtures();sh[2].sort=SS_OPAQUE;R_IFLC_ShadowFixture(&dl);
'''+needle)
 ext=(kit/'self_tests.inc').read_text()+'\n'+fixture+'\n'+shaft
 s=s.replace('int main(void) {',ext+'\nint main(void) {').replace('    TestClearFiles();\n    free(backEndData);','    TestFixturePolicy();\n    TestSlenderTorch();\n    TestClearFiles();\n    free(backEndData);');f.write_text(s)
 subprocess.run([sys.executable,str(d/'run_cpu_tests.py'),str(src),'--sanitize','--output',str(ev/'IFLC14_CPU.json')],check=True)
 # Preserve all inherited backend assertions; extract the actual new functions.
 p=d/'run_backend_tests.py';s=p.read_text().replace('    "RB_LocalVolumetricRenderEx",','    "RB_FireWorldOwner",\n    "RB_DWAlarmWorldLight",\n    "RB_LocalVolumetricRenderEx",').replace('"-Werror",','"-Werror", "-Wno-misleading-indentation",');p.write_text(s)
 p=d/'backend_tests_support.h';s=p.read_text().replace('#define MAX_DLIGHT_SHADOWS 3','#define MAX_DLIGHTS 32\n#define MAX_DLIGHT_SHADOWS 3')
 s=s.replace('int localVolumetricLamp;}dlight_t;','int localVolumetricLamp;int worldOcclusion,fireVolumetricSource,nativeAuthoredDlight,transientBlast,noDlightShadow,staticPromoteFixtureId;}dlight_t;')
 s=s.replace('int time;int dlightWorldSlot[32];','int time;int num_dlights;dlight_t dlights[32];int dlightWorldSlot[32];')
 s=s.replace('static int RB_DWAlarmWorldLight(const dlight_t *lamp,int mode){(void)lamp;(void)mode;return -1;}','static cvar_t containment={2,2};static cvar_t *r_dlightWorldContainment=&containment;');p.write_text(s)
 p=d/'backend_tests_cases.c';s=p.read_text();needle=' puts("IFLC_BACKEND_CPU_PASS';assert s.count(needle)==1
 extra=r'''
 light.staticPromoteFixtureId=42;light.localVolumetricLamp=1;
 backEnd.refdef.num_dlights=1;backEnd.refdef.dlights[0]=light;
 backEnd.refdef.dlights[0].worldOcclusion=1;backEnd.refdef.dlightWorldSlot[0]=0;tr.dlightWorldCubemaps[0]=&cube;
 VectorSet4(backEnd.refdef.dlightWorldOrigin[0],10,20,30,-2.0f-1.0f/512.0f);
 assert(RB_DWAlarmWorldLight(&light,3)==0);
 RB_LocalVolumetricRenderEx(&input,box,3,&light,0,NULL,.5f,200,flame,NULL,RB_IFLC_BaseColor(&light),1);
 eq(values[UNIFORM_DLIGHTWORLDORIGIN][3],1.0f/512.0f);eq(capturedParams[0],.5f);
 backEnd.refdef.num_dlights=2;backEnd.refdef.dlights[1]=backEnd.refdef.dlights[0];assert(RB_DWAlarmWorldLight(&light,3)==-1);
 backEnd.refdef.num_dlights=1;light.staticPromoteFixtureId=-1;light.nativeAuthoredDlight=1;backEnd.refdef.dlights[0]=light;backEnd.refdef.dlights[0].worldOcclusion=1;
 assert(RB_DWAlarmWorldLight(&light,3)==0);
 light.transientBlast=1;assert(RB_DWAlarmWorldLight(&light,3)==-1);light.transientBlast=0;
 backEnd.refdef.num_dlights=0;
 RB_LocalVolumetricRenderEx(&input,box,6,&light,-1,NULL,.5f,200,flame,&cube,RB_IFLC_BaseColor(&light),1);
 eq(values[UNIFORM_DLIGHTINFO][3],1);eq(capturedParams[0],.5f);containment.integer=0;
 RB_LocalVolumetricRenderEx(&input,box,6,&light,-1,NULL,.5f,200,flame,&cube,RB_IFLC_BaseColor(&light),1);
 eq(values[UNIFORM_DLIGHTINFO][3],0);eq(capturedParams[0],.5f);containment.integer=2;
 RB_LocalVolumetricRenderEx(&input,box,6,&light,0,NULL,.5f,200,flame,NULL,RB_IFLC_BaseColor(&light),1);
 eq(values[UNIFORM_DLIGHTINFO][3],0);
 puts("IFLC14_BACKEND_PASS local/native ownership, ambiguity, signed-PCF decode, gate binding, unchanged energy");
'''
 p.write_text(s.replace(needle,extra+needle))
 subprocess.run([sys.executable,str(d/'run_backend_tests.py'),str(src),'--output',str(ev/'backend')],check=True)
 subprocess.run([sys.executable,str(d/'run_shadow_tests.py'),str(src),'--output',str(ev/'shadow')],check=True)
