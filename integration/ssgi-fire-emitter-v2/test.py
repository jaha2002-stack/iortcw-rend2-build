#!/usr/bin/env python3
"""Source-locked fire-donor regression: nonemissive preservation and Factory/Tram controls."""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess
MARK='DARKWOLF_SSGI_FIRE_EMISSIVE_DONOR_ISOLATION_V2'
EXPECTED='222436a6fdecd967e439a61a5dbc7e9661d383e01297d300a3b105c5dee1a1c8'
def smooth(a,b,x):
 t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3.-2.*t)
def luma(c):return sum(x*y for x,y in zip(c,(.2125,.7154,.0721)))
def flame(c,cl):
 r,g,b=c
 return smooth(.08,.25,r-b)*smooth(.025,.09,g-b)*(1-smooth(.24,.48,b/max(g,0.0001)))*smooth(.12,.37,luma(c))*smooth(.28,.62,max(r,g))*smooth(.035,.16,luma(c)-cl)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(src,out):
 out.mkdir(parents=True,exist_ok=True)
 root=src/'SP/code/rend2';ssgi=root/'glsl/ssgi_fp.glsl';init=root/'tr_init.c'
 s=ssgi.read_text();i=init.read_text()
 assert sha(ssgi)==EXPECTED,(sha(ssgi),EXPECTED)
 assert s.count(MARK)==3 and i.count(MARK)==1,(s.count(MARK),i.count(MARK))
 assert 'r_ssgiBrightSourceFix = ri.Cvar_Get( "r_ssgiBrightSourceFix", "4", CVAR_ARCHIVE );' in i
 assert 'ri.Cvar_CheckRange( r_ssgiBrightSourceFix, 0, 4, qtrue );' in i
 assert 'r_ssgiResolveMode = ri.Cvar_Get( "r_ssgiResolveMode", "2", CVAR_ARCHIVE );' in i
 assert 'if (u_ViewInfo.w >= 3.5)' in s and s.count('if (u_ViewInfo.w >= 3.5)')==2
 assert 'return mix(1.0, emitterFloor, reject);' in s
 assert 'DARKWOLF_SSGI_FIRE_RECEIVER_TRAM_DEPTH_GUARD_V1' in s
 assert 'SsgiSceneEntityGuardMaskFromCenter' in s
 assert 'DARKWOLF_CSM_PRIMARY_VIEW_AREAMASK_V1' in (root/'tr_scene.c').read_text()
 assert 'DARKWOLF_VOLUMETRIC_EDGE_RAY_CSM_AA_V1' in (root/'glsl/volumetricsun_fp.glsl').read_text()
 assert 'DARKWOLF_VOLUMETRIC_EDGE_RAY_CSM_AA_V1' in (root/'glsl/volumetriclocal_upscale_fp.glsl').read_text()
 print('PASS_PROTECTED_FACTORY_CSM_VOLUMETRIC_LEGACY_MODES_0_3')
 tests={
  'torch_flame_HDR':((1.7,.9,.06),.03,'reject'),
  'furnace_flame_orange':((1.1,.43,.05),.03,'reject'),
  'warm_fringe_moderate':((.48,.29,.08),.04,'partial'),
  'diffuse_amber_wall':((.48,.32,.22),.10,'keep'),
  'lit_orange_stone':((.55,.28,.10),.30,'keep'),
  'evening_sky':((.85,.5,.35),.06,'keep'),
  'Factory_neutral_lamp':((2.,2.,2.),.03,'keep'),
  'Tram_neutral_fog':((.20,.20,.21),.05,'keep'),
  'nonemissive_dark_wall':((.17,.14,.09),.07,'keep'),
 }
 outputs={}
 for k,(color,cl,cls) in tests.items():
  gate=flame(color,cl);factor=1.-.998*gate
  outputs[k]={'gate':round(gate,6),'factor':round(factor,6),'expected':cls}
  if cls=='reject':assert factor<.02,(k,factor)
  if cls=='partial':assert 0.15<factor<0.75,(k,factor)
  if cls=='keep':assert factor>.99,(k,factor)
 assert 'gl_FragColor = vec4(bounce, 1.0);' in s
 assert 'SsgiBilateralResolve();' in s
 assert 'sumColor += tinted * w;' in s
 print('PASS_ESCAPE1_WARM_FIRE_DONOR_SUPPRESSION_WHILE_ORDINARY_DIFFUSE_GI_PRESERVED')
 print('PASS_FACTORY_WHITE_LAMPS_TRAM_FOG_SSGI_MODES_PRESERVED')
 assert s.count('SsgiAccumulate(vec2(')==12
 assert s.count('texture2D(u_ScreenImageMap, uv).rgb')==1
 print('PASS_NO_EXTRA_GI_SAMPLES_NO_ADDED_DRAW_OR_INPUT_TEXTURE_TAPS')
 if shutil.which('glslangValidator'):
  for mod in ('130','150'):
   prefix='#version '+mod+'\n#define varying in\nout vec4 fragColor;\n#define gl_FragColor fragColor\n#define texture2D texture\n'
   p=out/('ssgi_'+mod+'.frag');p.write_text(prefix+s)
   z=subprocess.run(['glslangValidator','-S','frag',str(p)],capture_output=True,text=True)
   (out/('ssgi_'+mod+'.log')).write_text(z.stdout+'\n'+z.stderr)
   if z.returncode:raise AssertionError(z.stdout+z.stderr)
   print('PASS_SSGI_GLSLANG_'+mod+'_COMPILE')
 else: print('GLSL_VALIDATION_REQUIRED_IN_CI')
 summary={'status':'SYNTHETIC_AND_SOURCE_TESTS_PASS','base_accepted':40294211216,'new_mode4':'EMISSIVE_FIRE',
 'preserve_csm_and_volumetrics':True,'preserve_lamps_factory':True,'tram':'UNRESOLVED_SEPARATE_WORK',
 'fire_cases':outputs,'real_gpu_windows_result':'PENDING_USER'}
 (out/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
 print('DW_SSGI_FIRE_EMISSIVE_V2_REGRESSION_PASS')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();run(a.source,a.out)
