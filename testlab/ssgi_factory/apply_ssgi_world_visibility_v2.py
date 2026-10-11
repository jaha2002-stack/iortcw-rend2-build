#!/usr/bin/env python3
"""Second/final gameplay evaluation: physically grounded hemisphere acceptance.

Run after apply_ssgi_world_visibility_v1.py. Preserve:
 mode 0 = exact legacy Fix3
 mode 1 = unchanged 3-tap ray-depth visibility
 mode 2 = ray + two-sided normal SIGN test, no global cosine attenuation
 mode 3 = ray + original strict cosine attenuation (control)
No camera/material hardcoded screen ROI, no change to light budgets or GI strength.
"""
from pathlib import Path
import re, sys
root=Path(sys.argv[1] if len(sys.argv)>1 else "source")/"SP/code/rend2"
shader=root/"glsl/ssgi_fp.glsl"
s=shader.read_text()
pattern=r'\bgeometryWeight\s*\*=\s*emitFacing\s*\*\s*receiveFacing\s*;'
assert len(re.findall(pattern,s))==1, "Expected one Lambert attenuation statement"
new="""// SSGI_GEOMETRY_V2: reject impossible donor/receiver hemispheres.
\t\t\t// Do NOT multiply the brightness of a valid donor by two tiny
\t\t\t// screen-space normal cosines: prior game test lost ~92% of GI.
\t\t\tif (emitFacing<=0.0 || receiveFacing<=0.0) return;
\t\t\t// Mode 3 deliberately reproduces v1 strict cosine control.
\t\t\tif (u_ViewLeft.z>2.5) geometryWeight*=emitFacing*receiveFacing;"""
shader.write_text(re.sub(pattern,new,s))
init=root/"tr_init.c";s=init.read_text()
a='ri.Cvar_CheckRange( r_ssgiGeometryVisibility, 0, 2, qtrue );'
assert s.count(a)==1, "Geometry mode range anchor mismatch"
init.write_text(s.replace(a,'ri.Cvar_CheckRange( r_ssgiGeometryVisibility, 0, 3, qtrue ); // 2=hemisphere 3=strict_cosine'))
backend=root/"tr_backend.c";s=backend.read_text()
a=r'brightfix=%d frame=%d\n",'
n=r'brightfix=%d geom=%d frame=%d\n",'
assert s.count(a)==1, "SSGITRACE format anchor mismatch"
s=s.replace(a,n)
a='r_ssgiBrightSourceFix ? r_ssgiBrightSourceFix->integer : 1,\n\t\t\t\t\ttr.frameCount);'
n='r_ssgiBrightSourceFix ? r_ssgiBrightSourceFix->integer : 1,\n\t\t\t\t\tr_ssgiGeometryVisibility ? r_ssgiGeometryVisibility->integer : 0,\n\t\t\t\t\ttr.frameCount);'
assert s.count(a)==1, "SSGITRACE argument anchor mismatch"
backend.write_text(s.replace(a,n))
print("SSGI_GEOMETRY_V2_STATIC_PASS hemisphere_no_cos_dimming=1 modes=0,1,2,3 trace=geom")
