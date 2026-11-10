#!/usr/bin/env python3
"""Compile actual changed visibility helpers and depth producer on Mesa EGL.
This is a shader-compiler gate, not a claim of complete game visual acceptance.
"""
from pathlib import Path
import ctypes as c,os,json,sys
os.environ['LIBGL_ALWAYS_SOFTWARE']='1'
E=c.CDLL('libEGL.so.1');G=c.CDLL('libGL.so.1');P=c.c_void_p;I=c.c_int;U=c.c_uint

def bind(lib,n,r,*a):
 f=getattr(lib,n);f.restype=r;f.argtypes=list(a);return f
getProc=bind(E,'eglGetProcAddress',P,c.c_char_p)
platform=c.CFUNCTYPE(P,U,P,c.POINTER(I))(getProc(b'eglGetPlatformDisplayEXT'))
d=platform(0x31DD,None,None);v1=I();v2=I()
assert bind(E,'eglInitialize',U,P,c.POINTER(I),c.POINTER(I))(d,c.byref(v1),c.byref(v2))
assert bind(E,'eglBindAPI',U,U)(0x30A2)
attrs=(I*15)(0x3024,8,0x3023,8,0x3022,8,0x3021,8,0x3033,1,0x3040,8,0x3025,0,0x3038)
config=P();count=I()
assert bind(E,'eglChooseConfig',U,P,c.POINTER(I),c.POINTER(P),I,c.POINTER(I))(d,attrs,c.byref(config),1,c.byref(count)) and count.value
s=bind(E,'eglCreatePbufferSurface',P,P,P,c.POINTER(I))(d,config,(I*5)(0x3057,64,0x3056,64,0x3038))
ctx=bind(E,'eglCreateContext',P,P,P,P,c.POINTER(I))(d,config,None,(I*1)(0x3038));assert ctx
assert bind(E,'eglMakeCurrent',U,P,P,P,P)(d,s,s,ctx)
renderer=bind(G,'glGetString',c.c_char_p,U)(0x1f01).decode()
create=bind(G,'glCreateShader',U,U);source=bind(G,'glShaderSource',None,U,I,c.POINTER(c.c_char_p),c.POINTER(I))
compileShader=bind(G,'glCompileShader',None,U);getiv=bind(G,'glGetShaderiv',None,U,U,c.POINTER(I));getlog=bind(G,'glGetShaderInfoLog',None,U,I,c.POINTER(I),c.c_char_p)
root=Path(sys.argv[1])/'SP/code/rend2/glsl';out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True);rows=[]
for name in ['lightall_fp.glsl','dlight_fp.glsl','shadowfill_fp.glsl']:
 text=(root/name).read_text()
 if name=='shadowfill_fp.glsl':body='#define USE_DEPTH\n'+text
 else:
  start=text.index('uniform samplerCube u_DlightWorldMap;');end=text.index('\nuniform samplerCube u_DlightShadowMap',start)
  body=text[start:end]+'\nvoid main(){gl_FragColor=vec4(DlightWorldVisibility(vec3(gl_FragCoord.xy,100.0)));}'
 for version in [120,130,150]:
  sh=create(0x8B30);b=c.c_char_p((f'#version {version}\n'+body).encode());source(sh,1,c.byref(b),None);compileShader(sh)
  ok=I();getiv(sh,0x8B81,c.byref(ok));buf=c.create_string_buffer(32768);getlog(sh,32768,None,buf)
  rows.append({'file':name,'version':version,'compiled':bool(ok.value),'log':buf.value.decode()})
  print(name,version,'PASS' if ok.value else 'FAIL',buf.value.decode(),flush=True)
result={'status':'PASS' if all(r['compiled'] for r in rows) else 'FAIL','renderer':renderer,'scope':'actual changed GLSL helper/producer compilation, not full visual acceptance','rows':rows}
(out/'glsl-results.json').write_text(json.dumps(result,indent=2))
assert result['status']=='PASS','GLSL compilation failed before game build'
