// DARKWOLF_ADAPTIVE_GLASS_V1; static environment, Fresnel, roughness; NO SSR.
uniform samplerCube u_CubeMap;
uniform sampler2D u_DiffuseMap;
uniform int u_AlphaTest;
uniform vec3 u_ViewOrigin;
uniform vec4 u_CubeMapInfo;
// x: user intensity, y: apparent glass opacity, z: roughness, w: 1 (reserved)
uniform vec4 u_SpecularScale;
varying vec3 v_DWGlassWorldPos;
varying vec3 v_DWGlassWorldNormal;
varying vec2 v_DWGlassTex;
// NVIDIA GLSL 150 core forbids deprecated textureCube; use texture() for 130+.
#if __VERSION__ >= 130
#define DW_GlassCubeSample(cube, direction) texture(cube, direction)
#else
#define DW_GlassCubeSample(cube, direction) textureCube(cube, direction)
#endif
void main() {
    vec3 eye = normalize(u_ViewOrigin - v_DWGlassWorldPos);
    vec3 normal = normalize(v_DWGlassWorldNormal);
    if (dot(normal, eye) < 0.0) normal = -normal;
    float ndv = clamp(dot(normal, eye), 0.0, 1.0);
    float textureAlpha = texture2D(u_DiffuseMap, v_DWGlassTex).a;
    if (u_AlphaTest == 1 && textureAlpha <= 0.0) discard;
    if (u_AlphaTest == 2 && textureAlpha >= 0.5) discard;
    if (u_AlphaTest == 3 && textureAlpha < 0.5) discard;
    // Original material alpha controls reflection on blended panes; opaque glass retains 1.0.
    float opacity = clamp(mix(u_SpecularScale.y, textureAlpha, u_SpecularScale.w), 0.0, 1.0);
    float roughness = clamp(u_SpecularScale.z, 0.0, 1.0);
    float f0 = mix(0.035, 0.14, opacity);
    float fresnel = f0 + (1.0 - f0) * pow(1.0 - ndv, 5.0);
    // V1.1: additive dielectric specular lobe, never replace transmitted
    // stained glass with a dark/black cubemap. Preserves authored colors.
    float reflectance = clamp(fresnel * u_SpecularScale.x, 0.0, 0.65);
    vec3 reflected = reflect(-eye, normal);
    // Keep local-probe parallax conservative: (probe-world_position)/radius.
    vec3 probeOffset = u_CubeMapInfo.xyz +
                       (u_ViewOrigin - v_DWGlassWorldPos) * u_CubeMapInfo.w;
    vec3 dir = normalize(reflected + 0.20 * probeOffset);
    vec3 env = DW_GlassCubeSample(u_CubeMap, dir).rgb;
    // Compatible GLSL 120 fallback: low-cost, directionally averaged rough glass.
    vec3 blurred = (DW_GlassCubeSample(u_CubeMap, normalize(dir + vec3(0.28, 0.08, -0.16))).rgb +
                    DW_GlassCubeSample(u_CubeMap, normalize(dir + vec3(-0.13, 0.23, 0.12))).rgb +
                    DW_GlassCubeSample(u_CubeMap, normalize(dir + vec3(0.09, -0.18, 0.29))).rgb +
                    env) * 0.25;
    env = mix(env, blurred, roughness * roughness);
    // Renderer uses GL_ONE, GL_ONE: black probe is a strict NO-OP.
    // Keep even a sunlit probe bounded to prevent HDR/bloom explosions.
    vec3 highlight = min(max(env, vec3(0.0)) * reflectance, vec3(0.45));
    gl_FragColor = vec4(highlight, 0.0);
}
