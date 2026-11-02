// DARKWOLF_ADAPTIVE_GLASS_V2_METAL_IBL: use existing metal cubemap reflection.
uniform samplerCube u_CubeMap;
uniform sampler2D u_DiffuseMap;
uniform int u_AlphaTest;
uniform vec3 u_ViewOrigin;
uniform vec4 u_CubeMapInfo;
// x: reflection strength; y: opacity; z: roughness; w: composite window atlas.
uniform vec4 u_SpecularScale;
varying vec3 v_DWGlassWorldPos;
varying vec3 v_DWGlassWorldNormal;
varying vec2 v_DWGlassTex;

// Source-shared with Rend2 metallic lightall path: mipmapped cubemap
// and EnvironmentBRDF shape. Legacy GLSL fallbacks compile independently.
#if __VERSION__ >= 150
#define DW_GlassMetalCube(cube, direction, lod) textureLod(cube, direction, lod)
#elif __VERSION__ >= 130
#define DW_GlassMetalCube(cube, direction, lod) texture(cube, direction)
#else
#define DW_GlassMetalCube(cube, direction, lod) textureCube(cube, direction)
#endif
vec3 DW_GlassEnvironmentBRDF(float roughness, float NE, vec3 specular)
{
    float v = 1.0 - max(roughness, NE);
    v *= v * v;
    return vec3(v) + specular;
}
void main()
{
    vec3 E = normalize(u_ViewOrigin - v_DWGlassWorldPos);
    vec3 N = normalize(v_DWGlassWorldNormal);
    if (dot(N, E) < 0.0) N = -N;
    float NE = clamp(dot(N, E), 0.0, 1.0);
    float alpha = texture2D(u_DiffuseMap, v_DWGlassTex).a;
    if (u_AlphaTest == 1 && alpha <= 0.0) discard;
    if (u_AlphaTest == 2 && alpha >= 0.5) discard;
    if (u_AlphaTest == 3 && alpha < 0.5) discard;

    float rough = clamp(u_SpecularScale.z, 0.035, 0.95);
    float opacity = clamp(u_SpecularScale.y, 0.0, 1.0);
    vec3 specularF0 = vec3(mix(0.055, 0.19, opacity));
    vec3 reflectance = DW_GlassEnvironmentBRDF(rough, NE, specularF0);

    // Exact existing-metal directional cubemap + parallax recipe.
    vec3 R = reflect(-E, N);
    vec3 parallax = u_CubeMapInfo.xyz + u_CubeMapInfo.w * E;
    vec3 direction = normalize(R + parallax);
    vec3 environment = max(DW_GlassMetalCube(u_CubeMap, direction, 8.0 * rough).rgb, vec3(0.0));

    // Composite window texture can contain a metal frame. Reflect chiefly
    // its translucent texels. A separate pure glass shader remains unrestricted.
    float mask = 1.0;
    if (u_SpecularScale.w > 0.5)
        mask = max(clamp((1.0 - alpha) * 3.2, 0.0, 1.0), 0.05);

    // Add the captured-world IBL (not undirected bloom), never darken old art.
    vec3 reflection = environment * reflectance * mask * (2.0 * u_SpecularScale.x);
    gl_FragColor = vec4(min(reflection, vec3(0.85)), 0.0);
}
