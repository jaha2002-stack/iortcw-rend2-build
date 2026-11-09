#!/usr/bin/env python3
from pathlib import Path
import argparse, json

ap=argparse.ArgumentParser()
ap.add_argument("source")
ap.add_argument("--proof")
args=ap.parse_args()

root=Path(args.source)/"SP/code/rend2"
changed=[]

def rw(rel):
    p=root/rel
    return p,p.read_text()

def one(s,old,new,label):
    n=s.count(old)
    if n!=1:
        raise SystemExit(f"{label}: expected 1 anchor, found {n}")
    return s.replace(old,new,1)

# ---------------------------------------------------------------------------
# Cvars: quality/safety controls. All are latched because they affect GLSL.
# ---------------------------------------------------------------------------
p,s=rw("tr_local.h")
s=one(s,
'''extern  cvar_t  *r_parallaxMapping;
extern  cvar_t  *r_parallaxMapOffset;
extern  cvar_t  *r_parallaxMapShadows;
''',
'''extern  cvar_t  *r_parallaxMapping;
extern  cvar_t  *r_parallaxMapOffset;
extern  cvar_t  *r_parallaxMapShadows;
extern  cvar_t  *r_pomMinLayers;
extern  cvar_t  *r_pomMaxLayers;
extern  cvar_t  *r_pomRefineSteps;
extern  cvar_t  *r_pomMaxOffset;
extern  cvar_t  *r_pomDepthScale;
extern  cvar_t  *r_pomShadowStrength;
''',"POM cvar externs")
p.write_text(s); changed.append("SP/code/rend2/tr_local.h")

p,s=rw("tr_init.c")
s=one(s,
'''cvar_t  *r_parallaxMapping;
cvar_t  *r_parallaxMapOffset;
cvar_t  *r_parallaxMapShadows;
''',
'''cvar_t  *r_parallaxMapping;
cvar_t  *r_parallaxMapOffset;
cvar_t  *r_parallaxMapShadows;
cvar_t  *r_pomMinLayers;
cvar_t  *r_pomMaxLayers;
cvar_t  *r_pomRefineSteps;
cvar_t  *r_pomMaxOffset;
cvar_t  *r_pomDepthScale;
cvar_t  *r_pomShadowStrength;
''',"POM cvar globals")

s=one(s,
'''	r_parallaxMapping = ri.Cvar_Get( "r_parallaxMapping", "0", CVAR_ARCHIVE | CVAR_LATCH );
	r_parallaxMapOffset = ri.Cvar_Get( "r_parallaxMapOffset", "0", CVAR_ARCHIVE | CVAR_LATCH );
	r_parallaxMapShadows = ri.Cvar_Get( "r_parallaxMapShadows", "0", CVAR_ARCHIVE | CVAR_LATCH );
''',
'''	r_parallaxMapping = ri.Cvar_Get( "r_parallaxMapping", "0", CVAR_ARCHIVE | CVAR_LATCH );
	r_parallaxMapOffset = ri.Cvar_Get( "r_parallaxMapOffset", "0", CVAR_ARCHIVE | CVAR_LATCH );
	r_parallaxMapShadows = ri.Cvar_Get( "r_parallaxMapShadows", "0", CVAR_ARCHIVE | CVAR_LATCH );
	r_pomMinLayers = ri.Cvar_Get( "r_pomMinLayers", "20", CVAR_ARCHIVE | CVAR_LATCH );
	r_pomMaxLayers = ri.Cvar_Get( "r_pomMaxLayers", "56", CVAR_ARCHIVE | CVAR_LATCH );
	r_pomRefineSteps = ri.Cvar_Get( "r_pomRefineSteps", "5", CVAR_ARCHIVE | CVAR_LATCH );
	r_pomMaxOffset = ri.Cvar_Get( "r_pomMaxOffset", "0.080", CVAR_ARCHIVE | CVAR_LATCH );
	r_pomDepthScale = ri.Cvar_Get( "r_pomDepthScale", "1.0", CVAR_ARCHIVE | CVAR_LATCH );
	r_pomShadowStrength = ri.Cvar_Get( "r_pomShadowStrength", "0.65", CVAR_ARCHIVE | CVAR_LATCH );
''',"POM cvar registration")
p.write_text(s); changed.append("SP/code/rend2/tr_init.c")

# ---------------------------------------------------------------------------
# GLSL defines. PBR V3.2 POM is opt-in: r_pbr>=3 and r_parallaxMapping>1.
# ---------------------------------------------------------------------------
p,s=rw("tr_glsl.c")
old='''				if ((i & LIGHTDEF_USE_PARALLAXMAP) && !(i & LIGHTDEF_ENTITY_VERTEX_ANIMATION) && !(i & LIGHTDEF_ENTITY_BONE_ANIMATION) && r_parallaxMapping->integer)
				{
					Q_strcat(extradefines, 1024, "#define USE_PARALLAXMAP\\n");
					if (r_parallaxMapping->integer > 1)
						Q_strcat(extradefines, 1024, "#define USE_RELIEFMAP\\n");

					if (r_parallaxMapShadows->integer)
						Q_strcat(extradefines, 1024, "#define USE_PARALLAXMAP_SHADOWS\\n");

					Q_strcat(extradefines, 1024, va("#define r_parallaxMapOffset %f\\n", r_parallaxMapOffset->value));
				}
'''
new='''				if ((i & LIGHTDEF_USE_PARALLAXMAP) && !(i & LIGHTDEF_ENTITY_VERTEX_ANIMATION) && !(i & LIGHTDEF_ENTITY_BONE_ANIMATION) && r_parallaxMapping->integer)
				{
					Q_strcat(extradefines, 1024, "#define USE_PARALLAXMAP\\n");
					if (r_parallaxMapping->integer > 1)
					{
						Q_strcat(extradefines, 1024, "#define USE_RELIEFMAP\\n");
						if (r_pbr->integer >= 3)
						{
							Q_strcat(extradefines, 1024, "#define USE_PBR_PHYSICAL_RELIEF_V32\\n");
							Q_strcat(extradefines, 1024, va("#define DW_POM_MIN_LAYERS %d\\n", CLAMP(r_pomMinLayers->integer, 8, 48)));
							Q_strcat(extradefines, 1024, va("#define DW_POM_MAX_LAYERS %d\\n", CLAMP(r_pomMaxLayers->integer, 16, 64)));
							Q_strcat(extradefines, 1024, va("#define DW_POM_REFINE_STEPS %d\\n", CLAMP(r_pomRefineSteps->integer, 2, 8)));
							Q_strcat(extradefines, 1024, va("#define DW_POM_MAX_OFFSET %f\\n", CLAMP(r_pomMaxOffset->value, 0.01f, 0.20f)));
							Q_strcat(extradefines, 1024, va("#define DW_POM_DEPTH_SCALE %f\\n", CLAMP(r_pomDepthScale->value, 0.25f, 2.0f)));
							Q_strcat(extradefines, 1024, va("#define DW_POM_SHADOW_STRENGTH %f\\n", CLAMP(r_pomShadowStrength->value, 0.0f, 1.0f)));
						}
					}

					if (r_parallaxMapShadows->integer)
						Q_strcat(extradefines, 1024, "#define USE_PARALLAXMAP_SHADOWS\\n");

					Q_strcat(extradefines, 1024, va("#define r_parallaxMapOffset %f\\n", r_parallaxMapOffset->value));
				}
'''
s=one(s,old,new,"POM GLSL defines")
p.write_text(s); changed.append("SP/code/rend2/tr_glsl.c")

# ---------------------------------------------------------------------------
# Shader: adaptive POM + binary refinement + safe UV clamp + optional shadow.
# Legacy function remains for r_pbr<3 / r_parallaxMapping1.
# ---------------------------------------------------------------------------
p,s=rw("glsl/lightall_fp.glsl")
anchor='''float LightRay(vec2 dp, vec2 ds, sampler2D normalMap)
{
'''
pom=r'''
#if defined(USE_PBR_PHYSICAL_RELIEF_V32)
#define DW_POM_LOOP_CAP 64
#define DW_POM_REFINE_CAP 8
#define DW_POM_SHADOW_CAP 24

vec2 DW_ClampPomVector(vec2 v)
{
	float lenV = length(v);
	if (lenV > DW_POM_MAX_OFFSET)
		v *= DW_POM_MAX_OFFSET / max(lenV, 0.000001);
	return v;
}

vec2 DW_ParallaxOcclusionMap(vec2 baseUv, vec3 viewTS, sampler2D normalMap, out float hitDepth)
{
	float vz = max(abs(viewTS.z), 0.12);
	float NoV = clamp(vz, 0.0, 1.0);
	float layerCountF = mix(float(DW_POM_MAX_LAYERS), float(DW_POM_MIN_LAYERS), NoV);
	int layerCount = int(clamp(layerCountF, float(DW_POM_MIN_LAYERS), float(DW_POM_MAX_LAYERS)) + 0.5);

	float materialDepth = max(u_NormalScale.a * DW_POM_DEPTH_SCALE, 0.0001);
	vec2 totalOffset = DW_ClampPomVector((-viewTS.xy / vz) * materialDepth);
	vec2 deltaUv = totalOffset / float(layerCount);
	float deltaDepth = 1.0 / float(layerCount);

	vec2 currentUv = baseUv;
	vec2 previousUv = baseUv;
	float currentDepth = 0.0;
	float previousDepth = 0.0;
	float currentMapDepth = SampleDepth(normalMap, currentUv);
	float previousMapDepth = currentMapDepth;

	for (int i = 0; i < DW_POM_LOOP_CAP; ++i)
	{
		if (i >= layerCount || currentDepth >= currentMapDepth)
			break;

		previousUv = currentUv;
		previousDepth = currentDepth;
		previousMapDepth = currentMapDepth;

		currentUv += deltaUv;
		currentDepth += deltaDepth;
		currentMapDepth = SampleDepth(normalMap, currentUv);
	}

	// If the first sample already lies inside the surface, keep the base UV.
	if (currentDepth <= 0.000001)
	{
		hitDepth = 0.0;
		return baseUv;
	}

	vec2 lowUv = previousUv;
	vec2 highUv = currentUv;
	float lowDepth = previousDepth;
	float highDepth = currentDepth;

	// Binary refine the bracket around the first heightfield crossing.
	for (int i = 0; i < DW_POM_REFINE_CAP; ++i)
	{
		if (i >= DW_POM_REFINE_STEPS)
			break;

		vec2 midUv = (lowUv + highUv) * 0.5;
		float midDepth = (lowDepth + highDepth) * 0.5;
		float mapDepth = SampleDepth(normalMap, midUv);

		if (midDepth >= mapDepth)
		{
			highUv = midUv;
			highDepth = midDepth;
		}
		else
		{
			lowUv = midUv;
			lowDepth = midDepth;
		}
	}

	// One secant-style interpolation inside the refined bracket reduces stair-step
	// swimming without adding more texture fetches.
	float lowMap = SampleDepth(normalMap, lowUv);
	float highMap = SampleDepth(normalMap, highUv);
	float fLow = lowMap - lowDepth;
	float fHigh = highMap - highDepth;
	float denom = fLow - fHigh;
	float w = abs(denom) > 0.000001 ? clamp(fLow / denom, 0.0, 1.0) : 0.5;

	hitDepth = mix(lowDepth, highDepth, w);
	return mix(lowUv, highUv, w);
}

float DW_PomSelfShadow(vec2 uv, float hitDepth, vec3 lightTS, sampler2D normalMap)
{
	if (hitDepth <= 0.001 || lightTS.z <= 0.08)
		return 1.0;

	float lz = max(lightTS.z, 0.12);
	float materialDepth = max(u_NormalScale.a * DW_POM_DEPTH_SCALE, 0.0001);
	vec2 totalOffset = DW_ClampPomVector((lightTS.xy / lz) * materialDepth);

	// More steps at grazing light angles, bounded by a compile-time cap.
	float grazing = 1.0 - clamp(lightTS.z, 0.0, 1.0);
	int steps = int(mix(8.0, 20.0, grazing) + 0.5);
	float visibility = 1.0;
	const float bias = 0.012;

	for (int i = 1; i <= DW_POM_SHADOW_CAP; ++i)
	{
		if (i > steps)
			break;

		float t = float(i) / float(steps);
		vec2 probeUv = uv + totalOffset * t;
		float rayDepth = hitDepth * (1.0 - t);
		float mapDepth = SampleDepth(normalMap, probeUv);

		if (mapDepth + bias < rayDepth)
		{
			visibility = 1.0 - DW_POM_SHADOW_STRENGTH;
			break;
		}
	}

	return visibility;
}
#endif

'''
if anchor not in s:
    raise SystemExit("POM function anchor missing")
s=s.replace(anchor,pom+anchor,1)

old='''#if defined(USE_PARALLAXMAP)
	vec3 offsetDir = E * tangentToWorld;

	offsetDir.xy *= -u_NormalScale.a / offsetDir.z;

	texCoords += offsetDir.xy * RayIntersectDisplaceMap(texCoords, offsetDir.xy, u_NormalMap);
#endif
'''
new='''#if defined(USE_PARALLAXMAP)
  #if defined(USE_PBR_PHYSICAL_RELIEF_V32)
	vec3 offsetDir = E * tangentToWorld;
	float dwPomHitDepth = 0.0;
	texCoords = DW_ParallaxOcclusionMap(texCoords, offsetDir, u_NormalMap, dwPomHitDepth);
  #else
	vec3 offsetDir = E * tangentToWorld;
	offsetDir.xy *= -u_NormalScale.a / offsetDir.z;
	texCoords += offsetDir.xy * RayIntersectDisplaceMap(texCoords, offsetDir.xy, u_NormalMap);
  #endif
#endif
'''
s=one(s,old,new,"main POM displacement")

old='''  #if defined(USE_PARALLAXMAP) && defined(USE_PARALLAXMAP_SHADOWS)
	offsetDir = L * tangentToWorld;
	offsetDir.xy *= u_NormalScale.a / offsetDir.z;
	lightColor *= LightRay(texCoords, offsetDir.xy, u_NormalMap);
  #endif
'''
new='''  #if defined(USE_PARALLAXMAP) && defined(USE_PARALLAXMAP_SHADOWS)
    #if defined(USE_PBR_PHYSICAL_RELIEF_V32)
	offsetDir = L * tangentToWorld;
	lightColor *= DW_PomSelfShadow(texCoords, dwPomHitDepth, offsetDir, u_NormalMap);
    #else
	offsetDir = L * tangentToWorld;
	offsetDir.xy *= u_NormalScale.a / offsetDir.z;
	lightColor *= LightRay(texCoords, offsetDir.xy, u_NormalMap);
    #endif
  #endif
'''
s=one(s,old,new,"primary POM self shadow")

old='''  #if defined(USE_PARALLAXMAP) && defined(USE_PARALLAXMAP_SHADOWS)
	offsetDir = L2 * tangentToWorld;
	offsetDir.xy *= u_NormalScale.a / offsetDir.z;
	lightColor *= LightRay(texCoords, offsetDir.xy, u_NormalMap);
  #endif
'''
new='''  #if defined(USE_PARALLAXMAP) && defined(USE_PARALLAXMAP_SHADOWS)
    #if defined(USE_PBR_PHYSICAL_RELIEF_V32)
	offsetDir = L2 * tangentToWorld;
	lightColor *= DW_PomSelfShadow(texCoords, dwPomHitDepth, offsetDir, u_NormalMap);
    #else
	offsetDir = L2 * tangentToWorld;
	offsetDir.xy *= u_NormalScale.a / offsetDir.z;
	lightColor *= LightRay(texCoords, offsetDir.xy, u_NormalMap);
    #endif
  #endif
'''
s=one(s,old,new,"secondary POM self shadow")

p.write_text(s); changed.append("SP/code/rend2/glsl/lightall_fp.glsl")

proof={
 "base":"PBR V3.1 True GGX IBL",
 "feature":"PBR V3.2 Physical Relief / adaptive POM",
 "activation":"r_pbr>=3 and r_parallaxMapping>1 on a parallax-capable material",
 "algorithm":{
   "adaptive_layers":"20..56 by view angle (cvar controlled, hard cap 64)",
   "refinement":"5 binary steps default + final secant interpolation",
   "uv_safety":"max displacement clamp 0.080 default",
   "depth":"per-material u_NormalScale.a from parallaxDepth, global multiplier 1.0",
   "self_shadow":"optional r_parallaxMapShadows, 8..20 heightfield ray steps"
 },
 "legacy":"r_parallaxMapping 1 and r_pbr<3 keep previous path",
 "changed_files":changed
}
if args.proof:
    q=Path(args.proof); q.parent.mkdir(parents=True,exist_ok=True); q.write_text(json.dumps(proof,indent=2)+"\n")
print(json.dumps(proof,indent=2))
