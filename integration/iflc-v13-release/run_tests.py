#!/usr/bin/env python3
"""Extend legacy CPU harness types; do not omit any inherited assertions."""
from pathlib import Path
import sys,subprocess
kit=Path(__file__).resolve().parent
r=kit.parent/'iflc-v1/tests'
p=r/'run_backend_tests.py';s=p.read_text();s=s.replace('    "RB_LocalVolumetricRenderEx",','    "RB_FireWorldOwner",\n    "RB_LocalVolumetricRenderEx",');p.write_text(s)
p=r/'backend_tests_support.h';s=p.read_text();s=s.replace('#define MAX_DLIGHT_SHADOWS 3','#define MAX_DLIGHTS 32\n#define MAX_DLIGHT_SHADOWS 3')
s=s.replace('int localVolumetricLamp;}dlight_t;', 'int localVolumetricLamp;int worldOcclusion,fireVolumetricSource;}dlight_t;')
s=s.replace('int time;int dlightWorldSlot[32];','int time;int num_dlights;dlight_t dlights[32];int dlightWorldSlot[32];');p.write_text(s)
p=r/'backend_tests_cases.c';s=p.read_text();needle=' puts("IFLC_BACKEND_CPU_PASS'
extra=r'''
 // Execute actual new world-owner path and its uniform plumbing.
 backEnd.refdef.num_dlights=1;backEnd.refdef.dlights[0]=light;
 backEnd.refdef.dlights[0].worldOcclusion=1;backEnd.refdef.dlights[0].iflcOptIn=1;
 backEnd.refdef.dlightWorldSlot[0]=0;tr.dlightWorldCubemaps[0]=&cube;
 VectorSet4(backEnd.refdef.dlightWorldOrigin[0],10,20,30,-2.0f-1.0f/512.0f);
 RB_LocalVolumetricRenderEx(&input,box,6,&light,0,NULL,.5f,200,flame,NULL,RB_IFLC_BaseColor(&light),3);
 eq(values[UNIFORM_DLIGHTWORLDORIGIN][3],1.0f/512.0f);eq(capturedParams[0],1.5f);
 colorEq(values[UNIFORM_PRIMARYLIGHTCOLOR],light.iflcBaseColor);
 for(int mode=1;mode<=9;mode++){
  if(mode==4)continue;
  RB_LocalVolumetricRenderEx(&input,box,mode,&light,0,NULL,.5f,200,flame,NULL,RB_IFLC_BaseColor(&light),1);
  eq(values[UNIFORM_DLIGHTWORLDORIGIN][3],mode>=5&&mode<=7?1.0f/512.0f:0.0f);
 }
 backEnd.refdef.num_dlights=2;backEnd.refdef.dlights[1]=backEnd.refdef.dlights[0];
 RB_LocalVolumetricRenderEx(&input,box,6,&light,0,NULL,.5f,200,flame,NULL,RB_IFLC_BaseColor(&light),1);
 eq(values[UNIFORM_DLIGHTWORLDORIGIN][3],0);eq(capturedParams[0],.5f);
 puts("IFLC13_BACKEND_WORLD_GATE_PASS sign_decode, uniforms, modes, ambiguity, original_energy");
'''
assert s.count(needle)==1;s=s.replace(needle,extra+needle);p.write_text(s)
subprocess.run([sys.executable,str(kit.parent/'iflc-v12/run_tests.py'),sys.argv[1],sys.argv[2]],check=True)
subprocess.run([sys.executable,str(kit/'test_guards.py'),sys.argv[1],str(Path(sys.argv[2])/'guard_tests')],check=True)
