#!/usr/bin/env python3
"""Strict source-anchored production-only Rend2 v4.4.6 shader optimizations."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = json.loads((ROOT / 'baseline_source_manifest.json').read_text(encoding='utf-8'))

def once(source: str, old: str, new: str, label: str, count: int = 1) -> str:
    found = source.count(old)
    if found != count:
        raise RuntimeError(f'{label}: expected {count} exact anchors, found {found}')
    return source.replace(old, new)

def ssgi(s: str) -> str:
    s = once(s, '''float SsgiViewmodelMask(const vec2 uv)
{
	float rawDepth = SsgiRawDepth(uv);
	return 1.0 - smoothstep(0.285, 0.335, rawDepth);
}''', '''// DARKWOLF_V446_OPT09_SHARED_RAW_DEPTH
float SsgiViewmodelMaskFromRaw(const float rawDepth)
{
	return 1.0 - smoothstep(0.285, 0.335, rawDepth);
}
float SsgiViewmodelMask(const vec2 uv)
{
	return SsgiViewmodelMaskFromRaw(SsgiRawDepth(uv));
}''', '09 viewmodel mask')
    s = once(s, '''float SsgiSceneEntityMask(const vec2 uv)
{
	float sceneRaw = SsgiRawDepth(uv);
	float entityRaw = texture2D(u_NormalMap, uv).r;
	float hasEntity = 1.0 - smoothstep(0.9975, 0.9998, entityRaw);
	float sceneWorld = SsgiLinearDepthValue(sceneRaw) * u_ViewInfo.y;
	float entityWorld = SsgiLinearDepthValue(entityRaw) * u_ViewInfo.y;
	float visibleMatch = 1.0 - smoothstep(1.5, 14.0, abs(sceneWorld - entityWorld));
	return hasEntity * visibleMatch;
}''', '''float SsgiSceneEntityMaskFromRaw(const float sceneRaw, const float entityRaw)
{
	float hasEntity = 1.0 - smoothstep(0.9975, 0.9998, entityRaw);
	float sceneWorld = SsgiLinearDepthValue(sceneRaw) * u_ViewInfo.y;
	float entityWorld = SsgiLinearDepthValue(entityRaw) * u_ViewInfo.y;
	float visibleMatch = 1.0 - smoothstep(1.5, 14.0, abs(sceneWorld - entityWorld));
	return hasEntity * visibleMatch;
}
float SsgiSceneEntityMask(const vec2 uv)
{
	return SsgiSceneEntityMaskFromRaw(SsgiRawDepth(uv), texture2D(u_NormalMap, uv).r);
}''', '09 entity mask')
    s = once(s, '''	// Exact visible entity rejection is always active.
	if (SsgiSceneEntityMask(uv) > 0.35)
		return;
	if (SsgiViewmodelMask(uv) > 0.5)
		return;

	float sampleDepth = SsgiLinearDepth(uv);''', '''	// One raw scene depth value at this exact UV for all three consumers.
	float sceneRaw = SsgiRawDepth(uv);
	float entityRaw = texture2D(u_NormalMap, uv).r;
	if (SsgiSceneEntityMaskFromRaw(sceneRaw, entityRaw) > 0.35)
		return;
	if (SsgiViewmodelMaskFromRaw(sceneRaw) > 0.5)
		return;

	float sampleDepth = SsgiLinearDepthValue(sceneRaw);''', '09 accumulate depth reuse')
    s = once(s, '	const vec3 centerColor,\n	inout vec3 sumColor,', '	const float centerLuma,\n	inout vec3 sumColor,', '09 accumulate signature')
    s = once(s, '	float centerLuma = SsgiLuma(centerColor);\n', '', '09 repeated center luma')
    s = once(s, '	vec3 centerColor = texture2D(u_ScreenImageMap, var_ScreenTex).rgb;\n', '	vec3 centerColor = texture2D(u_ScreenImageMap, var_ScreenTex).rgb;\n	float centerLuma = SsgiLuma(centerColor);\n', '09 center luma once')
    s = once(s, 'maskTexel, centerColor, sumColor, accepted);', 'maskTexel, centerLuma, sumColor, accepted);', '09 accumulation calls', 12)
    return s

def fire_local(s: str) -> str:
    for n, vec, width, weight in [('core', 'coreXY', 'coreWidth', '6.5'),
                                   ('body', 'bodyXY', 'bodyWidth', '4.6'),
                                   ('halo', 'haloXY', 'haloWidth', '3.1')]:
        s = once(s, f'    float {n}R = length({vec}) / {width};\n    float {n}Radial = exp(-{weight} * {n}R * {n}R);',
                 f'    float {n}R2 = dot({vec}, {vec}) / ({width} * {width});\n    float {n}Radial = exp(-{weight} * {n}R2);',
                 f'06 {n} gaussian')
    s = once(s, '''    float physicalLightRadius = ((mode >= 5 && mode <= 8) && u_DlightInfo.z > 1.0) ? u_DlightInfo.z : lightRadius;
    float energyGain''', '''    float physicalLightRadius = ((mode >= 5 && mode <= 8) && u_DlightInfo.z > 1.0) ? u_DlightInfo.z : lightRadius;
    // DARKWOLF_V446_OPT04_LOCALVOL_LOOP_INVARIANTS
    float physicalLightRadiusSquared = physicalLightRadius * physicalLightRadius;
    vec3 spotlightAxis = vec3(0.0);
    float cosOuter = 0.0;
    float cosInner = 0.0;
    if (mode == 4)
    {
        spotlightAxis = normalize(u_DlightInfo.xyz);
        cosOuter = u_DlightInfo.w;
        cosInner = max(u_BaseColor.z, cosOuter + 0.0001);
    }
    float energyGain''', '04 light invariants')
    s = once(s, 'localLightAttenuation(distanceSquared, physicalLightRadius * physicalLightRadius)',
             'localLightAttenuation(distanceSquared, physicalLightRadiusSquared)', '04 radius squared')
    s = once(s, '''            float coneDot = dot(fromLight, normalize(u_DlightInfo.xyz));
            float cosOuter = u_DlightInfo.w;
            float cosInner = max(u_BaseColor.z, cosOuter + 0.0001);
            cone = smoothstep(cosOuter, cosInner, coneDot);''', '''            float coneDot = dot(fromLight, spotlightAxis);
            cone = smoothstep(cosOuter, cosInner, coneDot);''', '04 spotlight invariants')
    s = once(s, 'float fireShapeMask(vec3 worldPos, vec3 lightOrigin, float lightRadius)',
             '// DARKWOLF_V446_OPT06_FIRE_GAUSSIAN_SQRT_ELIMINATION\nfloat fireShapeMask(vec3 worldPos, vec3 lightOrigin, float lightRadius)', '06 marker')
    return s

def sun(s: str) -> str:
    s = once(s, '''    float jitter = (interleavedGradientNoise(gl_FragCoord.xy) - 0.5) * jitterAmount;
    float integrated = 0.0;''', '''    float jitter = (interleavedGradientNoise(gl_FragCoord.xy) - 0.5) * jitterAmount;
    // DARKWOLF_V446_OPT02_SUN_TRANSMITTANCE_RECURRENCE
    // jitterAmount <= 0.5 => |jitter| <= 0.25: all sample centres remain in [0,maxDepth].
    float transmittance = exp(-density * (worldStep * (0.5 + jitter)));
    float transmittanceDecay = exp(-density * worldStep);
    float integrated = 0.0;''', '02 sun transmittance precompute')
    s = once(s, '''        float worldDistance = viewRayLength * sampleDepth;
        vec3 worldPos = u_ViewOrigin + var_ViewDir * sampleDepth;
        float visibility = sunVisibility(worldPos, pcfMode);
        float transmittance = exp(-density * worldDistance);
        integrated += visibility * transmittance * density * worldStep;''', '''        vec3 worldPos = u_ViewOrigin + var_ViewDir * sampleDepth;
        float visibility = sunVisibility(worldPos, pcfMode);
        integrated += visibility * transmittance * density * worldStep;
        transmittance *= transmittanceDecay;''', '02 sun loop')
    return s

def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: apply_targeted_shader_optimizations.py <exact reconstructed engine> <evidence dir>')
    engine = Path(sys.argv[1]).resolve()
    evidence = Path(sys.argv[2]).resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    transforms = {
        'SP/code/rend2/glsl/ssgi_fp.glsl': ssgi,
        'SP/code/rend2/glsl/volumetriclocal_fp.glsl': fire_local,
        'SP/code/rend2/glsl/volumetricsun_fp.glsl': sun,
    }
    # Validate every original hash and anchor before writing any files.
    staged, audit = {}, {}
    for rel, transform in transforms.items():
        original = (engine / rel).read_bytes()
        baseline = MANIFEST['baseline_source_files'][rel]
        got = hashlib.sha256(original).hexdigest()
        if got != baseline:
            raise RuntimeError(f'REFUSE UNVERIFIED V446 GLSL {rel}: {got} != {baseline}')
        changed = transform(original.decode('utf-8')).encode('utf-8')
        if changed == original:
            raise RuntimeError(f'NO_CHANGE {rel}')
        staged[rel] = changed
        audit[rel] = {'baseline_sha256': got, 'optimized_sha256': hashlib.sha256(changed).hexdigest()}
    for rel, data in staged.items():
        (engine / rel).write_bytes(data)
    (evidence / 'shader-source-audit.json').write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')
    print('TARGETED_V446_SHADER_PATCH_PASS', ', '.join(transforms))

if __name__ == '__main__':
    main()
