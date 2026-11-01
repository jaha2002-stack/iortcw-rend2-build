// DARKWOLF_ADAPTIVE_GLASS_V1; static environment, Fresnel, roughness; NO SSR.
uniform samplerCube u_CubeMap;
uniform vec3 u_ViewOrigin;
uniform vec4 u_CubeMapInfo;
// x: user intensity, y: apparent glass opacity, z: roughness, w: 1 (reserved)
uniform vec4 u_DWGlassParams;
varying vec3 v_DWGlassWorldPos;
varying vec3 v_DWGlassWorldNormal;
void main() {
    vec3 eye = normalize(u_ViewOrigin - v_DWGlassWorldPos);
    vec3 normal = normalize(v_DWGlassWorldNormal);
    if (dot(normal, eye) < 0.0) normal = -normal;
    float ndv = clamp(dot(normal, eye), 0.0, 1.0);
    float opacity = clamp(u_DWGlassParams.y, 0.0, 1.0);
    float roughness = clamp(u_DWGlassParams.z, 0.0, 1.0);
    float f0 = mix(0.035, 0.14, opacity);
    float fresnel = f0 + (1.0 - f0) * pow(1.0 - ndv, 5.0);
    float blendAlpha = clamp(fresnel * u_DWGlassParams.x, 0.0, 0.82);
    vec3 reflected = reflect(-eye, normal);
    // Keep local-probe parallax conservative: (probe-world_position)/radius.
    vec3 probeOffset = u_CubeMapInfo.xyz +
                       (u_ViewOrigin - v_DWGlassWorldPos) * u_CubeMapInfo.w;
    vec3 dir = normalize(reflected + 0.20 * probeOffset);
    vec3 env = textureCube(u_CubeMap, dir).rgb;
    // Compatible GLSL 120 fallback: low-cost, directionally averaged rough glass.
    vec3 blurred = (textureCube(u_CubeMap, normalize(dir + vec3(0.28, 0.08, -0.16))).rgb +
                    textureCube(u_CubeMap, normalize(dir + vec3(-0.13, 0.23, 0.12))).rgb +
                    textureCube(u_CubeMap, normalize(dir + vec3(0.09, -0.18, 0.29))).rgb +
                    env) * 0.25;
    env = mix(env, blurred, roughness * roughness);
    gl_FragColor = vec4(max(env, vec3(0.0)), blendAlpha);
}
