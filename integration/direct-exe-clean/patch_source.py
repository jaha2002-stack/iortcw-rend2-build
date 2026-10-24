#!/usr/bin/env python3
"""Direct-EXE clean release: default values only; keep archived user settings."""
from pathlib import Path
import hashlib, json, re, argparse

ORIG = {
 'SP/code/rend2/tr_init.c': 'b19fcf789f51dee3b8f21ad0a782f81b1683bc8dd0981f995dace512b94d14f0',
 'SP/code/rend2/tr_backend.c': '7ca9c750f5490ba5327cb7a53df152d7368f09714249d8734a53abed113e9fc9',
 'SP/code/client/cl_main.c': '396dbaa37db52e2561b092c60be76b04978efb336af05a3f45d94375db6cb4ae',
}
DEFAULTS = {
 'r_picmip':('1','0'), 'r_roundImagesDown':('1','0'),
 'r_ext_texture_filter_anisotropic':('0','1'),
 'r_ext_max_anisotropy':('2','8'), 'r_texturebits':('0','32'),
 'r_colorbits':('0','32'), 'r_depthbits':('0','24'),
 'r_stencilbits':('0','8'), 'r_mode':('3','-2'),
 'r_fullscreen':('0','1'), 'r_dlightShadowKernelMode':('0','1'),
 'r_shadowMapSize':('1024','2048'), 'r_volumetricLocalSamples':('24','32'),
 'r_volumetricLocalGain':('6.0','2.40'),
 'r_volumetricLocalKnee':('1.40','0.55'),
 'r_volumetricLocalAnisotropy':('0.20','0.05'),
 'r_volumetricLocalJitter':('0.10','0.04'),
 'r_volumetricLocalShadowPcf':('1','0'),
 'r_volumetricLocalMaxDistance':('3072','2048'),
 'r_volumetricSunSamples':('32','48'),
}
def sha(b):return hashlib.sha256(b).hexdigest()
def apply(root, output):
 for rel,expected in ORIG.items():
  assert sha((root/rel).read_bytes())==expected, ('source drift',rel,sha((root/rel).read_bytes()))
 p=root/'SP/code/rend2/tr_init.c';s=p.read_text(encoding='latin-1')
 for n,(old,new) in DEFAULTS.items():
  rx=re.compile(r'(\b'+re.escape(n)+r'\s*=\s*ri\.Cvar_Get\s*\(\s*"'+re.escape(n)+r'"\s*,\s*)"'+re.escape(old)+r'"(?=\s*,\s*CVAR_ARCHIVE)')
  s,c=rx.subn(lambda m: m.group(1)+'"'+new+'"',s)
  assert c==1,(n,c)
 for n in ('r_dwLut','r_dwCas','r_ssgi','r_bloom','r_forceSun','r_dlightMode','r_ext_framebuffer_multisample'):
  assert '"'+n+'"' in s,n
 p.write_text(s,encoding='latin-1',newline='\n')
 p=root/'SP/code/rend2/tr_backend.c';s=p.read_text(encoding='latin-1')
 a='\t\tif (r_ssgi && r_ssgi->integer)\n\t\t{\n\t\t\tif (!srcFbo)\n\t\t\t\tssgiReason = "no-src-fbo";'
 b='\t\tif (r_ssgi && r_ssgi->integer)\n\t\t{\n\t\t\t// DARKWOLF_RC4_SSGI_FOG_GUARD_V01: skip postprocess color bounce\n\t\t\t// where active Wolf world fog obscures the depth buffer (Tram).\n\t\t\t// Keep r_ssgi=1 and enable GI everywhere outside fog scenes.\n\t\t\tif (glfogNum > FOG_NONE && glfogsettings[FOG_CURRENT].registered)\n\t\t\t\tssgiReason = "world-fog-safety";\n\t\t\telse if (backEnd.refdef.rdflags & RDF_UNDERWATER)\n\t\t\t\tssgiReason = "underwater-fog-safety";\n\t\t\telse if (!srcFbo)\n\t\t\t\tssgiReason = "no-src-fbo";'
 assert s.count(a)==1,'missing SSGI anchor'
 p.write_text(s.replace(a,b,1),encoding='latin-1',newline='\n')
 p=root/'SP/code/client/cl_main.c';s=p.read_text(encoding='latin-1')
 a='\t// Keep Rend2 as the native production renderer, but do not overwrite user-facing\n\t// production CVars on CL_InitRef()/vid_restart when their baked defaults already\n\t// equal the accepted production values. r_dlightShadowMaxLights remains forced to 3.\n\tCvar_Set("cl_renderer", "rend2");\n\tCvar_Set("r_dlightShadowMaxLights", "3");'
 b='\t// DARKWOLF_RC4_DIRECT_EXE_PERSISTENCE_V01: Rend2 is the only shipped renderer.\n\t// Do not force quality CVars at CL_InitRef or vid_restart; user changes persist.\n\tCvar_Set("cl_renderer", "rend2");'
 assert s.count(a)==1,'missing client Cvar override anchor'
 p.write_text(s.replace(a,b,1),encoding='latin-1',newline='\n')
 changes={rel:sha((root/rel).read_bytes()) for rel in ORIG}
 assert changes=={
  'SP/code/rend2/tr_init.c':'a32ab38e7cae26cb71d6dd0df1eeffd58af1bd05a4303876c5040a5bc2109527',
  'SP/code/rend2/tr_backend.c':'0478f09714c679838a8939a7a853de505b14c68995c5bc3abe241435c05f9bc0',
  'SP/code/client/cl_main.c':'db39362a79bc762fb833a917ab95bd90c6dcbb0be754440fc9332353cf66f854',
 },changes
 output.mkdir(parents=True,exist_ok=True)
 (output/'DIRECT_EXE_SOURCE_MANIFEST.json').write_text(json.dumps({'master_v05_source_tree':'dcba28be81f1c7d22a62d8dd4733dbfdadebc666','changed_files_sha256':changes,'first_run_defaults':{n:v[1] for n,v in DEFAULTS.items()},'ssgi':'enabled but skipped on active Wolf fog and underwater','saved_settings':'CVAR_ARCHIVE values override Cvar_Get defaults','gpu_runtime_acceptance':'PENDING'},indent=2)+'\n')
 print('DIRECT_EXE_ONLY_THREE_SOURCE_FILES_CHANGED',changes)
 print('DEFAULTS_PERSISTENCE_FOG_GATES_PASS',len(DEFAULTS))

if __name__=='__main__':
 ap=argparse.ArgumentParser()
 ap.add_argument('source',type=Path)
 ap.add_argument('--out',type=Path,default=Path('dist'))
 args=ap.parse_args()
 apply(args.source,args.out)
