#!/usr/bin/env python3
"""Production-scoped SSGI fire/lamp emitter-receiver guard plus pure-lightmap isolation.

No change to sun CSM, world/dlight shadows, bloom, tone map, CAS/A2C/LUT,
volumetrics, geometry, entity masks or SSGI strength/radius.
"""
from pathlib import Path
import hashlib,json,sys

MARK="DARKWOLF_SSGI_EMITTER_RECEIVER_CORE_GUARD_V1"
def change(p,old,new,label):
    s=p.read_text()
    if s.count(old)!=1:raise RuntimeError(f"{label} original anchor count {s.count(old)} != 1")
    if MARK in s:raise RuntimeError(f"{label} already applied")
    p.write_text(s.replace(old,new,1))
    return {"file":str(p),"before_sha256":hashlib.sha256(s.encode()).hexdigest(),
            "after_sha256":hashlib.sha256(p.read_bytes()).hexdigest()}

def main(root):
    base=root/"SP/code/rend2"
    shader=base/"glsl/ssgi_fp.glsl"
    old="""	bounce *= edgeStability;
	bounce = min(bounce, vec3(clamp(u_Color.z, 0.0, 1.0)));"""
    new="""	bounce *= edgeStability;
	// DARKWOLF_SSGI_EMITTER_RECEIVER_CORE_GUARD_V1: prevent a bright
	// bulb, fire or torch surface from receiving its own quarter-res GI.
	// Preserve the direct emissive surface, volumetrics, bloom and world light.
	// Mode 2 remains the historical Factory-tested donor rejection.
	if (u_ViewInfo.w >= 2.5)
	{
		float corePeak = max(centerColor.r, max(centerColor.g, centerColor.b));
		float coreMetric = max(centerLuma, 0.75 * corePeak);
		float brightCore = smoothstep(0.72, 1.35, coreMetric);
		// Retain indirect bounce on the nonemissive surroundings.
		bounce *= 1.0 - 0.98 * brightCore;
	}
	bounce = min(bounce, vec3(clamp(u_Color.z, 0.0, 1.0)));"""
    reports=[change(shader,old,new,"ssgi bright receiver guard")]
    init=base/"tr_init.c"
    s=init.read_text()
    a='r_ssgiBrightSourceFix = ri.Cvar_Get( "r_ssgiBrightSourceFix", "2", CVAR_ARCHIVE );'
    b='r_ssgiBrightSourceFix = ri.Cvar_Get( "r_ssgiBrightSourceFix", "3", CVAR_ARCHIVE );'
    assert s.count(a)==1 and s.count('ri.Cvar_CheckRange( r_ssgiBrightSourceFix, 0, 2, qtrue );')==1
    assert MARK not in s
    init.write_text(s.replace(a,b,1).replace(
      'ri.Cvar_CheckRange( r_ssgiBrightSourceFix, 0, 2, qtrue );',
      '// '+MARK+' uses mode 3; modes 0..2 are unchanged.\n\tri.Cvar_CheckRange( r_ssgiBrightSourceFix, 0, 3, qtrue );',1))
    reports.append({"file":str(init),"before_sha256":hashlib.sha256(s.encode()).hexdigest(),
      "after_sha256":hashlib.sha256(init.read_bytes()).hexdigest()})
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"crypt1-ssgi-lightmap-isolation"))
    from apply import main as lightmap_guard
    lightmap_guard(root)
    reports.append({"file":str(base/"tr_backend.c"),"scope":"diagnostic r_lightmap 1 only"})
    print("SSGI_FIRE_SOURCE_GUARD_AND_LIGHTMAP_CLEAN_PASS",json.dumps(reports),flush=True)

if __name__=="__main__":
    main(Path(sys.argv[1]))
