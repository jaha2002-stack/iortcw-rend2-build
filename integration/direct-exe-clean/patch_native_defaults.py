#!/usr/bin/env python3
"""Fix default.cfg -> native defaults -> user wolfconfig.cfg startup precedence."""
from pathlib import Path
from hashlib import sha256
import json,argparse
EXPECTED='b5db7d63eac4380602b3bacbff094c44d58e2a5308c4066de37a81c1e4b30c74'
NATIVE_CODE="// DARKWOLF_RC4_NATIVE_CLEAN_CONFIG_PRECEDENCE_V01\n// Retail default.cfg is read BEFORE renderer CVars register. Apply native\n// clean defaults once AFTER default.cfg and BEFORE user wolfconfig.cfg.\nstatic void Com_DarkWolfNativeFirstRunDefaults(void)\n{\n\tstatic const struct { const char *name, *value; } defaults[] = {\n\t\t{ \"cl_renderer\", \"rend2\" },\n\t\t{ \"r_picmip\", \"0\" },\n\t\t{ \"r_picmip2\", \"0\" },\n\t\t{ \"r_roundImagesDown\", \"0\" },\n\t\t{ \"r_textureMode\", \"GL_LINEAR_MIPMAP_LINEAR\" },\n\t\t{ \"r_ext_texture_filter_anisotropic\", \"1\" },\n\t\t{ \"r_ext_max_anisotropy\", \"8\" },\n\t\t{ \"r_texturebits\", \"32\" },\n\t\t{ \"r_colorbits\", \"32\" },\n\t\t{ \"r_depthbits\", \"24\" },\n\t\t{ \"r_stencilbits\", \"8\" },\n\t\t{ \"r_mode\", \"-2\" },\n\t\t{ \"r_fullscreen\", \"1\" },\n\t\t{ \"r_hdr\", \"1\" },\n\t\t{ \"r_postProcess\", \"1\" },\n\t\t{ \"r_toneMap\", \"1\" },\n\t\t{ \"r_autoExposure\", \"1\" },\n\t\t{ \"r_ext_framebuffer_multisample\", \"4\" },\n\t\t{ \"r_bloom\", \"1\" },\n\t\t{ \"r_bloomMode\", \"2\" },\n\t\t{ \"r_dwLut\", \"1\" },\n\t\t{ \"r_dwLutStrength\", \"0.80\" },\n\t\t{ \"r_dwLutMode\", \"1\" },\n\t\t{ \"r_dwCas\", \"1\" },\n\t\t{ \"r_dwCasStrength\", \"0.55\" },\n\t\t{ \"r_dwA2C\", \"1\" },\n\t\t{ \"r_dwTextureFidelity\", \"1\" },\n\t\t{ \"r_dwMaterialFidelity\", \"1\" },\n\t\t{ \"r_dwAdaptiveUpsample\", \"1\" },\n\t\t{ \"r_dwCutoutMip\", \"1\" },\n\t\t{ \"r_forceSun\", \"1\" },\n\t\t{ \"r_sunShadows\", \"1\" },\n\t\t{ \"r_dlightMode\", \"2\" },\n\t\t{ \"r_dlightShadowMaxLights\", \"3\" },\n\t\t{ \"r_dlightShadowKernelMode\", \"1\" },\n\t\t{ \"r_shadowMapSize\", \"2048\" },\n\t\t{ \"r_staticPromote\", \"1\" },\n\t\t{ \"r_staticPromoteMaxLights\", \"32\" },\n\t\t{ \"r_ssgi\", \"1\" },\n\t\t{ \"r_softParticles\", \"1\" },\n\t\t{ \"r_volumetricSun\", \"1\" },\n\t\t{ \"r_volumetricLocal\", \"1\" },\n\t\t{ \"r_volumetricFire\", \"1\" },\n\t\t{ \"r_volumetricLocalSamples\", \"32\" },\n\t\t{ \"r_volumetricLocalGain\", \"2.40\" },\n\t\t{ \"r_volumetricLocalKnee\", \"0.55\" },\n\t\t{ \"r_volumetricLocalAnisotropy\", \"0.05\" },\n\t\t{ \"r_volumetricLocalJitter\", \"0.04\" },\n\t\t{ \"r_volumetricLocalShadowPcf\", \"0\" },\n\t\t{ \"r_volumetricLocalMaxDistance\", \"2048\" },\n\t\t{ \"r_volumetricSunSamples\", \"48\" },\n\t};\n\tint i;\n\tfor (i = 0; i < (int)(sizeof(defaults)/sizeof(defaults[0])); ++i)\n\t\tCvar_Set(defaults[i].name, defaults[i].value);\n}\n\n"
DEFAULTS={"cl_renderer":"rend2","r_picmip":"0","r_picmip2":"0","r_roundImagesDown":"0","r_textureMode":"GL_LINEAR_MIPMAP_LINEAR","r_ext_texture_filter_anisotropic":"1","r_ext_max_anisotropy":"8","r_texturebits":"32","r_colorbits":"32","r_depthbits":"24","r_stencilbits":"8","r_mode":"-2","r_fullscreen":"1","r_hdr":"1","r_postProcess":"1","r_toneMap":"1","r_autoExposure":"1","r_ext_framebuffer_multisample":"4","r_bloom":"1","r_bloomMode":"2","r_dwLut":"1","r_dwLutStrength":"0.80","r_dwLutMode":"1","r_dwCas":"1","r_dwCasStrength":"0.55","r_dwA2C":"1","r_dwTextureFidelity":"1","r_dwMaterialFidelity":"1","r_dwAdaptiveUpsample":"1","r_dwCutoutMip":"1","r_forceSun":"1","r_sunShadows":"1","r_dlightMode":"2","r_dlightShadowMaxLights":"3","r_dlightShadowKernelMode":"1","r_shadowMapSize":"2048","r_staticPromote":"1","r_staticPromoteMaxLights":"32","r_ssgi":"1","r_softParticles":"1","r_volumetricSun":"1","r_volumetricLocal":"1","r_volumetricFire":"1","r_volumetricLocalSamples":"32","r_volumetricLocalGain":"2.40","r_volumetricLocalKnee":"0.55","r_volumetricLocalAnisotropy":"0.05","r_volumetricLocalJitter":"0.04","r_volumetricLocalShadowPcf":"0","r_volumetricLocalMaxDistance":"2048","r_volumetricSunSamples":"48"}
def apply(root,out):
 p=root/'SP/code/qcommon/common.c'
 data=p.read_bytes()
 assert sha256(data).hexdigest()==EXPECTED,('original common.c source drift',sha256(data).hexdigest())
 s=data.decode('latin-1')
 anchor='void Com_ExecuteCfg(void)\n{\n'
 assert s.count(anchor)==1
 s=s.replace(anchor,NATIVE_CODE+anchor,1)
 anchor='\tCbuf_Execute(); // Always execute after exec to prevent text buffer overflowing\n\n\tif(!Com_SafeMode())'
 replacement='\tCbuf_Execute(); // Always execute after exec to prevent text buffer overflowing\n\n\t// Native first-run defaults, always BEFORE the user's wolfconfig.cfg.\n\tCom_DarkWolfNativeFirstRunDefaults();\n\n\tif(!Com_SafeMode())'
 assert s.count(anchor)==1
 s=s.replace(anchor,replacement,1)
 a='com_recommendedSet = Cvar_Get( "com_recommendedSet", "0", CVAR_ARCHIVE );'
 assert s.count(a)==1
 s=s.replace(a,'com_recommendedSet = Cvar_Get( "com_recommendedSet", "1", CVAR_ARCHIVE );',1)
 a='\tif ( !com_recommendedSet->integer ) {\n\t\tCom_SetRecommended( qtrue );\n\t\tCvar_Set( "com_recommendedSet", "1" );\n\t}'
 b='\tif ( !com_recommendedSet->integer ) {\n\t\t// DARKWOLF_RC4_DIRECT_EXE_PERSISTENCE_V02:\n\t\t// Do not execute legacy highVid*/lowVid* configs over user choices.\n\t\tCvar_Set( "com_recommendedSet", "1" );\n\t}'
 assert s.count(a)==1
 s=s.replace(a,b,1)
 p.write_text(s,encoding='latin-1',newline='\n')
 assert 'Com_SetRecommended( qtrue );' not in s
 assert s.index('Com_DarkWolfNativeFirstRunDefaults();')<s.index('Cbuf_ExecuteText(EXEC_NOW, "exec " Q3CONFIG_CFG')
 out.mkdir(parents=True,exist_ok=True)
 info={'source':'SP/code/qcommon/common.c','original_sha256':EXPECTED,'new_sha256':sha256(p.read_bytes()).hexdigest(),'first_run_defaults':DEFAULTS,'native_default_before_personal_config':True,'legacy_auto_recommendation_disabled':True}
 (out/'ENGINE_NATIVE_DEFAULTS_MANIFEST.json').write_text(json.dumps(info,indent=2)+'\n')
 print('DIRECT_EXE_NATIVE_DEFAULT_CONFIG_PRECEDENCE_PASS',len(DEFAULTS),info['new_sha256'])
if __name__=='__main__':
 parser=argparse.ArgumentParser()
 parser.add_argument('source',type=Path)
 parser.add_argument('--out',type=Path,default=Path('dist'))
 a=parser.parse_args()
 apply(a.source,a.out)
